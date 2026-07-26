"""导入千问预测结果。

运行方式（在项目根目录下）：
    python -m scripts.import_qianwen
"""
import asyncio
from typing import List, Optional
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match, LLMProvider, Prediction
from app.services.prediction_normalize import normalize_half_full_selection
from app.services.scoring import score_finished_matches


DATA = [
    {"match_id": "周一201", "scores": [(2, 2), (1, 2)], "half_fulls": ["平负", "负负"]},
    {"match_id": "周一202", "scores": [(2, 0), (3, 0)], "half_fulls": ["胜胜"]},
    {"match_id": "周日212", "scores": [(2, 1), (3, 1)], "half_fulls": ["胜胜", "平胜"]},
    {"match_id": "周日213", "scores": [(2, 0), (2, 1)], "half_fulls": ["胜胜", "平胜"]},
    {"match_id": "周日214", "scores": [(1, 2), (1, 3)], "half_fulls": ["负负", "平负"]},
    {"match_id": "周日215", "scores": [(0, 2), (1, 3)], "half_fulls": ["负负"]},
    {"match_id": "周日216", "scores": [(1, 1), (1, 2)], "half_fulls": ["平负", "负负"]},
    {"match_id": "周日217", "scores": [(1, 0), (2, 1)], "half_fulls": ["平胜", "胜胜"]},
    {"match_id": "周日218", "scores": [(1, 1), (0, 0)], "half_fulls": ["平平", "平负"]},
]


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


def _build_bets(match: Match, home_score: int, away_score: int, half_full: Optional[str]) -> List[dict]:
    bets = [
        {"market": "胜平负", "selection": _match_result_label(home_score, away_score), "reason": "千问预测"},
        {"market": "比分", "selection": f"{home_score}:{away_score}", "reason": "千问预测"},
        {"market": "总进球数", "selection": f"{home_score + away_score}球", "reason": "千问预测"},
    ]
    hhad = _handicap_result_label(home_score, away_score, match.handicap)
    if hhad:
        bets.append({"market": "让球胜平负", "selection": hhad, "reason": "千问预测"})
    if half_full:
        normalized_hf = normalize_half_full_selection(home_score, away_score, half_full)
        bets.append({"market": "半全场", "selection": normalized_hf, "reason": "千问预测"})
    return bets


async def main():
    async with AsyncSessionLocal() as db:
        provider_result = await db.execute(select(LLMProvider).where(LLMProvider.name == "qianwen"))
        provider = provider_result.scalar_one_or_none()
        if not provider:
            print("千问 provider 不存在，请先运行 seed_providers")
            return

        imported = 0
        for item in DATA:
            match_result = await db.execute(select(Match).where(Match.match_id == item["match_id"]))
            match = match_result.scalar_one_or_none()
            if not match:
                print(f"未找到比赛: {item['match_id']}")
                continue

            # 删除千问对该场比赛的已有预测
            await db.execute(
                Prediction.__table__.delete().where(
                    Prediction.match_id == match.id,
                    Prediction.provider_id == provider.id,
                )
            )

            scores = item["scores"]
            half_fulls = item["half_fulls"]

            # 如果只有一组预测，则两个 prediction_index 使用同一组
            for idx in range(2):
                home_score, away_score = scores[idx] if idx < len(scores) else scores[-1]
                hf = half_fulls[idx] if idx < len(half_fulls) else half_fulls[-1]
                bets = _build_bets(match, home_score, away_score, hf)
                db.add(
                    Prediction(
                        match_id=match.id,
                        provider_id=provider.id,
                        prediction_index=idx + 1,
                        home_score=home_score,
                        away_score=away_score,
                        confidence=None,
                        reasoning_summary="千问预测导入",
                        market_reasoning=None,
                        bets=bets,
                        raw_response=None,
                    )
                )
                imported += 1

        await db.commit()

        # 对已结束比赛触发评分
        scored = await score_finished_matches(db)
        print(f"导入完成：{imported} 条预测，评分 {scored} 条")


if __name__ == "__main__":
    asyncio.run(main())
