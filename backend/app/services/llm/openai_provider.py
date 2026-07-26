import json
import logging
import re
from typing import List, Optional
import httpx
from httpx import Timeout
from openai import AsyncOpenAI
from app.services.llm.base import LLMProvider
from app.models import Match
from app.schemas import PredictionItem, BetRecommendation
from app.services.prediction_normalize import normalize_prediction

logger = logging.getLogger(__name__)


def _strip_markdown_code_blocks(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:\w+)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


# 连接 30s，读写 180s；Doubao 等模型在长提示下响应较慢，需要更宽松的读取超时
_OPENAI_TIMEOUT = Timeout(connect=30.0, read=180.0, write=180.0, pool=180.0)


class OpenAICompatibleProvider(LLMProvider):
    """兼容 OpenAI 接口的 provider，可用于 GPT、DeepSeek、Kimi、豆包。"""

    # 国内服务走代理反而容易连接失败/限速，直接连接
    _NO_PROXY_PROVIDERS = {"kimi", "doubao", "deepseek", "qianwen"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        client_kwargs = {
            "api_key": self.api_key,
            "timeout": _OPENAI_TIMEOUT,
            "max_retries": 1,
        }
        if self.api_base_url:
            client_kwargs["base_url"] = self.api_base_url

        # 为国内 provider 创建不走系统代理的 httpx client
        if self.name in self._NO_PROXY_PROVIDERS:
            client_kwargs["http_client"] = httpx.AsyncClient(
                timeout=_OPENAI_TIMEOUT,
                proxy=None,
                follow_redirects=True,
                trust_env=False,  # 禁用 HTTP_PROXY/HTTPS_PROXY 环境变量
            )

        self.client = AsyncOpenAI(**client_kwargs)

    async def predict(self, match: Match, prompt: str) -> List[PredictionItem]:
        try:
            create_kwargs = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是一名资深足球数据分析师，擅长通过赔率、支持率等市场信号分析比赛走势。"
                            "请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 1.0 if self.name == "kimi" else 0.3,
                "max_tokens": 4096,
            }
            # Kimi 的 kimi-k2.6 对 response_format={"type": "json_object"} 支持不稳定，
            # 经常返回空内容；依赖 system prompt 要求 JSON 输出更可靠。
            if self.name != "kimi":
                create_kwargs["response_format"] = {"type": "json_object"}

            response = await self.client.chat.completions.create(**create_kwargs)
            content = response.choices[0].message.content or "{}"
            return self._parse_predictions(content)
        except Exception as exc:
            logger.error("[%s] prediction failed for match %s: %s", self.name, match.match_id, exc)
            return []

    def _parse_predictions(self, content: str) -> List[PredictionItem]:
        data = json.loads(_strip_markdown_code_blocks(content))
        predictions = data.get("predictions", [])
        result = []
        for idx, item in enumerate(predictions[:2], start=1):
            bets = []
            for b in item.get("bets") or []:
                try:
                    bets.append(
                        BetRecommendation(
                            market=str(b.get("market", "")),
                            selection=str(b.get("selection", "")),
                            reason=b.get("reason"),
                            confidence=float(b["confidence"]) if b.get("confidence") is not None else None,
                        )
                    )
                except Exception:
                    continue
            result.append(
                normalize_prediction(
                    PredictionItem(
                        prediction_index=idx,
                        home_score=int(item.get("home_score", 0)),
                        away_score=int(item.get("away_score", 0)),
                        confidence=float(item.get("confidence", 0)) if item.get("confidence") is not None else None,
                        reasoning_summary=item.get("reason") or item.get("reasoning_summary"),
                        market_reasoning=item.get("market_reasoning"),
                        bets=bets or None,
                    )
                )
            )
        return result
