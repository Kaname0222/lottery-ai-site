import asyncio
import sys
sys.path.insert(0, r'C:\Users\19692\Desktop\test\lottery-ai-site\backend')

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Match
from app.services.prompt_builder import build_prediction_prompt
import httpx
from httpx import Timeout
from openai import AsyncOpenAI

async def main():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Match).where(Match.match_id == '周日202'))
        match = result.scalar_one_or_none()
        prompt = build_prediction_prompt(match)

        print(f"Prompt length: {len(prompt)} chars")
        print("Prompt preview:")
        print(prompt[:500])
        print("...")

        timeout = Timeout(connect=30.0, read=180.0, write=180.0, pool=180.0)
        client = AsyncOpenAI(
            api_key=settings.KIMI_API_KEY,
            base_url="https://api.moonshot.cn/v1",
            timeout=timeout,
            max_retries=1,
            http_client=httpx.AsyncClient(timeout=timeout, proxy=None, follow_redirects=True, trust_env=False),
        )

        print("\n=== Test with response_format=json_object ===")
        response = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[
                {"role": "system", "content": "请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"},
                {"role": "user", "content": prompt},
            ],
            temperature=1.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        print(f"Response: {repr(response.choices[0].message.content)}")

        print("\n=== Test without response_format ===")
        response = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[
                {"role": "system", "content": "请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"},
                {"role": "user", "content": prompt},
            ],
            temperature=1.0,
            max_tokens=4096,
        )
        print(f"Response: {repr(response.choices[0].message.content)}")

asyncio.run(main())
