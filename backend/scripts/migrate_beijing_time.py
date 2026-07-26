"""将数据库中所有 UTC 存储的时间字段迁移为北京时间（+8 小时）。

警告：此脚本应仅运行一次。再次运行会导致时间再次被加 8 小时。
运行方式（在项目根目录下）：
    python -m scripts.migrate_beijing_time
"""
import asyncio
from datetime import timedelta
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match, Prediction, ProviderScore, ScrapeLog


OFFSET = timedelta(hours=8)


async def main():
    async with AsyncSessionLocal() as db:
        # matches
        result = await db.execute(select(Match))
        for match in result.scalars().all():
            if match.match_time:
                match.match_time += OFFSET
            if match.created_at:
                match.created_at += OFFSET
            if match.updated_at:
                match.updated_at += OFFSET
            if match.result_settled_at:
                match.result_settled_at += OFFSET

        # predictions
        result = await db.execute(select(Prediction))
        for pred in result.scalars().all():
            if pred.predicted_at:
                pred.predicted_at += OFFSET

        # provider_scores
        result = await db.execute(select(ProviderScore))
        for score in result.scalars().all():
            if score.updated_at:
                score.updated_at += OFFSET

        # scrape_logs
        result = await db.execute(select(ScrapeLog))
        for log in result.scalars().all():
            if log.run_at:
                log.run_at += OFFSET

        await db.commit()
        print("Beijing time migration completed.")


if __name__ == "__main__":
    asyncio.run(main())
