import json
import logging
from typing import List, Tuple, Optional
from sqlalchemy import select, func, Integer, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Match, Prediction, ProviderScore, LLMProvider

logger = logging.getLogger(__name__)

STAKE = 2  # 每注本金 2 元
LOSE_POINTS = -STAKE  # 未命中损失本金

# 玩法分类
DIRECTION_MARKETS = {"胜平负", "让球胜平负"}
OTHER_MARKETS = {"比分", "总进球数", "半全场"}


def _match_result(home_score: int, away_score: int) -> str:
    """返回比赛结果：主胜 / 平局 / 客胜。"""
    if home_score > away_score:
        return "主胜"
    if home_score == away_score:
        return "平局"
    return "客胜"


def _handicap_result(home_score: int, away_score: int, handicap: Optional[str]) -> Optional[str]:
    """根据让球盘口计算让球胜平负结果。"""
    if handicap is None or handicap == "":
        return None
    try:
        val = float(str(handicap).replace("+", ""))
    except ValueError:
        return None
    adjusted = home_score + val
    if adjusted > away_score:
        return "让球主胜"
    if adjusted == away_score:
        return "让球平局"
    return "让球客胜"


def _build_actual_results(match: Match) -> Optional[dict]:
    """根据实际比分构建各玩法的实际结果。"""
    if match.actual_home_score is None or match.actual_away_score is None:
        return None

    home = match.actual_home_score
    away = match.actual_away_score
    total = home + away

    return {
        "胜平负": _match_result(home, away),
        "让球胜平负": _handicap_result(home, away, match.handicap),
        "比分": f"{home}:{away}",
        "总进球数": f"{total}球",
        "半全场": match.actual_half_full,
    }


def _normalize_selection(market: str, selection: str) -> str:
    """统一 selection 格式，便于比较。"""
    s = str(selection).strip()
    if market == "让球胜平负":
        if "让球主胜" in s:
            return "让球主胜"
        if "让球平局" in s:
            return "让球平局"
        if "让球客胜" in s:
            return "让球客胜"
    if market == "半全场":
        return s.replace("主胜", "胜").replace("平局", "平").replace("客胜", "负")
    if market == "总进球数":
        return s.replace("球", "")
    return s


def _bet_hits(bet: dict, actual_results: dict) -> bool:
    """判断单条推荐是否命中实际结果。"""
    market = bet.get("market")
    selection = bet.get("selection")
    if not market or not selection:
        return False

    actual = actual_results.get(market)
    if actual is None:
        return False

    return _normalize_selection(market, selection) == _normalize_selection(market, actual)


def _get_odds_for_bet(bet: dict, match: Match) -> Optional[float]:
    """查找某条推荐对应的赔率。"""
    market = bet.get("market")
    selection = bet.get("selection")
    if not market or not selection:
        return None

    normalized = _normalize_selection(market, selection)

    if market == "胜平负":
        if normalized == "主胜":
            return match.odds_home_win
        if normalized == "平局":
            return match.odds_draw
        if normalized == "客胜":
            return match.odds_away_win
    elif market == "让球胜平负":
        if normalized == "让球主胜":
            return match.odds_hhad_home_win
        if normalized == "让球平局":
            return match.odds_hhad_draw
        if normalized == "让球客胜":
            return match.odds_hhad_away_win
    elif market == "比分":
        return match.score_odds.get(selection) if match.score_odds else None
    elif market == "总进球数":
        key = normalized
        return match.total_goals_odds.get(key) if match.total_goals_odds else None
    elif market == "半全场":
        key = normalized
        return match.half_full_odds.get(key) if match.half_full_odds else None

    return None


def evaluate_prediction(prediction: Prediction, match: Match) -> Tuple[float, float, float, bool, int]:
    """
    根据实际比分评估单条预测的所有推荐。
    返回：(总积分, 方向玩法积分, 其他玩法积分, 是否盈利, 命中推荐数)
    命中：odds * 2 - 2；未命中：-2
    """
    actual_results = _build_actual_results(match)
    if actual_results is None:
        return 0.0, 0.0, 0.0, False, 0

    bets = prediction.bets or []
    if not bets:
        return 0.0, 0.0, 0.0, False, 0

    total_points = 0.0
    direction_points = 0.0
    other_points = 0.0
    hit_count = 0
    for bet in bets:
        market = bet.get("market")
        if actual_results.get(market) is None:
            # 该玩法暂无实际结果（如未回填半全场），跳过不计分
            continue
        if _bet_hits(bet, actual_results):
            odds = _get_odds_for_bet(bet, match)
            if odds and odds > 0:
                points = round(odds * STAKE - STAKE, 2)
            else:
                points = LOSE_POINTS
            hit_count += 1
        else:
            points = LOSE_POINTS

        total_points += points
        if market in DIRECTION_MARKETS:
            direction_points += points
        elif market in OTHER_MARKETS:
            other_points += points

    return (
        round(total_points, 2),
        round(direction_points, 2),
        round(other_points, 2),
        other_points > 0,
        hit_count,
    )


async def score_finished_matches(db: AsyncSession) -> int:
    """
    对所有已有实际比分的预测重新评分，并更新 provider_scores。
    返回评分的预测条数。

    注意：这里不限制 points_awarded IS NULL，因为实际比分或赔率可能已更新，
    需要覆盖旧评分以保证积分准确。
    """
    result = await db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(
            Match.actual_home_score.isnot(None),
            Match.actual_away_score.isnot(None),
        )
    )
    rows = result.all()

    scored_count = 0
    for prediction, match in rows:
        points, direction_points, other_points, profitable, hit_count = evaluate_prediction(
            prediction, match
        )
        # 底部只展示比分、总进球、半全场三种玩法的积分
        prediction.points_awarded = other_points
        prediction.direction_points = direction_points
        prediction.other_points = other_points
        prediction.is_correct = profitable
        scored_count += 1
        logger.info(
            "Scored prediction %s for match %s: %.2f points (direction=%.2f, other=%.2f, profitable=%s, hits=%d)",
            prediction.id,
            match.match_id,
            other_points,
            direction_points,
            other_points,
            profitable,
            hit_count,
        )

    await db.commit()
    await _update_provider_scores(db)
    return scored_count


async def _update_provider_scores(db: AsyncSession):
    """根据 predictions 表重新计算每家 AI 的累计积分与准确率。"""
    provider_result = await db.execute(select(LLMProvider))
    providers = provider_result.scalars().all()

    for provider in providers:
        stats_result = await db.execute(
            select(
                func.count(Prediction.id).label("total"),
                func.sum(func.cast(Prediction.is_correct, Integer)).label("correct"),
                func.sum(Prediction.points_awarded).label("points"),
                func.sum(Prediction.direction_points).label("direction_points"),
                func.sum(Prediction.other_points).label("other_points"),
            ).where(Prediction.provider_id == provider.id, Prediction.points_awarded.isnot(None))
        )
        row = stats_result.one_or_none()
        total = row.total or 0
        correct = (row.correct or 0) if row else 0
        points = (row.points or 0) if row else 0
        direction_points = (row.direction_points or 0) if row else 0
        other_points = (row.other_points or 0) if row else 0

        direction_result = await db.execute(
            select(func.count(Prediction.id)).where(
                Prediction.provider_id == provider.id,
                Prediction.points_awarded.isnot(None),
                Prediction.direction_points > LOSE_POINTS,
            )
        )
        direction_correct = direction_result.scalar() or 0

        accuracy = round(correct / total, 4) if total > 0 else 0.0

        score_result = await db.execute(
            select(ProviderScore).where(ProviderScore.provider_id == provider.id)
        )
        score = score_result.scalar_one_or_none()
        if not score:
            score = ProviderScore(provider_id=provider.id)
            db.add(score)

        score.total_predictions = total
        score.correct_predictions = correct
        score.direction_correct_predictions = direction_correct
        score.total_points = round(float(points), 2)
        score.direction_points = round(float(direction_points), 2)
        score.other_points = round(float(other_points), 2)
        score.accuracy_rate = accuracy

    await db.commit()


async def get_leaderboard(db: AsyncSession) -> list[ProviderScore]:
    """获取排行榜：有预测记录的优先，再按其他玩法积分、方向玩法积分排序。"""
    result = await db.execute(
        select(ProviderScore)
        .options(selectinload(ProviderScore.provider))
        .order_by(
            case((ProviderScore.total_predictions > 0, 1), else_=0).desc(),
            ProviderScore.other_points.desc(),
            ProviderScore.direction_points.desc(),
        )
    )
    return result.scalars().all()
