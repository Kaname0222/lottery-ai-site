#!/usr/bin/env python3
"""
独立爬虫脚本（不调用 LLM）。

供 GitHub Actions 定时调用，负责：
1. 抓取在售赛程和全部玩法赔率，写入数据库
2. 抓取已结束比赛结果并触发评分

用法：
    cd backend
    DATABASE_URL=postgresql+asyncpg://... python scripts/run_scraper.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# 将 backend/ 加入 sys.path，保证在脚本目录下也能 import app
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.database import AsyncSessionLocal, init_db
from app.tasks.daily_pipeline import (
    scrape_and_save_matches,
    fetch_results_and_score,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("run_scraper")


async def run():
    logger.info("Initializing database tables if not exist...")
    await init_db()

    logger.info("Running match & odds scraper...")
    async with AsyncSessionLocal() as db:
        matches_count = await scrape_and_save_matches(db)
        logger.info("Saved/updated %d matches", matches_count)

    logger.info("Running results & scoring scraper...")
    async with AsyncSessionLocal() as db:
        scored_count = await fetch_results_and_score(db)
        logger.info("Scored %d predictions", scored_count)

    logger.info("Scraper finished successfully")


if __name__ == "__main__":
    asyncio.run(run())
