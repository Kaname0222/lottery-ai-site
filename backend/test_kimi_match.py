import asyncio
import sys
sys.path.insert(0, r'C:\Users\19692\Desktop\test\lottery-ai-site\backend')

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Match
from app.services.prompt_builder import build_prediction_prompt
from app.services.llm.openai_provider import OpenAICompatibleProvider

async def main():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Match).where(Match.match_id == '周日202'))
        match = result.scalar_one_or_none()
        if not match:
            print("Match not found")
            return
        prompt = build_prediction_prompt(match)
        provider = OpenAICompatibleProvider(
            provider_id=None,
            name="kimi",
            display_name="Kimi",
            model_name=settings.KIMI_MODEL,
            api_key=settings.KIMI_API_KEY,
            api_base_url="https://api.moonshot.cn/v1",
        )
        try:
            preds = await provider.predict(match, prompt)
            print(f"Got {len(preds)} predictions")
            for p in preds:
                print(p)
        except Exception as e:
            print("ERROR:", type(e).__name__, e)

asyncio.run(main())
