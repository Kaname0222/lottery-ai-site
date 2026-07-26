from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.models import Match
from app.schemas import PredictionItem


class LLMProvider(ABC):
    def __init__(
        self,
        provider_id: UUID,
        name: str,
        display_name: str,
        model_name: str,
        api_key: str,
        api_base_url: Optional[str] = None,
    ):
        self.provider_id = provider_id
        self.name = name
        self.display_name = display_name
        self.model_name = model_name
        self.api_key = api_key
        self.api_base_url = api_base_url

    @abstractmethod
    async def predict(self, match: Match, prompt: str) -> List[PredictionItem]:
        """对单场比赛返回两条预测。"""
        pass
