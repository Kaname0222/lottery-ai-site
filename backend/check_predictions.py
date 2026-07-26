import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Prediction, Match, LLMProvider

DATABASE_URL = "sqlite+aiosqlite:///./lottery_ai.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(LLMProvider.name, LLMProvider.model_name, LLMProvider.is_active))
        providers = result.all()
        print("Providers:")
        for p in providers:
            print(" ", p)

        result = await db.execute(select(func.count(Match.id)))
        matches = result.scalar()
        print(f"Matches: {matches}")

        result = await db.execute(
            select(LLMProvider.name, func.count(Prediction.id))
            .join(Prediction, Prediction.provider_id == LLMProvider.id)
            .group_by(LLMProvider.name)
        )
        counts = result.all()
        print("Predictions by provider:")
        for name, c in counts:
            print(f"  {name}: {c}")

        result = await db.execute(
            select(Match.home_team, Match.away_team, LLMProvider.name, Prediction.home_score, Prediction.away_score, Prediction.confidence)
            .join(Match, Prediction.match_id == Match.id)
            .join(LLMProvider, Prediction.provider_id == LLMProvider.id)
            .limit(15)
        )
        print("Sample predictions:")
        for row in result.all():
            print(" ", row)


if __name__ == "__main__":
    asyncio.run(main())
