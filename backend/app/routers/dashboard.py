from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Match, Prediction, ProviderScore
from app.schemas import DashboardToday, ProviderScoreOut
from app.routers.providers import leaderboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/today", response_model=DashboardToday)
async def today_dashboard(db: AsyncSession = Depends(get_db)):
    today = date.today()

    total_result = await db.execute(select(func.count(Match.id)).where(Match.match_date == today))
    total_matches = total_result.scalar() or 0

    predicted_result = await db.execute(
        select(func.count(func.distinct(Match.id)))
        .join(Prediction, Match.id == Prediction.match_id)
        .where(Match.match_date == today)
    )
    predicted_matches = predicted_result.scalar() or 0

    scores = await leaderboard(db)
    return DashboardToday(
        date=today,
        total_matches=total_matches,
        predicted_matches=predicted_matches,
        pending_matches=max(0, total_matches - predicted_matches),
        provider_scores=scores,
    )
