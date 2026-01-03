"""Event-Driven Trading Service.

Combines:
1. Multi-frequency scheduler (5x daily entry scans + 5min exit monitoring)
2. Real-time price/volume alerts (Alpaca WebSocket)
3. Breaking news monitoring (RSS feeds)

Architecture:
- Scheduled scans run at fixed times
- Real-time events trigger immediate focused scans
- All events logged for analysis
"""

import asyncio
from datetime import datetime
import pytz

from src.scheduler_service import run_scheduler
from src.adapters.realtime_stream import RealtimeMarketStream
from src.adapters.rss_monitor import RSSFeedMonitor
from src.main import daily_trading_loop
from src.utils.config import config
from src.utils.logger import logger


# Watchlist for real-time monitoring
MONITORED_TICKERS = [
    # Mega caps
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "META",
    "AMZN",
    "TSLA",
    # High momentum stocks
    "AMD",
    "PLTR",
    "SNOW",
    "CRWD",
    "NET",
    "DDOG",
    "SQ",
    # Volatility plays
    "SHOP",
    "RBLX",
    "U",
    "DASH",
]


class EventDrivenTradingService:
    """Unified event-driven trading service.

    Runs three concurrent tasks:
    1. Scheduled scans (time-based)
    2. Real-time market monitoring (event-based)
    3. News monitoring (event-based)
    """

    def __init__(self):
        """Initialize event-driven service."""
        self.realtime_stream = None
        self.rss_monitor = None
        self.running = False

        logger.info("Event-Driven Trading Service initialized")

    async def handle_market_event(self, event_type: str, ticker: str, data: dict):
        """Handle real-time market events (price/volume).

        Triggers immediate entry scan for the ticker.
        """
        logger.info(f"🎯 Market event: {event_type} on {ticker}")
        logger.info(f"   Data: {data}")

        # TODO: Modify daily_trading_loop to accept focused_ticker
        # For now, just log the event
        # await daily_trading_loop(focused_ticker=ticker)

    async def handle_news_event(self, event_type: str, ticker: str, data: dict):
        """Handle breaking news events.

        Triggers immediate entry scan for the ticker.
        """
        logger.info(f"📰 News event: {event_type} on {ticker}")
        logger.info(f"   Title: {data.get('title')}")

        # TODO: Trigger focused scan
        # await daily_trading_loop(focused_ticker=ticker)

    async def _run_heartbeat(self):
        """Log heartbeat to ensure service is alive."""
        while self.running:
            try:
                logger.info("💓 Event-Driven Service Heartbeat - System Operational")
                await asyncio.sleep(3600)  # Log every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)

    async def start(self):
        """Start all monitoring services."""
        logger.info("=" * 70)
        logger.info("🚀 Starting Event-Driven Trading Service")
        logger.info("=" * 70)

        self.running = True

        # Create tasks for concurrent execution
        tasks = []

        # Task 0: Heartbeat
        tasks.append(asyncio.create_task(self._run_heartbeat()))

        # Task 1: Multi-frequency scheduler
        tasks.append(asyncio.create_task(run_scheduler()))
        logger.info("✅ Multi-frequency scheduler started")

        # Task 2: Real-time market monitoring (if enabled)
        if config.ENABLE_LLM_FEATURES:  # Use same flag for now
            self.realtime_stream = RealtimeMarketStream(
                watchlist=MONITORED_TICKERS, event_callback=self.handle_market_event
            )
            tasks.append(asyncio.create_task(self.realtime_stream.start()))
            logger.info(f"✅ Real-time market stream started ({len(MONITORED_TICKERS)} tickers)")

            # Task 3: RSS news monitoring
            self.rss_monitor = RSSFeedMonitor(
                watchlist=MONITORED_TICKERS, event_callback=self.handle_news_event
            )
            tasks.append(asyncio.create_task(self.rss_monitor.start()))
            logger.info("✅ RSS news monitor started")

        logger.info("=" * 70)
        logger.info("All services running. Press Ctrl+C to stop.")
        logger.info("=" * 70)

        # Run all tasks concurrently
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Services cancelled")
        except Exception as e:
            logger.error(f"Service error: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop all services."""
        logger.info("Stopping Event-Driven Trading Service...")
        self.running = False

        if self.realtime_stream:
            await self.realtime_stream.stop()

        if self.rss_monitor:
            await self.rss_monitor.stop()

        logger.info("All services stopped")


async def main():
    """Main entry point."""
    service = EventDrivenTradingService()

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
