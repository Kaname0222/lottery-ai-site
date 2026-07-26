import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def main():
    client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url="https://api.moonshot.cn/v1", timeout=60, max_retries=1)
    try:
        resp = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[{"role": "user", "content": "输出 JSON: {\"predictions\": [{\"home_score\": 1, \"away_score\": 1}]}"}],
            temperature=1.0,
            max_tokens=1024,
        )
        choice = resp.choices[0]
        msg = choice.message
        print("content:", repr(msg.content))
        print("reasoning_content:", getattr(msg, "reasoning_content", None))
        print("finish_reason:", choice.finish_reason)
        print("usage:", resp.usage)
        print("full msg attrs:", dir(msg))
    except Exception as e:
        print("Failed:", e)

asyncio.run(main())
