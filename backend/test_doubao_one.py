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
    output_lines = []
    async with AsyncSessionLocal() as db:
        match = (await db.execute(select(Match).where(Match.match_id == "周日202"))).scalar()
        provider_rows = (await db.execute(select(LLMProvider).where(LLMProvider.name == "doubao"))).scalars().all()
        providers = build_providers(provider_rows)
        if not providers:
            output_lines.append("Doubao provider not built")
            with open("doubao_test_result.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            return
        provider = providers[0]
        prompt = build_prediction_prompt(match)
        output_lines.append(f"Prompt length: {len(prompt)}")
        try:
            result = await provider.predict(match, prompt)
            output_lines.append(f"Result count: {len(result)}")
            for r in result:
                output_lines.append(f"  {r.home_score}:{r.away_score} conf={r.confidence}")
        except Exception as e:
            output_lines.append(f"Error: {type(e).__name__}: {e}")
    
    with open("doubao_test_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("\n".join(output_lines))

asyncio.run(main())
