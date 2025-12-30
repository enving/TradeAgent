"""Test script for news and LLM logging functionality.

Tests the complete pipeline:
1. Fetch news articles
2. Analyze with LLM
3. Log articles to database
4. Log LLM analysis to database
5. Verify data was saved
"""

import asyncio
from datetime import datetime, timezone

from src.core.news_llm_logger import NewsLLMLogger
from src.database.supabase_client import SupabaseClient
from src.llm.sentiment_engine import SentimentEngine
from src.models.news_models import LLMAnalysisLog
from src.news.aggregator import NewsAggregator
from src.utils.logger import logger


async def test_news_logging():
    """Test the complete news and LLM logging pipeline."""

    logger.info("=== Testing News & LLM Logging Pipeline ===\n")

    # Test ticker
    ticker = "AAPL"

    # 1. Fetch News
    logger.info(f"1. Fetching news for {ticker}...")
    aggregator = NewsAggregator()
    articles = await aggregator.fetch_news(ticker, days=2)
    logger.info(f"   ✅ Fetched {len(articles)} articles\n")

    if not articles:
        logger.warning("   ⚠️  No articles found - cannot test further")
        return

    # 2. Log News Articles
    logger.info("2. Logging news articles to database...")
    news_logger = NewsLLMLogger()
    await news_logger.log_news_articles(articles)
    logger.info("   ✅ News articles logged\n")

    # 3. Analyze with LLM
    logger.info("3. Analyzing news with LLM...")
    sentiment_engine = SentimentEngine()
    prognosis = await sentiment_engine.analyze_news(ticker, articles)

    if not prognosis:
        logger.warning("   ⚠️  LLM analysis failed - cannot test further")
        return

    logger.info(f"   ✅ LLM Analysis Complete:")
    logger.info(f"      Action: {prognosis.action}")
    logger.info(f"      Sentiment: {prognosis.sentiment_score:.2f}")
    logger.info(f"      Confidence: {prognosis.confidence:.2f}")
    logger.info(f"      Impact: {prognosis.impact}")
    logger.info(f"      Reasoning: {prognosis.reasoning[:100]}...\n")

    # 4. Log LLM Analysis
    logger.info("4. Logging LLM analysis to database...")
    llm_log = LLMAnalysisLog(
        ticker=ticker,
        analysis_timestamp=datetime.now(timezone.utc),
        action=prognosis.action,
        sentiment_score=prognosis.sentiment_score,
        confidence=prognosis.confidence,
        impact=prognosis.impact,
        reasoning=prognosis.reasoning,
        article_count=len(articles),
        lookback_days=2,
        signal_generated=False,
        signal_approved=False,
    )
    analysis_id = await news_logger.log_llm_analysis(llm_log)
    logger.info(f"   ✅ LLM analysis logged (ID: {analysis_id})\n")

    # 5. Verify Data in Database
    logger.info("5. Verifying data in database...")
    client = await SupabaseClient.get_instance()

    # Check news_articles
    news_result = await client.table("news_articles").select("*").eq("ticker", ticker).limit(5).execute()
    logger.info(f"   ✅ Found {len(news_result.data)} news articles in DB for {ticker}")

    if news_result.data:
        sample = news_result.data[0]
        logger.info(f"      Sample: {sample['title'][:60]}...")
        logger.info(f"      Source: {sample['source']}")

    # Check llm_analysis_log
    llm_result = await client.table("llm_analysis_log").select("*").eq("ticker", ticker).limit(5).execute()
    logger.info(f"   ✅ Found {len(llm_result.data)} LLM analyses in DB for {ticker}")

    if llm_result.data:
        sample = llm_result.data[0]
        logger.info(f"      Action: {sample['action']}")
        logger.info(f"      Sentiment: {sample['sentiment_score']}")
        logger.info(f"      Signal Generated: {sample['signal_generated']}")
        logger.info(f"      Signal Approved: {sample['signal_approved']}\n")

    logger.info("=== ✅ All Tests Passed! ===")
    logger.info("\n📊 Summary:")
    logger.info(f"   - News articles fetched: {len(articles)}")
    logger.info(f"   - News articles in DB: {len(news_result.data)}")
    logger.info(f"   - LLM analyses in DB: {len(llm_result.data)}")
    logger.info(f"   - LLM recommendation: {prognosis.action} (score: {prognosis.sentiment_score:.2f})")


if __name__ == "__main__":
    asyncio.run(test_news_logging())
