"""
Performance data file writer with automatic rotation.
Writes CSV (performance metrics) + CSV (QA pairs) + JSON (summary).
"""

import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
from loguru import logger

from ..config import settings


class PerformanceDataWriter:
    """Write performance data to CSV/JSON files with automatic rotation."""

    PERF_HEADERS = [
        "序号", "request_id", "model", "arrival_time", "completion_time",
        "prompt_tokens", "forward_cal_tokens", "cached_tokens",
        "completion_tokens", "total_tokens", "ttft_ms", "tpot_ms",
        "tps", "e2e_latency_ms", "chunk_count",
    ]

    QA_HEADERS = ["序号", "request_id", "model", "messages", "response_content"]

    def __init__(self, task_id: str, data_dir: Path):
        self.task_id = task_id
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._file_index = 0
        self._file_record_count = 0
        self._total_record_count = 0
        self._max_per_file = settings.MAX_RECORDS_PER_FILE

        self._buffer: List[Dict] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task = None

    @property
    def total_records(self) -> int:
        return self._total_record_count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_record(self, stat: dict):
        async with self._lock:
            self._buffer.append(stat)
            if len(self._buffer) >= settings.FLUSH_BATCH:
                await self._flush()

    def start_periodic_flush(self):
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def finalize(self):
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            await self._flush()

        await self._generate_summary()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _periodic_flush(self):
        try:
            while True:
                await asyncio.sleep(settings.FLUSH_INTERVAL)
                async with self._lock:
                    await self._flush()
        except asyncio.CancelledError:
            pass

    async def _flush(self):
        if not self._buffer:
            return

        # Check rotation
        if self._file_record_count >= self._max_per_file:
            self._file_index += 1
            self._file_record_count = 0

        perf_path = self.data_dir / f"performance_data_{self._file_index}.csv"
        qa_path = self.data_dir / f"qa_pairs_{self._file_index}.csv"

        perf_exists = perf_path.exists()
        qa_exists = qa_path.exists()

        # Write performance CSV
        with open(perf_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=self.PERF_HEADERS)
            if not perf_exists:
                writer.writeheader()
            for stat in self._buffer:
                self._total_record_count += 1
                row = {
                    "序号": self._total_record_count,
                    "request_id": stat["request_id"],
                    "model": stat["model"],
                    "arrival_time": stat["arrival_time"],
                    "completion_time": stat["completion_time"],
                    "prompt_tokens": stat["prompt_tokens"],
                    "forward_cal_tokens": stat.get("forward_cal_tokens", 0),
                    "cached_tokens": stat["cached_tokens"],
                    "completion_tokens": stat["completion_tokens"],
                    "total_tokens": stat["total_tokens"],
                    "ttft_ms": stat["ttft_ms"],
                    "tpot_ms": stat["tpot_ms"],
                    "tps": stat["tps"],
                    "e2e_latency_ms": stat["e2e_latency_ms"],
                    "chunk_count": stat["chunk_count"],
                }
                writer.writerow(row)

        # Write QA pairs CSV
        with open(qa_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=self.QA_HEADERS)
            if not qa_exists:
                writer.writeheader()
            seq = self._total_record_count - len(self._buffer) + 1
            for stat in self._buffer:
                writer.writerow({
                    "序号": seq,
                    "request_id": stat["request_id"],
                    "model": stat["model"],
                    "messages": json.dumps(stat.get("messages", []), ensure_ascii=False),
                    "response_content": stat.get("response_content", ""),
                })
                seq += 1

        self._file_record_count += len(self._buffer)
        logger.debug(f"[{self.task_id}] Flushed {len(self._buffer)} records (total: {self._total_record_count})")
        self._buffer.clear()

    async def _generate_summary(self):
        """Read all CSV files and generate performance_summary.json."""
        all_csvs = sorted(self.data_dir.glob("performance_data_*.csv"))
        if not all_csvs:
            return

        dfs = [pd.read_csv(f) for f in all_csvs]
        df = pd.concat(dfs, ignore_index=True)

        def stats(series):
            return {
                "avg": round(float(series.mean()), 2),
                "p50": round(float(series.quantile(0.5)), 2),
                "p90": round(float(series.quantile(0.9)), 2),
                "p99": round(float(series.quantile(0.99)), 2),
                "min": round(float(series.min()), 2),
                "max": round(float(series.max()), 2),
            }

        summary = {
            "task_id": self.task_id,
            "total_requests": len(df),
            "time_range": {
                "start": str(df["arrival_time"].iloc[0]) if len(df) > 0 else "",
                "end": str(df["completion_time"].iloc[-1]) if len(df) > 0 else "",
            },
            "summary": {
                "ttft_ms": stats(df["ttft_ms"]),
                "tpot_ms": stats(df["tpot_ms"]),
                "tps": stats(df["tps"]),
                "e2e_latency_ms": stats(df["e2e_latency_ms"]),
                "prompt_tokens": stats(df["prompt_tokens"]),
                "completion_tokens": stats(df["completion_tokens"]),
                "cached_tokens": {
                    "avg": round(float(df["cached_tokens"].mean()), 2),
                    "total": int(df["cached_tokens"].sum()),
                },
            },
        }

        path = self.data_dir / "performance_summary.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"[{self.task_id}] Summary saved to {path}")

        # Also save QA pairs as JSON
        qa_csvs = sorted(self.data_dir.glob("qa_pairs_*.csv"))
        if qa_csvs:
            qa_dfs = [pd.read_csv(f) for f in qa_csvs]
            qa_df = pd.concat(qa_dfs, ignore_index=True)
            qa_json_path = self.data_dir / "qa_pairs.json"
            qa_records = qa_df.to_dict("records")
            with open(qa_json_path, "w", encoding="utf-8") as f:
                json.dump(qa_records, f, indent=2, ensure_ascii=False)
