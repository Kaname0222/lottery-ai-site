from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Match, Prediction, LLMProvider, now_beijing
from app.schemas import MatchOut, MatchWithPredictions, PredictionsByProvider, PredictionItem, PersonalPredictionSubmit, ManualPredictionSubmit
from app.services.prediction_normalize import normalize_half_full_selection

router = APIRouter(prefix="/matches", tags=["matches"])


def _build_match_with_predictions(match: Match) -> MatchWithPredictions:
    by_provider = {}
    for pred in match.predictions:
        key = pred.provider_id
        if key not in by_provider:
            by_provider[key] = {
                "provider_id": pred.provider_id,
                "provider_name": pred.provider.name,
                "provider_display_name": pred.provider.display_name,
                "predictions": [],
            }
        by_provider[key]["predictions"].append(
            PredictionItem(
                prediction_index=pred.prediction_index,
                home_score=pred.home_score,
                away_score=pred.away_score,
                confidence=pred.confidence,
                reasoning_summary=pred.reasoning_summary,
                market_reasoning=pred.market_reasoning,
                bets=pred.bets,
                is_correct=pred.is_correct,
                points_awarded=pred.points_awarded,
                direction_points=pred.direction_points,
                other_points=pred.other_points,
            )
        )
    match_dict = MatchOut.model_validate(match).model_dump()
    match_dict["predictions_by_provider"] = list(by_provider.values())
    return MatchWithPredictions(**match_dict)


@router.get("", response_model=List[MatchWithPredictions])
async def list_matches(
    match_date: date = None,
    league: str = None,
    include_completed: bool = False,
    personal_not_predicted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Match).order_by(Match.match_time).options(
        selectinload(Match.predictions).selectinload(Prediction.provider)
    )
    filters = []
    if match_date:
        filters.append(Match.match_date == match_date)
    if league:
        filters.append(Match.league == league)
    # 默认不展示已完赛的比赛（自动归档）
    if not include_completed:
        filters.append(Match.actual_home_score.is_(None))
    if personal_not_predicted:
        provider_result = await db.execute(select(LLMProvider.id).where(LLMProvider.name == "personal"))
        personal_id = provider_result.scalar_one_or_none()
        if personal_id:
            subquery = select(Prediction.match_id).where(Prediction.provider_id == personal_id).subquery()
            filters.append(~Match.id.in_(subquery))
    if filters:
        query = query.where(and_(*filters))
    result = await db.execute(query)
    matches = result.scalars().all()
    return [_build_match_with_predictions(m) for m in matches]


@router.get("/{match_id}", response_model=MatchWithPredictions)
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Match)
        .where(Match.match_id == match_id)
        .options(selectinload(Match.predictions).selectinload(Prediction.provider))
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return _build_match_with_predictions(match)


@router.post("/{match_id}/result")
async def set_match_result(
    match_id: str,
    home_score: int,
    away_score: int,
    half_full: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """手动回填实际比分、半全场并触发评分。"""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.actual_home_score = home_score
    match.actual_away_score = away_score
    if half_full:
        match.actual_half_full = half_full
    match.result_settled_at = now_beijing()
    await db.commit()

    from app.services.scoring import score_finished_matches
    scored = await score_finished_matches(db)
    return {"message": "ok", "scored_predictions": scored}


def _match_result_label(home: int, away: int) -> str:
    if home > away:
        return "主胜"
    if home == away:
        return "平局"
    return "客胜"


def _handicap_result_label(home: int, away: int, handicap: Optional[str]) -> Optional[str]:
    if not handicap:
        return None
    try:
        val = float(str(handicap).replace("+", ""))
    except ValueError:
        return None
    adjusted = home + val
    if adjusted > away:
        return "让球主胜"
    if adjusted == away:
        return "让球平局"
    return "让球客胜"


def _build_personal_bets(match: Match, home_score: int, away_score: int, half_full: Optional[str]) -> List[dict]:
    """根据个人预测比分生成五条玩法的投注推荐。"""
    bets = [
        {"market": "胜平负", "selection": _match_result_label(home_score, away_score), "reason": "个人预测"},
        {"market": "比分", "selection": f"{home_score}:{away_score}", "reason": "个人预测"},
        {"market": "总进球数", "selection": f"{home_score + away_score}球", "reason": "个人预测"},
    ]
    hhad = _handicap_result_label(home_score, away_score, match.handicap)
    if hhad:
        bets.append({"market": "让球胜平负", "selection": hhad, "reason": "个人预测"})
    if half_full:
        normalized_hf = normalize_half_full_selection(home_score, away_score, half_full)
        bets.append({"market": "半全场", "selection": normalized_hf, "reason": "个人预测"})
    return bets


@router.post("/{match_id}/personal-prediction")
async def submit_personal_prediction(
    match_id: str,
    data: PersonalPredictionSubmit,
    db: AsyncSession = Depends(get_db),
):
    """提交个人预测，保存到 personal provider，用于参与排行榜评分。"""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    provider_result = await db.execute(select(LLMProvider).where(LLMProvider.name == "personal"))
    provider = provider_result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=500, detail="Personal provider not initialized")

    created = 0
    for pred in data.predictions:
        # 幂等：先删除同场比赛同索引的个人预测
        await db.execute(
            Prediction.__table__.delete().where(
                Prediction.match_id == match.id,
                Prediction.provider_id == provider.id,
                Prediction.prediction_index == pred.prediction_index,
            )
        )

        # prediction_index 1 用 half_full，2 用 half_full2
        hf = data.half_full if pred.prediction_index == 1 else (data.half_full2 or data.half_full)
        bets = _build_personal_bets(match, pred.home_score, pred.away_score, hf)
        db.add(
            Prediction(
                match_id=match.id,
                provider_id=provider.id,
                prediction_index=pred.prediction_index,
                home_score=pred.home_score,
                away_score=pred.away_score,
                confidence=None,
                reasoning_summary="个人预测",
                market_reasoning=None,
                bets=bets,
                raw_response=None,
            )
        )
        created += 1

    await db.commit()

    # 如果比赛已有实际比分，立即评分
    if match.actual_home_score is not None:
        from app.services.scoring import score_finished_matches
        await score_finished_matches(db)

    return {"message": "ok", "created": created}


@router.post("/{match_id}/manual-prediction")
async def submit_manual_prediction(
    match_id: str,
    data: ManualPredictionSubmit,
    db: AsyncSession = Depends(get_db),
):
    """导入指定 provider 的手动预测（如千问、Gemini 等），用于参与排行榜评分。"""
    result = await db.execute(select(Match).where(Match.match_id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    provider_result = await db.execute(
        select(LLMProvider).where(LLMProvider.name == data.provider_name)
    )
    provider = provider_result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider {data.provider_name} not found")

    created = 0
    for pred in data.predictions:
        # 幂等：先删除同场比赛同索引同 provider 的预测
        await db.execute(
            Prediction.__table__.delete().where(
                Prediction.match_id == match.id,
                Prediction.provider_id == provider.id,
                Prediction.prediction_index == pred.prediction_index,
            )
        )

        # prediction_index 1 用 half_full，2 用 half_full2
        hf = data.half_full if pred.prediction_index == 1 else (data.half_full2 or data.half_full)
        bets = _build_personal_bets(match, pred.home_score, pred.away_score, hf)
        db.add(
            Prediction(
                match_id=match.id,
                provider_id=provider.id,
                prediction_index=pred.prediction_index,
                home_score=pred.home_score,
                away_score=pred.away_score,
                confidence=None,
                reasoning_summary=f"{provider.display_name}手动导入",
                market_reasoning=None,
                bets=bets,
                raw_response=None,
            )
        )
        created += 1

    await db.commit()

    # 如果比赛已有实际比分，立即评分
    if match.actual_home_score is not None:
        from app.services.scoring import score_finished_matches
        await score_finished_matches(db)

    return {"message": "ok", "created": created, "provider": provider.display_name}
