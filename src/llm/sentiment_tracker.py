"""Sentiment Trend Tracker.

Tracks sentiment evolution over time to detect momentum shifts
and inflection points. Generates signals based on sentiment trends.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Literal, cast, Any
from dataclasses import dataclass

from sqlalchemy import text
from ..database.postgres_client import PostgresClient
from ..models.trade import Signal
from ..utils.logger import logger


@dataclass
class SentimentDataPoint:
    """Single sentiment observation."""

    ticker: str
    timestamp: datetime
    sentiment_score: Decimal
    action: str
    confidence: Decimal
    impact: str


@dataclass
class SentimentTrend:
    """Sentiment trend analysis result."""

    ticker: str
    trend_direction: Literal["rising", "falling", "neutral", "volatile"]
    momentum_score: Decimal
    volatility: Decimal
    recent_sentiment: Decimal
    avg_sentiment: Decimal
    inflection_detected: bool
    datapoints_count: int


class SentimentTracker:
    """Tracks sentiment evolution over time."""

    LOOKBACK_DAYS = 7
    MIN_DATAPOINTS = 3

    MOMENTUM_THRESHOLD = Decimal("0.3")
    VOLATILITY_THRESHOLD = Decimal("0.4")
    INFLECTION_THRESHOLD = Decimal("0.5")

    def __init__(self):
        pass  # PostgresClient is singleton, no need to store instance

    async def get_sentiment_history(
        self, ticker: str, days: Optional[int] = None, reference_date: Optional[datetime] = None
    ) -> List[SentimentDataPoint]:
        client = await PostgresClient.get_instance()

        lookback = days or self.LOOKBACK_DAYS
        end_date = reference_date or datetime.now(timezone.utc)
        cutoff_date = end_date - timedelta(days=lookback)

        try:
            stmt = text("""
                SELECT * FROM llm_analysis_log
                WHERE ticker = :ticker
                  AND created_at >= :cutoff
                ORDER BY created_at ASC
            """)
            
            rows = []
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"ticker": ticker, "cutoff": cutoff_date})
                rows = result.fetchall()

            if not rows:
                return []

            datapoints = []
            for row in rows:
                data = dict(row._mapping)
                # created_at is likely already datetime in asyncpg
                timestamp = data["created_at"]
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                
                datapoints.append(
                    SentimentDataPoint(
                        ticker=data["ticker"],
                        timestamp=timestamp,
                        sentiment_score=Decimal(str(data["sentiment_score"])),
                        action=data["action"],
                        confidence=Decimal(str(data["confidence"])),
                        impact=data["impact"],
                    )
                )

            logger.debug(
                f"Fetched {len(datapoints)} sentiment datapoints for {ticker} (last {lookback} days)"
            )

            return datapoints

        except Exception as e:
            logger.error(f"Failed to fetch sentiment history for {ticker}: {e}")
            return []

    async def analyze_sentiment_trend(
        self, ticker: str, reference_date: Optional[datetime] = None
    ) -> Optional[SentimentTrend]:
        datapoints = await self.get_sentiment_history(ticker, reference_date=reference_date)

        if len(datapoints) < self.MIN_DATAPOINTS:
            return None

        sentiments = [dp.sentiment_score for dp in datapoints]

        recent_sentiment = sentiments[-1]
        avg_sentiment = sum(sentiments) / Decimal(str(len(sentiments)))

        momentum = self._calculate_momentum(sentiments)
        volatility = self._calculate_volatility(sentiments)
        inflection_detected = self._detect_inflection(sentiments)

        if volatility > self.VOLATILITY_THRESHOLD:
            trend_direction: Literal["rising", "falling", "neutral", "volatile"] = "volatile"
        elif abs(momentum) < Decimal("0.1"):
            trend_direction = "neutral"
        elif momentum > self.MOMENTUM_THRESHOLD:
            trend_direction = "rising"
        elif momentum < -self.MOMENTUM_THRESHOLD:
            trend_direction = "falling"
        else:
            trend_direction = "neutral"

        return SentimentTrend(
            ticker=ticker,
            trend_direction=trend_direction,
            momentum_score=momentum,
            volatility=volatility,
            recent_sentiment=recent_sentiment,
            avg_sentiment=avg_sentiment,
            inflection_detected=inflection_detected,
            datapoints_count=len(datapoints),
        )

    def _calculate_momentum(self, sentiments: List[Decimal]) -> Decimal:
        """Calculate sentiment momentum using linear regression."""
        n = len(sentiments)
        if n < 2:
            return Decimal("0")

        x_values = [Decimal(str(i)) for i in range(n)]
        x_mean = sum(x_values) / Decimal(str(n))
        y_mean = sum(sentiments) / Decimal(str(n))

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, sentiments))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            return Decimal("0")

        slope = numerator / denominator
        normalized_slope = slope * Decimal(str(n))
        return max(Decimal("-1.0"), min(Decimal("1.0"), normalized_slope))

    def _calculate_volatility(self, sentiments: List[Decimal]) -> Decimal:
        """Calculate sentiment volatility (standard deviation)."""
        n = len(sentiments)
        if n < 2:
            return Decimal("0")

        mean = sum(sentiments) / Decimal(str(n))
        variance = sum((s - mean) ** 2 for s in sentiments) / Decimal(str(n))
        return (
            variance.sqrt() if hasattr(variance, "sqrt") else Decimal(str(float(variance) ** 0.5))
        )

    def _detect_inflection(self, sentiments: List[Decimal]) -> bool:
        """Detect sentiment inflection point (reversal)."""
        if len(sentiments) < 4:
            return False

        mid = len(sentiments) // 2
        first_half = sentiments[:mid]
        second_half = sentiments[mid:]

        first_avg = sum(first_half) / Decimal(str(len(first_half)))
        second_avg = sum(second_half) / Decimal(str(len(second_half)))

        sentiment_change = abs(second_avg - first_avg)
        direction_reversed = (first_avg * second_avg) < 0

        return sentiment_change > self.INFLECTION_THRESHOLD or direction_reversed

    async def generate_sentiment_signals(
        self,
        tickers: List[str],
        alpaca_client: Any = None,
        reference_date: Optional[datetime] = None,
    ) -> List[Signal]:
        signals = []

        for ticker in tickers:
            try:
                trend = await self.analyze_sentiment_trend(ticker, reference_date=reference_date)
                if trend is None:
                    continue

                signal_generated = False
                reasoning = []

                if (
                    trend.trend_direction == "rising"
                    and trend.momentum_score > self.MOMENTUM_THRESHOLD
                    and trend.recent_sentiment > Decimal("0.3")
                ):
                    signal_generated = True
                    reasoning.append(f"Strong positive momentum (score={trend.momentum_score:.2f})")

                if (
                    trend.inflection_detected
                    and trend.recent_sentiment > Decimal("0")
                    and trend.avg_sentiment < Decimal("0")
                ):
                    signal_generated = True
                    reasoning.append("Sentiment inflection detected (negative to positive)")

                if trend.trend_direction == "volatile":
                    signal_generated = False

                if signal_generated:
                    current_price = Decimal("100.00")
                    if alpaca_client:
                        quote = await alpaca_client.get_latest_quote(ticker)
                        current_price = Decimal(str(quote.get("price", quote.get("last", 0))))

                    if current_price > 0:
                        signals.append(
                            Signal(
                                ticker=ticker,
                                action="BUY",
                                entry_price=current_price,
                                confidence=abs(trend.momentum_score),
                                strategy="sentiment_trend",
                                metadata={"reasoning": " | ".join(reasoning)},
                            )
                        )
            except Exception as e:
                logger.error(f"Failed to generate sentiment signal for {ticker}: {e}")

        return signals


_sentiment_tracker = None


def get_sentiment_tracker() -> SentimentTracker:
    global _sentiment_tracker
    if _sentiment_tracker is None:
        _sentiment_tracker = SentimentTracker()
    return _sentiment_tracker
