"""Test Market Data Adapter - Phase 1 & 2 Features."""

import asyncio
from datetime import date, timedelta

from src.adapters.market_data_adapter import get_market_data_adapter
from src.utils.logger import logger


async def test_phase_1():
    """Test Phase 1: Market Clock & Calendar."""
    logger.info("=" * 70)
    logger.info("PHASE 1 TEST: Market Clock & Calendar")
    logger.info("=" * 70)
    logger.info("")

    adapter = await get_market_data_adapter()

    # Test 1: Market Clock
    logger.info("1. Testing Market Clock...")
    clock = await adapter.get_market_clock()

    if clock:
        logger.info(f"   Timestamp: {clock.timestamp}")
        logger.info(f"   Market Status: {'OPEN' if clock.is_open else 'CLOSED'}")
        logger.info(f"   Next Open: {clock.next_open}")
        logger.info(f"   Next Close: {clock.next_close}")
    else:
        logger.error("   Failed to get market clock")

    logger.info("")

    # Test 2: Is Market Open
    logger.info("2. Testing is_market_open()...")
    is_open = await adapter.is_market_open()
    logger.info(f"   Market is currently: {'OPEN' if is_open else 'CLOSED'}")
    logger.info("")

    # Test 3: Market Calendar (This Month)
    logger.info("3. Testing Market Calendar (This Month)...")
    today = date.today()
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    calendar = await adapter.get_market_calendar(start_date=month_start, end_date=month_end)

    if calendar:
        trading_days = calendar.get_trading_days()
        logger.info(f"   Month: {month_start.strftime('%B %Y')}")
        logger.info(f"   Trading Days: {len(trading_days)}")
        logger.info(f"   First Trading Day: {trading_days[0] if trading_days else 'N/A'}")
        logger.info(f"   Last Trading Day: {trading_days[-1] if trading_days else 'N/A'}")
    else:
        logger.error("   Failed to get market calendar")

    logger.info("")

    # Test 4: First Trading Day of Month
    logger.info("4. Testing is_first_trading_day_of_month()...")
    is_first_day = await adapter.is_first_trading_day_of_month()
    logger.info(f"   Today ({today}) is first trading day: {is_first_day}")
    logger.info("")

    logger.info("=" * 70)
    logger.info("PHASE 1 COMPLETED")
    logger.info("=" * 70)
    logger.info("")


async def test_phase_2():
    """Test Phase 2: Portfolio History & Analytics."""
    logger.info("=" * 70)
    logger.info("PHASE 2 TEST: Portfolio History & Analytics")
    logger.info("=" * 70)
    logger.info("")

    adapter = await get_market_data_adapter()

    # Test 1: Portfolio History (1 Month)
    logger.info("1. Testing Portfolio History (1M, 1D)...")
    history = await adapter.get_portfolio_history(period="1M", timeframe="1D")

    if history:
        logger.info(f"   Data Points: {len(history.timestamps)}")
        logger.info(f"   Base Value: ${history.base_value:,.2f}")
        logger.info(f"   Timeframe: {history.timeframe}")

        if history.equity:
            logger.info(f"   Start Equity: ${history.equity[0]:,.2f}")
            logger.info(f"   End Equity: ${history.equity[-1]:,.2f}")

            # Calculate total return (handle zero equity case)
            if history.equity[0] > 0:
                total_return = (
                    (history.equity[-1] - history.equity[0]) / history.equity[0] * 100
                )
                logger.info(f"   Total Return: {total_return:+.2f}%")
            else:
                logger.info("   Total Return: N/A (starting equity is zero)")

        logger.info("")

        # Test 2: Sharpe Ratio
        logger.info("2. Calculating Sharpe Ratio...")
        try:
            sharpe_ratio = history.calculate_sharpe_ratio()
            logger.info(f"   Sharpe Ratio: {sharpe_ratio:.3f}")
        except Exception as e:
            logger.error(f"   Failed to calculate Sharpe Ratio: {e}")

        logger.info("")

        # Test 3: Max Drawdown
        logger.info("3. Calculating Max Drawdown...")
        try:
            max_dd, peak_date, trough_date = history.calculate_max_drawdown()
            logger.info(f"   Max Drawdown: {float(max_dd)*100:.2f}%")
            logger.info(f"   Peak Date: {peak_date}")
            logger.info(f"   Trough Date: {trough_date}")
        except Exception as e:
            logger.error(f"   Failed to calculate Max Drawdown: {e}")

        logger.info("")

        # Test 4: Calmar Ratio
        logger.info("4. Calculating Calmar Ratio...")
        try:
            calmar_ratio = history.calculate_calmar_ratio()
            logger.info(f"   Calmar Ratio: {calmar_ratio:.3f}")
        except Exception as e:
            logger.error(f"   Failed to calculate Calmar Ratio: {e}")

    else:
        logger.warning("   Portfolio history not available (requires live data)")

    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 2 COMPLETED")
    logger.info("=" * 70)


async def test_phase_3():
    """Test Phase 3: Orders History & Slippage Analysis."""
    logger.info("=" * 70)
    logger.info("PHASE 3 TEST: Orders History & Slippage Analysis")
    logger.info("=" * 70)
    logger.info("")

    adapter = await get_market_data_adapter()

    # Test 1: Get all orders
    logger.info("1. Testing get_orders_history (all orders)...")
    all_orders = await adapter.get_orders_history(status="all", limit=10)

    if all_orders:
        logger.info(f"   Total Orders: {len(all_orders)}")

        # Show first order details
        if len(all_orders) > 0:
            first_order = all_orders[0]
            logger.info(f"   First Order:")
            logger.info(f"      Symbol: {first_order.symbol}")
            logger.info(f"      Side: {first_order.side}")
            logger.info(f"      Status: {first_order.status}")
            logger.info(f"      Quantity: {first_order.quantity}")
            logger.info(f"      Filled Qty: {first_order.filled_quantity}")
            logger.info(f"      Order Type: {first_order.order_type}")

            if first_order.filled_avg_price:
                logger.info(f"      Filled Price: ${first_order.filled_avg_price:.2f}")

                # Test slippage calculation (if we have a limit price)
                if first_order.limit_price:
                    slippage = first_order.calculate_slippage(first_order.limit_price)
                    slippage_pct = first_order.calculate_slippage_pct(first_order.limit_price)

                    logger.info(f"      Limit Price: ${first_order.limit_price:.2f}")
                    logger.info(f"      Slippage: ${slippage:.4f}")
                    logger.info(f"      Slippage %: {slippage_pct:.4f}%")

    else:
        logger.info("   No orders found (new account or no trading history)")

    logger.info("")

    # Test 2: Get filled orders only
    logger.info("2. Testing get_orders_history (filled orders only)...")
    filled_orders = await adapter.get_orders_history(status="closed", limit=10)

    if filled_orders:
        logger.info(f"   Filled Orders: {len(filled_orders)}")

        # Calculate aggregate statistics
        total_slippage = 0
        slippage_count = 0

        for order in filled_orders:
            if order.filled_avg_price and order.limit_price:
                slippage = order.calculate_slippage(order.limit_price)
                if slippage is not None:
                    total_slippage += float(slippage)
                    slippage_count += 1

        if slippage_count > 0:
            avg_slippage = total_slippage / slippage_count
            logger.info(f"   Average Slippage: ${avg_slippage:.4f}")
        else:
            logger.info("   No slippage data available (no limit orders)")

        # Calculate fill rate
        total_qty = sum(float(o.quantity) for o in filled_orders)
        filled_qty = sum(float(o.filled_quantity) for o in filled_orders)

        if total_qty > 0:
            fill_rate = (filled_qty / total_qty) * 100
            logger.info(f"   Fill Rate: {fill_rate:.2f}%")

    else:
        logger.info("   No filled orders found")

    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 3 COMPLETED")
    logger.info("=" * 70)


async def main():
    """Run all tests."""
    logger.info("\n\n")
    logger.info("#" * 70)
    logger.info("# MARKET DATA ADAPTER TEST - PHASE 1, 2 & 3")
    logger.info("#" * 70)
    logger.info("\n")

    try:
        # Phase 1: Market Clock & Calendar
        await test_phase_1()

        await asyncio.sleep(1)

        # Phase 2: Portfolio History & Analytics
        await test_phase_2()

        await asyncio.sleep(1)

        # Phase 3: Orders History & Slippage Analysis
        await test_phase_3()

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

    logger.info("\n")
    logger.info("#" * 70)
    logger.info("# ALL TESTS COMPLETED")
    logger.info("#" * 70)


if __name__ == "__main__":
    asyncio.run(main())
