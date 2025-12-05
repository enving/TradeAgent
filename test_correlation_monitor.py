"""Test script for Portfolio Correlation Monitor.

Tests correlation checks and sector concentration rules.
"""

import asyncio
from decimal import Decimal

from src.models.portfolio import Position
from src.models.trade import Signal
from src.risk.correlation_monitor import get_correlation_monitor
from src.utils.logger import logger


async def test_correlation_monitor():
    """Test the correlation monitor with sample data."""

    logger.info("=" * 60)
    logger.info("TESTING PORTFOLIO CORRELATION MONITOR")
    logger.info("=" * 60)

    monitor = get_correlation_monitor()

    # Test 1: Sector Concentration
    logger.info("\n📊 TEST 1: Sector Concentration Check")
    logger.info("-" * 60)

    current_positions = [
        Position(
            symbol="AAPL",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("180"),
            current_price=Decimal("185"),
            market_value=Decimal("1850"),
            unrealized_pnl=Decimal("50"),
            unrealized_pnl_pct=Decimal("0.0278"),
        ),
        Position(
            symbol="MSFT",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("380"),
            current_price=Decimal("390"),
            market_value=Decimal("3900"),
            unrealized_pnl=Decimal("100"),
            unrealized_pnl_pct=Decimal("0.0263"),
        ),
    ]

    portfolio_value = Decimal("10000")

    # Try to add another tech stock (GOOGL)
    signal_googl = Signal(
        ticker="GOOGL",
        action="BUY",
        entry_price=Decimal("140"),
        confidence=Decimal("0.85"),
        strategy="momentum",
    )

    logger.info("Current positions: AAPL ($1850), MSFT ($3900)")
    logger.info("Portfolio value: $10,000")
    logger.info("Sector allocation: Technology = 57.5%")
    logger.info("\nAttempting to add GOOGL (another tech stock)...")

    approved, reason = await monitor.check_new_signal(
        signal_googl, current_positions, portfolio_value
    )

    if approved:
        logger.info("✅ GOOGL approved (sector concentration OK)")
    else:
        logger.warning(f"❌ GOOGL rejected: {reason}")

    # Test 2: Correlation Check
    logger.info("\n\n🔗 TEST 2: Correlation Check")
    logger.info("-" * 60)

    # Add NVDA (highly correlated with tech stocks)
    signal_nvda = Signal(
        ticker="NVDA",
        action="BUY",
        entry_price=Decimal("500"),
        confidence=Decimal("0.90"),
        strategy="momentum",
    )

    logger.info("Current positions: AAPL, MSFT (both tech)")
    logger.info("Attempting to add NVDA (semiconductor, correlated with tech)...")

    approved, reason = await monitor.check_new_signal(
        signal_nvda, current_positions, portfolio_value
    )

    if approved:
        logger.info("✅ NVDA approved")
    else:
        logger.warning(f"❌ NVDA rejected: {reason}")

    # Test 3: Diversified Position (Should Pass)
    logger.info("\n\n🌐 TEST 3: Diversified Position Check")
    logger.info("-" * 60)

    signal_xom = Signal(
        ticker="XOM",
        action="BUY",
        entry_price=Decimal("110"),
        confidence=Decimal("0.80"),
        strategy="momentum",
    )

    logger.info("Current positions: AAPL, MSFT (tech)")
    logger.info("Attempting to add XOM (energy, low correlation)...")

    approved, reason = await monitor.check_new_signal(
        signal_xom, current_positions, portfolio_value
    )

    if approved:
        logger.info("✅ XOM approved (good diversification!)")
    else:
        logger.warning(f"❌ XOM rejected: {reason}")

    # Test 4: Sector Allocation Report
    logger.info("\n\n📈 TEST 4: Portfolio Analysis")
    logger.info("-" * 60)

    sector_allocation = monitor.get_sector_allocation(
        current_positions, portfolio_value
    )

    logger.info("Current sector allocations:")
    for sector, allocation in sorted(
        sector_allocation.items(), key=lambda x: x[1], reverse=True
    ):
        logger.info(f"  {sector}: {allocation:.1%}")

    # Test 5: Correlation Matrix
    logger.info("\n\n🔢 TEST 5: Correlation Matrix")
    logger.info("-" * 60)

    # Pre-load price histories
    await monitor._get_price_history("AAPL")
    await monitor._get_price_history("MSFT")
    await monitor._get_price_history("NVDA")

    corr_matrix = monitor.get_portfolio_correlation_matrix(current_positions)

    if corr_matrix is not None:
        logger.info("Correlation matrix (last 90 days):")
        logger.info("\n" + str(corr_matrix))
    else:
        logger.warning("Could not calculate correlation matrix (insufficient data)")

    logger.info("\n" + "=" * 60)
    logger.info("✅ ALL TESTS COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_correlation_monitor())
