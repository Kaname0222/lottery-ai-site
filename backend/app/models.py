import uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Date,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def _uuid_column():
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )


def now_beijing() -> datetime:
    """返回当前北京时间（naive datetime），与数据库中时间字段统一。"""
    return datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)


class Match(Base):
    __tablename__ = "matches"

    id = _uuid_column()
    match_id = Column(String(32), unique=True, nullable=False, index=True, comment="体彩编号，如 周五201")
    mid = Column(String(32), nullable=True, comment="sporttery 详情页 mid")
    league = Column(String(64), nullable=False)
    home_team = Column(String(128), nullable=False)
    away_team = Column(String(128), nullable=False)
    match_date = Column(Date, nullable=False, index=True)
    match_time = Column(DateTime, nullable=True)
    sale_status = Column(String(32), default="on_sale")

    # 赔率（胜平负固定奖金）
    odds_home_win = Column(Float, nullable=True)
    odds_draw = Column(Float, nullable=True)
    odds_away_win = Column(Float, nullable=True)

    # 让球胜平负
    handicap = Column(String(16), nullable=True, comment="让球数，如 0, +1, -1")
    odds_hhad_home_win = Column(Float, nullable=True)
    odds_hhad_draw = Column(Float, nullable=True)
    odds_hhad_away_win = Column(Float, nullable=True)

    # 支持率
    support_home = Column(Float, nullable=True)
    support_draw = Column(Float, nullable=True)
    support_away = Column(Float, nullable=True)

    # 其它玩法赔率
    score_odds = Column(JSON, nullable=True, comment="比分赔率 {比分: 赔率}")
    total_goals_odds = Column(JSON, nullable=True, comment="总进球数赔率 {进球数: 赔率}")
    half_full_odds = Column(JSON, nullable=True, comment="半全场赔率 {半场/全场: 赔率}")

    # 实际比分（赛后回填）
    actual_home_score = Column(Integer, nullable=True)
    actual_away_score = Column(Integer, nullable=True)
    actual_half_full = Column(String(16), nullable=True, comment="实际半全场结果，如 胜/胜")
    result_settled_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=now_beijing)
    updated_at = Column(DateTime, default=now_beijing, onupdate=now_beijing)

    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id = _uuid_column()
    name = Column(String(32), unique=True, nullable=False)
    display_name = Column(String(64), nullable=False)
    model_name = Column(String(64), nullable=False)
    api_base_url = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True)
    api_key_env_name = Column(String(64), nullable=False)

    predictions = relationship("Prediction", back_populates="provider")
    score = relationship("ProviderScore", back_populates="provider", uselist=False)


class Prediction(Base):
    __tablename__ = "predictions"

    id = _uuid_column()
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id"), nullable=False, index=True)
    prediction_index = Column(Integer, nullable=False, comment="第几条预测，1 或 2")

    home_score = Column(Integer, nullable=False)
    away_score = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    market_reasoning = Column(Text, nullable=True, comment="操盘原因分析")
    bets = Column(JSON, nullable=True, comment="各玩法推荐 [{market, selection, reason, confidence}]")
    raw_response = Column(Text, nullable=True)
    predicted_at = Column(DateTime, default=now_beijing)

    # 赛后评分
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Float, nullable=True)
    direction_points = Column(Float, nullable=True, comment="胜平负+让球胜平负积分")
    other_points = Column(Float, nullable=True, comment="比分+总进球数+半全场积分")

    __table_args__ = (UniqueConstraint("match_id", "provider_id", "prediction_index", name="uix_prediction"),)

    match = relationship("Match", back_populates="predictions")
    provider = relationship("LLMProvider", back_populates="predictions")


class ProviderScore(Base):
    __tablename__ = "provider_scores"

    id = _uuid_column()
    provider_id = Column(UUID(as_uuid=True), ForeignKey("llm_providers.id"), unique=True, nullable=False)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    direction_correct_predictions = Column(Integer, default=0)
    total_points = Column(Float, default=0.0)
    direction_points = Column(Float, default=0.0, comment="胜平负+让球胜平负累计积分")
    other_points = Column(Float, default=0.0, comment="比分+总进球数+半全场累计积分")
    accuracy_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=now_beijing, onupdate=now_beijing)

    provider = relationship("LLMProvider", back_populates="score")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id = _uuid_column()
    run_at = Column(DateTime, default=now_beijing)
    log_type = Column(String(32), nullable=False, comment="matches 或 results")
    status = Column(String(32), nullable=False, default="running")
    count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
