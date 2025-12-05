"""Sentiment Engine - Analyzes financial news using LLM."""

import json
from typing import List, Dict, Any, Optional
from decimal import Decimal
from openai import AsyncOpenAI

from ..news.aggregator import NewsArticle
from ..utils.config import config
from ..utils.logger import logger

class SentimentPrognosis:
    """Structured sentiment analysis result."""
    def __init__(
        self,
        sentiment_score: float,  # -1.0 to 1.0
        confidence: float,       # 0.0 to 1.0
        impact: str,             # "HIGH", "MEDIUM", "LOW"
        reasoning: str,
        action: str              # "BUY", "SELL", "HOLD"
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
            "action": self.action
        }

class SentimentEngine:
    """Analyzes news articles to generate market prognosis."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )
        self.model = config.OPENROUTER_MODEL

    async def analyze_news(self, ticker: str, articles: List[NewsArticle]) -> Optional[SentimentPrognosis]:
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

        # Prepare context for LLM
        articles_text = ""
        for i, article in enumerate(articles[:10], 1):  # Limit to top 10 recent articles
            articles_text += f"{i}. Title: {article.title}\n   Source: {article.source}\n   Date: {article.published_at}\n   Summary: {article.summary}\n\n"

        prompt = f"""
        You are an expert financial analyst and trading AI.
        Analyze the following news articles for {ticker} and provide a trading prognosis.

        News Articles:
        {articles_text}

        Your task:
        1. Assess the overall sentiment (-1.0 to +1.0).
        2. Determine the potential market impact (HIGH, MEDIUM, LOW).
        3. Assign a confidence score (0.0 to 1.0) based on source quality and consensus.
        4. Recommend an action (BUY, SELL, HOLD).
        5. Provide a concise reasoning (max 2 sentences).

        Output must be valid JSON in this format:
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
                    {"role": "system", "content": "You are a financial trading assistant. Output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent output
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return SentimentPrognosis(
                sentiment_score=float(data.get("sentiment_score", 0.0)),
                confidence=float(data.get("confidence", 0.5)),
                impact=data.get("impact", "LOW").upper(),
                reasoning=data.get("reasoning", "No reasoning provided."),
                action=data.get("action", "HOLD").upper()
            )

        except Exception as e:
            logger.error(f"Sentiment analysis failed for {ticker}: {e}")
            return None
