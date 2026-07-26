import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Prediction
from app.services.scoring import score_finished_matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _score_to_total_goals(score_selection: str) -> str:
    """根据比分推荐计算出总进球数，格式为 'X球'。"""
    if not score_selection or ':' not in score_selection:
        return ''
    parts = score_selection.split(':')
    if len(parts) != 2:
        return ''
    try:
        total = int(parts[0]) + int(parts[1])
    except ValueError:
        return ''
    return f"{total}球"


async def fix_total_goals():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prediction))
        rows = result.scalars().all()

        fixed_count = 0
        added_count = 0

        for p in rows:
            if not p.bets:
                continue

            score_idx = None
            goals_idx = None
            for i, bet in enumerate(p.bets):
                if bet.get('market') == '比分':
                    score_idx = i
                elif bet.get('market') == '总进球数':
                    goals_idx = i

            if score_idx is None:
                continue

            expected = _score_to_total_goals(p.bets[score_idx].get('selection', ''))
            if not expected:
                continue

            # 必须重新赋值整个 bets 列表，SQLAlchemy 才能检测到 JSON 字段变更
            new_bets = list(p.bets)

            if goals_idx is None:
                new_bets.append({
                    'market': '总进球数',
                    'selection': expected,
                    'reason': new_bets[score_idx].get('reason', ''),
                })
                added_count += 1
                logger.info(
                    "Added total goals bet for prediction %s match %s: %s",
                    p.id, p.match_id, expected
                )
            elif new_bets[goals_idx].get('selection') != expected:
                old = new_bets[goals_idx].get('selection')
                new_bets[goals_idx] = {
                    **new_bets[goals_idx],
                    'selection': expected,
                }
                fixed_count += 1
                logger.info(
                    "Fixed total goals for prediction %s match %s: %s -> %s",
                    p.id, p.match_id, old, expected
                )
            else:
                continue

            p.bets = new_bets

        await db.commit()
        logger.info("Fixed %d predictions, added %d total goals bets", fixed_count, added_count)

        # 重新计算积分
        scored = await score_finished_matches(db)
        logger.info("Recomputed scores for %d finished predictions", scored)

        return {"fixed": fixed_count, "added": added_count, "scored": scored}


if __name__ == "__main__":
    result = asyncio.run(fix_total_goals())
    print(result)
