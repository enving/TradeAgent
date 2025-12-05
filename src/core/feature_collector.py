"""Feature collector for ML training data.

Collects event-driven features at trade time:
- News & sentiment
- Upcoming events (earnings, Fed, macro)
- Market context (VIX, SPY, sectors)
- Technical indicators
- Trade metadata
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import aiohttp

from ..models.ml_data import (
    EventFeatures,
    MarketContextFeatures,
    MetaFeatures,
    NewsFeatures,
    TechnicalFeatures,
    TradeFeatures,
)
from ..utils.config import config
from ..utils.logger import logger


class FeatureCollector:
    """Collects event-driven features for ML training."""

    def __init__(self):
        """Initialize feature collector."""
        self.news_api_key = config.ALPHA_VANTAGE_API_KEY  # Will use Alpha Vantage NEWS_SENTIMENT
        self.base_delay = 12  # Rate limit delay

    async def collect_features(
        self,
        ticker: str,
        strategy: str,
        trigger_reason: str,
        portfolio_value: Decimal,
        position_count: int,
        cash_available: Decimal,
        technicals: dict | None = None,
    ) -> TradeFeatures:
        """Collect all features for a trade.

        Args:
            ticker: Stock symbol
            strategy: Trading strategy name
            trigger_reason: Why we entered this trade
            portfolio_value: Current portfolio value
            position_count: Number of open positions
            cash_available: Available cash
            technicals: Optional dict with RSI, MACD, etc.

        Returns:
            Complete TradeFeatures object
        """
        logger.info(f"Collecting ML features for {ticker}")

        # Collect features in parallel (where possible)
        news_task = self._collect_news(ticker)
        events_task = self._collect_events(ticker)
        market_task = self._collect_market_context()

        # Wait for all async tasks
        news, events, market_context = await asyncio.gather(
            news_task, events_task, market_task, return_exceptions=True
        )

        # Handle exceptions
        if isinstance(news, Exception):
            logger.error(f"Failed to collect news: {news}")
            news = NewsFeatures()

        if isinstance(events, Exception):
            logger.error(f"Failed to collect events: {events}")
            events = EventFeatures()

        if isinstance(market_context, Exception):
            logger.error(f"Failed to collect market context: {market_context}")
            market_context = MarketContextFeatures()

        # Technical features (already calculated)
        tech_features = TechnicalFeatures(**(technicals or {}))

        # Meta features
        now = datetime.now(UTC)
        meta = MetaFeatures(
            strategy=strategy,
            trigger_reason=trigger_reason,
            portfolio_value=portfolio_value,
            position_count=position_count,
            cash_available=cash_available,
            market_hours=self._get_market_hours(now),
            day_of_week=now.strftime("%A"),
        )

        return TradeFeatures(
            news=news,
            events=events,
            market_context=market_context,
            technicals=tech_features,
            meta=meta,
        )

    async def _collect_news(self, ticker: str) -> NewsFeatures:
        """Collect news and sentiment features.

        Uses Alpha Vantage NEWS_SENTIMENT endpoint (free).

        Args:
            ticker: Stock symbol

        Returns:
            NewsFeatures object
        """
        # TODO: Implement when Alpha Vantage quota allows
        # For now, return placeholder
        logger.debug(f"News collection not yet implemented (rate limit)")
        return NewsFeatures()

        # Future implementation:
        # url = f"https://www.alphavantage.co/query"
        # params = {
        #     "function": "NEWS_SENTIMENT",
        #     "tickers": ticker,
        #     "apikey": self.news_api_key,
        # }
        #
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(url, params=params) as response:
        #         data = await response.json()
        #
        # # Parse news
        # articles = data.get("feed", [])
        # headlines = [a["title"] for a in articles[:10]]
        #
        # # Calculate sentiment
        # sentiments = [a.get("overall_sentiment_score", 0) for a in articles]
        # avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        #
        # return NewsFeatures(
        #     headlines=headlines,
        #     sentiment_score=avg_sentiment,
        #     sentiment_label=self._sentiment_to_label(avg_sentiment),
        #     news_count_24h=len(articles),
        #     breaking_news=any(a.get("relevance_score", 0) > 0.8 for a in articles),
        #     top_topics=self._extract_topics(articles),
        # )

    async def _collect_events(self, ticker: str) -> EventFeatures:
        """Collect upcoming events.

        Args:
            ticker: Stock symbol

        Returns:
            EventFeatures object
        """
        # TODO: Implement with FMP API or Alpha Vantage EARNINGS_CALENDAR
        logger.debug(f"Event collection not yet implemented")
        return EventFeatures()

    async def _collect_market_context(self) -> MarketContextFeatures:
        """Collect market context (VIX, SPY, sectors).

        Returns:
            MarketContextFeatures object
        """
        # TODO: Implement with Alpha Vantage or Yahoo Finance
        logger.debug(f"Market context collection not yet implemented")
        return MarketContextFeatures()

    def _get_market_hours(self, dt: datetime) -> str:
        """Determine market hours status.

        Args:
            dt: Current datetime

        Returns:
            'pre_market', 'regular', or 'after_hours'
        """
        # Convert to US Eastern Time
        hour = dt.hour - 5  # Rough EST conversion (ignores DST)

        if 4 <= hour < 9:
            return "pre_market"
        elif 9 <= hour < 16:
            return "regular"
        else:
            return "after_hours"

    def _sentiment_to_label(self, score: float) -> str:
        """Convert sentiment score to label.

        Args:
            score: Sentiment score -1 to 1

        Returns:
            'positive', 'negative', or 'neutral'
        """
        if score > 0.2:
            return "positive"
        elif score < -0.2:
            return "negative"
        else:
            return "neutral"

    def _extract_topics(self, articles: list[dict]) -> list[str]:
        """Extract main topics from news articles.

        Args:
            articles: List of news articles

        Returns:
            List of topic strings
        """
        # Simple keyword extraction
        keywords = {}
        for article in articles:
            title = article.get("title", "").lower()

            # Count common trading keywords
            for word in ["earnings", "revenue", "product", "launch", "ceo", "lawsuit", "acquisition"]:
                if word in title:
                    keywords[word] = keywords.get(word, 0) + 1

        # Return top 3 topics
        sorted_topics = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:3]]


# Placeholder sentiment analyzer (will use FinBERT later)
class SentimentAnalyzer:
    """Placeholder for FinBERT sentiment analysis."""

    async def analyze(self, texts: list[str]) -> float:
        """Analyze sentiment of text list.

        Args:
            texts: List of headlines/articles

        Returns:
            Average sentiment score -1 to 1
        """
        # TODO: Implement FinBERT
        logger.debug("FinBERT sentiment analysis not yet implemented")
        return 0.0
