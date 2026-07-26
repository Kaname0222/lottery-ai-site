import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models import LLMProvider

logger = logging.getLogger(__name__)

DEFAULT_PROVIDERS = [
    {
        "name": "gpt",
        "display_name": "GPT",
        "model_name": settings.OPENAI_MODEL,
        "api_base_url": "https://api.openai.com/v1",
        "api_key_env_name": "OPENAI_API_KEY",
        "is_active": settings.OPENAI_ENABLED,
    },
    {
        "name": "gemini",
        "display_name": "Gemini",
        "model_name": settings.GEMINI_MODEL,
        "api_base_url": None,
        "api_key_env_name": "GEMINI_API_KEY",
        "is_active": settings.GEMINI_ENABLED,
    },
    {
        "name": "deepseek",
        "display_name": "DeepSeek",
        "model_name": settings.DEEPSEEK_MODEL,
        "api_base_url": "https://api.deepseek.com/v1",
        "api_key_env_name": "DEEPSEEK_API_KEY",
        "is_active": settings.DEEPSEEK_ENABLED,
    },
    {
        "name": "kimi",
        "display_name": "Kimi",
        "model_name": settings.KIMI_MODEL,
        "api_base_url": "https://api.moonshot.cn/v1",
        "api_key_env_name": "KIMI_API_KEY",
        "is_active": settings.KIMI_ENABLED,
    },
    {
        "name": "doubao",
        "display_name": "豆包",
        "model_name": settings.DOUBAO_MODEL or "doubao-pro-32k",
        "api_base_url": settings.DOUBAO_ENDPOINT,
        "api_key_env_name": "DOUBAO_API_KEY",
        "is_active": settings.DOUBAO_ENABLED,
    },
    {
        "name": "qianwen",
        "display_name": "千问",
        "model_name": settings.QIANWEN_MODEL or "qwen-turbo",
        "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env_name": "QIANWEN_API_KEY",
        "is_active": settings.QIANWEN_ENABLED,
    },
    {
        "name": "personal",
        "display_name": "个人预测",
        "model_name": "personal",
        "api_base_url": None,
        "api_key_env_name": "PERSONAL_PREDICTIONS",
        "is_active": False,
    },
]


async def seed_providers(db: AsyncSession):
    """初始化 LLM provider 配置（幂等），并同步 .env 中的模型名变更。"""
    for cfg in DEFAULT_PROVIDERS:
        result = await db.execute(select(LLMProvider).where(LLMProvider.name == cfg["name"]))
        provider = result.scalar_one_or_none()
        if not provider:
            provider = LLMProvider(
                name=cfg["name"],
                display_name=cfg["display_name"],
                model_name=cfg["model_name"],
                api_base_url=cfg["api_base_url"],
                api_key_env_name=cfg["api_key_env_name"],
                is_active=cfg["is_active"],
            )
            db.add(provider)
            logger.info("Seeded provider: %s", cfg["name"])
        else:
            # 同步 .env 中修改的模型名、endpoint 或启用状态
            updated = False
            if provider.model_name != cfg["model_name"]:
                provider.model_name = cfg["model_name"]
                updated = True
            if provider.api_base_url != cfg["api_base_url"]:
                provider.api_base_url = cfg["api_base_url"]
                updated = True
            if provider.is_active != cfg["is_active"]:
                provider.is_active = cfg["is_active"]
                updated = True
            if updated:
                logger.info("Updated provider config: %s", cfg["name"])
    await db.commit()
