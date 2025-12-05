"""Sentiment Trend Tracker.

Tracks sentiment evolution over time to detect momentum shifts
and inflection points. Generates signals based on sentiment trends.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Literal
from dataclasses import dataclass

from ..database.supabase_client import SupabaseClient
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
    momentum_score: Decimal  # -1.0 to +1.0 (negative = falling, positive = rising)
    volatility: Decimal  # 0.0 to 1.0 (higher = more volatile)
    recent_sentiment: Decimal  # Latest sentiment score
    avg_sentiment: Decimal  # 7-day average
    inflection_detected: bool  # True if sentiment reversed recently
    datapoints_count: int


class SentimentTracker:
    """Tracks sentiment evolution over time."""

    # Configuration
    LOOKBACK_DAYS = 7
    MIN_DATAPOINTS = 3  # Need at least 3 sentiment analyses to detect trend

    # Trend detection thresholds
    MOMENTUM_THRESHOLD = Decimal("0.3")  # Significant momentum if > 0.3
    VOLATILITY_THRESHOLD = Decimal("0.4")  # High volatility if > 0.4
    INFLECTION_THRESHOLD = Decimal("0.5")  # Sentiment reversal if change > 0.5

    def __init__(self):
        """Initialize sentiment tracker."""
        self.supabase = None  # Will be set in async context

    async def _ensure_supabase(self):
        """Ensure Supabase client is initialized."""
        if self.supabase is None:
            self.supabase = await SupabaseClient.get_instance()

    async def get_sentiment_history(
        self, ticker: str, days: int = None
    ) -> List[SentimentDataPoint]:
        """Fetch sentiment history for a ticker.

        Args:
            ticker: Stock symbol
            days: Days of history to fetch (default: LOOKBACK_DAYS)

        Returns:
            List of sentiment datapoints, ordered by timestamp (oldest first)
        """
        await self._ensure_supabase()

        days = days or self.LOOKBACK_DAYS
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            response = await (
                self.supabase.table("llm_analysis_log")
                .select("*")
                .eq("ticker", ticker)
                .gte("created_at", cutoff_date.isoformat())
                .order("created_at", desc=False)
                .execute()
            )

            if not response.data:
                return []

            datapoints = []
            for row in response.data:
                datapoints.append(
                    SentimentDataPoint(
                        ticker=row["ticker"],
                        timestamp=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                        sentiment_score=Decimal(str(row["sentiment_score"])),
                        action=row["action"],
                        confidence=Decimal(str(row["confidence"])),
                        impact=row["impact"],
                    )
                )

            logger.debug(
                f"Fetched {len(datapoints)} sentiment datapoints for {ticker} "
                f"(last {days} days)"
            )

            return datapoints

        except Exception as e:
            logger.error(f"Failed to fetch sentiment history for {ticker}: {e}")
            return []

    async def analyze_sentiment_trend(self, ticker: str) -> Optional[SentimentTrend]:
        """Analyze sentiment trend for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            SentimentTrend analysis, or None if insufficient data
        """
        datapoints = await self.get_sentiment_history(ticker)

        if len(datapoints) < self.MIN_DATAPOINTS:
            logger.debug(
                f"Insufficient sentiment data for {ticker} "
                f"({len(datapoints)} < {self.MIN_DATAPOINTS})"
            )
            return None

        # Calculate metrics
        sentiments = [dp.sentiment_score for dp in datapoints]

        recent_sentiment = sentiments[-1]
        avg_sentiment = sum(sentiments) / len(sentiments)

        # Calculate momentum (linear regression slope)
        momentum = self._calculate_momentum(sentiments)

        # Calculate volatility (standard deviation)
        volatility = self._calculate_volatility(sentiments)

        # Detect inflection point (sentiment reversal)
        inflection_detected = self._detect_inflection(sentiments)

        # Determine trend direction
        if volatility > self.VOLATILITY_THRESHOLD:
            trend_direction = "volatile"
        elif abs(momentum) < Decimal("0.1"):
            trend_direction = "neutral"
        elif momentum > self.MOMENTUM_THRESHOLD:
            trend_direction = "rising"
        elif momentum < -self.MOMENTUM_THRESHOLD:
            trend_direction = "falling"
        else:
            trend_direction = "neutral"

        trend = SentimentTrend(
            ticker=ticker,
            trend_direction=trend_direction,
            momentum_score=momentum,
            volatility=volatility,
            recent_sentiment=recent_sentiment,
            avg_sentiment=avg_sentiment,
            inflection_detected=inflection_detected,
            datapoints_count=len(datapoints),
        )

        logger.info(
            f"Sentiment trend for {ticker}: {trend_direction} "
            f"(momentum={momentum:.2f}, volatility={volatility:.2f}, "
            f"inflection={inflection_detected})"
        )

        return trend

    def _calculate_momentum(self, sentiments: List[Decimal]) -> Decimal:
        """Calculate sentiment momentum using linear regression.

        Args:
            sentiments: List of sentiment scores (chronological order)

        Returns:
            Momentum score (-1.0 to +1.0)
        """
        n = len(sentiments)
        if n < 2:
            return Decimal("0")

        # Simple linear regression: y = mx + b
        # Calculate slope (m) which represents momentum
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(sentiments) / n

        numerator = sum(
            (Decimal(str(x)) - Decimal(str(x_mean))) * (y - y_mean)
            for x, y in zip(x_values, sentiments)
        )
        denominator = sum(
            (Decimal(str(x)) - Decimal(str(x_mean))) ** 2
            for x in x_values
        )

        if denominator == 0:
            return Decimal("0")

        slope = numerator / denominator

        # Normalize to -1.0 to +1.0 range
        # A slope of 0.2 per day is significant (e.g., 0.0 to 1.0 in 5 days)
        normalized_slope = slope * Decimal(str(n))

        # Clamp to [-1.0, 1.0]
        normalized_slope = max(Decimal("-1.0"), min(Decimal("1.0"), normalized_slope))

        return normalized_slope

    def _calculate_volatility(self, sentiments: List[Decimal]) -> Decimal:
        """Calculate sentiment volatility (standard deviation).

        Args:
            sentiments: List of sentiment scores

        Returns:
            Volatility score (0.0 to 1.0+)
        """
        if len(sentiments) < 2:
            return Decimal("0")

        mean = sum(sentiments) / len(sentiments)
        variance = sum((s - mean) ** 2 for s in sentiments) / len(sentiments)
        std_dev = variance ** Decimal("0.5")

        return std_dev

    def _detect_inflection(self, sentiments: List[Decimal]) -> bool:
        """Detect sentiment inflection point (reversal).

        An inflection is detected if:
        1. Recent sentiment differs significantly from earlier sentiment
        2. Direction changed (positive to negative or vice versa)

        Args:
            sentiments: List of sentiment scores (chronological order)

        Returns:
            True if inflection detected
        """
        if len(sentiments) < 4:
            return False

        # Split into two halves
        mid = len(sentiments) // 2
        first_half = sentiments[:mid]
        second_half = sentiments[mid:]

        # Calculate averages
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        # Check if sentiment reversed significantly
        sentiment_change = abs(second_avg - first_avg)
        direction_reversed = (first_avg * second_avg) < 0  # Different signs

        inflection = (
            sentiment_change > self.INFLECTION_THRESHOLD
            or direction_reversed
        )

        if inflection:
            logger.info(
                f"Inflection detected: sentiment changed from {first_avg:.2f} "
                f"to {second_avg:.2f} (change={sentiment_change:.2f})"
            )

        return inflection

    async def generate_sentiment_signals(
        self, tickers: List[str], alpaca_client=None
    ) -> List[Signal]:
        """Generate trading signals based on sentiment trends.

        Generates BUY signals when:
        - Sentiment is rising with momentum
        - Sentiment inflection from negative to positive

        Args:
            tickers: List of tickers to analyze
            alpaca_client: Alpaca client for fetching current prices (optional)

        Returns:
            List of trading signals
        """
        signals = []

        for ticker in tickers:
            try:
                trend = await self.analyze_sentiment_trend(ticker)

                if trend is None:
                    continue

                # Signal generation rules
                signal_generated = False
                reasoning = []

                # Rule 1: Rising sentiment with strong momentum
                if (
                    trend.trend_direction == "rising"
                    and trend.momentum_score > self.MOMENTUM_THRESHOLD
                    and trend.recent_sentiment > Decimal("0.3")
                ):
                    signal_generated = True
                    reasoning.append(
                        f"Strong positive momentum (score={trend.momentum_score:.2f})"
                    )
                    reasoning.append(
                        f"Recent sentiment={trend.recent_sentiment:.2f}"
                    )

                # Rule 2: Sentiment inflection from negative to positive
                if (
                    trend.inflection_detected
                    and trend.recent_sentiment > Decimal("0")
                    and trend.avg_sentiment < Decimal("0")
                ):
                    signal_generated = True
                    reasoning.append(
                        "Sentiment inflection detected (negative → positive)"
                    )
                    reasoning.append(
                        f"Recent={trend.recent_sentiment:.2f}, "
                        f"Avg={trend.avg_sentiment:.2f}"
                    )

                # Rule 3: Avoid volatile sentiment (too risky)
                if trend.trend_direction == "volatile":
                    signal_generated = False
                    reasoning = [f"Sentiment too volatile (σ={trend.volatility:.2f})"]

                if signal_generated:
                    # Fetch current price
                    try:
                        if alpaca_client:
                            # Fetch real price from Alpaca
                            quote = await alpaca_client.get_latest_quote(ticker)
                            current_price = Decimal(str(quote.get("price", quote.get("last", 0))))
                        else:
                            # Use placeholder price for testing
                            current_price = Decimal("100.00")
                            logger.warning(
                                f"No Alpaca client provided, using placeholder price ${current_price} for {ticker}"
                            )

                        if current_price <= 0:
                            logger.warning(
                                f"Could not fetch valid price for {ticker}, skipping signal"
                            )
                            continue

                        # Create signal with current price
                        signal = Signal(
                            ticker=ticker,
                            action="BUY",
                            entry_price=current_price,
                            confidence=abs(trend.momentum_score),  # Use momentum as confidence
                            strategy="sentiment_trend",
                            metadata={"reasoning": " | ".join(reasoning)},
                        )

                        signals.append(signal)

                        logger.info(
                            f"Sentiment signal generated for {ticker}: "
                            f"BUY @ ${current_price:.2f} (confidence={signal.confidence:.2f})"
                        )
                        logger.info(f"Reasoning: {' | '.join(reasoning)}")
                    except Exception as e:
                        logger.error(f"Failed to fetch price for {ticker}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Failed to generate sentiment signal for {ticker}: {e}")
                continue

        logger.info(
            f"Generated {len(signals)} sentiment-driven signals from {len(tickers)} tickers"
        )

        return signals


# Global singleton
_sentiment_tracker = None


def get_sentiment_tracker() -> SentimentTracker:
    """Get or create the SentimentTracker singleton.

    Returns:
        SentimentTracker instance
    """
    global _sentiment_tracker
    if _sentiment_tracker is None:
        _sentiment_tracker = SentimentTracker()
    return _sentiment_tracker
