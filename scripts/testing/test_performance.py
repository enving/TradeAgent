"""Test performance analytics with current portfolio data."""

import asyncio
from datetime import datetime, timedelta
from src.database.supabase_client import SupabaseClient
from src.core.performance_analyzer import analyze_daily_performance, generate_weekly_report
from src.utils.logger import logger


async def test_performance_analytics():
    """Test performance analytics system."""
    logger.info("=== Testing Performance Analytics ===")

    # Initialize Supabase
    supabase = await SupabaseClient.get_instance()

    # 1. Check recent trades
    logger.info("\n1. Checking recent trades...")
    try:
        response = await supabase.table("trades").select("*").order("date", desc=True).limit(10).execute()
        trades = response.data

        if trades:
            logger.info(f"Found {len(trades)} recent trades:")
            for trade in trades:
                logger.info(
                    f"  - {trade.get('date')}: {trade.get('action')} {trade.get('quantity')} "
                    f"{trade.get('ticker')} @ ${trade.get('entry_price')} "
                    f"(Strategy: {trade.get('strategy')})"
                )
        else:
            logger.warning("No trades found in database")
    except Exception as e:
        logger.error(f"Failed to fetch trades: {e}")

    # 2. Run daily performance analysis
    logger.info("\n2. Running daily performance analysis...")
    try:
        await analyze_daily_performance()
        logger.info("OK Daily performance analysis completed")
    except Exception as e:
        logger.error(f"Failed to run daily analysis: {e}")

    # 3. Check daily_performance table
    logger.info("\n3. Checking daily performance metrics...")
    try:
        response = await supabase.table("daily_performance").select("*").order("date", desc=True).limit(5).execute()
        metrics = response.data

        if metrics:
            logger.info(f"Found {len(metrics)} daily performance records:")
            for metric in metrics:
                logger.info(
                    f"  - {metric.get('date')}: {metric.get('total_trades')} trades, "
                    f"Win Rate: {float(metric.get('win_rate', 0)):.2%}, "
                    f"P&L: ${float(metric.get('daily_pnl', 0)):.2f}"
                )
        else:
            logger.info("No daily performance metrics found (expected if no trades with P&L yet)")
    except Exception as e:
        logger.error(f"Failed to fetch daily performance: {e}")

    # 4. Check strategy_metrics table
    logger.info("\n4. Checking strategy metrics...")
    try:
        response = await supabase.table("strategy_metrics").select("*").order("date", desc=True).limit(5).execute()
        strategy_metrics = response.data

        if strategy_metrics:
            logger.info(f"Found {len(strategy_metrics)} strategy performance records:")
            for sm in strategy_metrics:
                logger.info(
                    f"  - {sm.get('date')} ({sm.get('strategy')}): "
                    f"{sm.get('total_trades')} trades, "
                    f"Win Rate: {float(sm.get('win_rate', 0)):.2%}, "
                    f"P&L: ${float(sm.get('total_pnl', 0)):.2f}"
                )
        else:
            logger.info("No strategy metrics found (expected if no trades with P&L yet)")
    except Exception as e:
        logger.error(f"Failed to fetch strategy metrics: {e}")

    # 5. Run weekly report
    logger.info("\n5. Running weekly report...")
    try:
        await generate_weekly_report()
        logger.info("OK Weekly report completed")
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")

    # 6. Check signals table
    logger.info("\n6. Checking logged signals...")
    try:
        response = await supabase.table("signals").select("*").order("date", desc=True).limit(5).execute()
        signals = response.data

        if signals:
            logger.info(f"Found {len(signals)} logged signals:")
            for signal in signals:
                logger.info(
                    f"  - {signal.get('date')}: {signal.get('action')} {signal.get('ticker')} "
                    f"(Confidence: {float(signal.get('confidence', 0)):.2f}, "
                    f"Strategy: {signal.get('strategy')})"
                )
        else:
            logger.info("No signals found in database")
    except Exception as e:
        logger.error(f"Failed to fetch signals: {e}")

    logger.info("\n=== Performance Analytics Test Completed ===")


if __name__ == "__main__":
    asyncio.run(test_performance_analytics())
