import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.seed_providers import seed_providers
from app.tasks.daily_pipeline import run_full_pipeline
from app.routers import matches, predictions, providers, dashboard, admin

# Windows 下 Playwright 需要 ProactorEventLoop 才能启动 Chromium 子进程；
# uvicorn 默认策略在部分 Windows 环境会变成 SelectorEventLoop，导致 NotImplementedError。
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _sync_run_pipeline():
    """同步包装：APScheduler 在后台线程中运行异步 pipeline。"""
    try:
        asyncio.run(run_full_pipeline())
    except Exception as exc:
        logger.error("Scheduled pipeline failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("Initializing database...")
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_providers(db)

    if settings.SCHEDULED_PIPELINE_ENABLED:
        scheduler.add_job(_sync_run_pipeline, "cron", hour=9, minute=0, id="morning_pipeline")
        scheduler.add_job(_sync_run_pipeline, "cron", hour=16, minute=0, id="afternoon_pipeline")
        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduled pipeline disabled; skipping scheduler startup")

    yield

    # shutdown
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


app = FastAPI(
    title="Lottery AI Predictions",
    description="中国体彩竞彩足球 AI 比分预测网站",
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

app.include_router(matches.router)
app.include_router(predictions.router)
app.include_router(providers.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
