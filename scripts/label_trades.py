"""Daily labeling script for ML training data.

Run this script daily (via cron or Task Scheduler) to label trades
after their hold period (7, 14, or 30 days) and record the outcome.

Usage:
    python scripts/label_trades.py
    python scripts/label_trades.py --hold-period 14
    python scripts/label_trades.py --all
"""

import argparse
import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.models.ml_data import MLDataLabel
from src.utils.logger import logger

# Labeling thresholds
PROFITABLE_THRESHOLD = Decimal("0.05")  # +5% = profitable
UNPROFITABLE_THRESHOLD = Decimal("-0.02")  # -2% = unprofitable
# Between -2% and +5% = neutral


async def label_trades_for_period(hold_period: int) -> dict:
    """Label all unlabeled trades from X days ago.

    Args:
        hold_period: Number of days to hold before labeling (7, 14, or 30)

    Returns:
        Dict with labeling statistics
    """
    logger.info(f"=== Labeling trades with {hold_period}-day hold period ===")

    # Get unlabeled trades from X days ago
    unlabeled = await SupabaseClient.get_unlabeled_ml_data(
        days_ago=hold_period, hold_period=hold_period
    )

    if not unlabeled:
        logger.info(f"No unlabeled trades found from {hold_period} days ago")
        return {
            "hold_period": hold_period,
            "total": 0,
            "labeled": 0,
            "profitable": 0,
            "unprofitable": 0,
            "neutral": 0,
            "errors": 0,
        }

    logger.info(f"Found {len(unlabeled)} trades to label")

    # Initialize Alpaca client for current prices
    alpaca_client = AlpacaMCPClient()

    stats = {
        "hold_period": hold_period,
        "total": len(unlabeled),
        "labeled": 0,
        "profitable": 0,
        "unprofitable": 0,
        "neutral": 0,
        "errors": 0,
    }

    for record in unlabeled:
        try:
            ticker = record["ticker"]
            entry_price = Decimal(str(record["entry_price"]))
            record_id = record["id"]

            # Get current price
            quote = await alpaca_client.get_latest_quote(ticker)
            current_price = Decimal(str(quote.get("price", quote.get("last", 0))))

            if current_price == 0:
                logger.warning(f"Could not get price for {ticker}, skipping")
                stats["errors"] += 1
                continue

            # Calculate return
            return_pct = (current_price - entry_price) / entry_price

            # Determine outcome
            if return_pct >= PROFITABLE_THRESHOLD:
                outcome = "profitable"
                stats["profitable"] += 1
            elif return_pct <= UNPROFITABLE_THRESHOLD:
                outcome = "unprofitable"
                stats["unprofitable"] += 1
            else:
                outcome = "neutral"
                stats["neutral"] += 1

            # Create label
            label = MLDataLabel(
                hold_period_days=hold_period,
                exit_price=current_price,
                outcome=outcome,
                return_pct=return_pct,
                max_drawdown_pct=None,  # TODO: Calculate from historical data
                max_gain_pct=None,  # TODO: Calculate from historical data
                sharpe_ratio=None,  # TODO: Calculate if we have daily prices
                label_timestamp=datetime.now(UTC),
            )

            # Update database
            await SupabaseClient.update_ml_label(record_id, label)

            logger.info(
                f"Labeled {ticker}: {outcome} ({return_pct:+.2%}) "
                f"after {hold_period} days"
            )

            stats["labeled"] += 1

        except Exception as e:
            logger.error(f"Failed to label trade {record.get('ticker', 'unknown')}: {e}")
            stats["errors"] += 1
            continue

    return stats


async def main(hold_periods: list[int] | None = None):
    """Main labeling loop.

    Args:
        hold_periods: List of hold periods to process (default: [7, 14, 30])
    """
    if hold_periods is None:
        hold_periods = [7, 14, 30]

    logger.info("=============================================================")
    logger.info("ML TRAINING DATA LABELING SCRIPT")
    logger.info("=============================================================")
    logger.info(f"Time: {datetime.now(UTC).isoformat()}")
    logger.info(f"Hold periods: {hold_periods}")
    logger.info("=============================================================")
    logger.info("")

    all_stats = []

    for period in hold_periods:
        stats = await label_trades_for_period(period)
        all_stats.append(stats)
        logger.info("")

    # Print summary
    logger.info("=============================================================")
    logger.info("LABELING SUMMARY")
    logger.info("=============================================================")

    total_labeled = sum(s["labeled"] for s in all_stats)
    total_profitable = sum(s["profitable"] for s in all_stats)
    total_unprofitable = sum(s["unprofitable"] for s in all_stats)
    total_neutral = sum(s["neutral"] for s in all_stats)
    total_errors = sum(s["errors"] for s in all_stats)

    for stats in all_stats:
        logger.info(
            f"{stats['hold_period']}-day: "
            f"{stats['labeled']}/{stats['total']} labeled "
            f"({stats['profitable']} profitable, "
            f"{stats['unprofitable']} unprofitable, "
            f"{stats['neutral']} neutral, "
            f"{stats['errors']} errors)"
        )

    logger.info("")
    logger.info(
        f"Total: {total_labeled} labeled "
        f"({total_profitable} profitable, "
        f"{total_unprofitable} unprofitable, "
        f"{total_neutral} neutral, "
        f"{total_errors} errors)"
    )

    if total_labeled > 0:
        profitable_pct = (total_profitable / total_labeled) * 100
        logger.info(f"Win rate: {profitable_pct:.1f}%")

    logger.info("=============================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label ML training data")
    parser.add_argument(
        "--hold-period",
        type=int,
        choices=[7, 14, 30],
        help="Specific hold period to process (default: all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all hold periods (default behavior)",
    )

    args = parser.parse_args()

    if args.hold_period:
        hold_periods = [args.hold_period]
    else:
        hold_periods = [7, 14, 30]

    asyncio.run(main(hold_periods))
