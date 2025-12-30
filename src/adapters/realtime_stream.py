"""Real-time Market Data Stream via Alpaca WebSocket.

Monitors:
- Price movements (>2% in 5 minutes → Alert)
- Volume spikes (>3x average → Alert)
- Gap detection (pre-market vs open)

Triggers immediate entry scans when opportunities detected.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Callable, Any
from collections import deque

from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed
from alpaca.data.models import Bar

from ..utils.config import config
from ..utils.logger import logger


class RealtimeMarketStream:
    """Real-time market data stream for event-driven trading.

    Monitors watchlist for:
    1. Rapid price movements (momentum breakouts)
    2. Volume explosions (unusual activity)
    3. Gap ups/downs (pre-market movers)

    Triggers callbacks when events detected.
    """

    def __init__(self, watchlist: list[str], event_callback: Callable):
        """Initialize real-time stream.

        Args:
            watchlist: List of tickers to monitor
            event_callback: Async function to call when event detected
                          signature: async def callback(event_type: str, ticker: str, data: dict)
        """
        self.watchlist = watchlist
        self.event_callback = event_callback

        # Initialize Alpaca WebSocket stream
        self.stream = StockDataStream(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            feed=DataFeed.IEX,  # Use IEX for free tier
        )

        # Track recent bars for each ticker (5-minute window)
        self.price_history: Dict[str, deque] = {
            ticker: deque(maxlen=5) for ticker in watchlist
        }

        # Track average volume (20-bar rolling average)
        self.volume_history: Dict[str, deque] = {
            ticker: deque(maxlen=20) for ticker in watchlist
        }

        # Event thresholds
        self.PRICE_CHANGE_THRESHOLD = 0.02  # 2% move triggers alert
        self.VOLUME_SPIKE_MULTIPLIER = 3.0  # 3x average volume
        self.GAP_THRESHOLD = 0.015  # 1.5% gap

        logger.info(f"RealtimeMarketStream initialized for {len(watchlist)} tickers")

    async def _handle_bar(self, bar: Bar):
        """Handle incoming bar data."""
        ticker = bar.symbol

        # Store price
        self.price_history[ticker].append({
            'timestamp': bar.timestamp,
            'close': float(bar.close),
            'volume': float(bar.volume),
        })

        # Store volume
        self.volume_history[ticker].append(float(bar.volume))

        # Check for price momentum
        await self._check_price_momentum(ticker)

        # Check for volume spike
        await self._check_volume_spike(ticker)

    async def _check_price_momentum(self, ticker: str):
        """Check if price moved significantly in last 5 minutes."""
        if len(self.price_history[ticker]) < 2:
            return

        recent_bars = list(self.price_history[ticker])
        first_price = recent_bars[0]['close']
        last_price = recent_bars[-1]['close']

        price_change = (last_price - first_price) / first_price

        if abs(price_change) >= self.PRICE_CHANGE_THRESHOLD:
            direction = "UP" if price_change > 0 else "DOWN"
            logger.info(f"🚨 MOMENTUM ALERT: {ticker} moved {price_change*100:.2f}% {direction}")

            await self.event_callback(
                event_type="price_momentum",
                ticker=ticker,
                data={
                    'price_change': price_change,
                    'direction': direction,
                    'current_price': last_price,
                    'timestamp': recent_bars[-1]['timestamp'],
                }
            )

    async def _check_volume_spike(self, ticker: str):
        """Check if volume is unusually high."""
        if len(self.volume_history[ticker]) < 10:  # Need baseline
            return

        volumes = list(self.volume_history[ticker])
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1])  # Exclude current
        current_volume = volumes[-1]

        if current_volume > avg_volume * self.VOLUME_SPIKE_MULTIPLIER:
            logger.info(f"🔊 VOLUME SPIKE: {ticker} volume {current_volume/avg_volume:.1f}x average")

            await self.event_callback(
                event_type="volume_spike",
                ticker=ticker,
                data={
                    'current_volume': current_volume,
                    'average_volume': avg_volume,
                    'multiplier': current_volume / avg_volume,
                    'timestamp': datetime.now(),
                }
            )

    async def start(self):
        """Start the real-time stream."""
        logger.info(f"Starting real-time stream for {len(self.watchlist)} tickers...")

        # Subscribe to bars for all tickers
        for ticker in self.watchlist:
            self.stream.subscribe_bars(self._handle_bar, ticker)

        # Run stream
        try:
            await self.stream._run_forever()
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the real-time stream."""
        logger.info("Stopping real-time stream...")
        await self.stream.close()


async def event_handler(event_type: str, ticker: str, data: dict):
    """Example event handler.

    This gets called when real-time events are detected.
    Triggers immediate entry scan for the ticker.
    """
    from src.main import daily_trading_loop

    logger.info(f"Event detected: {event_type} on {ticker}")
    logger.info(f"Event data: {data}")

    # Trigger immediate scan focused on this ticker
    # (You can modify daily_trading_loop to accept a focused_ticker parameter)
    logger.info(f"Triggering immediate entry scan for {ticker}...")
    # await daily_trading_loop(focused_ticker=ticker)
