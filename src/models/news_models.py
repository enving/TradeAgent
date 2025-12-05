"""Pydantic models for news articles and LLM analysis logging."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class NewsArticleLog(BaseModel):
    """News article record for database storage.

    Attributes:
        ticker: Stock symbol this article is about
        title: Article headline
        summary: Article summary/description
        source: News source name
        url: Article URL
        published_at: When article was published
        fetched_at: When we retrieved it
    """

    ticker: str = Field(description="Stock ticker symbol")
    title: str = Field(description="Article headline")
    summary: str | None = Field(default=None, description="Article summary")
    source: str = Field(description="News source (e.g., 'Yahoo Finance')")
    url: str = Field(description="Article URL")
    published_at: datetime = Field(description="Article publication timestamp")
    fetched_at: datetime = Field(description="When we fetched this article")


class LLMAnalysisLog(BaseModel):
    """LLM sentiment analysis record for database storage.

    Stores EVERY analysis, regardless of whether signal was generated.

    Attributes:
        ticker: Stock symbol analyzed
        analysis_timestamp: When analysis was performed
        action: LLM recommendation (BUY/SELL/HOLD)
        sentiment_score: Sentiment score -1.0 to +1.0
        confidence: LLM confidence 0.0 to 1.0
        impact: News impact rating
        reasoning: Full LLM explanation
        article_count: Number of articles analyzed
        lookback_days: Days of news lookback
        signal_generated: Whether we created a Signal object
        signal_approved: Whether signal passed technical filters
        technical_filter_reason: Why signal was rejected (if applicable)
        signal_id: UUID of signal if generated
        llm_model: Model name used
        llm_provider: Provider name
        llm_tokens_used: Token count (optional)
        llm_cost_usd: API cost (optional)
    """

    ticker: str = Field(description="Stock ticker symbol")
    analysis_timestamp: datetime = Field(description="Analysis timestamp")
    action: Literal["BUY", "SELL", "HOLD"] = Field(description="LLM recommendation")
    sentiment_score: Decimal = Field(
        description="Sentiment score -1.0 to 1.0", ge=-1, le=1
    )
    confidence: Decimal = Field(description="Confidence 0.0 to 1.0", ge=0, le=1)
    impact: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Impact rating")
    reasoning: str = Field(description="Full LLM explanation")
    article_count: int = Field(description="Number of articles analyzed", ge=0)
    lookback_days: int = Field(default=2, description="Days of news lookback")

    # Signal flow tracking
    signal_generated: bool = Field(
        default=False, description="Whether Signal object was created"
    )
    signal_approved: bool = Field(
        default=False, description="Whether signal passed all filters"
    )
    technical_filter_reason: str | None = Field(
        default=None, description="Why signal was rejected"
    )
    signal_id: str | None = Field(
        default=None, description="UUID of generated signal"
    )

    # Model metadata
    llm_model: str = Field(default="claude-3.5-sonnet", description="LLM model name")
    llm_provider: str = Field(default="openrouter", description="LLM provider")
    llm_tokens_used: int | None = Field(default=None, description="Tokens consumed")
    llm_cost_usd: Decimal | None = Field(default=None, description="API cost in USD")
