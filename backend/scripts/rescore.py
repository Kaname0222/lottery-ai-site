"""重新计算所有已结束预测的积分。"""
import asyncio
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Match, Prediction
from app.services.scoring import score_finished_matches


async def main():
    async with AsyncSessionLocal() as db:
        # 清空已有实际比分预测的积分，触发重新评分
        await db.execute(
            update(Prediction)
            .where(Prediction.match_id.in_(
                select(Match.id).where(
                    Match.actual_home_score.isnot(None),
                    Match.actual_away_score.isnot(None),
                )
            ))
            .values(points_awarded=None, direction_points=None, other_points=None, is_correct=None)
        )
        await db.commit()

        scored = await score_finished_matches(db)
        print(f"Re-scored {scored} predictions")


if __name__ == "__main__":
    asyncio.run(main())
