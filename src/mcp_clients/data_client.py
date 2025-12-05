"""Data client for fetching market data with rate limiting.

Implements strict rate limiting for all external APIs to avoid hitting limits.
Priority: Alpaca MCP (most generous) > TwelveData > Alpha Vantage
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ..utils.logger import logger


class RateLimiter:
    """Generic rate limiter for API calls.

    Implements a sliding window rate limiter to prevent exceeding API limits.

    Example:
        limiter = RateLimiter(max_calls=200, period_seconds=60)
        await limiter.acquire()  # Blocks if rate limit would be exceeded
        result = await make_api_call()
    """

    def __init__(self, max_calls: int, period_seconds: int):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the period
            period_seconds: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = timedelta(seconds=period_seconds)
        self.calls: list[datetime] = []

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limit.

        Blocks the caller until it's safe to make another API call.
        """
        now = datetime.now()

        # Remove calls outside the time window
        self.calls = [t for t in self.calls if now - t < self.period]

        if len(self.calls) >= self.max_calls:
            # Calculate how long to wait
            oldest_call = self.calls[0]
            sleep_time = (oldest_call + self.period - now).total_seconds()

            if sleep_time > 0:
                logger.debug(
                    f"Rate limit reached, waiting {sleep_time:.2f}s "
                    f"({len(self.calls)}/{self.max_calls} calls)"
                )
                await asyncio.sleep(sleep_time)

            # Remove oldest call after waiting
            self.calls = self.calls[1:]

        # Record this call
        self.calls.append(datetime.now())


# Rate limiters for each service
# CRITICAL: Respect free tier limits to avoid API throttling
ALPACA_LIMITER = RateLimiter(max_calls=200, period_seconds=60)  # 200/min
TWELVEDATA_LIMITER = RateLimiter(max_calls=8, period_seconds=60)  # 8/min (free tier)
ALPHAVANTAGE_LIMITER = RateLimiter(max_calls=5, period_seconds=60)  # 5/min (free tier)


class DataClient:
    """Handles market data fetching with automatic rate limiting.

    Uses Alpaca MCP as primary source (most generous rate limit).
    Falls back to TwelveData and Alpha Vantage if needed.

    All methods implement automatic rate limiting and caching.
    """

    def __init__(self) -> None:
        """Initialize data client with empty cache."""
        self._cache: dict[str, dict[str, Any]] = {}

    async def get_bars_alpaca(
        self, symbol: str, days: int = 30, timeframe: str = "1D"
    ) -> list[dict[str, Any]]:
        """Get historical OHLCV bars from Alpaca MCP.

        Primary data source with generous rate limits (200/min).

        Args:
            symbol: Stock ticker symbol
            days: Number of days of history to fetch
            timeframe: Bar timeframe (1D, 1H, etc.)

        Returns:
            List of bar dictionaries with OHLCV data

        Raises:
            Exception: If Alpaca MCP call fails
        """
        # Check cache first
        cache_key = f"alpaca_{symbol}_{days}_{timeframe}"
        if cache_key in self._cache:
            cache_age = (datetime.now() - self._cache[cache_key]["timestamp"]).seconds
            if cache_age < 300:  # Cache for 5 minutes
                logger.debug(f"Using cached data for {symbol}")
                return self._cache[cache_key]["data"]

        # Apply rate limiting
        await ALPACA_LIMITER.acquire()

        try:
            # TODO: Implement actual Alpaca MCP call
            # For now, return placeholder
            logger.info(f"Fetching {days}d bars for {symbol} from Alpaca MCP")

            # Placeholder data structure
            bars = []
            # bars = await alpaca_mcp.get_bars(symbol=symbol, days=days, timeframe=timeframe)

            # Cache the result
            self._cache[cache_key] = {"data": bars, "timestamp": datetime.now()}

            return bars

        except Exception as e:
            logger.error(f"Failed to fetch bars from Alpaca: {e}")
            raise

    async def get_bars_twelvedata(self, symbol: str, days: int = 30) -> list[dict[str, Any]]:
        """Get historical bars from TwelveData API (fallback).

        CRITICAL: Very strict rate limits (8/min, 800/day on free tier).
        Only use when Alpaca is unavailable.

        Args:
            symbol: Stock ticker symbol
            days: Number of days of history

        Returns:
            List of bar dictionaries

        Raises:
            Exception: If API call fails
        """
        # Check cache first (cache longer for strict rate limits)
        cache_key = f"twelvedata_{symbol}_{days}"
        if cache_key in self._cache:
            cache_age = (datetime.now() - self._cache[cache_key]["timestamp"]).seconds
            if cache_age < 3600:  # Cache for 1 hour
                logger.debug(f"Using cached TwelveData for {symbol}")
                return self._cache[cache_key]["data"]

        # Apply STRICT rate limiting
        await TWELVEDATA_LIMITER.acquire()

        try:
            # TODO: Implement TwelveData API call
            logger.warning(f"Using TwelveData fallback for {symbol} (strict rate limits)")

            bars = []
            # Implement actual API call here

            # Cache the result (longer duration for strict limits)
            self._cache[cache_key] = {"data": bars, "timestamp": datetime.now()}

            return bars

        except Exception as e:
            logger.error(f"Failed to fetch bars from TwelveData: {e}")
            raise

    async def get_latest_quote(self, symbol: str) -> dict[str, Any]:
        """Get latest quote for a symbol.

        Uses Alpaca MCP as primary source.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Quote dictionary with price, bid, ask, etc.

        Raises:
            Exception: If API call fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            # TODO: Implement Alpaca MCP quote fetch
            logger.debug(f"Fetching latest quote for {symbol}")

            quote = {}
            # quote = await alpaca_mcp.get_latest_quote(symbol=symbol)

            return quote

        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise

    def clear_cache(self) -> None:
        """Clear all cached data.

        Useful for forcing fresh data fetch or freeing memory.
        """
        self._cache.clear()
        logger.info("Data cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and age info
        """
        total_entries = len(self._cache)
        total_size = sum(len(str(v)) for v in self._cache.values())

        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "entries": list(self._cache.keys()),
        }
