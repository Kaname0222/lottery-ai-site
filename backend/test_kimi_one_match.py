import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match, LLMProvider
from app.services.llm.registry import build_providers

logging.basicConfig(level=logging.INFO)

async def main():
    async with AsyncSessionLocal() as db:
        match = (await db.execute(select(Match).limit(1))).scalar()
        if not match:
            print("No match found")
            return

        provider_rows = (await db.execute(select(LLMProvider).where(LLMProvider.name == "kimi"))).scalars().all()
        providers = build_providers(provider_rows)
        if not providers:
            print("Kimi provider not built")
            return

        provider = providers[0]
        print(f"Testing Kimi prediction for {match.match_id}")
        prompt = f"""分析足球比赛：{match.home_team} vs {match.away_team}。
请输出两个最可能的比分预测，按以下 JSON 格式：
{{"predictions": [{{"home_score": 1, "away_score": 1, "confidence": 0.6, "reason": "理由", "market_reasoning": "赔率理由"}}, {{"home_score": 2, "away_score": 1, "confidence": 0.4, "reason": "理由", "market_reasoning": "赔率理由"}}]}}
只输出 JSON，不要任何额外说明。"""
        try:
            result = await provider.predict(match, prompt)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
