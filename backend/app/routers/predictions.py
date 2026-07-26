from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Prediction
from app.schemas import PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=List[PredictionOut])
async def list_predictions(
    match_id: UUID = None,
    provider_id: UUID = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Prediction).options(selectinload(Prediction.provider))
    if match_id:
        query = query.where(Prediction.match_id == match_id)
    if provider_id:
        query = query.where(Prediction.provider_id == provider_id)
    result = await db.execute(query)
    predictions = result.scalars().all()

    out = []
    for p in predictions:
        out.append(
            PredictionOut(
                id=p.id,
                match_id=p.match_id,
                provider_id=p.provider_id,
                provider_name=p.provider.name,
                provider_display_name=p.provider.display_name,
                prediction_index=p.prediction_index,
                home_score=p.home_score,
                away_score=p.away_score,
                confidence=p.confidence,
                reasoning_summary=p.reasoning_summary,
                market_reasoning=p.market_reasoning,
                bets=p.bets,
                is_correct=p.is_correct,
                points_awarded=p.points_awarded,
                direction_points=p.direction_points,
                other_points=p.other_points,
                predicted_at=p.predicted_at,
            )
        )
    return out
