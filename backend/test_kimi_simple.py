import asyncio
import sys
sys.path.insert(0, r'C:\Users\19692\Desktop\test\lottery-ai-site\backend')

from app.config import settings
import httpx
from httpx import Timeout
from openai import AsyncOpenAI

async def main():
    timeout = Timeout(connect=30.0, read=180.0, write=180.0, pool=180.0)
    client = AsyncOpenAI(
        api_key=settings.KIMI_API_KEY,
        base_url="https://api.moonshot.cn/v1",
        timeout=timeout,
        max_retries=1,
        http_client=httpx.AsyncClient(timeout=timeout, proxy=None, follow_redirects=True, trust_env=False),
    )

    prompts = [
        "输出 JSON: {\"hello\": \"world\"}",
        "分析一场足球比赛，主队实力较强，客队防守稳健。输出两个最可能比分，按 JSON 格式：{\"predictions\":[{\"home_score\":2,\"away_score\":1,\"confidence\":0.6,\"reason\":\"理由\",\"market_reasoning\":\"理由\"}]}",
        "请输出一个 JSON 对象，包含字段 name 和 age",
    ]

    for p in prompts:
        print(f"\n=== Prompt: {p[:50]}... ===")
        response = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[{"role": "user", "content": p}],
            temperature=1.0,
            max_tokens=4096,
        )
        content = response.choices[0].message.content
        print(f"Response: {repr(content)}")

asyncio.run(main())
