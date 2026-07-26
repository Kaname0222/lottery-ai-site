import logging
import os
from typing import List, Optional
from uuid import UUID
from app.config import settings
from app.models import LLMProvider as LLMProviderModel
from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import OpenAICompatibleProvider
from app.services.llm.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


def get_api_key(env_name: str) -> Optional[str]:
    # 优先从 pydantic-settings 读取（已加载 .env），其次读系统环境变量
    return getattr(settings, env_name, None) or os.environ.get(env_name) or None


def build_provider(provider_row: LLMProviderModel) -> Optional[LLMProvider]:
    api_key = get_api_key(provider_row.api_key_env_name)
    if not api_key:
        logger.warning("API key not configured for %s, skipping", provider_row.name)
        return None

    if provider_row.name == "gemini":
        return GeminiProvider(
            provider_id=provider_row.id,
            name=provider_row.name,
            display_name=provider_row.display_name,
            model_name=provider_row.model_name,
            api_key=api_key,
            api_base_url=provider_row.api_base_url,
        )

    return OpenAICompatibleProvider(
        provider_id=provider_row.id,
        name=provider_row.name,
        display_name=provider_row.display_name,
        model_name=provider_row.model_name,
        api_key=api_key,
        api_base_url=provider_row.api_base_url,
    )


def build_providers(provider_rows: List[LLMProviderModel]) -> List[LLMProvider]:
    providers = []
    for row in provider_rows:
        p = build_provider(row)
        if p:
            providers.append(p)
    return providers
