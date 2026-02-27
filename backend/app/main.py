from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import settings
from .models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AICP Performance Testing Tool...")
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "reports").mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(f"Data directory: {settings.DATA_DIR}")

    # Initialize proxy forwarder
    from .proxy.forwarder import proxy_forwarder
    await proxy_forwarder.start()

    yield

    await proxy_forwarder.stop()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="AICP LLM Inference Performance Testing Tool",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from .auth.router import router as auth_router
from .config_mgr.router import router as config_router
from .proxy.router import router as proxy_router
from .collect.router import router as collect_router
from .files.router import router as files_router
from .metrics.router import router as metrics_router
from .benchmark.router import router as benchmark_router
from .compare.router import router as compare_router
from .report.router import router as report_router
from .analysis.router import router as analysis_router

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(proxy_router)
app.include_router(collect_router)
app.include_router(files_router)
app.include_router(metrics_router)
app.include_router(benchmark_router)
app.include_router(compare_router)
app.include_router(report_router)
app.include_router(analysis_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
