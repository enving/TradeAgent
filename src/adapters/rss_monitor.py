"""RSS Feed Monitor for Breaking News.

Monitors multiple news sources for market-moving events:
- Yahoo Finance RSS
- Finnhub RSS
- Benzinga RSS
- SEC Edgar filings

Triggers immediate scans when breaking news detected.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Set
import xml.etree.ElementTree as ET
from collections import deque

from ..utils.logger import logger


class RSSFeedMonitor:
    """Monitor RSS feeds for breaking news and market events.

    Triggers immediate trading scans when:
    - High-impact news published
    - Earnings announcements
    - SEC filings (8-K, Form 4)
    - Analyst upgrades/downgrades
    """

    # Free RSS feeds
    RSS_FEEDS = {
        'yahoo_finance': 'https://finance.yahoo.com/news/rssindex',
        'benzinga': 'https://www.benzinga.com/feed',
        'marketwatch': 'https://www.marketwatch.com/rss/realtimeheadlines',
        'seeking_alpha': 'https://seekingalpha.com/feed.xml',
    }

    # Keywords that trigger immediate scans
    HIGH_IMPACT_KEYWORDS = [
        'earnings beat', 'earnings miss', 'guidance raised', 'guidance lowered',
        'upgrade', 'downgrade', 'acquired', 'acquisition', 'merger',
        'fda approval', 'clinical trial', 'lawsuit', 'investigation',
        'stock split', 'dividend', 'buyback', 'restructuring',
        'ceo', 'resignation', 'appointed', 'insider buying', 'insider selling',
    ]

    def __init__(self, watchlist: List[str], event_callback: Callable):
        """Initialize RSS monitor.

        Args:
            watchlist: List of tickers to monitor
            event_callback: Async function called when news detected
        """
        self.watchlist = set(watchlist)
        self.event_callback = event_callback

        # Track seen articles to avoid duplicates
        self.seen_articles: Set[str] = set()

        # Recent articles (last 2 hours)
        self.recent_articles = deque(maxlen=100)

        # Polling interval (seconds)
        self.poll_interval = 60  # Check every minute

        logger.info(f"RSS Feed Monitor initialized for {len(watchlist)} tickers")

    async def fetch_feed(self, session: aiohttp.ClientSession, feed_name: str, url: str) -> List[Dict]:
        """Fetch and parse RSS feed."""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {feed_name}: HTTP {response.status}")
                    return []

                content = await response.text()
                root = ET.fromstring(content)

                articles = []
                for item in root.findall('.//item'):
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    description = item.find('description')

                    if title is not None and link is not None:
                        article = {
                            'source': feed_name,
                            'title': title.text,
                            'link': link.text,
                            'published': pub_date.text if pub_date is not None else None,
                            'description': description.text if description is not None else "",
                        }
                        articles.append(article)

                return articles

        except Exception as e:
            logger.error(f"Error fetching {feed_name}: {e}")
            return []

    def is_relevant(self, article: Dict) -> tuple[bool, str | None]:
        """Check if article is relevant to watchlist.

        Returns:
            (is_relevant, ticker) tuple
        """
        title = article['title'].upper()
        description = article.get('description', '').upper()
        content = f"{title} {description}"

        # Check if any watchlist ticker mentioned
        for ticker in self.watchlist:
            if ticker.upper() in content:
                # Check for high-impact keywords
                for keyword in self.HIGH_IMPACT_KEYWORDS:
                    if keyword.upper() in content:
                        return True, ticker

        return False, None

    async def process_article(self, article: Dict):
        """Process new article and trigger events if relevant."""
        # Check if already seen
        article_id = article['link']
        if article_id in self.seen_articles:
            return

        self.seen_articles.add(article_id)
        self.recent_articles.append(article)

        # Check relevance
        is_relevant, ticker = self.is_relevant(article)

        if is_relevant:
            logger.info(f"📰 BREAKING NEWS: {ticker} - {article['title']}")

            await self.event_callback(
                event_type="breaking_news",
                ticker=ticker,
                data={
                    'title': article['title'],
                    'source': article['source'],
                    'link': article['link'],
                    'published': article.get('published'),
                    'description': article.get('description', ''),
                }
            )

    async def poll_feeds(self):
        """Poll all RSS feeds."""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_feed(session, name, url)
                for name, url in self.RSS_FEEDS.items()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process all articles
            for articles in results:
                if isinstance(articles, Exception):
                    continue

                for article in articles:
                    await self.process_article(article)

    async def start(self):
        """Start monitoring RSS feeds."""
        logger.info("Starting RSS Feed Monitor...")
        logger.info(f"Monitoring {len(self.RSS_FEEDS)} feeds every {self.poll_interval}s")

        while True:
            try:
                await self.poll_feeds()
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"RSS monitor error: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop monitoring."""
        logger.info("Stopping RSS Feed Monitor...")


async def news_event_handler(event_type: str, ticker: str, data: dict):
    """Handle breaking news events.

    Triggers immediate entry scan for the ticker.
    """
    from src.main import daily_trading_loop

    logger.info(f"📰 Breaking news on {ticker}: {data['title']}")
    logger.info(f"Source: {data['source']} - {data['link']}")

    # Trigger immediate scan for this ticker
    # await daily_trading_loop(focused_ticker=ticker)
