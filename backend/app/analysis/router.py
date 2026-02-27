"""
Analysis engine API endpoints (stub / placeholder for future implementation).
"""

from fastapi import APIRouter
from .base import engine_manager

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/engines")
async def list_engines():
    return {"engines": engine_manager.list_engines()}


@router.get("/{task_id}/suggestions")
async def get_suggestions(task_id: str, engine: str = None):
    if not engine_manager.list_engines():
        return {
            "task_id": task_id,
            "results": [],
            "message": "No analysis engines available. This feature is coming soon.",
        }
    results = await engine_manager.analyze(task_id, {}, [], engine_name=engine)
    return {
        "task_id": task_id,
        "results": [r.model_dump() for r in results],
    }


@router.post("/{task_id}/run")
async def run_analysis(task_id: str):
    if not engine_manager.list_engines():
        return {"status": "no_engine_available"}
    results = await engine_manager.analyze(task_id, {}, [])
    return {"status": "completed", "results": [r.model_dump() for r in results]}
