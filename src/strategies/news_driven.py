"""News-Driven Trading Strategy.

Uses the News Agent (Aggregator + Sentiment Engine) to generate trading signals.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, cast, Literal

from ..core.indicators import calculate_sma
from ..core.news_llm_logger import NewsLLMLogger
from ..llm.sentiment_engine import SentimentEngine
from ..mcp_clients.alpaca_client import AlpacaMCPClient
from ..models.news_models import LLMAnalysisLog
from ..models.trade import Signal
from ..news.aggregator import NewsAggregator
from ..utils.logger import logger
from .momentum_trading import get_dynamic_watchlist


class NewsSentimentStrategy:
    """Strategy that trades based on LLM-analyzed news sentiment."""

    def __init__(self):
        self.aggregator = NewsAggregator()
        self.engine = SentimentEngine()
        self.news_logger = NewsLLMLogger()

    async def analyze_ticker_for_signal(
        self, ticker: str, alpaca_client: AlpacaMCPClient
    ) -> Optional[Signal]:
        """Analyze a single ticker for news-driven signals.

        Args:
            ticker: Stock symbol to analyze
            alpaca_client: Alpaca client for market data

        Returns:
            Signal object if a bullish opportunity is found, else None
        """
        import yfinance as yf

        try:
            articles = await self.aggregator.fetch_news(ticker, days=2)
            if not articles:
                return None

            await self.news_logger.log_news_articles(articles)

            prognosis = await self.engine.analyze_news(ticker, articles)
            if not prognosis:
                return None

            logger.info(
                f"News Analysis for {ticker}: {prognosis.action} (Score: {prognosis.sentiment_score:.2f})"
            )

            action_val = cast(Literal["BUY", "SELL", "HOLD"], prognosis.action)
            impact_val = cast(Literal["HIGH", "MEDIUM", "LOW"], prognosis.impact)

            llm_log = LLMAnalysisLog(
                ticker=ticker,
                analysis_timestamp=datetime.now(timezone.utc),
                action=action_val,
                sentiment_score=Decimal(str(prognosis.sentiment_score)),
                confidence=Decimal(str(prognosis.confidence)),
                impact=impact_val,
                reasoning=prognosis.reasoning,
                article_count=len(articles),
                lookback_days=2,
                signal_generated=False,
                signal_approved=False,
            )
            analysis_id = await self.news_logger.log_llm_analysis(llm_log)

            if (
                prognosis.action == "BUY"
                and prognosis.sentiment_score >= 0.7
                and prognosis.impact == "HIGH"
            ):
                yf_ticker = yf.Ticker(ticker)

                bars_1d = yf_ticker.history(period="1mo", interval="1d")
                if bars_1d.empty:
                    return None
                bars_1d.columns = [c.lower() for c in bars_1d.columns]

                sma20_1d = calculate_sma(bars_1d, period=20).iloc[-1]
                latest_price = Decimal(str(bars_1d["close"].iloc[-1]))

                if latest_price <= Decimal(str(sma20_1d)):
                    if analysis_id:
                        await self.news_logger.update_signal_link(
                            analysis_id=analysis_id,
                            signal_id="",
                            signal_approved=False,
                            reject_reason=f"Daily: Price ${latest_price:.2f} <= SMA20 ${sma20_1d:.2f}",
                        )
                    return None

                bars_1h = yf_ticker.history(period="5d", interval="1h")
                if not bars_1h.empty:
                    bars_1h.columns = [c.lower() for c in bars_1h.columns]
                    sma10_1h = calculate_sma(bars_1h, period=10).iloc[-1]
                    if latest_price <= Decimal(str(sma10_1h)):
                        if analysis_id:
                            await self.news_logger.update_signal_link(
                                analysis_id=analysis_id,
                                signal_id="",
                                signal_approved=False,
                                reject_reason=f"Hourly: Price ${latest_price:.2f} <= SMA10 ${sma10_1h:.2f}",
                            )
                        return None

                from ..core.indicators import calculate_rsi

                bars_15m = yf_ticker.history(period="2d", interval="15m")
                if not bars_15m.empty:
                    bars_15m.columns = [c.lower() for c in bars_15m.columns]
                    rsi_15m = calculate_rsi(bars_15m).iloc[-1]
                    if rsi_15m <= 50:
                        if analysis_id:
                            await self.news_logger.update_signal_link(
                                analysis_id=analysis_id,
                                signal_id="",
                                signal_approved=False,
                                reject_reason=f"15m: RSI {rsi_15m:.1f} <= 50",
                            )
                        return None

                entry_price = latest_price
                stop_loss = entry_price * Decimal("0.95")
                take_profit = entry_price * Decimal("1.15")

                signal = Signal(
                    ticker=ticker,
                    action="BUY",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=Decimal(str(prognosis.confidence)),
                    strategy="news_sentiment",
                    metadata={
                        "sentiment_score": prognosis.sentiment_score,
                        "impact": prognosis.impact,
                        "reasoning": prognosis.reasoning,
                        "source_count": len(articles),
                        "llm_analysis_id": analysis_id,
                    },
                )

                if analysis_id:
                    await self.news_logger.update_signal_link(
                        analysis_id=analysis_id,
                        signal_id="",
                        signal_approved=True,
                        reject_reason=None,
                    )
                return signal

            return None
        except Exception as e:
            logger.error(f"Error processing news for {ticker}: {e}")
            return None

    async def scan_for_signals(self, alpaca_client: AlpacaMCPClient) -> List[Signal]:
        """Scan watchlist for news-driven signals.

        Returns:
            List of buy signals meeting all criteria
        """
        signals = []
        watchlist = get_dynamic_watchlist()

        logger.info(f"Scanning {len(watchlist)} tickers for news signals...")

        for ticker in watchlist:
            signal = await self.analyze_ticker_for_signal(ticker, alpaca_client)
            if signal:
                signals.append(signal)

        return signals
