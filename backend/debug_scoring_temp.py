import asyncio
import logging
import sys
import traceback
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

from app.database import AsyncSessionLocal
from app.tasks.daily_pipeline import fetch_results_and_score


async def main():
    try:
        async with AsyncSessionLocal() as db:
            result = await fetch_results_and_score(db)
            print(f"Scored: {result}")
    except Exception as exc:
        print("ERROR:", exc)
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
