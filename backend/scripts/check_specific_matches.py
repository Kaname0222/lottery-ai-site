import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match

async def main():
    async with AsyncSessionLocal() as db:
        ids = ['周日210', '周日211', '周日212', '周日213', '周日214', '周日215', '周日216', '周日217', '周日218']
        result = await db.execute(select(Match).where(Match.match_id.in_(ids)))
        matches = result.scalars().all()
        for m in matches:
            print(f"{m.match_id} date={m.match_date} time={m.match_time} mid={m.mid} {m.home_team} vs {m.away_team} result={m.actual_home_score}:{m.actual_away_score}")

if __name__ == "__main__":
    asyncio.run(main())
