"""Test Alpaca IEX data feed for momentum strategy."""

import asyncio

from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.utils.logger import logger


async def test_iex_feed():
    """Test IEX data feed from Alpaca."""
    logger.info("=== Testing Alpaca IEX Data Feed ===")
    logger.info("")

    try:
        # Initialize client
        client = AlpacaMCPClient()

        # Test 1: Get bars for AAPL
        logger.info("Test 1: Fetching 30 days of AAPL bars from IEX...")
        bars = await client.get_bars("AAPL", days=30)

        if not bars.empty:
            logger.info(f"  SUCCESS: Retrieved {len(bars)} bars")
            logger.info(f"  Latest close: ${bars.iloc[-1]['close']:.2f}")
            logger.info(f"  Date range: {bars.iloc[0]['timestamp']} to {bars.iloc[-1]['timestamp']}")
        else:
            logger.error("  FAILED: No data returned")

        logger.info("")

        # Test 2: Test multiple tickers
        logger.info("Test 2: Testing multiple tickers (AAPL, MSFT, NVDA)...")
        tickers = ["AAPL", "MSFT", "NVDA"]
        success_count = 0

        for ticker in tickers:
            bars = await client.get_bars(ticker, days=10)
            if not bars.empty:
                logger.info(f"  {ticker}: {len(bars)} bars retrieved")
                success_count += 1
            else:
                logger.error(f"  {ticker}: FAILED")

        logger.info(f"  SUCCESS: {success_count}/{len(tickers)} tickers")

        logger.info("")
        logger.info("=== Test Complete ===")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_iex_feed())
