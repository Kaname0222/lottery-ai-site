import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def main():
    client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url="https://api.moonshot.cn/v1", timeout=120, max_retries=1)
    prompt = '分析足球比赛，输出两个最可能的比分预测，JSON格式：{"predictions": [{"home_score": 1, "away_score": 1, "confidence": 0.6, "reason": "理由"}, {"home_score": 2, "away_score": 1, "confidence": 0.4, "reason": "理由"}]}。只输出JSON。'
    for max_tokens in [1024, 2048, 4096, 8192]:
        print(f"=== max_tokens={max_tokens} ===")
        try:
            resp = await client.chat.completions.create(
                model=settings.KIMI_MODEL,
                messages=[
                    {"role": "system", "content": "你是足球数据分析师，严格按JSON格式输出。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=1.0,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            print(f"content length: {len(content) if content else 0}")
            print(f"content: {repr(content[:300])}")
            print(f"finish_reason: {resp.choices[0].finish_reason}")
            print(f"usage: {resp.usage}")
        except Exception as e:
            print(f"failed: {e}")

asyncio.run(main())
