from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import Task
from .task_manager import collection_manager

router = APIRouter(prefix="/api/collect", tags=["collect"])


class StartCollectRequest(BaseModel):
    name: str
    stop_type: str = "count"  # count | time
    stop_value: int = 500


class StopCollectRequest(BaseModel):
    task_id: str


@router.post("/start")
async def start_collect(req: StartCollectRequest, db: Session = Depends(get_db)):
    try:
        result = await collection_manager.start_task(
            name=req.name, stop_type=req.stop_type,
            stop_value=req.stop_value, db=db,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/stop")
async def stop_collect(req: StopCollectRequest, db: Session = Depends(get_db)):
    try:
        await collection_manager.stop_task(req.task_id, db)
        return {"status": "stopped", "task_id": req.task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def collect_status():
    if collection_manager.has_active_task():
        writer = collection_manager._active_writer
        return {
            "active": True,
            "task_id": collection_manager.active_task_id,
            "record_count": writer.total_records if writer else 0,
        }
    return {"active": False, "task_id": None, "record_count": 0}


@router.get("/tasks")
async def list_collect_tasks(db: Session = Depends(get_db)):
    tasks = (
        db.query(Task).filter(Task.type == "collect")
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
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]
