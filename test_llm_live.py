"""Live test of LLM features with current portfolio positions."""

import asyncio
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.llm.trade_explainer import get_trade_explainer
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.models.portfolio import Portfolio
from src.models.trade import Trade
from src.utils.config import config
from src.utils.logger import logger


async def test_llm_live():
    """Test LLM with current live portfolio data."""
    logger.info("=" * 70)
    logger.info("LIVE LLM TEST - Trade Explanation Generator")
    logger.info("=" * 70)
    logger.info(f"LLM Features Enabled: {config.ENABLE_LLM_FEATURES}")
    logger.info(f"Model: {config.OPENROUTER_MODEL}")
    logger.info("")

    # Get current portfolio from Alpaca
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    logger.info("CURRENT PORTFOLIO:")
    logger.info(f"  Portfolio Value: ${portfolio.portfolio_value:,.2f}")
    logger.info(f"  Cash: ${portfolio.cash:,.2f}")
    logger.info(f"  Positions: {len(positions)}")
    logger.info("")

    # Get explainer
    explainer = await get_trade_explainer()

    # Test explanation for each current position
    logger.info("GENERATING EXPLANATIONS FOR CURRENT POSITIONS:")
    logger.info("-" * 70)

    for position in positions:
        # Create a simulated trade for this position
        trade = Trade(
            date="2025-11-19T00:00:00",
            ticker=position.symbol,
            action="BUY",
            quantity=position.quantity,
            entry_price=position.avg_entry_price,
            strategy="defensive" if position.symbol in ["VTI", "VGK", "GLD"] else "momentum",
        )

        logger.info(f"\nPosition: {position.symbol}")
        logger.info(f"  Quantity: {position.quantity}")
        logger.info(f"  Entry Price: ${position.avg_entry_price}")
        logger.info(f"  Current Price: ${position.current_price}")
        logger.info(f"  Market Value: ${position.market_value:,.2f}")
        logger.info(f"  P&L: ${position.unrealized_pnl:,.2f} ({float(position.unrealized_pnl_pct)*100:+.2f}%)")

        # Generate LLM explanation
        logger.info("\n  Generating LLM explanation...")
        explanation = await explainer.explain_trade(trade, portfolio)

        logger.info(f"\n  LLM EXPLANATION:")
        logger.info(f"  {explanation}")
        logger.info("-" * 70)

    logger.info("\n" + "=" * 70)
    logger.info("LIVE TEST COMPLETED")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_llm_live())
