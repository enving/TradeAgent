"""Portfolio Correlation Monitor.

Monitors portfolio correlation and sector exposure to prevent
over-concentration risk. Calculates correlation matrix between
positions and checks sector diversification rules.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import yfinance as yf
import pandas as pd

from ..models.portfolio import Position
from ..models.trade import Signal
from ..utils.logger import logger


# Sector mappings for common tickers
SECTOR_MAP = {
    # Technology
    "AAPL": "Technology",
    "MSFT": "Technology",
    "GOOGL": "Technology",
    "META": "Technology",
    "NVDA": "Technology",
    "AMD": "Technology",
    "AVGO": "Technology",
    "NFLX": "Technology",

    # Finance
    "JPM": "Finance",
    "BAC": "Finance",
    "WFC": "Finance",
    "GS": "Finance",
    "MS": "Finance",

    # Energy
    "XOM": "Energy",
    "CVX": "Energy",
    "COP": "Energy",

    # Healthcare
    "LLY": "Healthcare",
    "JNJ": "Healthcare",
    "PFE": "Healthcare",
    "UNH": "Healthcare",

    # Consumer
    "TSLA": "Consumer",
    "AMZN": "Consumer",
    "KO": "Consumer",
    "PEP": "Consumer",
    "MCD": "Consumer",

    # ETFs
    "VTI": "Broad Market",
    "VGK": "International",
    "GLD": "Commodities",
    "SPY": "Broad Market",
    "QQQ": "Technology",
}


class CorrelationMonitor:
    """Monitors portfolio correlation and sector exposure."""

    # Risk thresholds
    MAX_CORRELATION = 0.7  # Max correlation between any two positions
    MAX_SECTOR_ALLOCATION = 0.40  # Max 40% in single sector
    MIN_POSITIONS_FOR_CORRELATION = 2  # Need at least 2 positions to check correlation

    def __init__(self, lookback_days: int = 90):
        """Initialize correlation monitor.

        Args:
            lookback_days: Days of price history for correlation calculation
        """
        self.lookback_days = lookback_days
        self._price_cache: Dict[str, pd.DataFrame] = {}

    async def check_new_signal(
        self,
        signal: Signal,
        current_positions: List[Position],
        portfolio_value: Decimal,
    ) -> Tuple[bool, Optional[str]]:
        """Check if new signal would violate correlation/sector rules.

        Args:
            signal: New trading signal to evaluate
            current_positions: Current open positions
            portfolio_value: Current portfolio value

        Returns:
            Tuple of (approved: bool, rejection_reason: str or None)
        """
        ticker = signal.ticker

        # Skip correlation check if no current positions
        if len(current_positions) == 0:
            return True, None

        # 1. Check sector concentration
        sector_ok, sector_reason = self._check_sector_concentration(
            ticker, signal.entry_price * Decimal("10"),  # Assume 10 shares
            current_positions,
            portfolio_value,
        )

        if not sector_ok:
            logger.warning(f"Signal rejected for {ticker}: {sector_reason}")
            return False, sector_reason

        # 2. Check correlation with existing positions
        if len(current_positions) >= self.MIN_POSITIONS_FOR_CORRELATION:
            corr_ok, corr_reason = await self._check_correlation(
                ticker, current_positions
            )

            if not corr_ok:
                logger.warning(f"Signal rejected for {ticker}: {corr_reason}")
                return False, corr_reason

        return True, None

    def _check_sector_concentration(
        self,
        new_ticker: str,
        new_position_value: Decimal,
        current_positions: List[Position],
        portfolio_value: Decimal,
    ) -> Tuple[bool, Optional[str]]:
        """Check if adding new position would violate sector limits.

        Args:
            new_ticker: Ticker to add
            new_position_value: Dollar value of new position
            current_positions: Current positions
            portfolio_value: Total portfolio value

        Returns:
            Tuple of (approved, reason)
        """
        # Get sector for new ticker
        new_sector = SECTOR_MAP.get(new_ticker, "Unknown")

        # Calculate current sector allocations
        sector_values: Dict[str, Decimal] = {}

        for pos in current_positions:
            sector = SECTOR_MAP.get(pos.symbol, "Unknown")
            position_value = pos.market_value
            sector_values[sector] = sector_values.get(sector, Decimal("0")) + position_value

        # Add new position to sector
        sector_values[new_sector] = (
            sector_values.get(new_sector, Decimal("0")) + new_position_value
        )

        # Check if any sector exceeds limit
        for sector, value in sector_values.items():
            allocation = float(value / portfolio_value) if portfolio_value > 0 else 0

            if allocation > self.MAX_SECTOR_ALLOCATION:
                return False, (
                    f"Sector concentration limit: {sector} would be {allocation:.1%} "
                    f"(max {self.MAX_SECTOR_ALLOCATION:.0%})"
                )

        return True, None

    async def _check_correlation(
        self, new_ticker: str, current_positions: List[Position]
    ) -> Tuple[bool, Optional[str]]:
        """Check correlation between new ticker and existing positions.

        Args:
            new_ticker: Ticker to add
            current_positions: Current positions

        Returns:
            Tuple of (approved, reason)
        """
        try:
            # Get price history for new ticker
            new_prices = await self._get_price_history(new_ticker)

            if new_prices is None or len(new_prices) < 30:
                logger.warning(
                    f"Insufficient price history for {new_ticker}, skipping correlation check"
                )
                return True, None  # Allow if we can't calculate correlation

            # Check correlation with each existing position
            for pos in current_positions:
                existing_prices = await self._get_price_history(pos.symbol)

                if existing_prices is None or len(existing_prices) < 30:
                    continue

                # Calculate correlation
                correlation = self._calculate_correlation(new_prices, existing_prices)

                if correlation is None:
                    continue

                # Check if correlation is too high
                if abs(correlation) > self.MAX_CORRELATION:
                    return False, (
                        f"High correlation with {pos.symbol}: {correlation:.2f} "
                        f"(max {self.MAX_CORRELATION:.2f})"
                    )

            return True, None

        except Exception as e:
            logger.error(f"Error checking correlation for {new_ticker}: {e}")
            # Allow trade if correlation check fails (don't block on errors)
            return True, None

    async def _get_price_history(self, ticker: str) -> Optional[pd.Series]:
        """Get price history for ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Series of daily close prices, or None if error
        """
        # Check cache
        if ticker in self._price_cache:
            cached = self._price_cache[ticker]
            # Check if cache is fresh (less than 1 day old)
            if len(cached) > 0:
                # Make datetime timezone-aware for comparison
                last_cached_date = cached.index[-1]

                # Handle timezone conversion
                if last_cached_date.tzinfo is None:
                    # Timestamp is timezone-naive, add UTC
                    last_cached_date = last_cached_date.replace(tzinfo=timezone.utc)
                else:
                    # Timestamp is timezone-aware, convert to UTC
                    last_cached_date = last_cached_date.astimezone(timezone.utc)

                time_since_update = datetime.now(timezone.utc) - last_cached_date
                if time_since_update.days < 1:
                    return cached["Close"]

        try:
            # Fetch from yfinance
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)

            yf_ticker = yf.Ticker(ticker)
            history = yf_ticker.history(start=start_date, end=end_date, interval="1d")

            if history.empty:
                return None

            # Cache
            self._price_cache[ticker] = history

            return history["Close"]

        except Exception as e:
            logger.error(f"Failed to fetch price history for {ticker}: {e}")
            return None

    def _calculate_correlation(
        self, series1: pd.Series, series2: pd.Series
    ) -> Optional[float]:
        """Calculate correlation between two price series.

        Args:
            series1: First price series
            series2: Second price series

        Returns:
            Correlation coefficient (-1 to 1), or None if error
        """
        try:
            # Align series (same dates)
            aligned = pd.concat([series1, series2], axis=1, join="inner")

            if len(aligned) < 30:
                return None  # Not enough overlapping data

            # Calculate correlation
            correlation = aligned.iloc[:, 0].corr(aligned.iloc[:, 1])

            return float(correlation)

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return None

    def get_portfolio_correlation_matrix(
        self, positions: List[Position]
    ) -> Optional[pd.DataFrame]:
        """Calculate correlation matrix for entire portfolio.

        Args:
            positions: Current positions

        Returns:
            Correlation matrix DataFrame, or None if insufficient data
        """
        if len(positions) < 2:
            return None

        try:
            tickers = [pos.symbol for pos in positions]

            # Get price histories
            price_data = {}
            for ticker in tickers:
                prices = self._price_cache.get(ticker)
                if prices is not None and "Close" in prices.columns:
                    price_data[ticker] = prices["Close"]

            if len(price_data) < 2:
                return None

            # Create DataFrame
            df = pd.DataFrame(price_data)

            # Calculate correlation matrix
            corr_matrix = df.corr()

            return corr_matrix

        except Exception as e:
            logger.error(f"Error calculating portfolio correlation matrix: {e}")
            return None

    def get_sector_allocation(
        self, positions: List[Position], portfolio_value: Decimal
    ) -> Dict[str, float]:
        """Calculate current sector allocations.

        Args:
            positions: Current positions
            portfolio_value: Total portfolio value

        Returns:
            Dictionary of sector -> allocation percentage
        """
        sector_values: Dict[str, Decimal] = {}

        for pos in positions:
            sector = SECTOR_MAP.get(pos.symbol, "Unknown")
            position_value = pos.market_value
            sector_values[sector] = sector_values.get(sector, Decimal("0")) + position_value

        # Convert to percentages
        sector_allocations = {}
        for sector, value in sector_values.items():
            allocation = float(value / portfolio_value) if portfolio_value > 0 else 0
            sector_allocations[sector] = allocation

        return sector_allocations


# Global singleton
_correlation_monitor = None


def get_correlation_monitor() -> CorrelationMonitor:
    """Get or create the CorrelationMonitor singleton.

    Returns:
        CorrelationMonitor instance
    """
    global _correlation_monitor
    if _correlation_monitor is None:
        _correlation_monitor = CorrelationMonitor()
    return _correlation_monitor
