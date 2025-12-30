"""Test Alpha Vantage integration for momentum strategy."""

import asyncio

from src.clients.alpha_vantage_client import AlphaVantageClient
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.strategies.momentum_trading import scan_for_signals
from src.utils.logger import logger


async def test_alpha_vantage():
    """Test Alpha Vantage client and momentum scan."""
    logger.info("=== Testing Alpha Vantage Integration ===")
    logger.info("")

    # Test 1: Alpha Vantage client basic functionality
    logger.info("Test 1: Fetch bars for AAPL from Alpha Vantage")
    av_client = AlphaVantageClient()

    try:
        bars = await av_client.get_bars("AAPL", days=60)
        logger.info(f"  SUCCESS: Retrieved {len(bars)} bars for AAPL")
        logger.info(f"  Latest close: ${bars.iloc[-1]['close']:.2f}")
        logger.info(f"  Date range: {bars.iloc[0]['timestamp']} to {bars.iloc[-1]['timestamp']}")
    except Exception as e:
        logger.error(f"  FAILED: {e}")
        return

    logger.info("")

    # Test 2: Full momentum scan
    logger.info("Test 2: Run momentum scan with Alpha Vantage")
    logger.info("  NOTE: This will take ~2 minutes due to rate limiting (12s per ticker)")

    alpaca_client = AlpacaMCPClient()

    try:
        signals = await scan_for_signals(alpaca_client)
        logger.info(f"  SUCCESS: Scan completed")
        logger.info(f"  Found {len(signals)} momentum signals")

        if signals:
            logger.info("")
            logger.info("  Signals:")
            for signal in signals:
                logger.info(
                    f"    {signal.ticker}: ${signal.entry_price:.2f} "
                    f"(confidence: {signal.confidence:.2f})"
                )
    except Exception as e:
        logger.error(f"  FAILED: {e}", exc_info=True)

    logger.info("")
    logger.info("=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_alpha_vantage())
