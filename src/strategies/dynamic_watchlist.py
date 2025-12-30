"""Dynamic Watchlist Generator - Discovers new trading opportunities.

Instead of static watchlist, dynamically finds stocks based on:
- Volume spikes
- Price breakouts
- Unusual activity
- Sector rotation
- Small/Mid caps with momentum

Uses free APIs (yfinance, finviz screener).
"""

from decimal import Decimal
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd

from ..utils.logger import logger


class DynamicWatchlistGenerator:
    """Generates dynamic watchlist based on market conditions."""

    # Market cap categories
    LARGE_CAP_MIN = 10_000_000_000  # $10B+
    MID_CAP_MIN = 2_000_000_000     # $2B-10B
    SMALL_CAP_MIN = 300_000_000     # $300M-2B

    # Base universe (expanded to include mid-caps)
    BASE_UNIVERSE = [
        # Mega Caps (always included)
        "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",

        # Large Caps - Tech
        "AMD", "AVGO", "NFLX", "CRM", "ORCL", "ADBE", "INTC",

        # Large Caps - Finance
        "JPM", "BAC", "WFC", "GS", "MS", "C", "USB",

        # Large Caps - Healthcare
        "LLY", "JNJ", "UNH", "PFE", "ABBV", "MRK",

        # Large Caps - Energy
        "XOM", "CVX", "COP", "SLB", "MPC",

        # Large Caps - Consumer
        "WMT", "HD", "MCD", "NKE", "SBUX", "TGT",

        # Mid Caps - High Growth (NEW!)
        "PLTR", "SNOW", "DDOG", "NET", "CRWD", "ZS",
        "SQ", "SHOP", "RBLX", "U", "PATH", "BILL",

        # Mid Caps - Industrials
        "CARR", "GNRC", "PWR", "MLM",

        # Sector ETFs (for trend detection)
        "XLK", "XLF", "XLE", "XLV", "XLI", "XLC",
    ]

    def __init__(self):
        """Initialize watchlist generator."""
        self.cache: Dict[str, Any] = {}

    async def generate_watchlist(
        self,
        max_tickers: int = 20,
        include_mid_caps: bool = True,
        include_small_caps: bool = False,
        min_volume: int = 1_000_000,  # Min 1M daily volume
        min_price: float = 5.0,        # Avoid penny stocks
    ) -> List[str]:
        """Generate dynamic watchlist based on market conditions.

        Args:
            max_tickers: Maximum number of tickers to return
            include_mid_caps: Include mid-cap stocks
            include_small_caps: Include small-cap stocks
            min_volume: Minimum daily volume
            min_price: Minimum stock price

        Returns:
            List of ticker symbols
        """
        logger.info(
            f"Generating dynamic watchlist (max={max_tickers}, "
            f"mid_caps={include_mid_caps}, small_caps={include_small_caps})"
        )

        watchlist_candidates = []

        # 1. Always include mega caps (top performers)
        mega_caps = ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA"]
        watchlist_candidates.extend(mega_caps)

        # 2. Scan base universe for volume/price criteria
        for ticker in self.BASE_UNIVERSE:
            if ticker in mega_caps:
                continue  # Already added

            try:
                # Get basic info
                stock = yf.Ticker(ticker)
                info = stock.info

                # Check filters
                avg_volume = info.get("averageVolume", 0)
                current_price = info.get("currentPrice", 0)
                market_cap = info.get("marketCap", 0)

                if avg_volume < min_volume:
                    continue
                if current_price < min_price:
                    continue

                # Filter by market cap
                if market_cap >= self.LARGE_CAP_MIN:
                    watchlist_candidates.append(ticker)
                elif include_mid_caps and market_cap >= self.MID_CAP_MIN:
                    watchlist_candidates.append(ticker)
                elif include_small_caps and market_cap >= self.SMALL_CAP_MIN:
                    watchlist_candidates.append(ticker)

            except Exception as e:
                logger.debug(f"Error checking {ticker}: {e}")
                continue

        # 3. Score candidates by momentum
        scored_candidates = []
        for ticker in watchlist_candidates:
            try:
                score = await self._score_momentum(ticker)
                scored_candidates.append((ticker, score))
            except Exception as e:
                logger.debug(f"Error scoring {ticker}: {e}")
                continue

        # 4. Sort by score and take top N
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        final_watchlist = [ticker for ticker, score in scored_candidates[:max_tickers]]

        logger.info(
            f"Generated watchlist with {len(final_watchlist)} tickers: {final_watchlist[:10]}..."
        )

        return final_watchlist

    async def _score_momentum(self, ticker: str) -> float:
        """Score a ticker's momentum (0.0-1.0).

        Higher score = stronger momentum.
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")

            if hist.empty or len(hist) < 20:
                return 0.0

            # Calculate momentum score
            close_prices = hist["Close"]

            # 1. Price vs SMA20/SMA50
            sma20 = close_prices.rolling(window=20).mean().iloc[-1]
            sma50 = close_prices.rolling(window=50).mean().iloc[-1]
            current_price = close_prices.iloc[-1]

            above_sma20 = 1.0 if current_price > sma20 else 0.0
            above_sma50 = 1.0 if current_price > sma50 else 0.0

            # 2. Recent performance (last 20 days)
            returns_20d = (current_price - close_prices.iloc[-20]) / close_prices.iloc[-20]
            returns_score = min(returns_20d * 2, 1.0) if returns_20d > 0 else 0.0

            # 3. Volume trend
            volumes = hist["Volume"]
            avg_volume = volumes.rolling(window=20).mean().iloc[-1]
            recent_volume = volumes.iloc[-1]
            volume_score = min(recent_volume / avg_volume / 2, 1.0)

            # Combine scores
            total_score = (above_sma20 * 0.3 + above_sma50 * 0.2 +
                          returns_score * 0.3 + volume_score * 0.2)

            return total_score

        except Exception as e:
            logger.debug(f"Error calculating momentum for {ticker}: {e}")
            return 0.0

    async def get_sector_leaders(self) -> List[str]:
        """Get leading stocks from each sector.

        Returns:
            List of sector-leading stocks
        """
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Finance",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLI": "Industrials",
            "XLC": "Communication",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
        }

        leaders = []

        for etf, sector_name in sector_etfs.items():
            try:
                # Get ETF performance
                etf_data = yf.Ticker(etf)
                etf_hist = etf_data.history(period="1mo")

                if etf_hist.empty:
                    continue

                # Check if sector is trending
                returns = (etf_hist["Close"].iloc[-1] - etf_hist["Close"].iloc[0]) / etf_hist["Close"].iloc[0]

                if returns > 0.02:  # Sector up > 2%
                    logger.debug(f"{sector_name} sector trending up ({returns:.1%})")
                    # Add sector leaders to watchlist
                    # (This would require a mapping of sector -> stocks)
                    # For now, we use the base universe

            except Exception as e:
                logger.debug(f"Error checking sector {etf}: {e}")
                continue

        return leaders


# Example usage in momentum_trading.py:
"""
from .dynamic_watchlist import DynamicWatchlistGenerator

async def scan_for_signals(alpaca_client):
    # Generate dynamic watchlist
    watchlist_gen = DynamicWatchlistGenerator()
    watchlist = await watchlist_gen.generate_watchlist(
        max_tickers=20,
        include_mid_caps=True,  # Include mid-caps!
        include_small_caps=False,  # Skip small-caps (too risky)
    )

    # Scan for momentum signals
    for ticker in watchlist:
        # ... existing momentum logic ...
"""
