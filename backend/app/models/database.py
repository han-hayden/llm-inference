from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from ..config import settings

Base = declarative_base()

engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    _ensure_admin_user()


def _ensure_admin_user():
    from .schemas import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not user:
            user = User(
                username=settings.ADMIN_USERNAME,
                password_hash=pwd_context.hash(settings.ADMIN_PASSWORD),
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
