import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import get_db
from ..models.schemas import Task

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _load_perf_df(task_id: str, db: Session) -> pd.DataFrame:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task.data_dir:
        raise HTTPException(status_code=404, detail="Task not found")
    data_dir = Path(task.data_dir)
    if not data_dir.exists():
        raise HTTPException(status_code=404, detail="Data directory not found")
    files = sorted(data_dir.glob("performance_data_*.csv"))
    if not files:
        raise HTTPException(status_code=404, detail="No performance data")
    dfs = [pd.read_csv(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


def _histogram(series: pd.Series, bins: list, labels: list) -> list:
    cut = pd.cut(series, bins=bins, labels=labels, right=False)
    counts = cut.value_counts().reindex(labels, fill_value=0)
    return [{"range": str(r), "count": int(c)} for r, c in counts.items()]


@router.get("/{task_id}/distributions")
async def get_distributions(task_id: str, db: Session = Depends(get_db)):
    df = _load_perf_df(task_id, db)

    context_length = _histogram(
        df["prompt_tokens"],
        [0, 256, 512, 1024, 2048, 4096, float("inf")],
        ["0-256", "256-512", "512-1024", "1024-2048", "2048-4096", "4096+"],
    )

    response_latency = _histogram(
        df["e2e_latency_ms"],
        [0, 500, 1000, 2000, 3000, 5000, 10000, float("inf")],
        ["0-500ms", "500ms-1s", "1-2s", "2-3s", "3-5s", "5-10s", "10s+"],
    )

    # Cache hit rate: cached_tokens / prompt_tokens
    hit_rate = df["cached_tokens"] / df["prompt_tokens"].replace(0, 1)
    cache_hit_rate = _histogram(
        hit_rate,
        [0, 0.2, 0.4, 0.6, 0.8, 1.01],
        ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
    )

    return {
        "context_length": context_length,
        "response_latency": response_latency,
        "cache_hit_rate": cache_hit_rate,
    }


@router.get("/{task_id}/summary")
async def get_metrics_summary(task_id: str, db: Session = Depends(get_db)):
    df = _load_perf_df(task_id, db)

    def s(col):
        series = df[col]
        return {
            "avg": round(float(series.mean()), 2),
            "p50": round(float(series.quantile(0.5)), 2),
            "p90": round(float(series.quantile(0.9)), 2),
            "p99": round(float(series.quantile(0.99)), 2),
            "min": round(float(series.min()), 2),
            "max": round(float(series.max()), 2),
        }

    return {
        "total_requests": len(df),
        "ttft_ms": s("ttft_ms"),
        "tpot_ms": s("tpot_ms"),
        "tps": s("tps"),
        "e2e_latency_ms": s("e2e_latency_ms"),
    }
