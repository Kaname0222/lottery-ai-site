import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match, LLMProvider
from app.services.llm.registry import build_providers
from app.services.prompt_builder import build_prediction_prompt

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def main():
    async with AsyncSessionLocal() as db:
        matches = (await db.execute(select(Match).order_by(Match.match_id))).scalars().all()
        provider_rows = (await db.execute(select(LLMProvider).where(LLMProvider.is_active == True))).scalars().all()
        providers = build_providers(provider_rows)

        for match in matches:
            print(f"\n=== {match.match_id}: {match.home_team} vs {match.away_team} ===")
            prompt = build_prediction_prompt(match)
            for provider in providers:
                try:
                    result = await provider.predict(match, prompt)
                    print(f"  {provider.name}: {len(result)} predictions")
                    if result:
                        for r in result:
                            print(f"    {r.home_score}:{r.away_score} conf={r.confidence}")
                except Exception as e:
                    print(f"  {provider.name}: ERROR {e}")

asyncio.run(main())
