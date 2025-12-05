"""News Aggregator - Collects financial news from multiple sources."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import yfinance as yf
import finnhub
from newsapi import NewsApiClient

from ..utils.config import config
from ..utils.logger import logger

class NewsArticle:
    """Normalized news article structure."""
    def __init__(
        self,
        title: str,
        summary: str,
        source: str,
        url: str,
        published_at: datetime,
        ticker: Optional[str] = None
    ):
        self.title = title
        self.summary = summary
        self.source = source
        self.url = url
        self.published_at = published_at
        self.ticker = ticker

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "ticker": self.ticker
        }

class NewsAggregator:
    """Aggregates news from Yahoo Finance, Finnhub, and NewsAPI."""

    def __init__(self):
        self.finnhub_client = finnhub.Client(api_key=config.FINNHUB_API_KEY) if config.FINNHUB_API_KEY else None
        self.newsapi_client = NewsApiClient(api_key=config.NEWS_API_KEY) if config.NEWS_API_KEY else None

    async def fetch_news(self, ticker: str, days: int = 2) -> List[NewsArticle]:
        """Fetch news for a specific ticker from all available sources.

        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            days: Lookback period in days

        Returns:
            List of unique NewsArticle objects
        """
        tasks = [
            self._fetch_yfinance(ticker),
            self._fetch_finnhub(ticker, days),
            self._fetch_newsapi(ticker, days)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        for res in results:
            if isinstance(res, list):
                all_articles.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Error fetching news for {ticker}: {res}")

        # Deduplicate based on URL and Title similarity
        unique_articles = self._deduplicate(all_articles)
        
        # Sort by date (newest first)
        unique_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        return unique_articles

    async def _fetch_yfinance(self, ticker: str) -> List[NewsArticle]:
        """Fetch news from Yahoo Finance."""
        try:
            # yfinance calls are synchronous, run in executor
            def get_yf_news():
                t = yf.Ticker(ticker)
                return t.news

            loop = asyncio.get_event_loop()
            news_data = await loop.run_in_executor(None, get_yf_news)
            
            articles = []
            for item in news_data:
                # Parse timestamp (unix) - make timezone-aware (UTC)
                pub_date = datetime.fromtimestamp(item.get('providerPublishTime', 0), tz=timezone.utc)

                articles.append(NewsArticle(
                    title=item.get('title', ''),
                    summary=item.get('summary', '') or item.get('title', ''), # Fallback if no summary
                    source="Yahoo Finance",
                    url=item.get('link', ''),
                    published_at=pub_date,
                    ticker=ticker
                ))
            return articles
        except Exception as e:
            logger.warning(f"YFinance news fetch failed for {ticker}: {e}")
            return []

    async def _fetch_finnhub(self, ticker: str, days: int) -> List[NewsArticle]:
        """Fetch company news from Finnhub."""
        if not self.finnhub_client:
            return []

        try:
            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Synchronous call, run in executor
            loop = asyncio.get_event_loop()
            news_data = await loop.run_in_executor(
                None, 
                lambda: self.finnhub_client.company_news(ticker, _from=start_date, to=end_date)
            )
            
            articles = []
            for item in news_data:
                articles.append(NewsArticle(
                    title=item.get('headline', ''),
                    summary=item.get('summary', ''),
                    source=f"Finnhub ({item.get('source', 'Unknown')})",
                    url=item.get('url', ''),
                    published_at=datetime.fromtimestamp(item.get('datetime', 0), tz=timezone.utc),
                    ticker=ticker
                ))
            return articles
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed for {ticker}: {e}")
            return []

    async def _fetch_newsapi(self, ticker: str, days: int) -> List[NewsArticle]:
        """Fetch news from NewsAPI."""
        if not self.newsapi_client:
            return []

        try:
            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Synchronous call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.newsapi_client.get_everything(
                    q=ticker,
                    from_param=start_date,
                    language='en',
                    sort_by='relevancy',
                    page_size=10
                )
            )
            
            articles = []
            if response['status'] == 'ok':
                for item in response['articles']:
                    articles.append(NewsArticle(
                        title=item.get('title', ''),
                        summary=item.get('description', '') or item.get('title', ''),
                        source=f"NewsAPI ({item.get('source', {}).get('name', 'Unknown')})",
                        url=item.get('url', ''),
                        published_at=datetime.fromisoformat(item.get('publishedAt').replace('Z', '+00:00')),
                        ticker=ticker
                    ))
            return articles
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed for {ticker}: {e}")
            return []

    def _deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on URL and Title."""
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for article in articles:
            if article.url in seen_urls:
                continue
            
            # Simple title normalization for dedup
            title_norm = article.title.lower().strip()
            if title_norm in seen_titles:
                continue
                
            seen_urls.add(article.url)
            seen_titles.add(title_norm)
            unique.append(article)
            
        return unique
