"""Background trading loop - runs continuously and executes trades.

This script:
1. Waits for market to open
2. Executes daily trading loop
3. Logs all activity
4. Runs until manually stopped
"""

import asyncio
import sys
from datetime import UTC, datetime

from src.adapters.market_data_adapter import get_market_data_adapter
from src.main import daily_trading_loop
from src.utils.logger import logger


async def wait_for_market_open():
    """Wait until market opens."""
    adapter = await get_market_data_adapter()

    while True:
        clock = await adapter.get_market_clock()

        if clock and clock.is_open:
            logger.info("Market is OPEN - Starting trading")
            return True

        if clock:
            logger.info(f"Market closed - Next open: {clock.next_open}")
            logger.info("   Waiting 60 seconds...")
        else:
            logger.warning("Could not get market clock - waiting 60s...")

        await asyncio.sleep(60)  # Check every minute


async def background_trading_loop():
    """Run trading loop in background with market hours check."""
    logger.info("=" * 70)
    logger.info("BACKGROUND TRADING STARTED")
    logger.info("=" * 70)
    logger.info(f"Time: {datetime.now(UTC).isoformat()}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)

    try:
        # Wait for market to open
        await wait_for_market_open()

        # Execute trading loop
        logger.info("")
        logger.info("Executing daily trading loop...")
        logger.info("")

        result = await daily_trading_loop()

        logger.info("")
        logger.info("=" * 70)
        logger.info("TRADING LOOP COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Result: {result}")
        logger.info("")
        logger.info("System will now monitor positions until market close...")
        logger.info("(Currently no exit monitoring implemented - manual only)")

        # Keep running to show logs
        logger.info("")
        logger.info("Press Ctrl+C to stop background loop")

        while True:
            await asyncio.sleep(300)  # Check every 5 minutes

            # Optional: Could add position monitoring here
            adapter = await get_market_data_adapter()
            if not await adapter.is_market_open():
                logger.info("Market has closed - stopping background loop")
                break

    except KeyboardInterrupt:
        logger.info("")
        logger.info("Background trading stopped by user")

    except Exception as e:
        logger.error(f"❌ Error in background loop: {e}", exc_info=True)
        raise

    finally:
        logger.info("")
        logger.info("=" * 70)
        logger.info("Background trading loop ended")
        logger.info("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(background_trading_loop())
    except KeyboardInterrupt:
        logger.info("Exiting...")
        sys.exit(0)
