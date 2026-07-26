import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./lottery_ai.db"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = "gpt-4o-mini"
    OPENAI_ENABLED: bool = True
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: Optional[str] = "gemini-1.5-flash"
    GEMINI_ENABLED: bool = True
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: Optional[str] = "deepseek-chat"
    DEEPSEEK_ENABLED: bool = True
    KIMI_API_KEY: Optional[str] = None
    KIMI_MODEL: Optional[str] = "moonshot-v1-8k"
    KIMI_ENABLED: bool = True
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_ENDPOINT: Optional[str] = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: Optional[str] = None
    DOUBAO_ENABLED: bool = True

    QIANWEN_API_KEY: Optional[str] = None
    QIANWEN_MODEL: Optional[str] = "qwen-turbo"
    QIANWEN_ENABLED: bool = True

    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    SCRAPER_REQUEST_TIMEOUT: int = 30
    SCRAPER_RETRY_TIMES: int = 3

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # 是否在后端启动时注册定时任务（赛程抓取、LLM 预测、赛果评分）。
    # 在 Render 等 PaaS 免费实例上建议关闭，改为 GitHub Actions 执行爬虫，避免内存不足/休眠问题。
    SCHEDULED_PIPELINE_ENABLED: bool = True

    # 代理：当梯子只开了系统代理但 Python 不会自动读取 Windows 注册表时，手动指定
    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None


settings = Settings()

# 让 openai/httpx 等库能感知到代理
if settings.HTTP_PROXY:
    os.environ.setdefault("HTTP_PROXY", settings.HTTP_PROXY)
if settings.HTTPS_PROXY:
    os.environ.setdefault("HTTPS_PROXY", settings.HTTPS_PROXY)
