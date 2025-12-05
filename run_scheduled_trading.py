"""Scheduled trading script - Runs multiple scans throughout the day.

Optimizes Alpha Vantage quota (25 requests/day) by spreading scans:
- Morning scan (7:00 AM Berlin) - Pre-market analysis
- Pre-open scan (15:00 Berlin) - Just before US market opens
- Mid-day scan (18:00 Berlin) - Mid-market check

Each scan uses ~10-12 requests, allowing 2 full scans per day.
"""

import asyncio
import sys
from datetime import UTC, datetime

from src.adapters.market_data_adapter import get_market_data_adapter
from src.main import daily_trading_loop
from src.utils.logger import logger


async def pre_market_scan():
    """Run pre-market analysis and place orders for market open.

    Orders placed during pre-market will execute when market opens.
    """
    logger.info("=" * 70)
    logger.info("PRE-MARKET SCAN STARTED")
    logger.info("=" * 70)
    logger.info(f"Time: {datetime.now(UTC).isoformat()}")
    logger.info("Scanning for momentum signals...")
    logger.info("Orders will be placed as MARKET orders (execute at open)")
    logger.info("=" * 70)

    try:
        # Run trading loop with pre-market flag enabled
        # This allows placing orders even when market is closed
        result = await daily_trading_loop(allow_premarket=True)

        logger.info("")
        logger.info("=" * 70)
        logger.info("PRE-MARKET SCAN COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Result: {result}")
        logger.info("")

        if result.get("orders_executed", 0) > 0:
            logger.info(f"Orders placed: {result['orders_executed']}")
            logger.info("These orders will execute when market opens at 9:30 AM ET")
        else:
            logger.info("No signals found - no orders placed")

        return result

    except Exception as e:
        logger.error(f"Error in pre-market scan: {e}", exc_info=True)
        raise


async def market_hours_scan():
    """Run scan during market hours and execute immediately."""
    logger.info("=" * 70)
    logger.info("MARKET HOURS SCAN STARTED")
    logger.info("=" * 70)
    logger.info(f"Time: {datetime.now(UTC).isoformat()}")
    logger.info("=" * 70)

    try:
        # Check if market is open
        adapter = await get_market_data_adapter()
        if not await adapter.is_market_open():
            logger.info("Market is currently closed - skipping scan")
            logger.info("Use pre-market scan instead")
            return {"status": "skipped", "reason": "market_closed"}

        # Run trading loop
        result = await daily_trading_loop()

        logger.info("")
        logger.info("=" * 70)
        logger.info("MARKET HOURS SCAN COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Result: {result}")
        logger.info("")

        return result

    except Exception as e:
        logger.error(f"Error in market hours scan: {e}", exc_info=True)
        raise


async def scheduled_scan(scan_type: str = "market"):
    """Run scheduled scan based on type.

    Args:
        scan_type: "pre-market" or "market" (default: "market")
    """
    if scan_type == "pre-market":
        return await pre_market_scan()
    else:
        return await market_hours_scan()


def main():
    """Main entry point for scheduled scans."""
    # Get scan type from command line (default: market)
    scan_type = "market"
    if len(sys.argv) > 1:
        scan_type = sys.argv[1]

    logger.info(f"Starting scheduled scan: {scan_type}")

    try:
        asyncio.run(scheduled_scan(scan_type))
        logger.info("Scheduled scan completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduled scan failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
