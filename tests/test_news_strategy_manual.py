"""Manual verification script for News Strategy."""

import asyncio
from unittest.mock import MagicMock, patch

from unittest.mock import MagicMock, patch

from src.models.trade import Signal
from src.strategies.news_strategy import NewsStrategy


async def test_news_strategy():
    """Test news strategy with mocked dependencies."""
    print("Testing News Strategy...")

    # Mock SentimentAnalyzer
    with patch("src.strategies.news_strategy.SentimentAnalyzer") as MockAnalyzer:
        # Setup mock
        mock_instance = MockAnalyzer.return_value
        # Make analyze_ticker an async mock
        future = asyncio.Future()
        future.set_result({
            "sentiment_score": 0.8,
            "confidence": 0.9,
            "summary": "Positive earnings report.",
            "article_count": 5
        })
        mock_instance.analyze_ticker.return_value = future

        # Initialize strategy
        strategy = NewsStrategy()
        
        # Test analyze_anomaly
        print("\n1. Testing analyze_anomaly (Positive Case)...")
        from decimal import Decimal
        signal = await strategy.analyze_anomaly("AAPL", "volume_spike", Decimal("150.00"))
        
        if signal:
            print(f"✅ Signal generated: {signal.action} {signal.ticker}")
            print(f"   Confidence: {signal.confidence}")
            print(f"   Metadata: {signal.metadata}")
        else:
            print("❌ No signal generated (Expected Signal)")

        # Test Negative Case
        print("\n2. Testing analyze_anomaly (Negative Case)...")
        future_neg = asyncio.Future()
        future_neg.set_result({
            "sentiment_score": -0.5,
            "confidence": 0.8,
            "summary": "Negative regulatory news.",
            "article_count": 3
        })
        mock_instance.analyze_ticker.return_value = future_neg
        
        signal = await strategy.analyze_anomaly("GOOGL", "price_drop", Decimal("2800.00"))
        
        if signal is None:
            print("✅ No signal generated (Expected None)")
        else:
            print(f"❌ Signal generated: {signal.action} (Expected None)")

if __name__ == "__main__":
    asyncio.run(test_news_strategy())
