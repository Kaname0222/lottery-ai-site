import asyncio
import logging
from app.database import AsyncSessionLocal
from app.tasks.daily_pipeline import run_predictions_for_unpredicted

logging.basicConfig(level=logging.DEBUG)

async def main():
    async with AsyncSessionLocal() as db:
        count = await run_predictions_for_unpredicted(db)
        print(f"Created predictions: {count}")

asyncio.run(main())
