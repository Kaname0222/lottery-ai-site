import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def main():
    client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url="https://api.moonshot.cn/v1", timeout=60, max_retries=1)
    prompt = """分析一场足球比赛，主队实力较强，客队防守稳健。请输出两个最可能的比分预测，按以下 JSON 格式：
{"predictions": [{"home_score": 2, "away_score": 1, "confidence": 0.6, "reason": "理由"}, {"home_score": 1, "away_score": 1, "confidence": 0.4, "reason": "理由"}]}
只输出 JSON，不要任何额外说明。"""
    try:
        resp = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=1024,
        )
        print("Content:", repr(resp.choices[0].message.content))
        print("Finish reason:", resp.choices[0].finish_reason)
        print("Usage:", resp.usage)
    except Exception as e:
        print("Kimi failed:", e)

asyncio.run(main())
