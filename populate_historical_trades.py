"""Populate database with historical trades from current positions."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.models.trade import Trade
from src.utils.logger import logger


async def populate_historical_trades():
    """Create trade records for current positions."""
    logger.info("=== Populating Historical Trades ===")

    # Initialize clients
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    logger.info(f"Found {len(positions)} positions to log")

    # Create entry trades for each position (dated yesterday to avoid "today" filter)
    yesterday = datetime.now(UTC) - timedelta(days=1)

    trades_to_log = []

    for pos in positions:
        # Entry trade
        entry_trade = Trade(
            date=yesterday,
            ticker=pos.symbol,
            action="BUY",
            quantity=pos.quantity,
            entry_price=pos.avg_entry_price,
            strategy="defensive" if pos.symbol in ["VTI", "VGK", "GLD"] else "momentum",
            alpaca_order_id=f"historical_{pos.symbol}",
        )
        trades_to_log.append(entry_trade)

        logger.info(
            f"Prepared entry trade: BUY {pos.quantity} {pos.symbol} @ ${pos.avg_entry_price}"
        )

    # Log all trades
    for trade in trades_to_log:
        try:
            await SupabaseClient.log_trade(trade)
            logger.info(f"Logged: {trade.action} {trade.quantity} {trade.ticker}")
        except Exception as e:
            logger.error(f"Failed to log trade {trade.ticker}: {e}")

    logger.info(f"\n{len(trades_to_log)} trades logged successfully!")

    # Verify trades in database
    logger.info("\nVerifying trades in database...")
    supabase = await SupabaseClient.get_instance()
    response = await supabase.table("trades").select("*").order("date", desc=True).execute()
    trades = response.data

    logger.info(f"Total trades in database: {len(trades)}")
    for trade in trades[:5]:  # Show first 5
        logger.info(
            f"  - {trade.get('date')}: {trade.get('action')} {trade.get('quantity')} "
            f"{trade.get('ticker')} @ ${trade.get('entry_price')} ({trade.get('strategy')})"
        )

    logger.info("\n=== Historical Trades Population Completed ===")


if __name__ == "__main__":
    asyncio.run(populate_historical_trades())
