import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Match).where(Match.match_id.like('周六%')).order_by(Match.match_id))
        rows = result.scalars().all()
        for m in rows:
            has_score = '有' if m.score_odds else '无'
            print(f"{m.match_id}: {m.home_team} VS {m.away_team} | score_odds={has_score} | mid={m.mid} | created={m.created_at} | updated={m.updated_at}")

asyncio.run(main())
