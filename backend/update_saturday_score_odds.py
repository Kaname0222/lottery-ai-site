import asyncio
import re
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match
from app.services.scoring import score_finished_matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 用户提供的周六比赛实际正确比分及赔率
SATURDAY_CORRECT_SCORES = {
    "周六201": ("3:2", 29.0),
    "周六202": ("0:2", 11.5),
    "周六203": ("0:1", 9.0),
    "周六204": ("1:1", 8.25),
    "周六205": ("1:2", 9.5),
    "周六206": ("3:1", 15.0),
    "周六207": ("2:1", 7.75),
    "周六208": ("2:0", 7.5),
    "周六209": ("2:2", 20.0),
    "周六210": ("1:0", 14.0),
    "周六211": ("1:1", 7.75),
}


async def main():
    async with AsyncSessionLocal() as db:
        updated = 0
        for match_id, (score, odds) in SATURDAY_CORRECT_SCORES.items():
            result = await db.execute(
                select(Match).where(Match.match_id == match_id)
            )
            match = result.scalar_one_or_none()
            if not match:
                logger.warning("Match %s not found", match_id)
                continue

            # 合并：保留已有的比分赔率，并补充/覆盖用户提供的正确比分赔率
            score_odds = dict(match.score_odds) if match.score_odds else {}
            old = score_odds.get(score)
            score_odds[score] = odds
            match.score_odds = score_odds

            updated += 1
            logger.info(
                "Updated %s score %s odds %.2f (old: %s)",
                match_id, score, odds, old
            )

        await db.commit()
        logger.info("Updated %d matches", updated)

        # 重新计算所有已完赛预测的积分
        scored = await score_finished_matches(db)
        logger.info("Recomputed scores for %d finished predictions", scored)

        return {"updated": updated, "scored": scored}


if __name__ == "__main__":
    result = asyncio.run(main())
    print(result)
