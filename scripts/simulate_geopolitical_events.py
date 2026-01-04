import asyncio
import json
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd

from src.strategies.news_driven import NewsSentimentStrategy
from src.agents.orchestrator import TradingOrchestrator
from src.news.aggregator import NewsArticle
from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal
from src.utils.logger import logger

SCENARIOS = {
    "trump_tariffs": {
        "description": "Donald Trump announces new 60% tariffs on all Chinese imports.",
        "news": {
            "BABA": [
                NewsArticle(
                    title="TRUMP DECLARES TOTAL TRADE WAR: 60% TARIFFS ON CHINA",
                    summary="In a historic move, Donald Trump has signed an executive order imposing 60% tariffs on all Chinese imports, effective immediately. Economists predict devastating impact on Chinese tech giants like Alibaba (BABA).",
                    source="Simulation News",
                    url="https://sim.com/tariffs",
                    published_at=datetime.now(timezone.utc),
                    ticker="BABA",
                )
            ],
            "DE": [
                NewsArticle(
                    title="US INDUSTRIAL REVIVAL: DEERE TO GAIN MASSIVE MARKET SHARE",
                    summary="With Chinese competition effectively blocked by new 60% tariffs, John Deere (DE) is expected to dominate the domestic market. Analysts have upgraded DE to a 'Super Buy' with a $600 price target.",
                    source="Simulation News",
                    url="https://sim.com/us-boost",
                    published_at=datetime.now(timezone.utc),
                    ticker="DE",
                )
            ],
        },
        "market_context": "Volatility increasing as trade war fears resurface.",
    },
    "taiwan_escalation": {
        "description": "Reports of increased military activity in the Taiwan Strait.",
        "news": {
            "TSM": [
                NewsArticle(
                    title="WAR CLOUDS OVER TAIWAN: TSMC FABRICATION AT RISK",
                    summary="Global semiconductor supply chain faces collapse as military activity in the Taiwan Strait reaches unprecedented levels. TSMC production could be halted for months.",
                    source="Simulation News",
                    url="https://sim.com/taiwan-tension",
                    published_at=datetime.now(timezone.utc),
                    ticker="TSM",
                )
            ],
            "LMT": [
                NewsArticle(
                    title="DEFENSE DEMAND EXPLODES: LOCKHEED MARTIN RECEIVES $50B EMERGENCY ORDER",
                    summary="The US government has placed a massive $50 billion emergency order for F-35s and missile systems from Lockheed Martin (LMT) amid rising global tensions.",
                    source="Simulation News",
                    url="https://sim.com/defense-rally",
                    published_at=datetime.now(timezone.utc),
                    ticker="LMT",
                )
            ],
            "AAPL": [
                NewsArticle(
                    title="APPLE STOCK CRASHES AS IPHONE PRODUCTION HALTS IN ASIA",
                    summary="Apple's total reliance on Taiwan for chips has become a catastrophic liability. Analysts expect 50% drop in iPhone shipments this year.",
                    source="Simulation News",
                    url="https://sim.com/apple-risk",
                    published_at=datetime.now(timezone.utc),
                    ticker="AAPL",
                )
            ],
        },
        "market_context": "Safe-haven flows into defense and gold; tech under pressure.",
    },
    "fed_rate_cut": {
        "description": "Federal Reserve announces unexpected 50bps rate cut to stimulate growth.",
        "news": {
            "SPY": [
                NewsArticle(
                    title="FED CUTS RATES BY 50BPS: MARKET SURGES ON STIMULUS",
                    summary="In a surprise move, the Federal Reserve has slashed interest rates by 50 basis points. Chair Powell cited the need to support economic expansion as inflation cools.",
                    source="Simulation News",
                    url="https://sim.com/fed-cut",
                    published_at=datetime.now(timezone.utc),
                    ticker="SPY",
                )
            ],
            "NVDA": [
                NewsArticle(
                    title="TECH SECTOR REJOICES AS BORROWING COSTS PLUMMET",
                    summary="High-growth tech stocks like NVIDIA are the primary beneficiaries of the Fed's aggressive rate cut. Analysts predict a multi-year bull run in AI infrastructure.",
                    source="Simulation News",
                    url="https://sim.com/tech-boom",
                    published_at=datetime.now(timezone.utc),
                    ticker="NVDA",
                )
            ],
        },
        "market_context": "Risk-on sentiment; indices hitting new all-time highs.",
    },
}


class MockYFTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period="1mo", interval="1d"):
        dates = pd.date_range(end=datetime.now(), periods=30)
        data = {
            "Open": [100.0 + i for i in range(30)],
            "High": [101.0 + i for i in range(30)],
            "Low": [99.0 + i for i in range(30)],
            "Close": [100.5 + i for i in range(30)],
            "Volume": [1000000] * 30,
        }
        df = pd.DataFrame(data, index=dates)
        return df


async def run_simulation(scenario_name):
    scenario = SCENARIOS[scenario_name]
    logger.info("\n" + "=" * 80)
    logger.info(f"SIMULATING SCENARIO: {scenario_name.upper()}")
    logger.info(f"Description: {scenario['description']}")
    logger.info("=" * 80)

    strategy = NewsSentimentStrategy()
    orchestrator = TradingOrchestrator()

    mock_alpaca = MagicMock()
    mock_alpaca.get_account = AsyncMock(
        return_value=Portfolio(
            cash=Decimal("50000.00"),
            portfolio_value=Decimal("100000.00"),
            buying_power=Decimal("100000.00"),
            equity=Decimal("50000.00"),
            last_equity=Decimal("50000.00"),
            positions=[],
        )
    )
    mock_alpaca.get_positions = AsyncMock(return_value=[])

    all_signals = []

    with patch("src.news.aggregator.NewsAggregator.fetch_news") as mock_fetch:
        with patch("yfinance.Ticker") as mock_yf:
            with patch(
                "src.core.news_llm_logger.NewsLLMLogger.log_news_articles", new_callable=AsyncMock
            ):
                with patch(
                    "src.core.news_llm_logger.NewsLLMLogger.log_llm_analysis",
                    new_callable=AsyncMock,
                ) as mock_log_analysis:
                    with patch(
                        "src.core.news_llm_logger.NewsLLMLogger.update_signal_link",
                        new_callable=AsyncMock,
                    ):
                        mock_log_analysis.return_value = "550e8400-e29b-41d4-a716-446655440000"
                        mock_yf.side_effect = lambda t: MockYFTicker(t)

                        for ticker, articles in scenario["news"].items():
                            logger.info(f"\n--- Analyzing Ticker: {ticker} ---")
                            mock_fetch.return_value = articles

                            signal = await strategy.analyze_ticker_for_signal(ticker, mock_alpaca)
                            if signal:
                                logger.info(
                                    f"✅ Strategy generated signal: {signal.action} {ticker}"
                                )
                                all_signals.append(signal)
                            else:
                                logger.info(f"❌ Strategy did not generate signal for {ticker}")

    if not all_signals:
        logger.info("\nNo BUY signals generated in this scenario.")
        return

    logger.info("\n" + "=" * 60)
    logger.info("ORCHESTRATOR ANALYSIS")
    logger.info("=" * 60)

    portfolio = await mock_alpaca.get_account()
    positions = await mock_alpaca.get_positions()

    with patch(
        "src.agents.orchestrator.tools.OrchestratorTools.get_market_data_summary"
    ) as mock_summary:
        mock_summary.return_value = {
            "SPY": {
                "name": "S&P 500",
                "price": 450.0,
                "change_pct": -1.5 if scenario_name == "taiwan_escalation" else -0.5,
            },
            "VIX": {
                "name": "Volatility Index",
                "price": 25.0 if scenario_name == "taiwan_escalation" else 18.0,
                "change_pct": 20.0,
            },
            "overall_sentiment": "BEARISH" if scenario_name == "taiwan_escalation" else "NEUTRAL",
        }

        regime, confidence, reasoning = await orchestrator.analyze_market_regime(
            portfolio, positions
        )
        logger.info(f"Detected Regime: {regime} (Confidence: {confidence:.2f})")
        logger.info(f"Reasoning: {reasoning}")

        prioritized = await orchestrator.prioritize_signals(all_signals, portfolio, positions)

        logger.info("\nRANKED SIGNALS:")
        for i, (sig, score, reason) in enumerate(prioritized, 1):
            logger.info(f"{i}. {sig.ticker} - Score: {score:.2f}")
            logger.info(f"   Reasoning: {reason}")

            explanation = await orchestrator.explain_decision(
                sig, approved=(score > 0.6), factors={"scenario": scenario_name}
            )
            logger.info(f"   AI Explanation: {explanation.splitlines()[0]}...")


async def main():
    import os

    if not os.path.exists("logs"):
        os.makedirs("logs")

    await run_simulation("trump_tariffs")
    await run_simulation("taiwan_escalation")
    await run_simulation("fed_rate_cut")


if __name__ == "__main__":
    asyncio.run(main())
