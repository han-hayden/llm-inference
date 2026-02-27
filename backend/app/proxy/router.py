from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import ProxyConfig
from .forwarder import proxy_forwarder

router = APIRouter(tags=["proxy"])


def _get_active_config() -> ProxyConfig:
    """Get active proxy configuration from database."""
    from ..models.database import SessionLocal
    db = SessionLocal()
    try:
        config = db.query(ProxyConfig).filter(ProxyConfig.is_active == True).first()
        return config
    finally:
        db.close()


@router.api_route(
    "/proxy/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_all(request: Request, full_path: str):
    """Catch-all proxy endpoint. Transparently forwards to target model service."""
    config = _get_active_config()
    if not config:
        raise HTTPException(status_code=503, detail="Proxy not configured. Set target service first.")

    from ..collect.task_manager import collection_manager
    collect = collection_manager.has_active_task()

    return await proxy_forwarder.forward(
        request=request,
        target_host=config.target_host,
        target_port=config.target_port,
        path=f"/{full_path}",
        collect_metrics=collect,
    )
