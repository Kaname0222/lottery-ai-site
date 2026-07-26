import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models import Match

async def main():
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count(Match.id)))).scalar()
        no_result = (await db.execute(select(func.count(Match.id)).where(Match.actual_home_score.is_(None)))).scalar()
        with_result = (await db.execute(select(func.count(Match.id)).where(Match.actual_home_score.isnot(None)))).scalar()
        print(f"Total matches: {total}, no result: {no_result}, with result: {with_result}")

        result = await db.execute(
            select(Match).where(Match.actual_home_score.is_(None)).order_by(Match.match_date).limit(20)
        )
        matches = result.scalars().all()
        print("Matches without result:")
        for m in matches:
            print(f"  {m.match_id} {m.match_date} {m.home_team} vs {m.away_team}")

if __name__ == "__main__":
    asyncio.run(main())
