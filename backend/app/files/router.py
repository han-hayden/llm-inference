import json
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Optional

import pandas as pd
from ..config import settings
from ..models.database import get_db
from ..models.schemas import Task
from sqlalchemy.orm import Session
from fastapi import Depends

router = APIRouter(prefix="/api/files", tags=["files"])


def _find_task_dir(task_id: str, db: Session) -> Path:
    """Resolve task data directory."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task and task.data_dir:
        p = Path(task.data_dir)
        if p.exists():
            return p
    # Fallback: glob
    matches = list(settings.DATA_DIR.glob(f"{task_id}_*"))
    if matches:
        return matches[0]
    raise HTTPException(status_code=404, detail=f"Task {task_id} data not found")


def _read_all_csvs(data_dir: Path, pattern: str) -> pd.DataFrame:
    files = sorted(data_dir.glob(pattern))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_csv(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


@router.get("/tasks")
async def list_task_files(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    result = []
    for t in tasks:
        files = []
        if t.data_dir:
            p = Path(t.data_dir)
            if p.exists():
                files = [f.name for f in p.iterdir() if f.is_file()]
        result.append({
            "task_id": t.id,
            "name": t.name,
            "type": t.type,
            "status": t.status,
            "record_count": t.record_count,
            "dir": Path(t.data_dir).name if t.data_dir else "",
            "files": files,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        })
    return result


@router.get("/{task_id}/performance")
async def get_performance_data(
    task_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    db: Session = Depends(get_db),
):
    task_dir = _find_task_dir(task_id, db)
    df = _read_all_csvs(task_dir, "performance_data_*.csv")
    if df.empty:
        return {"total": 0, "page": page, "size": size, "items": []}

    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=(sort_order == "asc"))

    total = len(df)
    start = (page - 1) * size
    items = df.iloc[start : start + size].to_dict("records")

    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/{task_id}/qa")
async def get_qa_data(
    task_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    task_dir = _find_task_dir(task_id, db)
    df = _read_all_csvs(task_dir, "qa_pairs_*.csv")
    if df.empty:
        return {"total": 0, "page": page, "size": size, "items": []}

    total = len(df)
    start = (page - 1) * size
    items = df.iloc[start : start + size].to_dict("records")

    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/{task_id}/summary")
async def get_summary(task_id: str, db: Session = Depends(get_db)):
    task_dir = _find_task_dir(task_id, db)
    summary_file = task_dir / "performance_summary.json"
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Summary not generated yet")
    with open(summary_file, "r", encoding="utf-8") as f:
        return json.load(f)
