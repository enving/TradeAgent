"""Alpha Vantage API Client - Free market data for momentum trading.

Provides:
- Historical bars (OHLCV)
- Technical indicators (RSI, MACD, SMA)
- Free tier: 5 calls/min, 500 calls/day
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import aiohttp
import pandas as pd

from ..utils.config import config
from ..utils.logger import logger


class AlphaVantageClient:
    """Alpha Vantage API client for market data."""

    def __init__(self):
        """Initialize Alpha Vantage client."""
        self.api_key = config.ALPHA_VANTAGE_API_KEY
        self.base_url = "https://www.alphavantage.co/query"
        self._rate_limit_delay = 12  # 5 calls/min = 12s between calls

    async def get_bars(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Get historical bars (OHLCV) for a symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            days: Number of days of history (default: 30)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            Exception: If API call fails
        """
        logger.debug(f"Fetching {days} days of bars for {symbol} from Alpha Vantage")

        # Rate limit
        await asyncio.sleep(self._rate_limit_delay)

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact" if days <= 100 else "full",
            "apikey": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()

            # Check for errors
            if "Error Message" in data:
                raise Exception(f"Alpha Vantage error: {data['Error Message']}")

            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                raise Exception("Rate limit exceeded - wait 1 minute")

            # Parse time series data
            time_series = data.get("Time Series (Daily)", {})

            if not time_series:
                logger.error(f"No data returned for {symbol}: {data}")
                return pd.DataFrame()

            # Convert to DataFrame
            df_data = []
            for date_str, values in time_series.items():
                df_data.append(
                    {
                        "timestamp": datetime.strptime(date_str, "%Y-%m-%d"),
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": int(values["5. volume"]),
                    }
                )

            df = pd.DataFrame(df_data)

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Limit to requested days
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            logger.debug(f"Retrieved {len(df)} bars for {symbol}")

            return df

        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            raise

    async def get_rsi(self, symbol: str, period: int = 14) -> pd.DataFrame:
        """Get RSI indicator directly from Alpha Vantage.

        Args:
            symbol: Stock symbol
            period: RSI period (default: 14)

        Returns:
            DataFrame with timestamp and RSI columns
        """
        logger.debug(f"Fetching RSI for {symbol} from Alpha Vantage")

        # Rate limit
        await asyncio.sleep(self._rate_limit_delay)

        params = {
            "function": "RSI",
            "symbol": symbol,
            "interval": "daily",
            "time_period": period,
            "series_type": "close",
            "apikey": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()

            # Parse technical analysis data
            technical_data = data.get("Technical Analysis: RSI", {})

            if not technical_data:
                logger.error(f"No RSI data returned for {symbol}")
                return pd.DataFrame()

            # Convert to DataFrame
            df_data = []
            for date_str, values in technical_data.items():
                df_data.append(
                    {
                        "timestamp": datetime.strptime(date_str, "%Y-%m-%d"),
                        "rsi": float(values["RSI"]),
                    }
                )

            df = pd.DataFrame(df_data)
            df = df.sort_values("timestamp").reset_index(drop=True)

            logger.debug(f"Retrieved RSI data for {symbol}: {len(df)} values")

            return df

        except Exception as e:
            logger.error(f"Failed to get RSI for {symbol}: {e}")
            raise

    async def get_macd(self, symbol: str) -> pd.DataFrame:
        """Get MACD indicator directly from Alpha Vantage.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with timestamp, MACD, MACD_Signal, MACD_Hist columns
        """
        logger.debug(f"Fetching MACD for {symbol} from Alpha Vantage")

        # Rate limit
        await asyncio.sleep(self._rate_limit_delay)

        params = {
            "function": "MACD",
            "symbol": symbol,
            "interval": "daily",
            "series_type": "close",
            "apikey": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()

            # Parse technical analysis data
            technical_data = data.get("Technical Analysis: MACD", {})

            if not technical_data:
                logger.error(f"No MACD data returned for {symbol}")
                return pd.DataFrame()

            # Convert to DataFrame
            df_data = []
            for date_str, values in technical_data.items():
                df_data.append(
                    {
                        "timestamp": datetime.strptime(date_str, "%Y-%m-%d"),
                        "macd": float(values["MACD"]),
                        "macd_signal": float(values["MACD_Signal"]),
                        "histogram": float(values["MACD_Hist"]),
                    }
                )

            df = pd.DataFrame(df_data)
            df = df.sort_values("timestamp").reset_index(drop=True)

            logger.debug(f"Retrieved MACD data for {symbol}: {len(df)} values")

            return df

        except Exception as e:
            logger.error(f"Failed to get MACD for {symbol}: {e}")
            raise
