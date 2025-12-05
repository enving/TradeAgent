"""Main trading loop - orchestrates daily trading execution.

Entry point for the trading system.
100% deterministic - no LLM involvement in trading decisions.

Usage:
    uv run python src/main.py
"""

import asyncio
from datetime import UTC, datetime

from .adapters.market_data_adapter import get_market_data_adapter
from .core.ml_logger import get_ml_logger
from .core.performance_analyzer import analyze_daily_performance, generate_weekly_report
from .core.risk_manager import (
    calculate_position_size,
    filter_signals_by_risk,
)
from .database.supabase_client import SupabaseClient
from .mcp_clients.alpaca_client import AlpacaMCPClient
from .models.trade import Trade
from .strategies.defensive_core import calculate_rebalancing_orders, should_rebalance
from .strategies.defensive_core import calculate_rebalancing_orders, should_rebalance
from .strategies.momentum_trading import check_exit_conditions, scan_for_signals
from .strategies.news_strategy import NewsStrategy
from .strategies.news_driven import NewsSentimentStrategy
from .utils.config import config
from .utils.logger import logger


async def daily_trading_loop(allow_premarket: bool = False) -> dict[str, any]:
    """Main trading loop - executes all trading logic.

    Workflow:
    1. Get portfolio state
    2. Check defensive core rebalancing
    3. Scan for momentum signals
    4. Apply risk filters
    5. Execute orders
    6. Check exit conditions
    7. Analyze performance

    Args:
        allow_premarket: If True, allows trading even when market is closed
                        (orders will execute at market open)

    Returns:
        Dictionary with execution summary

    Raises:
        Exception: If critical errors occur
    """
    logger.info("=== Daily Trading Loop Started ===")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    logger.info(f"Time: {datetime.now(UTC).isoformat()}")

    try:
        # Check market hours before trading (unless pre-market allowed)
        adapter = await get_market_data_adapter()
        market_open = await adapter.is_market_open()

        if not market_open and not allow_premarket:
            clock = await adapter.get_market_clock()
            if clock:
                logger.info("Market is currently closed")
                logger.info(f"Next open: {clock.next_open}")
            else:
                logger.info("Market is currently closed")
            return {
                "status": "skipped",
                "reason": "market_closed",
                "next_open": clock.next_open if clock else None,
            }

        if market_open:
            logger.info("Market is OPEN - proceeding with trading")
        else:
            logger.info("Market is CLOSED - placing pre-market orders")
            logger.info("Orders will execute when market opens at 9:30 AM ET")

        # Initialize clients
        alpaca = AlpacaMCPClient()
        supabase = await SupabaseClient.get_instance()
        ml_logger = get_ml_logger()
        news_strategy = NewsStrategy()

        # 1. Get portfolio state
        logger.info("Fetching portfolio state...")
        portfolio = await alpaca.get_account()
        positions = await alpaca.get_positions()

        logger.info(f"Portfolio Value: ${portfolio.portfolio_value}")
        logger.info(f"Cash: ${portfolio.cash}")
        logger.info(f"Positions: {len(positions)}")

        execution_summary = {
            "start_time": datetime.now(UTC),
            "portfolio_value": float(portfolio.portfolio_value),
            "rebalance_orders": 0,
            "momentum_signals": 0,
            "orders_executed": 0,
            "positions_closed": 0,
        }

        # 2. Defensive Core: Check rebalancing
        today = datetime.now(UTC).date()

        if await should_rebalance(today, positions, portfolio):
            logger.info("Rebalancing triggered")
            rebalance_signals = await calculate_rebalancing_orders(positions, portfolio, alpaca)
            execution_summary["rebalance_orders"] = len(rebalance_signals)

            for signal in rebalance_signals:
                try:
                    # Calculate position size
                    qty = calculate_position_size(signal, portfolio)

                    # Submit order
                    order_id = await alpaca.submit_market_order(
                        symbol=signal.ticker, qty=qty, side=signal.action.lower()
                    )

                    # Log trade
                    trade = Trade(
                        date=datetime.now(UTC),
                        ticker=signal.ticker,
                        action=signal.action,
                        quantity=qty,
                        entry_price=signal.entry_price,
                        strategy="defensive",
                        alpaca_order_id=order_id,
                    )

                    await SupabaseClient.log_trade(trade)

                    # Log ML features for rebalancing trades
                    await ml_logger.log_signal(
                        signal=signal,
                        portfolio_value=portfolio.portfolio_value,
                        position_count=len(positions),
                        cash_available=portfolio.cash,
                        trigger_reason="defensive_core_rebalancing",
                    )

                    execution_summary["orders_executed"] += 1

                    logger.info(f"Rebalance order: {signal.action} {qty} {signal.ticker}")

                except Exception as e:
                    logger.error(f"Failed to execute rebalance order for {signal.ticker}: {e}")
                    continue

        # 3. Momentum Trading: Scan for signals
        logger.info("Scanning for momentum signals...")
        momentum_signals = await scan_for_signals(alpaca)
        execution_summary["momentum_signals"] = len(momentum_signals)

        logger.info(f"Found {len(momentum_signals)} momentum signals")

        # REMOVED: News verification layer that was filtering momentum signals
        # Technical signals now execute directly without LLM confirmation
        # This reduces over-filtering and allows more valid trades through

        # 3b. News Sentiment Strategy (Optional - Prognosis-Driven)
        # Generates independent signals based on news sentiment
        # Does NOT filter momentum signals, only adds additional opportunities
        if config.ENABLE_LLM_FEATURES:
            logger.info("Running News Sentiment Strategy...")
            news_sentiment_strategy = NewsSentimentStrategy()
            news_signals = await news_sentiment_strategy.scan_for_signals(alpaca)
            
            if news_signals:
                logger.info(f"Found {len(news_signals)} news-driven signals")
                momentum_signals.extend(news_signals)
                execution_summary["news_signals"] = len(news_signals)
            else:
                logger.info("No news-driven signals found")

        # 4. Apply risk filters (includes correlation & sector checks)
        filtered_signals = await filter_signals_by_risk(momentum_signals, portfolio, positions)

        logger.info(f"Risk filter: {len(filtered_signals)} signals approved")

        # 5. Execute momentum entries
        for signal in filtered_signals:
            try:
                # Calculate position size
                qty = calculate_position_size(signal, portfolio)

                # Submit order with bracket (stop-loss + take-profit)
                order_id = await alpaca.submit_market_order(
                    symbol=signal.ticker,
                    qty=qty,
                    side="buy",
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                )

                # Log trade
                trade = Trade(
                    date=datetime.now(UTC),
                    ticker=signal.ticker,
                    action="BUY",
                    quantity=qty,
                    entry_price=signal.entry_price,
                    strategy="momentum",
                    rsi=signal.rsi,
                    macd_histogram=signal.macd_histogram,
                    volume_ratio=signal.volume_ratio,
                    alpaca_order_id=order_id,
                )

                await SupabaseClient.log_trade(trade)
                await SupabaseClient.log_signal(signal)

                # Log ML features for self-learning
                await ml_logger.log_signal(
                    signal=signal,
                    portfolio_value=portfolio.portfolio_value,
                    position_count=len(positions),
                    cash_available=portfolio.cash,
                    trigger_reason="momentum_entry_criteria_met",
                )

                execution_summary["orders_executed"] += 1

                logger.info(
                    f"Momentum entry: BUY {qty} {signal.ticker} @ ${signal.entry_price:.2f}"
                )

            except Exception as e:
                logger.error(f"Failed to execute momentum order for {signal.ticker}: {e}")
                continue

        # 6. Check exit conditions for momentum positions
        defensive_symbols = {"VTI", "VGK", "GLD"}

        for position in positions:
            # Skip defensive core positions
            if position.symbol in defensive_symbols:
                continue

            try:
                should_exit, reason = await check_exit_conditions(position, alpaca)

                if should_exit:
                    logger.info(f"Exiting {position.symbol}: {reason}")

                    # Close position
                    await alpaca.close_position(position.symbol)

                    # Log exit
                    exit_trade = Trade(
                        date=datetime.now(UTC),
                        ticker=position.symbol,
                        action="SELL",
                        quantity=position.quantity,
                        entry_price=position.avg_entry_price,
                        exit_price=position.current_price,
                        exit_reason=reason,
                        pnl=position.unrealized_pnl,
                        pnl_pct=position.unrealized_pnl_pct,
                        strategy="momentum",
                    )

                    await SupabaseClient.log_trade(exit_trade)
                    execution_summary["positions_closed"] += 1

                    logger.info(
                        f"Position closed: {position.symbol} "
                        f"(P&L: ${position.unrealized_pnl:.2f})"
                    )

            except Exception as e:
                logger.error(f"Failed to check exit for {position.symbol}: {e}")
                continue

        # 7. Daily Performance Analysis
        logger.info("Running daily performance analysis...")
        await analyze_daily_performance()

        # 8. Weekly Report (if Sunday)
        if today.weekday() == 6:  # Sunday
            logger.info("Generating weekly report...")
            await generate_weekly_report()

        execution_summary["end_time"] = datetime.now(UTC)
        execution_summary["success"] = True

        logger.info("=== Daily Trading Loop Completed ===")
        logger.info(f"Summary: {execution_summary}")

        return execution_summary

    except Exception as e:
        logger.error(f"Critical error in trading loop: {e}", exc_info=True)
        raise


async def main() -> None:
    """Main entry point for the trading system."""
    try:
        await daily_trading_loop()
        logger.info("Trading system executed successfully")

    except Exception as e:
        logger.error(f"Trading system failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
