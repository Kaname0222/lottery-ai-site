import json
import logging
import re
from typing import List
import google.generativeai as genai
from google.generativeai.types import RequestOptions
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


class GeminiProvider(LLMProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 使用 REST 而非 gRPC，否则在 HTTP/SOCKS5 代理下容易出现 SSL 握手失败
        genai.configure(api_key=self.api_key, transport="rest")
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=(
                "你是一名资深足球数据分析师，擅长通过赔率、支持率等市场信号分析比赛走势。"
                "请严格按用户要求的 JSON 格式输出，不要输出任何额外说明。"
            ),
        )

    async def predict(self, match: Match, prompt: str) -> List[PredictionItem]:
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                ),
                # 30s 超时、关闭默认重试，避免网络不可达时无限重试挂死
                request_options=RequestOptions(timeout=30, retry=None),
            )
            content = response.text or "{}"
            return self._parse_predictions(content)
        except Exception as exc:
            logger.error("[gemini] prediction failed for match %s: %s", match.match_id, exc)
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
