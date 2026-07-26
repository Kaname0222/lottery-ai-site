import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Prediction

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prediction))
        rows = result.scalars().all()
        print('Total predictions:', len(rows))
        mismatches = []
        for p in rows:
            if not p.bets:
                continue
            score_bet = next((b for b in p.bets if b.get('market') == '比分'), None)
            goals_bet = next((b for b in p.bets if b.get('market') == '总进球数'), None)
            if score_bet and goals_bet:
                sel = score_bet.get('selection', '')
                if ':' in sel:
                    h, a = sel.split(':')
                    try:
                        expected = str(int(h) + int(a)) + '球'
                    except ValueError:
                        continue
                    actual = goals_bet.get('selection', '')
                    if expected != actual:
                        mismatches.append({
                            'id': str(p.id),
                            'match_id': p.match_id,
                            'provider_id': str(p.provider_id),
                            'score': sel,
                            'expected_goals': expected,
                            'actual_goals': actual,
                        })
        print('Mismatches:', len(mismatches))
        for m in mismatches:
            print(m)

asyncio.run(main())
