import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def test_model(model_name):
    print(f"=== {model_name} ===")
    client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url="https://api.moonshot.cn/v1", timeout=30, max_retries=1)
    try:
        resp = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "你好，请回复OK"}],
            temperature=1.0 if "k2" in model_name else 0.3,
            max_tokens=10,
        )
        print("OK:", repr(resp.choices[0].message.content))
    except Exception as e:
        print("Failed:", e)

async def main():
    for m in ["kimi-k2.6", "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]:
        await test_model(m)

asyncio.run(main())
