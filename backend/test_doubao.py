import asyncio
import httpx
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models import Match
from app.services.prompt_builder import build_prediction_prompt
from app.config import settings

DATABASE_URL = "sqlite+aiosqlite:///./lottery_ai.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Match).limit(1))
        match = result.scalar_one_or_none()
        prompt = build_prediction_prompt(match)

        timeout = httpx.Timeout(connect=30.0, read=180.0, write=180.0, pool=180.0)
        client = AsyncOpenAI(
            api_key=settings.DOUBAO_API_KEY,
            base_url=settings.DOUBAO_ENDPOINT,
            timeout=timeout,
            http_client=httpx.AsyncClient(
                timeout=timeout,
                proxy=None,
                follow_redirects=True,
                trust_env=False,
            ),
        )

        response = await client.chat.completions.create(
            model=settings.DOUBAO_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一名资深足球数据分析师，擅长通过赔率、支持率等市场信号分析比赛走势。"
                        "请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        content = response.choices[0].message.content
        print("Content length:", len(content))
        print(content[:1500])


if __name__ == "__main__":
    asyncio.run(main())
