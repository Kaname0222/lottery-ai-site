from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Match
from app.tasks.daily_pipeline import (
    scrape_and_save_matches,
    run_predictions_for_unpredicted,
    fetch_results_and_score,
)
from app.services.scoring import score_finished_matches

router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateMatchOddsRequest(BaseModel):
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    odds_hhad_home_win: Optional[float] = None
    odds_hhad_draw: Optional[float] = None
    odds_hhad_away_win: Optional[float] = None
    score_odds: Optional[dict] = None
    total_goals_odds: Optional[dict] = None
    half_full_odds: Optional[dict] = None


@router.post("/update-match-odds/{match_id}")
async def update_match_odds(
    match_id: str,
    payload: UpdateMatchOddsRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动更新单场比赛赔率（常用于补录已下架比赛的比分赔率）。"""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        return {"error": "match not found", "match_id": match_id}

    updated_fields = []
    for field in [
        "odds_home_win",
        "odds_draw",
        "odds_away_win",
        "odds_hhad_home_win",
        "odds_hhad_draw",
        "odds_hhad_away_win",
        "score_odds",
        "total_goals_odds",
        "half_full_odds",
    ]:
        value = getattr(payload, field)
        if value is not None:
            setattr(match, field, value)
            updated_fields.append(field)

    await db.commit()
    return {"message": "match odds updated", "match_id": match_id, "updated_fields": updated_fields}


@router.post("/run-scrape")
async def run_scrape(db: AsyncSession = Depends(get_db)):
    count = await scrape_and_save_matches(db)
    return {"message": "scrape completed", "matches_count": count}


@router.post("/run-predictions")
async def run_predictions(db: AsyncSession = Depends(get_db)):
    count = await run_predictions_for_unpredicted(db)
    return {"message": "predictions completed", "predictions_count": count}


@router.post("/run-scoring")
async def run_scoring(db: AsyncSession = Depends(get_db)):
    count = await fetch_results_and_score(db)
    return {"message": "scoring completed", "scored_count": count}


@router.post("/recompute-scores")
async def recompute_scores(db: AsyncSession = Depends(get_db)):
    """不重新抓取赛果，仅根据当前数据库中的实际比分和赔率重新计算所有积分。"""
    count = await score_finished_matches(db)
    return {"message": "scores recomputed", "scored_count": count}


@router.post("/run-full-pipeline")
async def run_full_pipeline(db: AsyncSession = Depends(get_db)):
    matches_count = await scrape_and_save_matches(db)
    predictions_count = await run_predictions_for_unpredicted(db)
    scored_count = await fetch_results_and_score(db)
    return {
        "message": "full pipeline completed",
        "matches_count": matches_count,
        "predictions_count": predictions_count,
        "scored_count": scored_count,
    }
