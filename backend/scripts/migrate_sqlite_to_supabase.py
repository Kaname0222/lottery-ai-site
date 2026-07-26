"""
将本地 SQLite 数据库迁移到 Supabase/PostgreSQL。
用法（在 backend 目录下）：
    set DATABASE_URL=postgresql+asyncpg://...
    python scripts/migrate_sqlite_to_supabase.py
"""
import asyncio
import os
import sys
from uuid import UUID

from sqlalchemy import create_engine, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

# 把 backend 目录加入路径，确保能导入 app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 先保存真正的目标连接串，再把环境变量临时改成 SQLite，避免导入 app.database 时
# 因缺少 psycopg2 等同步驱动而报错（迁移本身使用 asyncpg）
TARGET_URL = os.environ.get('DATABASE_URL')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./lottery_ai.db'

from app.models import Base, LLMProvider, Match, Prediction, ProviderScore, ScrapeLog

SQLITE_PATH = r'C:\Users\19692\Desktop\test\lottery-ai-site\backend\lottery_ai.db'


def _to_async_url(url: str) -> str:
    """把同步 postgresql URL 转成 asyncpg URL。"""
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+asyncpg://', 1)
    return url


async def migrate():
    if not TARGET_URL:
        print('请先设置环境变量 DATABASE_URL')
        sys.exit(1)

    async_url = _to_async_url(TARGET_URL)
    source_engine = create_engine(f'sqlite:///{SQLITE_PATH}')
    target_engine = create_async_engine(async_url)

    async_session = sessionmaker(target_engine, class_=AsyncSession, expire_on_commit=False)

    # 创建目标表
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 读取源数据
    with Session(source_engine) as src:
        providers = src.execute(select(LLMProvider)).scalars().all()
        matches = src.execute(select(Match)).scalars().all()
        predictions = src.execute(select(Prediction)).scalars().all()
        scores = src.execute(select(ProviderScore)).scalars().all()
        logs = src.execute(select(ScrapeLog)).scalars().all()

    print(f'读取到 {len(providers)} 个 provider, {len(matches)} 场比赛, {len(predictions)} 条预测, {len(scores)} 条积分, {len(logs)} 条日志')

    async with async_session() as session:
        # 清空目标表（按外键依赖顺序）
        await session.execute(delete(Prediction))
        await session.execute(delete(ProviderScore))
        await session.execute(delete(ScrapeLog))
        await session.execute(delete(Match))
        await session.execute(delete(LLMProvider))
        await session.commit()
        print('已清空目标数据库')

        # 插入 provider
        for p in providers:
            session.add(LLMProvider(
                id=p.id,
                name=p.name,
                display_name=p.display_name,
                model_name=p.model_name,
                api_base_url=p.api_base_url,
                is_active=p.is_active,
                api_key_env_name=p.api_key_env_name,
            ))
        await session.commit()
        print(f'已插入 {len(providers)} 个 provider')

        # 插入 match
        for m in matches:
            session.add(Match(
                id=m.id,
                match_id=m.match_id,
                mid=m.mid,
                league=m.league,
                home_team=m.home_team,
                away_team=m.away_team,
                match_date=m.match_date,
                match_time=m.match_time,
                sale_status=m.sale_status,
                odds_home_win=m.odds_home_win,
                odds_draw=m.odds_draw,
                odds_away_win=m.odds_away_win,
                handicap=m.handicap,
                odds_hhad_home_win=m.odds_hhad_home_win,
                odds_hhad_draw=m.odds_hhad_draw,
                odds_hhad_away_win=m.odds_hhad_away_win,
                support_home=m.support_home,
                support_draw=m.support_draw,
                support_away=m.support_away,
                score_odds=m.score_odds,
                total_goals_odds=m.total_goals_odds,
                half_full_odds=m.half_full_odds,
                actual_home_score=m.actual_home_score,
                actual_away_score=m.actual_away_score,
                actual_half_full=m.actual_half_full,
                result_settled_at=m.result_settled_at,
                created_at=m.created_at,
                updated_at=m.updated_at,
            ))
        await session.commit()
        print(f'已插入 {len(matches)} 场比赛')

        # 插入 prediction（分批提交，避免单条大事务超时）
        BATCH_SIZE = 50
        for i, pred in enumerate(predictions):
            session.add(Prediction(
                id=pred.id,
                match_id=pred.match_id,
                provider_id=pred.provider_id,
                prediction_index=pred.prediction_index,
                home_score=pred.home_score,
                away_score=pred.away_score,
                confidence=pred.confidence,
                reasoning_summary=pred.reasoning_summary,
                market_reasoning=pred.market_reasoning,
                bets=pred.bets,
                raw_response=pred.raw_response,
                predicted_at=pred.predicted_at,
                is_correct=pred.is_correct,
                points_awarded=pred.points_awarded,
                direction_points=pred.direction_points,
                other_points=pred.other_points,
            ))
            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
                print(f'已插入 {i + 1}/{len(predictions)} 条预测')
        if len(predictions) % BATCH_SIZE != 0:
            await session.commit()
        print(f'已插入 {len(predictions)} 条预测')

        # 插入 provider score
        for s in scores:
            session.add(ProviderScore(
                id=s.id,
                provider_id=s.provider_id,
                total_predictions=s.total_predictions,
                correct_predictions=s.correct_predictions,
                direction_correct_predictions=s.direction_correct_predictions,
                total_points=s.total_points,
                direction_points=s.direction_points,
                other_points=s.other_points,
                accuracy_rate=s.accuracy_rate,
                updated_at=s.updated_at,
            ))
        await session.commit()
        print(f'已插入 {len(scores)} 条积分')

        # 插入 scrape logs
        for log in logs:
            session.add(ScrapeLog(
                id=log.id,
                run_at=log.run_at,
                log_type=log.log_type,
                status=log.status,
                count=log.count,
                error_message=log.error_message,
            ))
        await session.commit()
        print(f'已插入 {len(logs)} 条日志')

    await target_engine.dispose()
    source_engine.dispose()
    print('迁移完成')


if __name__ == '__main__':
    asyncio.run(migrate())
