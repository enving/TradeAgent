"""News-Driven Trading Strategy.

Uses the News Agent (Aggregator + Sentiment Engine) to generate trading signals.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from ..clients.alpha_vantage_client import AlphaVantageClient
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
        # Removed AlphaVantageClient due to rate limits

    async def scan_for_signals(self, alpaca_client: AlpacaMCPClient) -> List[Signal]:
        """Scan watchlist for news-driven signals.

        Logic:
        1. Fetch news for each ticker.
        2. Analyze sentiment.
        3. If Sentiment > 0.7 (Bullish) and Impact is HIGH:
           - Check Technicals (Price > SMA20).
           - Generate BUY signal.
        """
        import yfinance as yf
        signals = []
        watchlist = get_dynamic_watchlist()

        logger.info(f"Scanning {len(watchlist)} tickers for news signals...")

        for ticker in watchlist:
            try:
                # 1. Fetch News
                articles = await self.aggregator.fetch_news(ticker, days=2)
                if not articles:
                    continue

                # 1a. LOG ALL NEWS ARTICLES
                await self.news_logger.log_news_articles(articles)

                # 2. Analyze Sentiment
                prognosis = await self.engine.analyze_news(ticker, articles)
                if not prognosis:
                    continue

                logger.info(f"News Analysis for {ticker}: {prognosis.action} (Score: {prognosis.sentiment_score:.2f})")

                # 2a. LOG EVERY LLM ANALYSIS (BUY, SELL, HOLD)
                llm_log = LLMAnalysisLog(
                    ticker=ticker,
                    analysis_timestamp=datetime.now(timezone.utc),
                    action=prognosis.action,
                    sentiment_score=Decimal(str(prognosis.sentiment_score)),
                    confidence=Decimal(str(prognosis.confidence)),
                    impact=prognosis.impact,
                    reasoning=prognosis.reasoning,
                    article_count=len(articles),
                    lookback_days=2,
                    signal_generated=False,  # Will update if signal created
                    signal_approved=False,
                )
                analysis_id = await self.news_logger.log_llm_analysis(llm_log)

                # 3. Filter for High Conviction
                if prognosis.action == "BUY" and prognosis.sentiment_score >= 0.7 and prognosis.impact == "HIGH":
                    
                    # 4. Technical Confirmation (Price > SMA20)
                    # We need current price and SMA
                    # Use yfinance instead of Alpha Vantage
                    yf_ticker = yf.Ticker(ticker)
                    bars = yf_ticker.history(period="1mo", interval="1d")
                    
                    if bars.empty:
                        continue
                        
                    # Normalize columns
                    bars.columns = [c.lower() for c in bars.columns]
                    
                    bars["sma20"] = calculate_sma(bars, period=20)
                    bars = bars.dropna()
                    
                    if bars.empty:
                        continue

                    latest = bars.iloc[-1]
                    
                    if latest["close"] > latest["sma20"]:
                        # Valid Signal - PASSED all filters
                        entry_price = Decimal(str(latest["close"]))
                        stop_loss = entry_price * Decimal("0.95") # 5% trailing stop logic
                        take_profit = entry_price * Decimal("1.15") # 15% target

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
                                "llm_analysis_id": analysis_id  # Link to LLM log
                            }
                        )
                        signals.append(signal)
                        logger.info(f"NEWS SIGNAL: BUY {ticker} - {prognosis.reasoning}")

                        # Update LLM log: signal was generated AND approved
                        if analysis_id:
                            await self.news_logger.update_signal_link(
                                analysis_id=analysis_id,
                                signal_id=None,  # Will be set when signal is stored
                                signal_approved=True,
                                reject_reason=None
                            )
                    else:
                        # Signal NOT approved - technical filter failed
                        if analysis_id:
                            reject_reason = f"Price ${latest['close']:.2f} below SMA20 ${latest['sma20']:.2f}"
                            await self.news_logger.update_signal_link(
                                analysis_id=analysis_id,
                                signal_id=None,
                                signal_approved=False,
                                reject_reason=reject_reason
                            )
                            logger.debug(f"NEWS SIGNAL REJECTED for {ticker}: {reject_reason}")

            except Exception as e:
                logger.error(f"Error processing news for {ticker}: {e}")
                continue

        return signals
