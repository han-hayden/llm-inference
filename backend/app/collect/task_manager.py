"""
Collection task lifecycle manager.
Manages active collection tasks and routes incoming performance records.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from ..config import settings
from ..models.schemas import Task
from .data_writer import PerformanceDataWriter


class CollectionTaskManager:
    """Singleton manager for collection tasks."""

    def __init__(self):
        self._active_writer: Optional[PerformanceDataWriter] = None
        self._active_task_id: Optional[str] = None
        self._stop_type: Optional[str] = None
        self._stop_value: int = 0
        self._counter = 0

    def has_active_task(self) -> bool:
        return self._active_writer is not None

    @property
    def active_task_id(self) -> Optional[str]:
        return self._active_task_id

    def _next_id(self) -> str:
        self._counter += 1
        return f"collect_{self._counter:03d}"

    def sync_counter(self, db: Session):
        """Sync counter from existing tasks in DB."""
        from ..models.schemas import Task
        tasks = db.query(Task).filter(Task.type == "collect").all()
        for t in tasks:
            try:
                num = int(t.id.split("_")[1])
                if num > self._counter:
                    self._counter = num
            except (IndexError, ValueError):
                pass

    async def start_task(
        self, name: str, stop_type: str, stop_value: int, db: Session
    ) -> dict:
        if self._active_writer:
            raise RuntimeError("A collection task is already running. Stop it first.")

        self.sync_counter(db)
        task_id = self._next_id()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = settings.DATA_DIR / f"{task_id}_{timestamp}"

        task = Task(
            id=task_id,
            name=name,
            type="collect",
            status="running",
            config=json.dumps({"stop_type": stop_type, "stop_value": stop_value}),
            data_dir=str(data_dir),
            record_count=0,
        )
        db.add(task)
        db.commit()

        writer = PerformanceDataWriter(task_id, data_dir)
        writer.start_periodic_flush()
        self._active_writer = writer
        self._active_task_id = task_id
        self._stop_type = stop_type
        self._stop_value = stop_value

        logger.info(f"Collection task started: {task_id} ({stop_type}={stop_value})")
        return {"task_id": task_id, "data_dir": str(data_dir)}

    async def stop_task(self, task_id: str, db: Session):
        if self._active_task_id != task_id:
            raise ValueError(f"Task {task_id} is not the active task.")

        await self._active_writer.finalize()
        total = self._active_writer.total_records

        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.record_count = total
            db.commit()

        logger.info(f"Collection task stopped: {task_id} (records: {total})")
        self._active_writer = None
        self._active_task_id = None

    async def add_record(self, stat: dict):
        if not self._active_writer:
            return

        await self._active_writer.add_record(stat)

        # Auto-stop if count limit reached
        if self._stop_type == "count" and self._active_writer.total_records >= self._stop_value:
            logger.info(f"Auto-stopping task {self._active_task_id}: count limit reached.")
            from ..models.database import SessionLocal
            db = SessionLocal()
            try:
                await self.stop_task(self._active_task_id, db)
            finally:
                db.close()


collection_manager = CollectionTaskManager()
