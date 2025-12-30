"""Test script for the AI Orchestrator Agent.

Run this to verify the orchestrator is working correctly before enabling in production.

Usage:
    python test_orchestrator.py
"""

import asyncio
from decimal import Decimal

from src.agents.orchestrator import TradingOrchestrator
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal
from src.utils.config import config
from src.utils.logger import logger


async def test_market_regime_analysis():
    """Test market regime analysis."""
    logger.info("=" * 60)
    logger.info("TEST 1: Market Regime Analysis")
    logger.info("=" * 60)

    orchestrator = TradingOrchestrator()

    # Get real portfolio data
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    # Analyze market regime
    regime, confidence, reasoning = await orchestrator.analyze_market_regime(
        portfolio, positions
    )

    logger.info(f"✓ Market Regime: {regime}")
    logger.info(f"✓ Confidence: {confidence:.2f}")
    logger.info(f"✓ Reasoning: {reasoning}")
    logger.info(f"✓ Strategy Weights: {orchestrator.get_strategy_weights()}")

    return regime


async def test_signal_quality_scoring():
    """Test signal quality scoring."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Signal Quality Scoring")
    logger.info("=" * 60)

    orchestrator = TradingOrchestrator()

    # Get real portfolio data
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    # Create a test signal (realistic)
    test_signal = Signal(
        ticker="AAPL",
        action="BUY",
        entry_price=Decimal("180.00"),
        stop_loss=Decimal("174.60"),  # -3%
        take_profit=Decimal("194.40"),  # +8%
        confidence=Decimal("0.75"),
        strategy="momentum",
        rsi=Decimal("65.0"),
        macd_histogram=Decimal("0.5"),
        volume_ratio=Decimal("1.3"),
    )

    # Score signal quality
    quality_score, recommendation, reasoning = await orchestrator.score_signal_quality(
        test_signal, portfolio, positions
    )

    logger.info(f"✓ Signal: {test_signal.ticker}")
    logger.info(f"✓ Quality Score: {quality_score:.2f}")
    logger.info(f"✓ Recommendation: {recommendation}")
    logger.info(f"✓ Reasoning: {reasoning}")

    return quality_score


async def test_signal_prioritization():
    """Test signal prioritization."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Signal Prioritization")
    logger.info("=" * 60)

    orchestrator = TradingOrchestrator()

    # Get real portfolio data
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    # Create multiple test signals
    test_signals = [
        Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("180.00"),
            stop_loss=Decimal("174.60"),
            take_profit=Decimal("194.40"),
            confidence=Decimal("0.75"),
            strategy="momentum",
            rsi=Decimal("65.0"),
            macd_histogram=Decimal("0.5"),
            volume_ratio=Decimal("1.3"),
        ),
        Signal(
            ticker="MSFT",
            action="BUY",
            entry_price=Decimal("420.00"),
            stop_loss=Decimal("407.40"),
            take_profit=Decimal("453.60"),
            confidence=Decimal("0.65"),
            strategy="momentum",
            rsi=Decimal("62.0"),
            macd_histogram=Decimal("0.3"),
            volume_ratio=Decimal("1.2"),
        ),
        Signal(
            ticker="NVDA",
            action="BUY",
            entry_price=Decimal("850.00"),
            stop_loss=Decimal("824.50"),
            take_profit=Decimal("918.00"),
            confidence=Decimal("0.80"),
            strategy="news_sentiment",
            metadata={"sentiment_score": 0.85, "impact": "HIGH"},
        ),
    ]

    # Prioritize signals
    prioritized = await orchestrator.prioritize_signals(
        test_signals, portfolio, positions
    )

    logger.info(f"✓ Prioritized {len(prioritized)} signals")

    for i, (signal, score, reasoning) in enumerate(prioritized, 1):
        logger.info(f"\nRank {i}: {signal.ticker}")
        logger.info(f"  Priority Score: {score:.2f}")
        logger.info(f"  Reasoning: {reasoning}")

    return prioritized


async def test_decision_explanation():
    """Test decision explanation."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Decision Explanation")
    logger.info("=" * 60)

    orchestrator = TradingOrchestrator()

    # Create a test signal
    test_signal = Signal(
        ticker="AAPL",
        action="BUY",
        entry_price=Decimal("180.00"),
        stop_loss=Decimal("174.60"),
        take_profit=Decimal("194.40"),
        confidence=Decimal("0.75"),
        strategy="momentum",
        rsi=Decimal("65.0"),
        macd_histogram=Decimal("0.5"),
        volume_ratio=Decimal("1.3"),
    )

    # Test approved decision
    explanation = await orchestrator.explain_decision(
        signal=test_signal,
        approved=True,
        factors={
            "risk_filter_passed": True,
            "correlation_check": "PASSED",
            "sector_limit": "OK",
            "position_size": 10,
            "portfolio_value": 100000.0,
        },
    )

    logger.info("✓ APPROVED Decision Explanation:")
    logger.info(explanation)

    # Test rejected decision
    explanation_rejected = await orchestrator.explain_decision(
        signal=test_signal,
        approved=False,
        factors={
            "risk_filter_passed": False,
            "correlation_check": "FAILED",
            "correlation_with": "MSFT (0.85)",
            "reason": "High correlation with existing position",
        },
    )

    logger.info("\n✓ REJECTED Decision Explanation:")
    logger.info(explanation_rejected)

    return explanation


async def test_strategy_weight_adjustment():
    """Test strategy weight adjustment."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Strategy Weight Adjustment")
    logger.info("=" * 60)

    orchestrator = TradingOrchestrator()

    # First analyze regime (needed for context)
    alpaca = AlpacaMCPClient()
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()

    await orchestrator.analyze_market_regime(portfolio, positions)

    # Get current weights
    old_weights = orchestrator.get_strategy_weights()
    logger.info(f"Current Weights: {old_weights}")

    # Adjust weights based on performance
    new_weights = await orchestrator.adjust_strategy_weights()

    logger.info(f"✓ New Weights: {new_weights}")
    logger.info(f"✓ Changes: {', '.join([f'{k}: {old_weights[k]:.2f} → {new_weights[k]:.2f}' for k in old_weights])}")

    return new_weights


async def main():
    """Run all orchestrator tests."""
    logger.info("Starting AI Orchestrator Tests")
    logger.info("=" * 60)

    # Check if LLM features are enabled
    if not config.ENABLE_LLM_FEATURES:
        logger.error("❌ ENABLE_LLM_FEATURES is not enabled in .env")
        logger.error("Please set ENABLE_LLM_FEATURES=true to test the orchestrator")
        return

    if not config.OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY is not set in .env")
        logger.error("Please add your OpenRouter API key to test the orchestrator")
        return

    try:
        # Run tests
        await test_market_regime_analysis()
        await test_signal_quality_scoring()
        await test_signal_prioritization()
        await test_decision_explanation()
        await test_strategy_weight_adjustment()

        logger.info("\n" + "=" * 60)
        logger.info("✅ All tests completed successfully!")
        logger.info("=" * 60)
        logger.info("\nThe AI Orchestrator is ready to use.")
        logger.info("You can now run the main trading loop with orchestrator enabled.")

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        logger.error("\nPlease fix the error before using the orchestrator in production.")


if __name__ == "__main__":
    asyncio.run(main())
