from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ------------------ Match schemas ------------------

class MatchBase(BaseModel):
    match_id: str
    mid: Optional[str] = None
    league: str
    home_team: str
    away_team: str
    match_date: date
    match_time: Optional[datetime] = None
    sale_status: str = "on_sale"
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None
    handicap: Optional[str] = None
    odds_hhad_home_win: Optional[float] = None
    odds_hhad_draw: Optional[float] = None
    odds_hhad_away_win: Optional[float] = None
    support_home: Optional[float] = None
    support_draw: Optional[float] = None
    support_away: Optional[float] = None
    score_odds: Optional[dict] = None
    total_goals_odds: Optional[dict] = None
    half_full_odds: Optional[dict] = None
    actual_home_score: Optional[int] = None
    actual_away_score: Optional[int] = None
    actual_half_full: Optional[str] = None


class MatchCreate(MatchBase):
    pass


class MatchOut(MatchBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ------------------ Prediction schemas ------------------

class BetRecommendation(BaseModel):
    market: str
    selection: str
    reason: Optional[str] = None
    confidence: Optional[float] = None


class PredictionItem(BaseModel):
    prediction_index: int
    home_score: int
    away_score: int
    confidence: Optional[float] = None
    reasoning_summary: Optional[str] = None
    market_reasoning: Optional[str] = None
    bets: Optional[List[BetRecommendation]] = None
    is_correct: Optional[bool] = None
    points_awarded: Optional[float] = None
    direction_points: Optional[float] = None
    other_points: Optional[float] = None


class PredictionOut(BaseModel):
    id: UUID
    match_id: UUID
    provider_id: UUID
    provider_name: str
    provider_display_name: str
    prediction_index: int
    home_score: int
    away_score: int
    confidence: Optional[float] = None
    reasoning_summary: Optional[str] = None
    market_reasoning: Optional[str] = None
    bets: Optional[List[BetRecommendation]] = None
    is_correct: Optional[bool] = None
    points_awarded: Optional[float] = None
    direction_points: Optional[float] = None
    other_points: Optional[float] = None
    predicted_at: datetime

    class Config:
        from_attributes = True


class PredictionsByProvider(BaseModel):
    provider_id: UUID
    provider_name: str
    provider_display_name: str
    predictions: List[PredictionItem]


# ------------------ Provider schemas ------------------

class ProviderBase(BaseModel):
    name: str
    display_name: str
    model_name: str
    api_base_url: Optional[str] = None
    is_active: bool = True
    api_key_env_name: str


class ProviderCreate(ProviderBase):
    pass


class ProviderOut(ProviderBase):
    id: UUID

    class Config:
        from_attributes = True


class ProviderScoreOut(BaseModel):
    provider_id: UUID
    provider_name: str
    provider_display_name: str
    total_predictions: int
    correct_predictions: int
    direction_correct_predictions: int
    total_points: float
    direction_points: float
    other_points: float
    accuracy_rate: float
    updated_at: datetime

    class Config:
        from_attributes = True


# ------------------ Dashboard schemas ------------------

class DashboardToday(BaseModel):
    date: date
    total_matches: int
    predicted_matches: int
    pending_matches: int
    provider_scores: List[ProviderScoreOut]


class MatchWithPredictions(MatchOut):
    predictions_by_provider: List[PredictionsByProvider]


class PersonalPredictionSubmit(BaseModel):
    half_full: Optional[str] = None
    half_full2: Optional[str] = None
    predictions: List[PredictionItem]


class ManualPredictionSubmit(BaseModel):
    provider_name: str
    half_full: Optional[str] = None
    half_full2: Optional[str] = None
    predictions: List[PredictionItem]
