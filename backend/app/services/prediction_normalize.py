"""预测结果规范化工具。"""
from typing import List, Optional
from app.schemas import BetRecommendation, PredictionItem


def _match_result_label(home: int, away: int) -> str:
    if home > away:
        return "胜"
    if home == away:
        return "平"
    return "负"


def _normalize_half_full_part(text: str) -> str:
    return (
        str(text)
        .replace("主胜", "胜")
        .replace("平局", "平")
        .replace("客胜", "负")
        .strip()
    )


def normalize_half_full_selection(home_score: int, away_score: int, selection: str) -> str:
    """
    修正半全场推荐，使其与预测比分自洽：
    1. 支持 "胜胜"、"胜/胜"、"主胜/胜" 等多种写法。
    2. 全场结果必须和比分的胜负对应。
    3. 如果全场比分主队为 0，半场不可能是 主胜，修正为 平。
    4. 如果全场比分客队为 0，半场不可能是 客胜，修正为 平。
    """
    raw = _normalize_half_full_part(str(selection))

    # 兼容无斜杠的简写，如 "胜胜" => ["胜", "胜"]
    if "/" in raw:
        parts = raw.split("/")
    elif len(raw) == 2 and raw[0] in ("胜", "平", "负") and raw[1] in ("胜", "平", "负"):
        parts = [raw[0], raw[1]]
    else:
        return selection

    if len(parts) != 2:
        return selection

    half = _normalize_half_full_part(parts[0])
    full = _normalize_half_full_part(parts[1])

    # 全场结果必须对应比分胜负
    full = _match_result_label(home_score, away_score)

    # 主队全场 0 球，半场不可能胜
    if home_score == 0 and half == "胜":
        half = "平"
    # 客队全场 0 球，半场不可能负
    if away_score == 0 and half == "负":
        half = "平"

    return f"{half}/{full}"


def _normalize_total_goals_selection(home_score: int, away_score: int, selection: str) -> str:
    """总进球数必须等于两队比分之和，格式统一为 'X球'。"""
    return f"{home_score + away_score}球"


def normalize_bets(home_score: int, away_score: int, bets: Optional[List[BetRecommendation]]) -> Optional[List[BetRecommendation]]:
    """规范化单条预测的所有投注推荐。"""
    if not bets:
        return bets

    result = []
    for bet in bets:
        if bet.market == "半全场":
            result.append(
                BetRecommendation(
                    market=bet.market,
                    selection=normalize_half_full_selection(home_score, away_score, bet.selection),
                    reason=bet.reason,
                    confidence=bet.confidence,
                )
            )
        elif bet.market == "总进球数":
            result.append(
                BetRecommendation(
                    market=bet.market,
                    selection=_normalize_total_goals_selection(home_score, away_score, bet.selection),
                    reason=bet.reason,
                    confidence=bet.confidence,
                )
            )
        else:
            result.append(bet)
    return result


def normalize_prediction(pred: PredictionItem) -> PredictionItem:
    """规范化预测项，返回新的 PredictionItem。"""
    return PredictionItem(
        prediction_index=pred.prediction_index,
        home_score=pred.home_score,
        away_score=pred.away_score,
        confidence=pred.confidence,
        reasoning_summary=pred.reasoning_summary,
        market_reasoning=pred.market_reasoning,
        bets=normalize_bets(pred.home_score, pred.away_score, pred.bets),
        is_correct=pred.is_correct,
        points_awarded=pred.points_awarded,
        direction_points=pred.direction_points,
        other_points=pred.other_points,
    )
