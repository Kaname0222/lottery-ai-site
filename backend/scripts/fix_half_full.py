"""修正所有 AI 预测中的半全场推荐，使其与预测比分自洽。"""
import asyncio
from uuid import UUID
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models import Match, Prediction, LLMProvider
from app.services.prediction_normalize import normalize_half_full_selection
from app.services.scoring import score_finished_matches


async def main():
    async with AsyncSessionLocal() as db:
        # 获取所有非 personal 的 AI provider id
        provider_result = await db.execute(
            select(LLMProvider.id).where(LLMProvider.name != "personal")
        )
        ai_provider_ids = [r[0] for r in provider_result.all()]
        print(f"Found {len(ai_provider_ids)} AI providers")

        pred_result = await db.execute(
            select(Prediction)
            .where(Prediction.provider_id.in_(ai_provider_ids))
            .where(Prediction.bets.isnot(None))
        )
        predictions = pred_result.scalars().all()
        print(f"Found {len(predictions)} AI predictions with bets")

        fixed = 0
        changed_ids = []
        for pred in predictions:
            bets = pred.bets or []
            new_bets = []
            changed = False
            for bet in bets:
                if bet.get("market") == "半全场":
                    old = bet.get("selection", "")
                    new = normalize_half_full_selection(pred.home_score, pred.away_score, old)
                    if new != old:
                        changed = True
                        bet = {**bet, "selection": new}
                new_bets.append(bet)

            if changed:
                pred.bets = new_bets
                fixed += 1
                changed_ids.append(pred.id)

        await db.commit()
        print(f"Fixed {fixed} predictions")

        if changed_ids:
            # 对已有实际比分的受影响预测重新评分
            await db.execute(
                update(Prediction)
                .where(Prediction.id.in_(changed_ids))
                .where(Prediction.match_id.in_(select(Match.id).where(
                    Match.actual_home_score.isnot(None),
                    Match.actual_away_score.isnot(None),
                )))
                .values(points_awarded=None, direction_points=None, other_points=None, is_correct=None)
            )
            await db.commit()
            scored = await score_finished_matches(db)
            print(f"Re-scored {scored} affected finished predictions")


if __name__ == "__main__":
    asyncio.run(main())
