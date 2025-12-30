"""Internal Scheduler Service.

Multi-frequency trading scheduler with exit monitoring.
Replaces external schedulers like cron or Ofelia for self-contained execution.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time as dt_time
import pytz
from time import sleep

from src.main import daily_trading_loop
from src.utils.logger import logger

# Eastern Time for market hours
ET = pytz.timezone('US/Eastern')

# Trading schedule (Eastern Time)
ENTRY_SCAN_TIMES = [
    dt_time(9, 35),   # Gap & Morning Momentum
    dt_time(10, 30),  # Post-Open Continuation
    dt_time(12, 0),   # Midday Breakouts
    dt_time(14, 0),   # Afternoon Setup
    dt_time(15, 45),  # Power Hour Momentum
]

# Exit monitoring frequency (minutes)
EXIT_MONITORING_INTERVAL = 5  # Every 5 minutes during market hours

async def should_run_entry_scan(now_et: datetime) -> bool:
    """Check if we should run an entry scan now."""
    current_time = now_et.time()

    # Check if current time matches any scheduled entry scan (within 1 minute)
    for scan_time in ENTRY_SCAN_TIMES:
        time_diff = abs(
            (current_time.hour * 60 + current_time.minute) -
            (scan_time.hour * 60 + scan_time.minute)
        )
        if time_diff <= 1:
            return True
    return False

async def is_market_hours(now_et: datetime) -> bool:
    """Check if current time is during market hours (9:30 AM - 4:00 PM ET)."""
    current_time = now_et.time()
    market_open = dt_time(9, 30)
    market_close = dt_time(16, 0)

    # Check if weekday (Monday=0, Sunday=6)
    if now_et.weekday() >= 5:
        return False

    return market_open <= current_time <= market_close

async def run_scheduler():
    """Run the multi-frequency trading scheduler."""
    logger.info("=" * 60)
    logger.info("Starting Multi-Frequency Trading Scheduler")
    logger.info("=" * 60)
    logger.info("Entry Scans: 5x daily (9:35, 10:30, 12:00, 14:00, 15:45 ET)")
    logger.info("Exit Monitoring: Every 5 minutes during market hours")
    logger.info("=" * 60)

    last_entry_scan = None
    last_exit_check = None

    while True:
        try:
            now_et = datetime.now(ET)

            # Entry Scan - Run at scheduled times
            if await should_run_entry_scan(now_et):
                # Avoid running same scan twice
                if last_entry_scan is None or (now_et - last_entry_scan).total_seconds() > 60:
                    logger.info(f"🎯 ENTRY SCAN triggered at {now_et.strftime('%H:%M:%S ET')}")
                    await daily_trading_loop()
                    last_entry_scan = now_et

            # Exit Monitoring - Run every 5 minutes during market hours
            elif await is_market_hours(now_et):
                # Check if 5 minutes passed since last exit check
                if last_exit_check is None or (now_et - last_exit_check).total_seconds() >= EXIT_MONITORING_INTERVAL * 60:
                    logger.info(f"🔍 Exit monitoring at {now_et.strftime('%H:%M:%S ET')}")
                    await daily_trading_loop()  # This will check exit conditions
                    last_exit_check = now_et

            # Sleep for 30 seconds before next check
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            # Sleep before retrying to avoid tight loop on error
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
