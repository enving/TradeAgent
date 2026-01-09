"""Main trading loop - orchestrates daily trading execution.

Entry point for the trading system.
100% deterministic - no LLM involvement in trading decisions.

Usage:
    uv run python src/main.py
"""

import asyncio
from typing import Any, cast, Literal
from datetime import UTC, datetime
from decimal import Decimal

from .adapters.market_data_adapter import get_market_data_adapter
from .agents.orchestrator import TradingOrchestrator
from .agents.reflection_agent import ReflectionAgent
from .ml.adaptive_optimizer import get_optimizer
from .tools.economic_calendar import get_economic_calendar
from .core.ml_logger import get_ml_logger
from .core.performance_analyzer import analyze_daily_performance, generate_weekly_report
from .core.risk_manager import (
    calculate_position_size,
    filter_signals_by_risk,
    check_daily_loss_limit,
)
from .database.supabase_client import SupabaseClient
from .mcp_clients.alpaca_client import AlpacaMCPClient
from .models.trade import Trade
from .risk.position_sizer import initialize_position_sizer
from .strategies.defensive_core import calculate_rebalancing_orders, should_rebalance
from .strategies.momentum_trading import check_exit_conditions, scan_for_signals
from .strategies.news_strategy import NewsStrategy
from .strategies.news_driven import NewsSentimentStrategy
from .utils.config import config
from .utils.logger import logger


_trading_lock = asyncio.Lock()


async def daily_trading_loop(
    allow_premarket: bool = False, focused_ticker: str | None = None
) -> dict[str, Any]:
    """Main trading loop - executes all trading logic.

    Args:
        allow_premarket: Whether to allow trading during pre-market hours
        focused_ticker: If provided, only scan/trade this specific ticker (reactive mode)
    """
    async with _trading_lock:
        logger.info("=== Daily Trading Loop Started ===")
        if focused_ticker:
            logger.info(f"REACTIVE MODE: Focusing on {focused_ticker}")
        logger.info(f"Environment: {config.ENVIRONMENT}")

    logger.info(f"Time: {datetime.now(UTC).isoformat()}")

    execution_summary: dict[str, Any] = {
        "start_time": datetime.now(UTC),
        "rebalance_orders": 0,
        "momentum_signals": 0,
        "orders_executed": 0,
        "positions_closed": 0,
    }

    try:
        # Check market hours before trading
        adapter = await get_market_data_adapter()
        market_open = await adapter.is_market_open()

        if not market_open and not allow_premarket:
            clock = await adapter.get_market_clock()
            next_open = getattr(clock, "next_open", None) if clock else None
            logger.info(f"Market is currently closed. Next open: {next_open}")

            execution_summary.update(
                {
                    "status": "skipped",
                    "reason": "market_closed",
                    "next_open": str(next_open) if next_open else None,
                }
            )
            return execution_summary

        if market_open:
            logger.info("Market is OPEN - proceeding with trading")
        else:
            logger.info("Market is CLOSED - placing pre-market orders")

        # Economic Calendar Check
        calendar = get_economic_calendar()
        should_avoid, reason = calendar.should_avoid_trading()

        if should_avoid:
            logger.warning(f"⚠️ HIGH IMPACT EVENT DETECTED: {reason}")
            logger.warning("Reducing position sizes by 50% for safety.")
            execution_summary["risk_mode"] = "conservative"

        # Initialize clients
        alpaca = AlpacaMCPClient()
        supabase = await SupabaseClient.get_instance()
        ml_logger = get_ml_logger()
        news_strategy = NewsStrategy()

        # Initialize AI Orchestrator (if LLM features enabled)
        orchestrator = None
        if config.ENABLE_LLM_FEATURES:
            logger.info("Initializing AI Orchestrator...")
            orchestrator = TradingOrchestrator()

        # Initialize position sizer
        await initialize_position_sizer(supabase)

        # 1. Get portfolio state
        logger.info("Fetching portfolio state...")
        portfolio = await alpaca.get_account()
        positions = await alpaca.get_positions()

        logger.info(f"Portfolio Value: ${portfolio.portfolio_value}")
        logger.info(f"Positions: {len(positions)}")

        # 1a. CRITICAL RISK CHECK: Daily Circuit Breaker
        daily_pnl = portfolio.equity - portfolio.last_equity
        daily_pnl_pct = daily_pnl / portfolio.last_equity if portfolio.last_equity > 0 else 0

        logger.info(f"Daily PnL: ${daily_pnl:.2f} ({daily_pnl_pct:.2%})")

        if check_daily_loss_limit(daily_pnl, portfolio.portfolio_value):
            logger.error("🛑 CIRCUIT BREAKER TRIPPED. Halting trading for the day.")
            execution_summary.update(
                {
                    "status": "halted",
                    "reason": "circuit_breaker",
                    "daily_pnl": float(daily_pnl),
                    "daily_pnl_pct": float(daily_pnl_pct),
                }
            )
            return execution_summary

        execution_summary["portfolio_value"] = float(portfolio.portfolio_value)

        # 1b. AI Orchestrator: Analyze Market Regime
        if orchestrator:
            regime, confidence, reasoning = await orchestrator.analyze_market_regime(
                portfolio, positions
            )
            execution_summary["market_regime"] = regime
            execution_summary["regime_confidence"] = confidence

        # 2. Defensive Core: Check rebalancing
        today = datetime.now(UTC).date()
        if await should_rebalance(today, positions, portfolio):
            rebalance_signals = await calculate_rebalancing_orders(positions, portfolio, alpaca)
            execution_summary["rebalance_orders"] = len(rebalance_signals)

            for signal in rebalance_signals:
                try:
                    qty = calculate_position_size(signal, portfolio)
                    side = cast(Literal["buy", "sell"], signal.action.lower())
                    order_id = await alpaca.submit_market_order(
                        symbol=signal.ticker, qty=qty, side=side
                    )

                    action = cast(Literal["BUY", "SELL"], signal.action)
                    trade = Trade(
                        date=datetime.now(UTC),
                        ticker=signal.ticker,
                        action=action,
                        quantity=qty,
                        entry_price=signal.entry_price,
                        strategy="defensive",
                        alpaca_order_id=order_id,
                    )
                    await SupabaseClient.log_trade(trade)
                    execution_summary["orders_executed"] += 1
                except Exception as e:
                    logger.error(f"Failed to execute rebalance order for {signal.ticker}: {e}")

        # 3. Momentum Trading: Scan for signals
        if focused_ticker:
            # focused_ticker scan logic (simplified for reactive mode)
            momentum_signals = await scan_for_signals(alpaca, tickers=[focused_ticker])
        else:
            momentum_signals = await scan_for_signals(alpaca)

        execution_summary["momentum_signals"] = len(momentum_signals)

        # 3b. News Sentiment Strategy
        if config.ENABLE_LLM_FEATURES:
            news_sentiment_strategy = NewsSentimentStrategy()
            if focused_ticker:
                # Focused news scan
                news_signals = await news_sentiment_strategy.analyze_ticker_for_signal(
                    focused_ticker, alpaca
                )
                if news_signals:
                    # news_signals is a single Signal if successful, or None
                    if isinstance(news_signals, list):
                        momentum_signals.extend(news_signals)
                    else:
                        momentum_signals.append(news_signals)
            else:
                news_signals = await news_sentiment_strategy.scan_for_signals(alpaca)
                if news_signals:
                    momentum_signals.extend(news_signals)

            execution_summary["news_signals"] = (
                len(news_signals) if isinstance(news_signals, list) else (1 if news_signals else 0)
            )

        # 3c. AI Orchestrator: Prioritize Signals
        if orchestrator and momentum_signals:
            prioritized = await orchestrator.prioritize_signals(
                momentum_signals, portfolio, positions
            )
            momentum_signals = [signal for signal, score, reasoning in prioritized]

        # 4. Apply risk filters
        filtered_signals = await filter_signals_by_risk(momentum_signals, portfolio, positions)

        # 5. Execute momentum entries
        for signal in filtered_signals:
            try:
                qty = calculate_position_size(signal, portfolio)
                if execution_summary.get("risk_mode") == "conservative":
                    qty = Decimal(str(max(1, int(qty) // 2)))

                limit_price = signal.entry_price * Decimal("1.002")

                order_id = await alpaca.submit_limit_order(
                    symbol=signal.ticker,
                    qty=qty,
                    side="buy",
                    limit_price=limit_price,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                )

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
                execution_summary["orders_executed"] += 1
            except Exception as e:
                logger.error(f"Failed to execute momentum order for {signal.ticker}: {e}")

        # 6. Check exit conditions
        defensive_symbols = {"VTI", "VGK", "GLD"}
        for position in positions:
            if position.symbol in defensive_symbols:
                continue

            try:
                should_exit, reason = await check_exit_conditions(position, alpaca)
                if should_exit:
                    # Prepare trade data BEFORE closing (in case close fails)
                    exit_reason = cast(
                        Literal["stop_loss", "take_profit", "technical_exit", "rebalance"] | None,
                        reason,
                    )
                    exit_trade = Trade(
                        date=datetime.now(UTC),
                        ticker=position.symbol,
                        action="SELL",
                        quantity=position.quantity,
                        entry_price=position.avg_entry_price,
                        exit_price=position.current_price,
                        exit_reason=exit_reason,
                        pnl=position.unrealized_pnl,
                        pnl_pct=position.unrealized_pnl_pct,
                        strategy="momentum",
                    )

                    # Try to close position
                    try:
                        await alpaca.close_position(position.symbol)
                        logger.info(f"✅ Closed position: {position.symbol}")
                    except Exception as close_error:
                        # Position might already be closed - that's OK, log it anyway
                        logger.warning(
                            f"Could not close {position.symbol} (may already be closed): {close_error}"
                        )

                    # Always log the trade (even if close failed)
                    await SupabaseClient.log_trade(exit_trade)
                    execution_summary["positions_closed"] += 1

            except Exception as e:
                logger.error(f"Failed to check exit for {position.symbol}: {e}")

        # 7. Performance Analysis
        await analyze_daily_performance()

        # 8. Daily Reflection
        reflection_agent = ReflectionAgent()
        await reflection_agent.run_daily_reflection()

        # 9. Order Reconciliation (daily after market close)
        logger.info("🔄 Running order reconciliation...")
        try:
            from .utils.order_reconciliation import reconcile_orders
            reconcile_stats = await reconcile_orders(lookback_hours=48)
            if reconcile_stats["updated"] > 0 or reconcile_stats["missing"] > 0:
                logger.warning(
                    f"⚠️  Reconciliation fixed {reconcile_stats['updated']} trades with missing order IDs, "
                    f"logged {reconcile_stats['missing']} completely missing orders"
                )
            else:
                logger.info("✅ All orders in sync")
        except Exception as e:
            logger.error(f"Order reconciliation failed: {e}", exc_info=True)

        # 10. Weekly Parameter Optimization (Sunday)
        if today.weekday() == 6:  # Sunday
            logger.info("🔧 Running weekly parameter optimization...")
            try:
                optimizer = get_optimizer()
                optimized_params = await optimizer.optimize_momentum_parameters()
                logger.info(f"✅ Parameter optimization complete: {optimized_params}")
            except Exception as e:
                logger.error(f"Parameter optimization failed: {e}", exc_info=True)

            await generate_weekly_report()

        execution_summary["end_time"] = datetime.now(UTC)
        execution_summary["success"] = True
        return execution_summary

    except Exception as e:
        logger.error(f"Critical error in trading loop: {e}", exc_info=True)
        execution_summary["error"] = str(e)
        execution_summary["success"] = False
        return execution_summary


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
