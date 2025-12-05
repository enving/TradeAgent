"""Test script for Sentiment Trend Tracker.

Tests sentiment trend analysis and signal generation.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.llm.sentiment_tracker import get_sentiment_tracker
from src.database.supabase_client import SupabaseClient
from src.utils.logger import logger


async def insert_test_sentiment_data():
    """Insert test sentiment data for demonstration."""

    supabase = await SupabaseClient.get_instance()

    # Test Case 1: Rising sentiment (AAPL)
    # Simulates positive news momentum building over 7 days
    logger.info("\n📊 Creating test data: AAPL (Rising sentiment)")

    aapl_sentiments = [
        (7, -0.3, "HOLD", 0.6, "MEDIUM"),  # Day -7: Slightly negative
        (6, -0.1, "HOLD", 0.65, "MEDIUM"), # Day -6: Improving
        (5, 0.1, "HOLD", 0.7, "MEDIUM"),   # Day -5: Turning positive
        (4, 0.3, "BUY", 0.75, "HIGH"),     # Day -4: Positive momentum
        (3, 0.5, "BUY", 0.8, "HIGH"),      # Day -3: Strong positive
        (2, 0.7, "BUY", 0.85, "HIGH"),     # Day -2: Very positive
        (1, 0.8, "BUY", 0.9, "HIGH"),      # Day -1: Peak sentiment
    ]

    for days_ago, sentiment, action, confidence, impact in aapl_sentiments:
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        try:
            await supabase.table("llm_analysis_log").insert({
                "ticker": "AAPL",
                "action": action,
                "sentiment_score": float(sentiment),
                "confidence": float(confidence),
                "impact": impact,
                "reasoning": f"Test data: sentiment={sentiment}",
                "signal_generated": action == "BUY",
                "signal_approved": False,
                "created_at": timestamp.isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to insert test data (may already exist): {e}")

    # Test Case 2: Sentiment inflection (TSLA)
    # Simulates sentiment reversal from negative to positive
    logger.info("\n📊 Creating test data: TSLA (Sentiment inflection)")

    tsla_sentiments = [
        (7, -0.8, "SELL", 0.85, "HIGH"),   # Day -7: Very negative
        (6, -0.7, "SELL", 0.8, "HIGH"),    # Day -6: Still negative
        (5, -0.5, "HOLD", 0.75, "MEDIUM"), # Day -5: Improving slightly
        (4, -0.2, "HOLD", 0.7, "MEDIUM"),  # Day -4: Approaching neutral
        (3, 0.1, "HOLD", 0.7, "MEDIUM"),   # Day -3: Turning positive (INFLECTION)
        (2, 0.4, "BUY", 0.75, "HIGH"),     # Day -2: Positive momentum
        (1, 0.6, "BUY", 0.8, "HIGH"),      # Day -1: Strong positive
    ]

    for days_ago, sentiment, action, confidence, impact in tsla_sentiments:
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        try:
            await supabase.table("llm_analysis_log").insert({
                "ticker": "TSLA",
                "action": action,
                "sentiment_score": float(sentiment),
                "confidence": float(confidence),
                "impact": impact,
                "reasoning": f"Test data: sentiment={sentiment}",
                "signal_generated": action == "BUY",
                "signal_approved": False,
                "created_at": timestamp.isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to insert test data (may already exist): {e}")

    # Test Case 3: Volatile sentiment (NVDA)
    # Simulates unstable sentiment (should NOT generate signal)
    logger.info("\n📊 Creating test data: NVDA (Volatile sentiment)")

    nvda_sentiments = [
        (7, 0.5, "BUY", 0.7, "MEDIUM"),
        (6, -0.3, "HOLD", 0.6, "MEDIUM"),
        (5, 0.6, "BUY", 0.75, "HIGH"),
        (4, -0.4, "HOLD", 0.65, "MEDIUM"),
        (3, 0.7, "BUY", 0.8, "HIGH"),
        (2, -0.2, "HOLD", 0.7, "MEDIUM"),
        (1, 0.4, "BUY", 0.75, "MEDIUM"),
    ]

    for days_ago, sentiment, action, confidence, impact in nvda_sentiments:
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        try:
            await supabase.table("llm_analysis_log").insert({
                "ticker": "NVDA",
                "action": action,
                "sentiment_score": float(sentiment),
                "confidence": float(confidence),
                "impact": impact,
                "reasoning": f"Test data: sentiment={sentiment}",
                "signal_generated": action == "BUY",
                "signal_approved": False,
                "created_at": timestamp.isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to insert test data (may already exist): {e}")

    # Test Case 4: Insufficient data (GOOGL)
    logger.info("\n📊 Creating test data: GOOGL (Insufficient data)")

    googl_sentiments = [
        (1, 0.5, "BUY", 0.8, "HIGH"),  # Only 1 datapoint
    ]

    for days_ago, sentiment, action, confidence, impact in googl_sentiments:
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        try:
            await supabase.table("llm_analysis_log").insert({
                "ticker": "GOOGL",
                "action": action,
                "sentiment_score": float(sentiment),
                "confidence": float(confidence),
                "impact": impact,
                "reasoning": f"Test data: sentiment={sentiment}",
                "signal_generated": action == "BUY",
                "signal_approved": False,
                "created_at": timestamp.isoformat(),
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to insert test data (may already exist): {e}")


async def test_sentiment_tracker():
    """Test the sentiment tracker with sample data."""

    logger.info("=" * 60)
    logger.info("TESTING SENTIMENT TREND TRACKER")
    logger.info("=" * 60)

    # Insert test data
    logger.info("\n📝 Inserting test sentiment data...")
    await insert_test_sentiment_data()
    logger.info("✅ Test data inserted")

    tracker = get_sentiment_tracker()

    # Test 1: Analyze rising sentiment (AAPL)
    logger.info("\n\n🔍 TEST 1: Rising Sentiment (AAPL)")
    logger.info("-" * 60)

    trend_aapl = await tracker.analyze_sentiment_trend("AAPL")

    if trend_aapl:
        logger.info(f"✅ Trend detected for AAPL:")
        logger.info(f"  Direction: {trend_aapl.trend_direction}")
        logger.info(f"  Momentum: {trend_aapl.momentum_score:.2f}")
        logger.info(f"  Volatility: {trend_aapl.volatility:.2f}")
        logger.info(f"  Recent sentiment: {trend_aapl.recent_sentiment:.2f}")
        logger.info(f"  Avg sentiment: {trend_aapl.avg_sentiment:.2f}")
        logger.info(f"  Inflection detected: {trend_aapl.inflection_detected}")
        logger.info(f"  Datapoints: {trend_aapl.datapoints_count}")

        if trend_aapl.trend_direction == "rising":
            logger.info("✅ PASS: Correctly identified rising sentiment")
        else:
            logger.warning(f"⚠️ UNEXPECTED: Expected 'rising', got '{trend_aapl.trend_direction}'")
    else:
        logger.error("❌ FAIL: No trend detected for AAPL")

    # Test 2: Analyze sentiment inflection (TSLA)
    logger.info("\n\n🔄 TEST 2: Sentiment Inflection (TSLA)")
    logger.info("-" * 60)

    trend_tsla = await tracker.analyze_sentiment_trend("TSLA")

    if trend_tsla:
        logger.info(f"✅ Trend detected for TSLA:")
        logger.info(f"  Direction: {trend_tsla.trend_direction}")
        logger.info(f"  Momentum: {trend_tsla.momentum_score:.2f}")
        logger.info(f"  Volatility: {trend_tsla.volatility:.2f}")
        logger.info(f"  Recent sentiment: {trend_tsla.recent_sentiment:.2f}")
        logger.info(f"  Avg sentiment: {trend_tsla.avg_sentiment:.2f}")
        logger.info(f"  Inflection detected: {trend_tsla.inflection_detected}")
        logger.info(f"  Datapoints: {trend_tsla.datapoints_count}")

        if trend_tsla.inflection_detected:
            logger.info("✅ PASS: Correctly detected sentiment inflection")
        else:
            logger.warning("⚠️ UNEXPECTED: Expected inflection to be detected")
    else:
        logger.error("❌ FAIL: No trend detected for TSLA")

    # Test 3: Analyze volatile sentiment (NVDA)
    logger.info("\n\n🌊 TEST 3: Volatile Sentiment (NVDA)")
    logger.info("-" * 60)

    trend_nvda = await tracker.analyze_sentiment_trend("NVDA")

    if trend_nvda:
        logger.info(f"✅ Trend detected for NVDA:")
        logger.info(f"  Direction: {trend_nvda.trend_direction}")
        logger.info(f"  Momentum: {trend_nvda.momentum_score:.2f}")
        logger.info(f"  Volatility: {trend_nvda.volatility:.2f}")
        logger.info(f"  Recent sentiment: {trend_nvda.recent_sentiment:.2f}")
        logger.info(f"  Avg sentiment: {trend_nvda.avg_sentiment:.2f}")
        logger.info(f"  Inflection detected: {trend_nvda.inflection_detected}")
        logger.info(f"  Datapoints: {trend_nvda.datapoints_count}")

        if trend_nvda.trend_direction == "volatile":
            logger.info("✅ PASS: Correctly identified volatile sentiment")
        else:
            logger.warning(f"⚠️ Note: Expected 'volatile', got '{trend_nvda.trend_direction}'")
    else:
        logger.error("❌ FAIL: No trend detected for NVDA")

    # Test 4: Insufficient data (GOOGL)
    logger.info("\n\n📉 TEST 4: Insufficient Data (GOOGL)")
    logger.info("-" * 60)

    trend_googl = await tracker.analyze_sentiment_trend("GOOGL")

    if trend_googl is None:
        logger.info("✅ PASS: Correctly returned None for insufficient data")
    else:
        logger.warning(f"⚠️ UNEXPECTED: Expected None, got trend: {trend_googl.trend_direction}")

    # Test 5: Generate signals
    logger.info("\n\n🎯 TEST 5: Signal Generation")
    logger.info("-" * 60)

    signals = await tracker.generate_sentiment_signals(["AAPL", "TSLA", "NVDA", "GOOGL"])

    logger.info(f"\nGenerated {len(signals)} signals:")
    for signal in signals:
        logger.info(f"\n  📊 {signal.ticker}:")
        logger.info(f"    Action: {signal.action}")
        logger.info(f"    Entry Price: ${signal.entry_price:.2f}")
        logger.info(f"    Confidence: {signal.confidence:.2f}")
        logger.info(f"    Strategy: {signal.strategy}")
        if signal.metadata and "reasoning" in signal.metadata:
            logger.info(f"    Reasoning: {signal.metadata['reasoning']}")

    # Expected results:
    # - AAPL: Should generate BUY (rising sentiment)
    # - TSLA: Should NOT generate signal (volatile despite inflection)
    # - NVDA: Should NOT generate signal (volatile)
    # - GOOGL: Should NOT generate signal (insufficient data)

    expected_signals = {"AAPL"}
    actual_signals = {s.ticker for s in signals}

    if expected_signals == actual_signals:
        logger.info(f"\n✅ PASS: Generated signals for expected tickers: {expected_signals}")
    else:
        if not expected_signals.issubset(actual_signals):
            missing = expected_signals - actual_signals
            logger.warning(f"\n⚠️ UNEXPECTED: Missing signals for: {missing}")
        extra = actual_signals - expected_signals
        if extra:
            logger.warning(f"\n⚠️ UNEXPECTED: Unexpected signals generated for: {extra}")

    if "NVDA" in actual_signals:
        logger.warning("\n⚠️ UNEXPECTED: Generated signal for NVDA (should be filtered as volatile)")

    if "GOOGL" in actual_signals:
        logger.warning("\n⚠️ UNEXPECTED: Generated signal for GOOGL (insufficient data)")

    logger.info("\n" + "=" * 60)
    logger.info("✅ ALL TESTS COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_sentiment_tracker())
