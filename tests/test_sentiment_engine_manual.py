"""Manual test for SentimentEngine."""

import asyncio
from datetime import datetime
from src.news.aggregator import NewsArticle
from src.llm.sentiment_engine import SentimentEngine

async def main():
    engine = SentimentEngine()
    ticker = "AAPL"
    
    # Mock articles
    articles = [
        NewsArticle(
            title="Apple Reports Record Earnings",
            summary="Apple smashed expectations with record iPhone sales.",
            source="Bloomberg",
            url="http://example.com/1",
            published_at=datetime.now(),
            ticker=ticker
        ),
        NewsArticle(
            title="Analysts Upgrade Apple Target",
            summary="Morgan Stanley raises price target to $300.",
            source="Reuters",
            url="http://example.com/2",
            published_at=datetime.now(),
            ticker=ticker
        )
    ]
    
    print(f"Analyzing {len(articles)} articles for {ticker}...")
    prognosis = await engine.analyze_news(ticker, articles)
    
    if prognosis:
        print("\n=== Prognosis ===")
        print(f"Action: {prognosis.action}")
        print(f"Score: {prognosis.sentiment_score}")
        print(f"Confidence: {prognosis.confidence}")
        print(f"Impact: {prognosis.impact}")
        print(f"Reasoning: {prognosis.reasoning}")
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    asyncio.run(main())
