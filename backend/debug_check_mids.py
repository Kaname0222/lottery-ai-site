import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match

async def main():
    async with AsyncSessionLocal() as db:
        for match_id in ['周六202', '周六203', '周六204', '周六205', '周六210']:
            m = (await db.execute(select(Match).where(Match.match_id == match_id))).scalar_one_or_none()
            if m:
                print(f"{match_id}: mid={m.mid} {m.home_team} vs {m.away_team}")

asyncio.run(main())
