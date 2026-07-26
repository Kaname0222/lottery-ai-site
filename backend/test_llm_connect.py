import asyncio
import logging
import os

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_openai():
    from openai import AsyncOpenAI

    logger.info("=== Testing OpenAI / GPT ===")
    logger.info("Proxy env: HTTP_PROXY=%s, HTTPS_PROXY=%s", os.environ.get("HTTP_PROXY"), os.environ.get("HTTPS_PROXY"))
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=1)
    try:
        resp = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=5,
        )
        logger.info("OpenAI OK: %s", resp.choices[0].message.content)
        return True
    except Exception as e:
        logger.error("OpenAI failed: %s", e)
        return False


async def test_gemini():
    import google.generativeai as genai
    from google.generativeai.types import RequestOptions

    logger.info("=== Testing Gemini ===")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
    try:
        resp = await model.generate_content_async(
            "Say hi",
            generation_config=genai.types.GenerationConfig(max_output_tokens=5),
            request_options=RequestOptions(timeout=30, retry=None),
        )
        logger.info("Gemini OK: %s", resp.text)
        return True
    except Exception as e:
        logger.error("Gemini failed: %s", e)
        return False


async def test_kimi():
    from openai import AsyncOpenAI

    logger.info("=== Testing Kimi ===")
    client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url="https://api.moonshot.cn/v1", timeout=30, max_retries=1)
    try:
        resp = await client.chat.completions.create(
            model=settings.KIMI_MODEL,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=5,
        )
        logger.info("Kimi OK: %s", resp.choices[0].message.content)
        return True
    except Exception as e:
        logger.error("Kimi failed: %s", e)
        return False


async def main():
    logger.info("Settings proxy: HTTP_PROXY=%s, HTTPS_PROXY=%s", settings.HTTP_PROXY, settings.HTTPS_PROXY)
    await test_openai()
    await test_gemini()
    await test_kimi()


if __name__ == "__main__":
    asyncio.run(main())
