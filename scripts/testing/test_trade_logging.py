"""Test trade logging to Supabase database."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.models.trade import Trade
from src.utils.logger import logger


async def test_trade_logging():
    """Test creating and logging a trade to database."""
    logger.info("=== Testing Trade Logging ===")

    # Create a test trade
    test_trade = Trade(
        date=datetime.now(UTC),
        ticker="AAPL",
        action="BUY",
        quantity=Decimal("10"),
        entry_price=Decimal("268.50"),
        strategy="momentum",
        rsi=Decimal("62.5"),
        macd_histogram=Decimal("1.25"),
        volume_ratio=Decimal("1.8"),
        alpaca_order_id="test_order_123",
    )

    logger.info(f"Created test trade: {test_trade.action} {test_trade.quantity} {test_trade.ticker}")

    # Log to database
    try:
        result = await SupabaseClient.log_trade(test_trade)
        logger.info(f"Trade logged successfully: {result}")
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")
        raise

    # Verify it was saved
    logger.info("\nVerifying trade in database...")
    supabase = await SupabaseClient.get_instance()

    try:
        response = await supabase.table("trades").select("*").eq("ticker", "AAPL").order("date", desc=True).limit(1).execute()
        trades = response.data

        if trades:
            latest_trade = trades[0]
            logger.info("Found trade in database:")
            logger.info(f"  Date: {latest_trade.get('date')}")
            logger.info(f"  Ticker: {latest_trade.get('ticker')}")
            logger.info(f"  Action: {latest_trade.get('action')}")
            logger.info(f"  Quantity: {latest_trade.get('quantity')}")
            logger.info(f"  Entry Price: ${latest_trade.get('entry_price')}")
            logger.info(f"  Strategy: {latest_trade.get('strategy')}")
            logger.info("OK Trade logging works!")
        else:
            logger.error("Trade not found in database!")

    except Exception as e:
        logger.error(f"Failed to query trades: {e}")
        raise

    logger.info("\n=== Trade Logging Test Completed ===")


if __name__ == "__main__":
    asyncio.run(test_trade_logging())
