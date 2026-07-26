import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match

async def main():
    async with AsyncSessionLocal() as db:
        matches = (await db.execute(select(Match).order_by(Match.match_id))).scalars().all()
        print(f"总比赛数: {len(matches)}")
        print("\n缺少 score_odds 的比赛:")
        for m in matches:
            if not m.score_odds:
                print(f"  {m.match_id} {m.league} {m.home_team} vs {m.away_team} sale={m.sale_status}")
        
        print("\n有 score_odds 的比赛:")
        for m in matches:
            if m.score_odds:
                keys = list(m.score_odds.keys())
                print(f"  {m.match_id} {m.home_team} vs {m.away_team}: {len(keys)} 个赔率")

asyncio.run(main())
