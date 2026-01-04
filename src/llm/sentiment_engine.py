"""Sentiment Engine - Analyzes financial news using LLM."""

import json
from typing import List, Dict, Any, Optional, cast
from decimal import Decimal
from openai import AsyncOpenAI

from ..news.aggregator import NewsArticle
from ..utils.config import config
from ..utils.logger import logger


class SentimentPrognosis:
    """Structured sentiment analysis result."""

    def __init__(
        self,
        sentiment_score: float,
        confidence: float,
        impact: str,
        reasoning: str,
        action: str,
    ):
        self.sentiment_score = sentiment_score
        self.confidence = confidence
        self.impact = impact
        self.reasoning = reasoning
        self.action = action

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentiment_score": self.sentiment_score,
            "confidence": self.confidence,
            "impact": self.impact,
            "reasoning": self.reasoning,
            "action": self.action,
        }


class SentimentEngine:
    """Analyzes news articles to generate market prognosis."""

    def __init__(self):
        """Initialize sentiment engine with flexible LLM provider."""
        self.client = AsyncOpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.model = config.LLM_MODEL
        logger.debug(
            f"SentimentEngine initialized with {config.LLM_PROVIDER} (model: {config.LLM_MODEL})"
        )

    async def analyze_news(
        self, ticker: str, articles: List[NewsArticle]
    ) -> Optional[SentimentPrognosis]:
        """Analyze a list of news articles for a specific ticker.

        Args:
            ticker: Stock symbol
            articles: List of NewsArticle objects

        Returns:
            SentimentPrognosis object or None if analysis fails
        """
        if not articles:
            logger.warning(f"No articles to analyze for {ticker}")
            return None

        articles_text = ""
        for i, article in enumerate(articles[:10], 1):
            articles_text += f"{i}. Title: {article.title}\n   Source: {article.source}\n   Date: {article.published_at}\n   Summary: {article.summary}\n\n"

        prompt = f"""
        You are an expert financial analyst and alpha-seeking trading AI.
        Analyze these news articles for {ticker} to identify high-probability trading opportunities.

        News Articles:
        {articles_text}

        Your task:
        1. Identify "Alpha Drivers": Focus on material events that cause rapid price appreciation (e.g., earnings beats, guidance raises, new contracts, FDA approvals, breakthrough products).
        2. Assess Sentiment: Score from -1.0 (extremely bearish) to +1.0 (extremely bullish).
        3. Determine Impact: (HIGH, MEDIUM, LOW) - how likely is this to move the price by >2% today?
        4. Recommend Action: (BUY, SELL, HOLD).
        5. Reasoning: Concise 1-sentence explanation of the primary alpha driver.

        Ignore noise, recurring news, and minor updates. We only trade on significant news catalysts.

        Output must be valid JSON:
        {{
            "sentiment_score": float,
            "confidence": float,
            "impact": "HIGH" | "MEDIUM" | "LOW",
            "reasoning": "string",
            "action": "BUY" | "SELL" | "HOLD"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial trading assistant. Output only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content_raw = response.choices[0].message.content
            if content_raw is None:
                logger.error(f"Empty response from LLM for {ticker}")
                return None

            content = cast(str, content_raw)
            data = json.loads(content)

            return SentimentPrognosis(
                sentiment_score=float(data.get("sentiment_score", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                impact=data.get("impact", "LOW").upper(),
                reasoning=data.get("reasoning", "No reasoning provided."),
                action=data.get("action", "HOLD").upper(),
            )

        except Exception as e:
            logger.error(f"Sentiment analysis failed for {ticker}: {e}")
            return None
