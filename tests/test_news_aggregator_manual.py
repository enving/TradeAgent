"""Manual test for NewsAggregator."""

import asyncio
from src.news.aggregator import NewsAggregator
from src.utils.logger import logger

async def main():
    aggregator = NewsAggregator()
    ticker = "AAPL"
    
    print(f"Fetching news for {ticker}...")
    articles = await aggregator.fetch_news(ticker)
    
    print(f"\nFound {len(articles)} articles:")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. {article.title}")
        print(f"   Source: {article.source}")
        print(f"   Date: {article.published_at}")
        print(f"   Summary: {article.summary[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
