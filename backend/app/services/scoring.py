import json
import logging
from typing import List, Tuple, Optional
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Match, Prediction, ProviderScore, LLMProvider, now_beijing

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
    """统一 selection 格式，便于比较和赔率查找。"""
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
        return s.replace("球", "").replace("两", "2").replace("三", "3").replace("四", "4").replace("五", "5")
    if market == "比分":
        # 统一中英文冒号、横杠、空格等分隔符为英文冒号
        return s.replace("：", ":").replace("-", ":").replace("–", ":").replace("—", ":").replace(" ", "")
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


def evaluate_prediction_market(
    prediction: Prediction, match: Match, market: str
) -> Optional[Tuple[float, bool]]:
    """评估单条预测在指定玩法上的积分与是否命中。

    返回 None 表示该场比赛此玩法暂无实际结果或该预测未推荐此玩法。
    """
    actual_results = _build_actual_results(match)
    if actual_results is None:
        return None
    if actual_results.get(market) is None:
        return None

    bets = prediction.bets or []
    for bet in bets:
        if bet.get("market") != market:
            continue
        if _bet_hits(bet, actual_results):
            odds = _get_odds_for_bet(bet, match)
            if odds and odds > 0:
                points = round(odds * STAKE - STAKE, 2)
            else:
                points = LOSE_POINTS
            return points, points > 0
        else:
            return LOSE_POINTS, False

    return None


async def build_market_leaderboard(db: AsyncSession, market: str) -> list[dict]:
    """按指定玩法（比分/总进球数/半全场）构建排行榜，实时计算不做持久化。

    规则：同一场比赛同一 AI 先取"其他玩法"（比分+总进球数+半全场）
    总分更高的那条预测，再用该预测计算指定玩法的命中与积分。
    """
    if market not in OTHER_MARKETS:
        raise ValueError(f"Unsupported market: {market}")

    result = await db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(
            Match.actual_home_score.isnot(None),
            Match.actual_away_score.isnot(None),
        )
        .options(selectinload(Prediction.provider))
    )
    rows = result.all()

    # 按 (provider_id, match_id) 分组，先保留其他玩法总分更高的那条预测
    grouped: dict = {}
    for prediction, match in rows:
        other_total = 0.0
        has_any = False
        for m in OTHER_MARKETS:
            market_result = evaluate_prediction_market(prediction, match, m)
            if market_result is not None:
                has_any = True
                other_total += market_result[0]
        if not has_any:
            continue

        key = (prediction.provider_id, prediction.match_id)
        if key not in grouped or other_total > grouped[key]["other_total"]:
            grouped[key] = {
                "provider": prediction.provider,
                "prediction": prediction,
                "match": match,
                "other_total": other_total,
            }

    stats: dict = {}
    for item in grouped.values():
        provider = item["provider"]
        prediction = item["prediction"]
        match = item["match"]

        market_result = evaluate_prediction_market(prediction, match, market)
        if market_result is None:
            continue
        points, is_correct = market_result

        if provider.id not in stats:
            stats[provider.id] = {
                "provider_id": provider.id,
                "provider_name": provider.name,
                "provider_display_name": provider.display_name,
                "total": 0,
                "correct": 0,
                "points": 0.0,
            }

        stats[provider.id]["total"] += 1
        stats[provider.id]["points"] += points
        if is_correct:
            stats[provider.id]["correct"] += 1

    leaderboard = []
    for item in stats.values():
        total = item["total"]
        leaderboard.append(
            {
                "provider_id": item["provider_id"],
                "provider_name": item["provider_name"],
                "provider_display_name": item["provider_display_name"],
                "total_predictions": total,
                "correct_predictions": item["correct"],
                "total_points": round(item["points"], 2),
                "accuracy_rate": round(item["correct"] / total, 4) if total > 0 else 0.0,
                "updated_at": now_beijing(),
            }
        )

    leaderboard.sort(
        key=lambda x: (-x["total_points"], -x["correct_predictions"], x["provider_name"])
    )
    return leaderboard


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
    """根据 predictions 表重新计算每家 AI 的累计积分与准确率。

    规则：同一场比赛同一个 AI 有两次预测。先计算每条预测在
    比分 + 总进球数 + 半全场 三个方向上的总分，取总分更高的那条预测。
    主排行榜 other_points 为该最佳预测在三个方向上的积分之和。
    方向玩法（胜平负、让球胜平负）仍按每个玩法分别取最高分后相加。
    """
    DIRECTION_MARKETS_LIST = ["胜平负", "让球胜平负"]
    OTHER_MARKETS_LIST = ["比分", "总进球数", "半全场"]

    provider_result = await db.execute(select(LLMProvider))
    providers = provider_result.scalars().all()

    for provider in providers:
        result = await db.execute(
            select(Prediction, Match)
            .join(Match, Prediction.match_id == Match.id)
            .where(
                Prediction.provider_id == provider.id,
                Match.actual_home_score.isnot(None),
                Match.actual_away_score.isnot(None),
            )
        )
        rows = result.all()

        # 按 match_id 分组
        by_match: dict = {}
        for prediction, match in rows:
            by_match.setdefault(match.id, {"match": match, "predictions": []})
            by_match[match.id]["predictions"].append(prediction)

        total = 0
        correct = 0
        direction_correct = 0
        total_direction_points = 0.0
        total_other_points = 0.0

        for data in by_match.values():
            match = data["match"]
            predictions = data["predictions"]

            # 1. 找出其他玩法（比分+总进球数+半全场）总分最高的预测
            best_other_prediction = None
            best_other_total = None
            for prediction in predictions:
                other_total = 0.0
                has_any = False
                for market in OTHER_MARKETS_LIST:
                    market_result = evaluate_prediction_market(prediction, match, market)
                    if market_result is not None:
                        has_any = True
                        other_total += market_result[0]
                if has_any:
                    if best_other_total is None or other_total > best_other_total:
                        best_other_total = other_total
                        best_other_prediction = prediction

            if best_other_prediction is not None:
                total += 1
                total_other_points += best_other_total
                if best_other_total > 0:
                    correct += 1

            # 2. 方向玩法：每个市场取两次预测中的最高分
            match_direction = 0.0
            for market in DIRECTION_MARKETS_LIST:
                market_best = None
                for prediction in predictions:
                    market_result = evaluate_prediction_market(prediction, match, market)
                    if market_result is None:
                        continue
                    points, _ = market_result
                    if market_best is None or points > market_best:
                        market_best = points
                if market_best is not None:
                    match_direction += market_best

            total_direction_points += match_direction
            # 方向玩法：至少命中一个方向（两个都未命中为 -4，命中一个则 > -2）
            if match_direction > LOSE_POINTS:
                direction_correct += 1

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
        score.total_points = round(float(total_other_points), 2)
        score.direction_points = round(float(total_direction_points), 2)
        score.other_points = round(float(total_other_points), 2)
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
