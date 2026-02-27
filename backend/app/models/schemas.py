from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime, timezone
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class ProxyConfig(Base):
    __tablename__ = "proxy_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_host = Column(String(256), nullable=False)
    target_port = Column(Integer, nullable=False)
    api_type = Column(String(32), default="openai_compatible")
    custom_tokens_jsonpath = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)  # collect / benchmark
    status = Column(String(32), default="pending")
    config = Column(Text, nullable=True)  # JSON
    data_dir = Column(String(512), nullable=True)
    record_count = Column(Integer, default=0)
    target_host = Column(String(256), nullable=True)
    target_port = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
