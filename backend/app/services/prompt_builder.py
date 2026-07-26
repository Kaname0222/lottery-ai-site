import json
from app.models import Match


_BET_SCHEMA = [
    {
        "market": "胜平负",
        "selection": "主胜 / 平局 / 客胜 之一",
        "reason": "结合赔率与支持率给出的一句话理由",
        "confidence": "0-1 之间的浮点数（可选）",
    },
    {
        "market": "让球胜平负",
        "selection": "让球主胜 / 让球平局 / 让球客胜 之一，需结合让球数",
        "reason": "结合让球盘口与赔率给出的一句话理由",
        "confidence": "0-1 之间的浮点数（可选）",
    },
    {
        "market": "比分",
        "selection": "如 2:1",
        "reason": "结合比分赔率给出的一句话理由",
        "confidence": "0-1 之间的浮点数（可选）",
    },
    {
        "market": "总进球数",
        "selection": "如 2球",
        "reason": "结合总进球赔率给出的一句话理由",
        "confidence": "0-1 之间的浮点数（可选）",
    },
    {
        "market": "半全场",
        "selection": "如 平/主胜",
        "reason": "结合半全场赔率给出的一句话理由",
        "confidence": "0-1 之间的浮点数（可选）",
    },
]


def build_prediction_prompt(match: Match) -> str:
    """为单场比赛构造给 LLM 的预测 prompt。"""
    odds_text = ""
    if match.odds_home_win and match.odds_draw and match.odds_away_win:
        odds_text += (
            f"胜平负赔率：主胜 {match.odds_home_win}，平局 {match.odds_draw}，客胜 {match.odds_away_win}。"
        )
    if match.handicap and match.odds_hhad_home_win and match.odds_hhad_draw and match.odds_hhad_away_win:
        odds_text += (
            f"让球{match.handicap}赔率：主胜 {match.odds_hhad_home_win}，"
            f"平局 {match.odds_hhad_draw}，客胜 {match.odds_hhad_away_win}。"
        )
    if match.total_goals_odds:
        odds_text += f"总进球数赔率：{json.dumps(match.total_goals_odds, ensure_ascii=False)}。"
    if match.score_odds:
        top_scores = sorted(match.score_odds.items(), key=lambda x: x[1])[:8]
        odds_text += f"热门比分赔率：{json.dumps(dict(top_scores), ensure_ascii=False)}。"
    if match.half_full_odds:
        top_hf = sorted(match.half_full_odds.items(), key=lambda x: x[1])[:8]
        odds_text += f"热门半全场赔率：{json.dumps(dict(top_hf), ensure_ascii=False)}。"

    support_text = ""
    if match.support_home is not None and match.support_draw is not None and match.support_away is not None:
        support_text = (
            f"用户支持率：主胜 {match.support_home}%，平局 {match.support_draw}%，客胜 {match.support_away}%"
        )

    handicap_text = f"让球：{match.handicap}" if match.handicap else ""

    match_time_str = match.match_time.strftime("%Y-%m-%d %H:%M") if match.match_time else "未知"

    schema = {
        "predictions": [
            {
                "home_score": "整数",
                "away_score": "整数",
                "confidence": "0-1 之间的浮点数",
                "reason": "基于基本面的一句话理由",
                "market_reasoning": "基于赔率与支持率分析的操盘意图解读",
                "bets": _BET_SCHEMA,
            },
            {
                "home_score": "整数",
                "away_score": "整数",
                "confidence": "0-1 之间的浮点数",
                "reason": "基于基本面的一句话理由",
                "market_reasoning": "基于赔率与支持率分析的操盘意图解读",
                "bets": _BET_SCHEMA,
            },
        ]
    }

    prompt = f"""请对以下足球比赛进行分析，并输出两条最可能的比分预测。

联赛：{match.league}
比赛时间：{match_time_str}
主队：{match.home_team}
客队：{match.away_team}
{handicap_text}
{odds_text}
{support_text}

要求：
1. 给出两条最可能比分，信心分之和约等于 1。
2. 对每条预测提供：比分、信心分、基本面理由、市场原因分析。
3. "市场原因分析"需要结合赔率变化意图与支持率分布，分析机构可能的诱导方向或真实看好方向。
4. 对每条预测，再给出 5 种玩法的推荐投注选项及理由：胜平负、让球胜平负、比分、总进球数、半全场。
   - selection 必须是当前赔率列表中存在的选项，不要编造没有给出的选项。
   - reason 用一句话说明为什么选这个选项。
   - confidence 为可选，表示对该推荐的信心（0-1）。
5. 严格按以下 JSON Schema 输出，不要包含任何额外文本：

{json.dumps(schema, ensure_ascii=False, indent=2)}
"""
    return prompt
