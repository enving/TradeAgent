"""Test and compare system performance WITH and WITHOUT LLM features.

This script runs tests in two modes:
1. WITHOUT LLM (ENABLE_LLM_FEATURES=false) - Baseline
2. WITH LLM (ENABLE_LLM_FEATURES=true) - LLM-enhanced

Tests the Trade Explanation Generator using real trades from database.
"""

import asyncio
import os
import time
from decimal import Decimal

from src.database.supabase_client import SupabaseClient
from src.llm.trade_explainer import get_trade_explainer
from src.models.portfolio import Portfolio
from src.models.trade import Trade
from src.utils.config import config
from src.utils.logger import logger


async def test_without_llm():
    """Test baseline system WITHOUT LLM features."""
    logger.info("=" * 70)
    logger.info("TEST 1: BASELINE - WITHOUT LLM")
    logger.info("=" * 70)
    logger.info(f"ENABLE_LLM_FEATURES: {config.ENABLE_LLM_FEATURES}")
    logger.info("")

    # Fetch recent trades from database
    supabase = await SupabaseClient.get_instance()
    response = await supabase.table("trades").select("*").order("date", desc=True).limit(5).execute()
    trades_data = response.data

    if not trades_data:
        logger.warning("No trades found in database")
        return

    logger.info(f"Found {len(trades_data)} trades to process")
    logger.info("")

    # Create mock portfolio
    portfolio = Portfolio(
        cash=Decimal("50000"),
        portfolio_value=Decimal("100000"),
        buying_power=Decimal("150000"),
        equity=Decimal("100000"),
    )

    # Get explainer (will return fallback explanations)
    explainer = await get_trade_explainer()

    start_time = time.time()
    explanations = []

    for trade_data in trades_data:
        # Convert to Trade model
        trade = Trade(
            date=trade_data["date"],
            ticker=trade_data["ticker"],
            action=trade_data["action"],
            quantity=Decimal(str(trade_data["quantity"])),
            entry_price=Decimal(str(trade_data["entry_price"])),
            strategy=trade_data["strategy"],
            rsi=Decimal(str(trade_data["rsi"])) if trade_data.get("rsi") else None,
            macd_histogram=Decimal(str(trade_data["macd_histogram"]))
            if trade_data.get("macd_histogram")
            else None,
            volume_ratio=Decimal(str(trade_data["volume_ratio"]))
            if trade_data.get("volume_ratio")
            else None,
        )

        # Get explanation (will be fallback since LLM disabled)
        explanation = await explainer.explain_trade(trade, portfolio)

        logger.info(f"Trade: {trade.action} {trade.quantity} {trade.ticker} @ ${trade.entry_price}")
        logger.info(f"Strategy: {trade.strategy}")
        logger.info(f"Explanation: {explanation}")
        logger.info("")

        explanations.append(explanation)

    elapsed_time = time.time() - start_time

    logger.info("=" * 70)
    logger.info("BASELINE RESULTS:")
    logger.info(f"Trades processed: {len(trades_data)}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    logger.info(f"Avg time per trade: {elapsed_time / len(trades_data):.3f} seconds")
    logger.info(f"LLM API calls: 0 (disabled)")
    logger.info(f"Cost: $0.00")
    logger.info("=" * 70)
    logger.info("")

    return {
        "mode": "WITHOUT_LLM",
        "trades_processed": len(trades_data),
        "total_time": elapsed_time,
        "avg_time": elapsed_time / len(trades_data),
        "llm_calls": 0,
        "cost": 0.00,
        "explanations": explanations,
    }


async def test_with_llm():
    """Test system WITH LLM features enabled."""
    logger.info("=" * 70)
    logger.info("TEST 2: LLM-ENHANCED - WITH OPENROUTER")
    logger.info("=" * 70)

    # Temporarily enable LLM features
    original_value = config.ENABLE_LLM_FEATURES
    config.ENABLE_LLM_FEATURES = True

    logger.info(f"ENABLE_LLM_FEATURES: {config.ENABLE_LLM_FEATURES}")
    logger.info(f"OpenRouter Model: {config.OPENROUTER_MODEL}")
    logger.info(f"OpenRouter Base URL: {config.OPENROUTER_BASE_URL}")
    logger.info("")

    # Fetch recent trades from database
    supabase = await SupabaseClient.get_instance()
    response = await supabase.table("trades").select("*").order("date", desc=True).limit(5).execute()
    trades_data = response.data

    if not trades_data:
        logger.warning("No trades found in database")
        config.ENABLE_LLM_FEATURES = original_value
        return

    logger.info(f"Found {len(trades_data)} trades to process")
    logger.info("")

    # Create mock portfolio
    portfolio = Portfolio(
        cash=Decimal("50000"),
        portfolio_value=Decimal("100000"),
        buying_power=Decimal("150000"),
        equity=Decimal("100000"),
    )

    # Get explainer (will use OpenRouter)
    explainer = await get_trade_explainer()

    start_time = time.time()
    explanations = []
    llm_calls = 0

    for trade_data in trades_data:
        # Convert to Trade model
        trade = Trade(
            date=trade_data["date"],
            ticker=trade_data["ticker"],
            action=trade_data["action"],
            quantity=Decimal(str(trade_data["quantity"])),
            entry_price=Decimal(str(trade_data["entry_price"])),
            strategy=trade_data["strategy"],
            rsi=Decimal(str(trade_data["rsi"])) if trade_data.get("rsi") else None,
            macd_histogram=Decimal(str(trade_data["macd_histogram"]))
            if trade_data.get("macd_histogram")
            else None,
            volume_ratio=Decimal(str(trade_data["volume_ratio"]))
            if trade_data.get("volume_ratio")
            else None,
            stop_loss=Decimal(str(trade_data["stop_loss"])) if trade_data.get("stop_loss") else None,
            take_profit=Decimal(str(trade_data["take_profit"]))
            if trade_data.get("take_profit")
            else None,
        )

        logger.info(f"Processing: {trade.action} {trade.quantity} {trade.ticker}...")

        # Get LLM explanation
        explanation = await explainer.explain_trade(trade, portfolio)
        llm_calls += 1

        logger.info(f"Trade: {trade.action} {trade.quantity} {trade.ticker} @ ${trade.entry_price}")
        logger.info(f"Strategy: {trade.strategy}")
        logger.info(f"LLM Explanation: {explanation}")
        logger.info("")

        explanations.append(explanation)

    elapsed_time = time.time() - start_time

    # Estimate cost (approximate, based on ~500 input + 200 output tokens per call)
    # Claude 3.5 Sonnet via OpenRouter: $3/1M input, $15/1M output
    estimated_cost = llm_calls * ((500 * 3 / 1_000_000) + (200 * 15 / 1_000_000))

    logger.info("=" * 70)
    logger.info("LLM-ENHANCED RESULTS:")
    logger.info(f"Trades processed: {len(trades_data)}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")
    logger.info(f"Avg time per trade: {elapsed_time / len(trades_data):.3f} seconds")
    logger.info(f"LLM API calls: {llm_calls}")
    logger.info(f"Estimated cost: ${estimated_cost:.4f}")
    logger.info("=" * 70)
    logger.info("")

    # Restore original config
    config.ENABLE_LLM_FEATURES = original_value

    return {
        "mode": "WITH_LLM",
        "trades_processed": len(trades_data),
        "total_time": elapsed_time,
        "avg_time": elapsed_time / len(trades_data),
        "llm_calls": llm_calls,
        "cost": estimated_cost,
        "explanations": explanations,
    }


async def compare_results(baseline_results, llm_results):
    """Compare baseline vs LLM-enhanced results."""
    logger.info("=" * 70)
    logger.info("COMPARISON SUMMARY")
    logger.info("=" * 70)
    logger.info("")

    logger.info("MODE COMPARISON:")
    logger.info(f"  Baseline (No LLM):")
    logger.info(f"    - Avg time: {baseline_results['avg_time']:.3f}s")
    logger.info(f"    - API calls: {baseline_results['llm_calls']}")
    logger.info(f"    - Cost: ${baseline_results['cost']:.4f}")
    logger.info("")
    logger.info(f"  LLM-Enhanced:")
    logger.info(f"    - Avg time: {llm_results['avg_time']:.3f}s")
    logger.info(f"    - API calls: {llm_results['llm_calls']}")
    logger.info(f"    - Cost: ${llm_results['cost']:.4f}")
    logger.info("")

    # Calculate differences
    time_overhead = llm_results["avg_time"] - baseline_results["avg_time"]
    time_overhead_pct = (time_overhead / baseline_results["avg_time"]) * 100

    logger.info("OVERHEAD:")
    logger.info(f"  Time overhead: +{time_overhead:.3f}s per trade ({time_overhead_pct:.1f}%)")
    logger.info(f"  Cost per trade: ${llm_results['cost'] / llm_results['trades_processed']:.4f}")
    logger.info("")

    logger.info("EXPLANATION QUALITY:")
    logger.info("  Baseline: Simple rule-based explanations")
    logger.info("  LLM: Natural language, context-aware explanations")
    logger.info("")

    logger.info("RECOMMENDATION:")
    if time_overhead < 2.0 and llm_results["cost"] < 0.01:
        logger.info("  LLM overhead is minimal - RECOMMEND ENABLING for better UX")
    else:
        logger.info("  LLM overhead is significant - evaluate if worth the cost")

    logger.info("=" * 70)


async def main():
    """Run comparison tests."""
    logger.info("\n\n")
    logger.info("#" * 70)
    logger.info("# LLM COMPARISON TEST")
    logger.info("# Testing Trade Explanation Generator with and without LLM")
    logger.info("#" * 70)
    logger.info("\n")

    try:
        # Test 1: Without LLM (baseline)
        baseline_results = await test_without_llm()

        # Wait a bit before next test
        await asyncio.sleep(2)

        # Test 2: With LLM
        llm_results = await test_with_llm()

        # Compare
        if baseline_results and llm_results:
            await asyncio.sleep(1)
            await compare_results(baseline_results, llm_results)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise

    logger.info("\n")
    logger.info("#" * 70)
    logger.info("# TEST COMPLETED")
    logger.info("#" * 70)


if __name__ == "__main__":
    asyncio.run(main())
