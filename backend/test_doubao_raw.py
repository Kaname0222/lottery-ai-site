import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Match, LLMProvider
from app.services.llm.registry import build_providers
from app.services.prompt_builder import build_prediction_prompt

logging.basicConfig(level=logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def main():
    output_lines = []
    async with AsyncSessionLocal() as db:
        match = (await db.execute(select(Match).where(Match.match_id == "周日202"))).scalar()
        provider_rows = (await db.execute(select(LLMProvider).where(LLMProvider.name == "doubao"))).scalars().all()
        providers = build_providers(provider_rows)
        provider = providers[0]
        prompt = build_prediction_prompt(match)
        output_lines.append(f"Prompt length: {len(prompt)}")
        try:
            response = await provider.client.chat.completions.create(
                model=provider.model_name,
                messages=[
                    {"role": "system", "content": "你是一名资深足球数据分析师，擅长通过赔率、支持率等市场信号分析比赛走势。请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            output_lines.append(f"Content: {repr(content)}")
            output_lines.append(f"Finish reason: {response.choices[0].finish_reason}")
            output_lines.append(f"Usage: {response.usage}")
        except Exception as e:
            output_lines.append(f"Error: {type(e).__name__}: {e}")
    
    with open("doubao_raw_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print("\n".join(output_lines))

asyncio.run(main())
