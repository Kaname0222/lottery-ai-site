import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Match, LLMProvider, Prediction, ScrapeLog, now_beijing
from app.schemas import PredictionItem
from app.services.scraper.china_sports_lottery import scrape_matches
from app.services.scraper.parser import ParsedMatch
from app.services.scraper.result_scraper import (
    scrape_lottery_results,
    half_full_result,
    fetch_match_result,
)
from app.services.llm.registry import build_providers
from app.services.llm.rate_limiter import RateLimiter
from app.services.prompt_builder import build_prediction_prompt
from app.services.scoring import score_finished_matches

logger = logging.getLogger(__name__)


async def scrape_and_save_matches(db: AsyncSession) -> int:
    """抓取赛程并 upsert 到数据库，返回比赛数量。"""
    log = ScrapeLog(log_type="matches", status="running")
    db.add(log)
    await db.commit()

    try:
        parsed_matches = await scrape_matches()
        count = 0
        for pm in parsed_matches:
            result = await db.execute(select(Match).where(Match.match_id == pm.match_id))
            match = result.scalar_one_or_none()
            if not match:
                match = Match(match_id=pm.match_id)
                db.add(match)

            match.mid = pm.mid or match.mid
            match.league = pm.league
            match.home_team = pm.home_team
            match.away_team = pm.away_team
            match.match_date = pm.match_date
            match.match_time = pm.match_time
            match.handicap = pm.handicap
            match.odds_home_win = pm.odds_home_win
            match.odds_draw = pm.odds_draw
            match.odds_away_win = pm.odds_away_win
            match.odds_hhad_home_win = pm.odds_hhad_home_win
            match.odds_hhad_draw = pm.odds_hhad_draw
            match.odds_hhad_away_win = pm.odds_hhad_away_win
            match.support_home = pm.support_home
            match.support_draw = pm.support_draw
            match.support_away = pm.support_away
            match.score_odds = pm.score_odds
            match.total_goals_odds = pm.total_goals_odds
            match.half_full_odds = pm.half_full_odds
            count += 1

        log.status = "success"
        log.count = count
        await db.commit()
        logger.info("Saved/updated %d matches", count)
        return count
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        await db.commit()
        logger.error("Scrape matches failed: %s", exc)
        raise


def _naive_beijing_now() -> datetime:
    """返回与数据库中 naive 北京字段对齐的当前时间。"""
    return now_beijing()


async def run_predictions_for_unpredicted(db: AsyncSession) -> int:
    """对未预测的比赛调用 LLM，返回生成的预测条数。"""
    provider_rows_result = await db.execute(select(LLMProvider).where(LLMProvider.is_active == True))
    provider_rows = provider_rows_result.scalars().all()
    providers = build_providers(provider_rows)
    if not providers:
        logger.warning("No LLM providers configured, skip predictions")
        return 0

    # 选择所有未开始的比赛；按 provider 维度的去重在循环内处理，
    # 这样即使某场比赛已有部分模型的预测，也能继续让其余模型预测。
    result = await db.execute(
        select(Match).where(Match.match_time >= _naive_beijing_now()).order_by(Match.match_time)
    )
    matches = result.scalars().all()
    logger.info("Found %d future matches to process", len(matches))

    rate_limiter = RateLimiter(max_concurrent=len(providers))
    total_created = 0

    for match in matches:
        # 判断每个 provider 对该比赛还缺几条预测
        needed_providers = []
        for provider in providers:
            existing_count = (
                await db.execute(
                    select(func.count(Prediction.id)).where(
                        Prediction.match_id == match.id,
                        Prediction.provider_id == provider.provider_id,
                    )
                )
            ).scalar() or 0
            if existing_count < 2:
                needed_providers.append(provider)

        if not needed_providers:
            logger.debug("Match %s already has predictions from all providers", match.match_id)
            continue

        prompt = build_prediction_prompt(match)
        coros = [p.predict(match, prompt) for p in needed_providers]
        predictions_per_provider = await rate_limiter.gather(coros)

        for provider, predictions in zip(needed_providers, predictions_per_provider):
            for pred in predictions:
                # 再次检查是否已存在，防止并发/重入导致唯一约束冲突
                existing = await db.execute(
                    select(Prediction).where(
                        Prediction.match_id == match.id,
                        Prediction.provider_id == provider.provider_id,
                        Prediction.prediction_index == pred.prediction_index,
                    )
                )
                if existing.scalar_one_or_none():
                    logger.debug(
                        "Prediction already exists for match %s provider %s index %s",
                        match.match_id,
                        provider.name,
                        pred.prediction_index,
                    )
                    continue

                bets_data = None
                if pred.bets:
                    bets_data = [b.model_dump() for b in pred.bets]

                db.add(
                    Prediction(
                        match_id=match.id,
                        provider_id=provider.provider_id,
                        prediction_index=pred.prediction_index,
                        home_score=pred.home_score,
                        away_score=pred.away_score,
                        confidence=pred.confidence,
                        reasoning_summary=pred.reasoning_summary,
                        market_reasoning=pred.market_reasoning,
                        bets=bets_data,
                        raw_response=None,
                    )
                )
                total_created += 1

        await db.commit()

    logger.info("Created %d predictions", total_created)
    return total_created


async def fetch_results_and_score(db: AsyncSession) -> int:
    """从体彩赛果开奖页批量抓取实际比分并触发评分。"""
    log = ScrapeLog(log_type="results", status="running")
    db.add(log)
    await db.commit()

    try:
        results = await scrape_lottery_results()
        if not results:
            log.status = "success"
            log.count = 0
            await db.commit()
            logger.info("No results fetched from lottery results page")
            return 0

        updated = 0
        for result in results:
            # 只处理有全场比分的比赛（取消/无效场次无比分）
            if not result.full_time_score:
                continue

            score_match = re.match(r"(\d+):(\d+)", result.full_time_score)
            if not score_match:
                continue
            home_score = int(score_match.group(1))
            away_score = int(score_match.group(2))

            # 优先用 match_id 匹配，再用 mid 兜底
            stmt = select(Match).where(Match.match_id == result.match_id)
            match_result = await db.execute(stmt)
            match = match_result.scalar_one_or_none()
            if not match and result.mid:
                stmt = select(Match).where(Match.mid == result.mid)
                match_result = await db.execute(stmt)
                match = match_result.scalar_one_or_none()
            if not match:
                continue

            new_half_full = half_full_result(result.half_time_score, result.full_time_score)
            # 更新未完成比赛，或同步/修正已有比赛的结果
            if (
                match.actual_home_score is None
                or match.actual_home_score != home_score
                or match.actual_away_score != away_score
                or match.actual_half_full != new_half_full
            ):
                match.actual_home_score = home_score
                match.actual_away_score = away_score
                match.actual_half_full = new_half_full
                match.result_settled_at = _naive_beijing_now()
                updated += 1

        # 兜底：如果批量赛果页没有抓到任何结果，尝试逐个比赛详情页抓取
        if updated == 0:
            cutoff = _naive_beijing_now() - timedelta(hours=2)
            fallback_result = await db.execute(
                select(Match)
                .where(Match.match_time <= cutoff)
                .where(Match.actual_home_score.is_(None))
                .where(Match.mid.isnot(None))
            )
            fallback_matches = fallback_result.scalars().all()
            logger.info("Batch results empty, falling back to %d detail pages", len(fallback_matches))
            for match in fallback_matches:
                score = fetch_match_result(match.mid)
                if score:
                    match.actual_home_score, match.actual_away_score = score
                    match.result_settled_at = _naive_beijing_now()
                    updated += 1
            await db.commit()

        scored = await score_finished_matches(db)

        log.status = "success"
        log.count = updated
        await db.commit()

        logger.info("Updated %d match results, scored %d predictions", updated, scored)
        return scored
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        await db.commit()
        logger.error("Fetch results and score failed: %s", exc)
        raise


async def run_full_pipeline():
    """供 scheduler 或脚本直接调用的完整流水线。"""
    async with AsyncSessionLocal() as db:
        await scrape_and_save_matches(db)
        await run_predictions_for_unpredicted(db)
        await fetch_results_and_score(db)
