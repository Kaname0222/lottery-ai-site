from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import LLMProvider, ProviderScore
from app.schemas import ProviderOut, ProviderScoreOut, MarketLeaderboardOut
from app.services.scoring import build_market_leaderboard

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=List[ProviderOut])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.is_active == True))
    return result.scalars().all()


@router.get("/leaderboard", response_model=List[ProviderScoreOut])
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """获取 AI 排行榜：其他玩法积分优先，同分看方向玩法积分。"""
    result = await db.execute(
        select(ProviderScore)
        .options(selectinload(ProviderScore.provider))
        .order_by(
            case((ProviderScore.total_predictions > 0, 1), else_=0).desc(),
            ProviderScore.other_points.desc(),
            ProviderScore.direction_points.desc(),
        )
    )
    scores = result.scalars().all()
    return [
        ProviderScoreOut(
            provider_id=s.provider_id,
            provider_name=s.provider.name,
            provider_display_name=s.provider.display_name,
            total_predictions=s.total_predictions,
            correct_predictions=s.correct_predictions,
            direction_correct_predictions=s.direction_correct_predictions,
            total_points=s.total_points,
            direction_points=s.direction_points,
            other_points=s.other_points,
            accuracy_rate=s.accuracy_rate,
            updated_at=s.updated_at,
        )
        for s in scores
    ]


@router.get("/leaderboard/score", response_model=List[MarketLeaderboardOut])
async def score_leaderboard(db: AsyncSession = Depends(get_db)):
    """比分玩法排行榜。"""
    return await build_market_leaderboard(db, "比分")


@router.get("/leaderboard/total-goals", response_model=List[MarketLeaderboardOut])
async def total_goals_leaderboard(db: AsyncSession = Depends(get_db)):
    """总进球数玩法排行榜。"""
    return await build_market_leaderboard(db, "总进球数")


@router.get("/leaderboard/half-full", response_model=List[MarketLeaderboardOut])
async def half_full_leaderboard(db: AsyncSession = Depends(get_db)):
    """半全场玩法排行榜。"""
    return await build_market_leaderboard(db, "半全场")
