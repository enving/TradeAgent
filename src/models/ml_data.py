"""ML Training Data models for self-learning trading system.

Stores features collected at trade time and labels added later.
Used for training custom time-series models and FinBERT fine-tuning.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class NewsFeatures(BaseModel):
    """News and sentiment features."""

    headlines: list[str] = Field(default_factory=list, description="Recent news headlines")
    sentiment_score: float | None = Field(None, ge=-1.0, le=1.0, description="Sentiment score from FinBERT")
    sentiment_label: Literal["positive", "negative", "neutral"] | None = None
    news_count_24h: int = Field(0, ge=0, description="Number of news articles in last 24h")
    breaking_news: bool = Field(False, description="Major breaking news detected")
    top_topics: list[str] = Field(default_factory=list, description="Main topics (earnings, product, etc.)")


class EventFeatures(BaseModel):
    """Upcoming events and catalysts."""

    earnings_soon: bool = Field(False, description="Earnings within 5 days")
    earnings_days_away: int | None = Field(None, ge=0, description="Days until earnings")
    fed_meeting_soon: bool = Field(False, description="Fed meeting within 3 days")
    fed_days_away: int | None = Field(None, ge=0, description="Days until Fed meeting")
    macro_event: str | None = Field(None, description="Upcoming macro event (CPI, GDP, etc.)")
    sector_event: str | None = Field(None, description="Sector-specific event")


class MarketContextFeatures(BaseModel):
    """Overall market context and conditions."""

    vix: float | None = Field(None, ge=0, description="VIX volatility index")
    vix_change_1d: float | None = Field(None, description="VIX 1-day change")
    spy_return_1d: float | None = Field(None, description="SPY 1-day return %")
    spy_return_5d: float | None = Field(None, description="SPY 5-day return %")
    sector_performance: dict[str, float] = Field(
        default_factory=dict, description="Sector returns (tech, energy, etc.)"
    )
    market_breadth: float | None = Field(None, ge=0, le=1, description="% stocks above SMA50")
    put_call_ratio: float | None = Field(None, ge=0, description="Market put/call ratio")


class TechnicalFeatures(BaseModel):
    """Technical indicators at trade time."""

    rsi: float | None = Field(None, ge=0, le=100, description="RSI indicator")
    macd_histogram: float | None = Field(None, description="MACD histogram")
    volume_ratio: float | None = Field(None, ge=0, description="Volume vs average")
    price_vs_sma20: float | None = Field(None, ge=0, description="Price / SMA20 ratio")
    price_vs_sma50: float | None = Field(None, ge=0, description="Price / SMA50 ratio")
    bollinger_position: float | None = Field(None, ge=0, le=1, description="Position in Bollinger Bands")
    atr: float | None = Field(None, ge=0, description="Average True Range")


class MetaFeatures(BaseModel):
    """Metadata about the trade decision."""

    strategy: str = Field(..., description="Strategy that generated signal")
    trigger_reason: str = Field(..., description="Why we entered (which rules)")
    portfolio_value: Decimal = Field(..., gt=0, description="Total portfolio value")
    position_count: int = Field(..., ge=0, description="Number of open positions")
    cash_available: Decimal = Field(..., ge=0, description="Available cash")
    market_hours: Literal["pre_market", "regular", "after_hours"] = "regular"
    day_of_week: str = Field(..., description="Monday, Tuesday, etc.")


class TradeFeatures(BaseModel):
    """Complete feature set collected at trade time."""

    news: NewsFeatures = Field(default_factory=NewsFeatures)
    events: EventFeatures = Field(default_factory=EventFeatures)
    market_context: MarketContextFeatures = Field(default_factory=MarketContextFeatures)
    technicals: TechnicalFeatures = Field(default_factory=TechnicalFeatures)
    meta: MetaFeatures


class MLTrainingData(BaseModel):
    """ML training data record with features and labels.

    Features are collected at trade time.
    Labels are added later by the labeling script.
    """

    # Record metadata
    id: UUID | None = None
    created_at: datetime | None = None

    # Trade identification
    ticker: str = Field(..., min_length=1, max_length=10)
    action: Literal["BUY", "SELL"]
    timestamp: datetime
    entry_price: Decimal = Field(..., gt=0)
    strategy: str

    # Features (collected at trade time)
    features: TradeFeatures

    # Labels (added later by labeling script)
    label_timestamp: datetime | None = None
    hold_period_days: int | None = Field(None, description="7, 14, or 30 days")
    exit_price: Decimal | None = Field(None, gt=0)
    outcome: Literal["profitable", "unprofitable", "neutral"] | None = None
    return_pct: Decimal | None = None
    max_drawdown_pct: Decimal | None = None
    max_gain_pct: Decimal | None = None

    # Labeling status
    is_labeled: bool = False

    # ML pipeline
    is_train: bool | None = None
    model_version: str | None = None
    prediction_at_entry: Decimal | None = None

    # Links to other tables
    trade_id: UUID | None = None
    signal_id: UUID | None = None

    # Performance metrics
    sharpe_ratio: Decimal | None = None

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
        }


class MLDataLabel(BaseModel):
    """Label data for updating an existing ML training record."""

    hold_period_days: int = Field(..., description="7, 14, or 30 days")
    exit_price: Decimal = Field(..., gt=0)
    outcome: Literal["profitable", "unprofitable", "neutral"]
    return_pct: Decimal
    max_drawdown_pct: Decimal | None = None
    max_gain_pct: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    label_timestamp: datetime = Field(default_factory=lambda: datetime.now())
