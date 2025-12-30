"""Internal Scheduler Service.

Runs the daily trading loop at specified times.
Replaces external schedulers like cron or Ofelia for self-contained execution.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from time import sleep

from src.main import daily_trading_loop
from src.utils.logger import logger

# Eastern Time for market hours
ET = pytz.timezone('US/Eastern')

async def run_scheduler():
    """Run the scheduler loop."""
    logger.info("Starting Internal Scheduler Service")
    logger.info("Target: Daily trading at 9:35 AM ET")

    while True:
        try:
            now_et = datetime.now(ET)
            
            # Schedule for 9:35 AM ET
            target_time = now_et.replace(hour=9, minute=35, second=0, microsecond=0)
            
            # If target already passed today, schedule for tomorrow
            if now_et >= target_time:
                target_time = target_time + timedelta(days=1)
            
            # Calculate sleep duration
            sleep_seconds = (target_time - now_et).total_seconds()
            
            next_run_str = target_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            logger.info(f"Next run scheduled for: {next_run_str} (in {sleep_seconds/3600:.1f} hours)")
            
            # Sleep until next run (wake up occasionally to log health?)
            # Sleeping full duration is efficient for CPU
            await asyncio.sleep(sleep_seconds)
            
            # Execute trading loop
            logger.info("Waking up for scheduled trading...")
            await daily_trading_loop()
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            # Sleep a bit before retrying to avoid tight loop on error
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
