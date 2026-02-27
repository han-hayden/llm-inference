from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import ProxyConfig

router = APIRouter(prefix="/api/config", tags=["config"])


class ProxyConfigRequest(BaseModel):
    target_host: str
    target_port: int
    api_type: str = "openai_compatible"
    custom_tokens_jsonpath: Optional[str] = None


class ProxyConfigResponse(BaseModel):
    id: int
    target_host: str
    target_port: int
    api_type: str
    custom_tokens_jsonpath: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


@router.post("/proxy", response_model=ProxyConfigResponse)
async def set_proxy_config(req: ProxyConfigRequest, db: Session = Depends(get_db)):
    # Deactivate all existing configs
    db.query(ProxyConfig).update({"is_active": False})

    config = ProxyConfig(
        target_host=req.target_host,
        target_port=req.target_port,
        api_type=req.api_type,
        custom_tokens_jsonpath=req.custom_tokens_jsonpath,
        is_active=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/proxy", response_model=Optional[ProxyConfigResponse])
async def get_proxy_config(db: Session = Depends(get_db)):
    config = db.query(ProxyConfig).filter(ProxyConfig.is_active == True).first()
    if not config:
        return None
    return config


@router.delete("/proxy/{config_id}")
async def delete_proxy_config(config_id: int, db: Session = Depends(get_db)):
    config = db.query(ProxyConfig).filter(ProxyConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(config)
    db.commit()
    return {"status": "deleted"}
