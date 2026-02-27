"""
Compare two test records and calculate improvement metrics.
"""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import Task

router = APIRouter(prefix="/api/compare", tags=["compare"])


def _load_df(task_id: str, db: Session) -> pd.DataFrame:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or not task.data_dir:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    data_dir = Path(task.data_dir)
    files = sorted(data_dir.glob("performance_data_*.csv"))
    if not files:
        raise HTTPException(status_code=404, detail=f"No data for {task_id}")
    dfs = [pd.read_csv(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


@router.get("")
async def compare_tasks(
    baseline_id: str = Query(...),
    optimized_id: str = Query(...),
    db: Session = Depends(get_db),
):
    baseline_df = _load_df(baseline_id, db)
    optimized_df = _load_df(optimized_id, db)

    b_ttft = float(baseline_df["ttft_ms"].mean())
    o_ttft = float(optimized_df["ttft_ms"].mean())
    ttft_reduction = round((b_ttft - o_ttft) / b_ttft * 100, 1) if b_ttft > 0 else 0

    b_tps = float(baseline_df["tps"].mean())
    o_tps = float(optimized_df["tps"].mean())
    tps_increase = round((o_tps - b_tps) / b_tps * 100, 1) if b_tps > 0 else 0

    b_tpot = float(baseline_df["tpot_ms"].mean())
    o_tpot = float(optimized_df["tpot_ms"].mean())
    tpot_reduction = round((b_tpot - o_tpot) / b_tpot * 100, 1) if b_tpot > 0 else 0

    b_e2e = float(baseline_df["e2e_latency_ms"].mean())
    o_e2e = float(optimized_df["e2e_latency_ms"].mean())
    e2e_reduction = round((b_e2e - o_e2e) / b_e2e * 100, 1) if b_e2e > 0 else 0

    return {
        "baseline_id": baseline_id,
        "optimized_id": optimized_id,
        "ttft_improvement": {
            "baseline_avg": round(b_ttft, 2),
            "optimized_avg": round(o_ttft, 2),
            "reduction_pct": ttft_reduction,
        },
        "decode_speed_improvement": {
            "baseline_avg": round(b_tps, 2),
            "optimized_avg": round(o_tps, 2),
            "increase_pct": tps_increase,
        },
        "tpot_improvement": {
            "baseline_avg": round(b_tpot, 2),
            "optimized_avg": round(o_tpot, 2),
            "reduction_pct": tpot_reduction,
        },
        "e2e_improvement": {
            "baseline_avg": round(b_e2e, 2),
            "optimized_avg": round(o_e2e, 2),
            "reduction_pct": e2e_reduction,
        },
        "ttft_series": {
            "baseline": baseline_df["ttft_ms"].tolist(),
            "optimized": optimized_df["ttft_ms"].tolist(),
        },
        "decode_speed_series": {
            "baseline": baseline_df["tps"].tolist(),
            "optimized": optimized_df["tps"].tolist(),
        },
    }
