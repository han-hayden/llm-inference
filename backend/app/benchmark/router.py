"""
Benchmark / load testing module.
Replays recorded QA pairs against target service with configurable concurrency.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import get_db
from ..models.schemas import Task
from ..collect.data_writer import PerformanceDataWriter

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])

# In-memory tracking of running benchmarks
_running: dict = {}


class BenchmarkStartRequest(BaseModel):
    name: str
    source_task_id: str
    concurrency: int = 1
    replay_mode: str = "sequential"  # sequential | concurrent
    target_host: str
    target_port: int
    delay_ms: int = 100
    timeout_s: int = 60


class BenchmarkProgress(BaseModel):
    task_id: str
    total: int
    completed: int
    status: str
    elapsed_s: float = 0


@router.post("/start")
async def start_benchmark(req: BenchmarkStartRequest, db: Session = Depends(get_db)):
    # Load QA pairs from source task
    source = db.query(Task).filter(Task.id == req.source_task_id).first()
    if not source or not source.data_dir:
        raise HTTPException(status_code=404, detail="Source task not found")

    source_dir = Path(source.data_dir)
    qa_json = source_dir / "qa_pairs.json"
    if not qa_json.exists():
        # Try reading CSV
        qa_csvs = sorted(source_dir.glob("qa_pairs_*.csv"))
        if not qa_csvs:
            raise HTTPException(status_code=404, detail="No QA data in source task")
        dfs = [pd.read_csv(f) for f in qa_csvs]
        qa_df = pd.concat(dfs, ignore_index=True)
        qa_records = qa_df.to_dict("records")
    else:
        with open(qa_json, "r", encoding="utf-8") as f:
            qa_records = json.load(f)

    # Create benchmark task
    counter = db.query(Task).filter(Task.type == "benchmark").count() + 1
    task_id = f"benchmark_{counter:03d}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = settings.DATA_DIR / f"{task_id}_{timestamp}"

    task = Task(
        id=task_id,
        name=req.name,
        type="benchmark",
        status="running",
        config=json.dumps({
            "source_task_id": req.source_task_id,
            "concurrency": req.concurrency,
            "replay_mode": req.replay_mode,
            "delay_ms": req.delay_ms,
            "timeout_s": req.timeout_s,
        }),
        data_dir=str(data_dir),
        target_host=req.target_host,
        target_port=req.target_port,
        record_count=0,
    )
    db.add(task)
    db.commit()

    # Start benchmark in background
    progress = {"total": len(qa_records), "completed": 0, "status": "running", "start_time": time.time()}
    _running[task_id] = progress

    asyncio.create_task(
        _run_benchmark(task_id, qa_records, req, data_dir, progress)
    )

    return {"task_id": task_id, "data_dir": str(data_dir), "total": len(qa_records)}


async def _run_benchmark(task_id, qa_records, req, data_dir, progress):
    writer = PerformanceDataWriter(task_id, data_dir)
    writer.start_periodic_flush()

    timeout = aiohttp.ClientTimeout(total=req.timeout_s)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        target_url = f"http://{req.target_host}:{req.target_port}/v1/chat/completions"
        delay = req.delay_ms / 1000.0

        if req.replay_mode == "sequential":
            for rec in qa_records:
                stat = await _send_one(session, target_url, rec, req.timeout_s)
                await writer.add_record(stat)
                progress["completed"] += 1
                await asyncio.sleep(delay)
        else:
            # Concurrent mode
            sem = asyncio.Semaphore(req.concurrency)

            async def bounded(rec):
                async with sem:
                    stat = await _send_one(session, target_url, rec, req.timeout_s)
                    await writer.add_record(stat)
                    progress["completed"] += 1

            tasks = [bounded(rec) for rec in qa_records]
            await asyncio.gather(*tasks, return_exceptions=True)

    await writer.finalize()
    progress["status"] = "completed"

    # Update DB
    from ..models.database import SessionLocal
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.record_count = writer.total_records
            db.commit()
    finally:
        db.close()


async def _send_one(session: aiohttp.ClientSession, url: str, qa_record: dict, timeout_s: int) -> dict:
    """Send a single request and collect metrics."""
    request_id = str(uuid.uuid4())
    arrival_time = time.time()

    # Parse messages
    messages_str = qa_record.get("messages", "[]")
    if isinstance(messages_str, str):
        try:
            messages = json.loads(messages_str)
        except json.JSONDecodeError:
            messages = [{"role": "user", "content": messages_str}]
    else:
        messages = messages_str

    payload = {
        "model": qa_record.get("model", "default"),
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    first_token_time = None
    chunk_count = 0
    usage_data = {}
    response_parts = []
    model = payload["model"]

    try:
        async with session.post(url, json=payload) as resp:
            buffer = b""
            async for raw in resp.content.iter_any():
                buffer += raw
                while b"\n\n" in buffer:
                    idx = buffer.find(b"\n\n") + 2
                    msg = buffer[:idx]
                    buffer = buffer[idx:]
                    for line in msg.decode("utf-8", errors="replace").strip().split("\n"):
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str in ("[DONE]", ""):
                            continue
                        try:
                            data = json.loads(data_str)
                            if data.get("usage"):
                                usage_data = data["usage"]
                            model = data.get("model", model)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    response_parts.append(content)
                                    if first_token_time is None:
                                        first_token_time = time.time()
                            chunk_count += 1
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        pass

    completion_time = time.time()
    ttft = (first_token_time - arrival_time) * 1000 if first_token_time else 0
    e2e = (completion_time - arrival_time) * 1000
    decode_time = (completion_time - first_token_time) if first_token_time else 0

    prompt_tokens = usage_data.get("prompt_tokens", 0)
    completion_tokens = usage_data.get("completion_tokens", 0)
    total_tokens = usage_data.get("total_tokens", 0)
    details = usage_data.get("prompt_tokens_details") or {}
    cached_tokens = details.get("cached_tokens", usage_data.get("num_cached_tokens", 0)) or 0
    output_count = completion_tokens if completion_tokens > 0 else max(chunk_count - 1, 0)
    tpot = (decode_time * 1000 / output_count) if output_count > 0 and decode_time > 0 else 0
    tps = (output_count / decode_time) if decode_time > 0 else 0

    return {
        "request_id": request_id,
        "model": model,
        "arrival_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(arrival_time)),
        "completion_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(completion_time)),
        "prompt_tokens": prompt_tokens,
        "forward_cal_tokens": 0,
        "cached_tokens": cached_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "ttft_ms": round(ttft, 2),
        "tpot_ms": round(tpot, 2),
        "tps": round(tps, 2),
        "e2e_latency_ms": round(e2e, 2),
        "chunk_count": chunk_count,
        "messages": messages,
        "response_content": "".join(response_parts),
    }


@router.get("/{task_id}/progress")
async def get_progress(task_id: str):
    if task_id in _running:
        p = _running[task_id]
        elapsed = time.time() - p["start_time"]
        return BenchmarkProgress(
            task_id=task_id,
            total=p["total"],
            completed=p["completed"],
            status=p["status"],
            elapsed_s=round(elapsed, 1),
        )
    return BenchmarkProgress(task_id=task_id, total=0, completed=0, status="not_found")


@router.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload external QA dataset (JSON or CSV)."""
    upload_dir = settings.DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = upload_dir / filename
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Count records
    count = 0
    if file.filename.endswith(".json"):
        records = json.loads(content)
        count = len(records) if isinstance(records, list) else 0
    elif file.filename.endswith(".csv"):
        import io
        df = pd.read_csv(io.BytesIO(content))
        count = len(df)

    return {"dataset_id": filename, "record_count": count, "path": str(filepath)}


@router.get("/tasks")
async def list_benchmark_tasks(db: Session = Depends(get_db)):
    tasks = (
        db.query(Task).filter(Task.type == "benchmark")
        .order_by(Task.created_at.desc()).all()
    )
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "record_count": t.record_count,
            "data_dir": t.data_dir,
            "config": json.loads(t.config) if t.config else {},
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]
