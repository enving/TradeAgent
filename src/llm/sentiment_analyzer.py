"""Sentiment Analyzer using LLM to analyze news for trading signals."""

import json
from datetime import datetime, timedelta

from openai import AsyncOpenAI
from newsapi import NewsApiClient

from src.utils.config import config
from src.utils.logger import logger


class SentimentAnalyzer:
    """Analyzes news sentiment using LLM."""

    def __init__(self):
        """Initialize clients."""
        if not config.NEWS_API_KEY:
            logger.warning("NEWS_API_KEY not set - Sentiment Analysis disabled")
            self.news_api = None
        else:
            self.news_api = NewsApiClient(api_key=config.NEWS_API_KEY)

        if not config.OPENROUTER_API_KEY:
            logger.warning("OPENROUTER_API_KEY not set - Sentiment Analysis disabled")
            self.llm_client = None
        else:
            self.llm_client = AsyncOpenAI(
                api_key=config.OPENROUTER_API_KEY,
                base_url=config.OPENROUTER_BASE_URL
            )

    async def analyze_ticker(self, ticker: str) -> dict:
        """Analyze news sentiment for a specific ticker.

        Args:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            Dictionary with sentiment analysis results:
            {
                "sentiment_score": float (-1.0 to 1.0),
                "confidence": float (0.0 to 1.0),
                "summary": str,
                "article_count": int
            }
        """
        if not self.news_api or not self.llm_client:
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "summary": "Sentiment analysis disabled (missing API keys)",
                "article_count": 0,
            }

        try:
            # 1. Fetch News
            # Get news from last 24 hours
            from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            
            news = self.news_api.get_everything(
                q=ticker,
                from_param=from_date,
                language="en",
                sort_by="relevancy",
                page_size=10,
            )

            if not news["articles"]:
                return {
                    "sentiment_score": 0.0,
                    "confidence": 0.0,
                    "summary": f"No recent news found for {ticker}",
                    "article_count": 0,
                }

            # Prepare context for LLM
            articles_text = "\n\n".join(
                [
                    f"Title: {a['title']}\nDescription: {a['description']}\nSource: {a['source']['name']}"
                    for a in news["articles"][:5]  # Analyze top 5 articles
                ]
            )

            # 2. Analyze with LLM
            prompt = f"""
            Analyze the sentiment of these news articles about {ticker} for a trading bot.
            
            Articles:
            {articles_text}
            
            Return a JSON object with:
            1. "sentiment_score": float between -1.0 (very negative) and 1.0 (very positive)
            2. "confidence": float between 0.0 and 1.0 (how sure are you?)
            3. "summary": 1 sentence summary of the news driver
            
            Focus on material financial news (earnings, products, regulations). Ignore noise.
            """

            response = await self.llm_client.chat.completions.create(
                model=config.OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
            )

            # Parse JSON from response
            content = response.choices[0].message.content
            # Simple extraction if LLM adds text around JSON
            if "{" in content and "}" in content:
                json_str = content[content.find("{") : content.rfind("}") + 1]
                result = json.loads(json_str)
            else:
                result = json.loads(content)

            result["article_count"] = len(news["articles"])
            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {ticker}: {e}")
            return {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "summary": f"Error: {str(e)}",
                "article_count": 0,
            }
