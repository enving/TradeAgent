"""Performance analysis and automatic parameter optimization.

100% deterministic - rule-based parameter adjustment based on performance metrics.
No machine learning - just clear if/then rules for strategy improvement.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from ..database.supabase_client import SupabaseClient
from ..models.performance import DailyPerformance, ParameterChange, StrategyMetrics, WeeklyReport
from ..strategies.momentum_trading import get_current_parameters, update_strategy_parameters
from ..utils.logger import logger


async def analyze_daily_performance() -> None:
    """Analyze today's trading performance and store metrics.

    Runs at end of day (after market close).
    Pure deterministic analysis - calculates metrics and stores to database.
    """
    logger.info("=== Daily Performance Analysis Started ===")

    supabase = await SupabaseClient.get_instance()
    today = datetime.now().date()

    # Fetch today's trades
    try:
        response = await supabase.table("trades").select("*").eq("date", today).execute()
        trades = response.data
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")
        return

    if not trades:
        logger.info("No trades today - skipping analysis")
        return

    # Calculate daily metrics (filter out None values)
    total_trades = len(trades)
    winning_trades = [t for t in trades if (t.get("pnl") or 0) > 0]
    losing_trades = [t for t in trades if (t.get("pnl") or 0) < 0]

    win_rate = Decimal(len(winning_trades) / total_trades if total_trades > 0 else 0)

    total_pnl = Decimal(sum(t.get("pnl") or 0 for t in trades))
    avg_win = Decimal(
        sum(t.get("pnl") or 0 for t in winning_trades) / len(winning_trades) if winning_trades else 0
    )
    avg_loss = Decimal(
        sum(t.get("pnl") or 0 for t in losing_trades) / len(losing_trades) if losing_trades else 0
    )

    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else Decimal(0)

    # --- Advanced Analytics ---
    sharpe_ratio = None
    max_drawdown = None

    try:
        # Fetch last 30 days of performance for Sharpe/Drawdown
        history_response = await supabase.table("daily_performance").select("*").order("date", desc=True).limit(30).execute()
        history = history_response.data
        
        if history:
            # Calculate Sharpe Ratio (assuming risk-free rate = 0 for simplicity)
            # We need daily returns, but we only have PnL. We'll use PnL as a proxy for return magnitude.
            pnls = [float(d["daily_pnl"]) for d in history]
            pnls.append(float(total_pnl)) # Add today
            
            import numpy as np
            if len(pnls) > 5:
                mean_pnl = np.mean(pnls)
                std_pnl = np.std(pnls)
                if std_pnl != 0:
                    sharpe_ratio = Decimal(str(mean_pnl / std_pnl * np.sqrt(252))) # Annualized
            
            # Calculate Max Drawdown
            # We need cumulative PnL to simulate equity curve
            cumulative = 0
            peak = -float('inf')
            max_dd = 0
            
            # Reconstruct equity curve from history (reverse order: oldest to newest)
            for day in reversed(history):
                cumulative += float(day["daily_pnl"])
                peak = max(peak, cumulative)
                dd = (peak - cumulative) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            
            # Add today
            cumulative += float(total_pnl)
            peak = max(peak, cumulative)
            dd = (peak - cumulative) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            
            max_drawdown = Decimal(str(max_dd))

    except Exception as e:
        logger.warning(f"Failed to calculate advanced metrics: {e}")

    logger.info(
        f"Daily Stats: {total_trades} trades, "
        f"Win Rate: {win_rate:.2%}, "
        f"P&L: ${total_pnl:.2f}, "
        f"Sharpe: {sharpe_ratio}, DD: {max_drawdown}"
    )

    # Store daily performance
    daily_perf = DailyPerformance(
        date=today,
        total_trades=total_trades,
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=win_rate,
        daily_pnl=total_pnl,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown
    )

    await SupabaseClient.log_daily_performance(daily_perf)

    # Per-strategy breakdown
    for strategy in ["defensive", "momentum"]:
        strategy_trades = [t for t in trades if t["strategy"] == strategy]
        if strategy_trades:
            strategy_pnl = Decimal(sum(t.get("pnl") or 0 for t in strategy_trades))
            strategy_winners = [t for t in strategy_trades if (t.get("pnl") or 0) > 0]
            strategy_win_rate = Decimal(
                len(strategy_winners) / len(strategy_trades) if strategy_trades else 0
            )

            metrics = StrategyMetrics(
                strategy=strategy,
                date=today,
                total_trades=len(strategy_trades),
                win_rate=strategy_win_rate,
                total_pnl=strategy_pnl,
            )

            await SupabaseClient.log_strategy_metrics(metrics)

            logger.info(
                f"{strategy.upper()} Strategy: {len(strategy_trades)} trades, "
                f"Win Rate: {strategy_win_rate:.2%}, P&L: ${strategy_pnl:.2f}"
            )

    # Check if parameter adjustment needed
    await adjust_parameters_if_needed()

    logger.info("=== Daily Performance Analysis Completed ===")


async def adjust_parameters_if_needed() -> None:
    """Adjust strategy parameters based on last 5 days of performance.

    Deterministic rules:
    1. Win rate < 55% → Tighten entry criteria
    2. Risk/Reward > 0.5 → Widen stop-loss
    3. Win rate > 65% → Loosen entry criteria
    """
    supabase = await SupabaseClient.get_instance()

    # Get last 5 days of momentum strategy performance
    try:
        recent_perf = await supabase.get_strategy_performance("momentum", days=5)
    except Exception as e:
        logger.error(f"Failed to fetch strategy performance: {e}")
        return

    if len(recent_perf) < 5:
        logger.info(f"Not enough data for parameter adjustment (have {len(recent_perf)}, need 5)")
        return

    # Calculate 5-day average win rate
    avg_win_rate = sum(p["win_rate"] for p in recent_perf) / len(recent_perf)

    current_params = get_current_parameters()

    # Rule 1: Low win rate → Tighten entry
    if avg_win_rate < 0.55:
        logger.warning(f"Low win rate: {avg_win_rate:.2%}. Tightening entry criteria.")

        new_params = {
            "rsi_min": 55,  # More conservative
            "rsi_max": 65,
            "min_volume_ratio": 1.2,
        }

        update_strategy_parameters(new_params)

        change = ParameterChange(
            date=datetime.now().date(),
            reason=f"Low win rate: {avg_win_rate:.2%}",
            old_params=current_params,
            new_params=get_current_parameters(),
        )
        await SupabaseClient.log_parameter_change(change)

    # Rule 2: Risk/Reward worsening → Widen stop-loss
    # (Simplified - would need more data for full implementation)

    # Rule 3: High win rate → Loosen entry
    elif avg_win_rate > 0.65:
        logger.info(f"High win rate: {avg_win_rate:.2%}. Loosening entry criteria.")

        new_params = {
            "rsi_min": 45,
            "rsi_max": 75,
        }

        update_strategy_parameters(new_params)

        change = ParameterChange(
            date=datetime.now().date(),
            reason=f"High win rate: {avg_win_rate:.2%}",
            old_params=current_params,
            new_params=get_current_parameters(),
        )
        await SupabaseClient.log_parameter_change(change)


async def generate_weekly_report() -> None:
    """Generate weekly performance report.

    Runs every Sunday.
    Identifies best/worst performers and calculates weekly metrics.
    """
    logger.info("===== WEEKLY REPORT =====")

    supabase = await SupabaseClient.get_instance()
    week_ago = datetime.now().date() - timedelta(days=7)

    # Fetch week's trades
    try:
        response = (
            await supabase.table("trades").select("*").gte("date", week_ago.isoformat()).execute()
        )
        weekly_trades = response.data
    except Exception as e:
        logger.error(f"Failed to fetch weekly trades: {e}")
        return

    if not weekly_trades:
        logger.info("No trades this week")
        return

    # Calculate metrics (filter out None values for P&L)
    total_pnl = Decimal(sum(t.get("pnl") or 0 for t in weekly_trades))
    total_trades = len(weekly_trades)
    winning_trades = [t for t in weekly_trades if (t.get("pnl") or 0) > 0]
    win_rate = Decimal(len(winning_trades) / total_trades if total_trades > 0 else 0)

    # Best and worst performers (only include trades with P&L)
    trades_with_pnl = [t for t in weekly_trades if t.get("pnl") is not None]
    if trades_with_pnl:
        sorted_trades = sorted(trades_with_pnl, key=lambda t: t.get("pnl_pct") or 0, reverse=True)
        best_performers = [t["ticker"] for t in sorted_trades[:min(3, len(sorted_trades))]]
        worst_performers = [t["ticker"] for t in sorted_trades[-min(3, len(sorted_trades)):]]
    else:
        best_performers = []
        worst_performers = []

    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Win Rate: {win_rate:.2%}")
    logger.info(f"Total P&L: ${total_pnl:.2f}")
    logger.info(f"Best Performers: {best_performers}")
    logger.info(f"Worst Performers: {worst_performers}")
    logger.info("========================")

    # Store report
    report = WeeklyReport(
        week_ending=datetime.now().date(),
        total_trades=total_trades,
        win_rate=win_rate,
        total_pnl=total_pnl,
        best_performers=best_performers,
        worst_performers=worst_performers,
    )

    await SupabaseClient.log_weekly_report(report)

    logger.info("Weekly report saved to database")
