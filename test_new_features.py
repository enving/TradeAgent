#!/usr/bin/env python3
"""
Test all newly enabled API integrations and LLM features.
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_alpha_vantage():
    """Test Alpha Vantage API."""
    print("\n" + "="*80)
    print("📊 Testing Alpha Vantage API")
    print("="*80)

    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        print("❌ ALPHAVANTAGE_API_KEY not set")
        return False

    try:
        from src.clients.alpha_vantage_client import AlphaVantageClient

        client = AlphaVantageClient()
        print(f"✅ Client initialized with key: {api_key[:10]}...")

        # Test getting bars for AAPL
        print("\n🔍 Fetching AAPL bars (last 60 days)...")
        bars = await client.get_bars("AAPL", days=60)

        if bars and len(bars) > 0:
            print(f"✅ Received {len(bars)} bars")
            latest = bars[-1]
            print(f"   Latest close: ${latest['close']:.2f}")
            print(f"   Latest volume: {latest['volume']:,}")
            return True
        else:
            print("⚠️  No data received")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_news_api():
    """Test News API."""
    print("\n" + "="*80)
    print("📰 Testing News API")
    print("="*80)

    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print("❌ NEWS_API_KEY not set")
        return False

    try:
        import aiohttp

        print(f"✅ API Key configured: {api_key[:10]}...")

        # Test fetching news
        url = "https://newsapi.org/v2/everything"
        params = {
            "apiKey": api_key,
            "q": "Apple stock",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5
        }

        print("\n🔍 Fetching Apple stock news...")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("articles", [])
                    print(f"✅ Received {len(articles)} articles")

                    if articles:
                        print("\n📰 Latest headline:")
                        print(f"   {articles[0].get('title', 'N/A')}")
                        print(f"   Source: {articles[0].get('source', {}).get('name', 'N/A')}")
                        return True
                else:
                    print(f"⚠️  API returned status {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_finnhub():
    """Test Finnhub API."""
    print("\n" + "="*80)
    print("📈 Testing Finnhub API")
    print("="*80)

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        print("❌ FINNHUB_API_KEY not set")
        return False

    try:
        import aiohttp

        print(f"✅ API Key configured: {api_key[:10]}...")

        # Test fetching company news
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": "AAPL",
            "from": "2025-11-01",
            "to": "2025-12-03",
            "token": api_key
        }

        print("\n🔍 Fetching AAPL company news...")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    news = await response.json()
                    print(f"✅ Received {len(news)} news items")

                    if news:
                        print("\n📰 Latest news:")
                        print(f"   {news[0].get('headline', 'N/A')}")
                        print(f"   Source: {news[0].get('source', 'N/A')}")
                        return True
                else:
                    print(f"⚠️  API returned status {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_openrouter():
    """Test OpenRouter LLM API."""
    print("\n" + "="*80)
    print("🤖 Testing OpenRouter LLM API")
    print("="*80)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    try:
        import aiohttp

        print(f"✅ API Key configured: {api_key[:15]}...")

        # Test simple completion
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "anthropic/claude-3.5-sonnet",
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze this stock news in 1 sentence: 'Apple announces record iPhone sales'"
                }
            ],
            "max_tokens": 100
        }

        print("\n🔍 Testing sentiment analysis...")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"✅ LLM Response received")
                    print(f"\n💭 Analysis: {content}")
                    return True
                else:
                    error = await response.text()
                    print(f"⚠️  API returned status {response.status}")
                    print(f"   Error: {error[:200]}")
                    return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_llm_integration():
    """Test LLM integration in trading system."""
    print("\n" + "="*80)
    print("🧠 Testing LLM Integration in Trading System")
    print("="*80)

    try:
        from src.llm.sentiment_analyzer import SentimentAnalyzer

        print("✅ Importing SentimentAnalyzer...")

        analyzer = SentimentAnalyzer()
        print("✅ SentimentAnalyzer initialized")

        # Test sentiment analysis
        test_news = [
            "Apple announces record-breaking iPhone sales, stock surges",
            "Tesla faces production delays, investors concerned",
            "Microsoft Azure reports strong cloud growth"
        ]

        print("\n🔍 Testing sentiment analysis on news...")
        for i, headline in enumerate(test_news, 1):
            print(f"\n   {i}. {headline}")
            sentiment = await analyzer.analyze_sentiment(headline)
            print(f"      → Sentiment: {sentiment}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 TradeAgent - New Features Test Suite")
    print("="*80)
    print("Testing all newly enabled APIs and features")
    print("="*80)

    results = {
        "Alpha Vantage": await test_alpha_vantage(),
        "News API": await test_news_api(),
        "Finnhub": await test_finnhub(),
        "OpenRouter": await test_openrouter(),
        "LLM Integration": await test_llm_integration()
    }

    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)

    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {service}")

    total = len(results)
    passed = sum(results.values())

    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 ALL SYSTEMS GO! Ready for enhanced trading!")
    else:
        print("\n⚠️  Some systems need attention")

if __name__ == "__main__":
    asyncio.run(main())
