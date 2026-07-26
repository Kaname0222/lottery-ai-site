import asyncio
import sys
sys.path.insert(0, r'C:\Users\19692\Desktop\test\lottery-ai-site\backend')

from app.config import settings
from openai import AsyncOpenAI
import httpx
from httpx import Timeout

async def main():
    timeout = Timeout(connect=30.0, read=180.0, write=180.0, pool=180.0)
    client = AsyncOpenAI(
        api_key=settings.KIMI_API_KEY,
        base_url="https://api.moonshot.cn/v1",
        timeout=timeout,
        max_retries=1,
        http_client=httpx.AsyncClient(timeout=timeout, proxy=None, follow_redirects=True, trust_env=False),
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[{"role": "user", "content": "请只输出 JSON: {\"hello\": \"world\"}"}],
            temperature=1.0,
            max_tokens=100,
        )
        print("Kimi OK:", resp.choices[0].message.content)
    except Exception as e:
        print("Kimi FAILED:", type(e).__name__, e)

asyncio.run(main())
