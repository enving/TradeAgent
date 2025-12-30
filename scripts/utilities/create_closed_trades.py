"""Create some simulated closed trades with P&L for testing performance analytics."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.models.trade import Trade
from src.utils.logger import logger


async def create_closed_trades():
    """Create simulated closed trades with P&L."""
    logger.info("=== Creating Simulated Closed Trades ===")

    yesterday = datetime.now(UTC) - timedelta(days=1)
    two_days_ago = datetime.now(UTC) - timedelta(days=2)

    # Winning trade: TSLA momentum
    winning_trade = Trade(
        date=two_days_ago,
        ticker="TSLA",
        action="SELL",
        quantity=Decimal("10"),
        entry_price=Decimal("240.00"),
        exit_price=Decimal("276.00"),  # +15% profit
        exit_reason="take_profit",
        pnl=Decimal("360.00"),  # 10 * (276 - 240)
        pnl_pct=Decimal("0.15"),  # +15%
        strategy="momentum",
        rsi=Decimal("68.0"),
        macd_histogram=Decimal("2.5"),
        volume_ratio=Decimal("1.6"),
        alpaca_order_id="sim_tsla_win",
    )

    # Losing trade: NFLX momentum
    losing_trade = Trade(
        date=yesterday,
        ticker="NFLX",
        action="SELL",
        quantity=Decimal("5"),
        entry_price=Decimal("720.00"),
        exit_price=Decimal("684.00"),  # -5% loss
        exit_reason="stop_loss",
        pnl=Decimal("-180.00"),  # 5 * (684 - 720)
        pnl_pct=Decimal("-0.05"),  # -5%
        strategy="momentum",
        rsi=Decimal("45.0"),
        macd_histogram=Decimal("-0.8"),
        volume_ratio=Decimal("1.2"),
        alpaca_order_id="sim_nflx_loss",
    )

    # Another winning trade: NVDA momentum
    winning_trade_2 = Trade(
        date=yesterday,
        ticker="NVDA",
        action="SELL",
        quantity=Decimal("8"),
        entry_price=Decimal("130.00"),
        exit_price=Decimal("143.00"),  # +10% profit
        exit_reason="take_profit",
        pnl=Decimal("104.00"),  # 8 * (143 - 130)
        pnl_pct=Decimal("0.10"),  # +10%
        strategy="momentum",
        rsi=Decimal("72.0"),
        macd_histogram=Decimal("3.1"),
        volume_ratio=Decimal("1.9"),
        alpaca_order_id="sim_nvda_win",
    )

    trades = [winning_trade, losing_trade, winning_trade_2]

    # Log all trades
    for trade in trades:
        try:
            await SupabaseClient.log_trade(trade)
            pnl_str = f"+${trade.pnl}" if trade.pnl > 0 else f"${trade.pnl}"
            logger.info(
                f"Logged: {trade.action} {trade.quantity} {trade.ticker} - "
                f"P&L: {pnl_str} ({float(trade.pnl_pct)*100:+.1f}%)"
            )
        except Exception as e:
            logger.error(f"Failed to log trade {trade.ticker}: {e}")

    logger.info(f"\n{len(trades)} closed trades logged!")

    # Calculate summary
    total_pnl = sum(t.pnl for t in trades)
    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl < 0]
    win_rate = len(winning) / len(trades) * 100

    logger.info("\nSummary:")
    logger.info(f"  Total P&L: ${total_pnl:.2f}")
    logger.info(f"  Winning Trades: {len(winning)}")
    logger.info(f"  Losing Trades: {len(losing)}")
    logger.info(f"  Win Rate: {win_rate:.1f}%")

    logger.info("\n=== Closed Trades Creation Completed ===")


if __name__ == "__main__":
    asyncio.run(create_closed_trades())
