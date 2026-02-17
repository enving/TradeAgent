"""News and LLM Analysis Logger.

Stores ALL news articles and LLM analyses in the database,
not just the ones that generate signals.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import text
from ..database.postgres_client import PostgresClient
from ..models.news_models import LLMAnalysisLog, NewsArticleLog
from ..news.aggregator import NewsArticle
from ..utils.logger import logger


class NewsLLMLogger:
    """Logger for news articles and LLM sentiment analyses."""

    @staticmethod
    async def log_news_articles(articles: List[NewsArticle]) -> None:
        """Store news articles in database.

        Args:
            articles: List of NewsArticle objects to store

        Note:
            Duplicates (by URL) are automatically handled by UNIQUE constraint
        """
        if not articles:
            return

        try:
            client = await PostgresClient.get_instance()
            
            # Prepare data
            records = []
            for article in articles:
                records.append(
                    {
                        "ticker": article.ticker,
                        "title": article.title,
                        "summary": article.summary,
                        "source": article.source,
                        "url": article.url,
                        "published_at": article.published_at, # SQLAlchemy handles datetime
                        "fetched_at": datetime.now(timezone.utc),
                    }
                )
            
            # In Postgres, bulk insert with ON CONFLICT can be tricky with SQLAlchemy core across different drivers.
            # Easiest deterministic way for asyncpg is execute_many with check or using insert().on_conflict_do_nothing
            
            # Using raw SQL for clarity and ON CONFLICT DO NOTHING (since we just want to log new ones)
            # Upsert is also fine but expensive if we don't need to update.
            # Supabase code used UPSERT. Let's stick to ON CONFLICT UPDATE to match behavior if possible, 
            # OR DO NOTHING if we don't care about updates. News usually doesn't change.
            # User requirement: "Duplicates ... handled by UNIQUE constraint" implies we just want to avoid errors.
            
            stmt = text("""
                INSERT INTO news_articles (ticker, title, summary, source, url, published_at, fetched_at)
                VALUES (:ticker, :title, :summary, :source, :url, :published_at, :fetched_at)
                ON CONFLICT (url) DO UPDATE 
                SET title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    fetched_at = EXCLUDED.fetched_at
            """)
            
            async with client._connection() as conn:
                await conn.execute(stmt, records)

            logger.debug(
                f"Logged {len(articles)} news articles for {articles[0].ticker if articles else 'unknown'}"
            )

        except Exception as e:
            # Don't fail trading if logging fails
            logger.error(f"Failed to log news articles: {e}")

    @staticmethod
    async def log_llm_analysis(analysis: LLMAnalysisLog) -> str | None:
        """Store LLM analysis in database.

        Args:
            analysis: LLMAnalysisLog object

        Returns:
            UUID of inserted record, or None if failed
        """
        try:
            client = await PostgresClient.get_instance()

            # Convert to dict
            data = {
                "ticker": analysis.ticker,
                "analysis_timestamp": analysis.analysis_timestamp,
                "action": analysis.action,
                "sentiment_score": float(analysis.sentiment_score),
                "confidence": float(analysis.confidence),
                "impact": analysis.impact,
                "reasoning": analysis.reasoning,
                "article_count": analysis.article_count,
                "lookback_days": analysis.lookback_days,
                "signal_generated": analysis.signal_generated,
                "signal_approved": analysis.signal_approved,
                "technical_filter_reason": analysis.technical_filter_reason,
                "signal_id": analysis.signal_id,
                "llm_model": analysis.llm_model,
                "llm_provider": analysis.llm_provider,
                "llm_tokens_used": analysis.llm_tokens_used,
                "llm_cost_usd": float(analysis.llm_cost_usd) if analysis.llm_cost_usd else None,
            }
            
            columns = list(data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO llm_analysis_log ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, data)
                row = result.fetchone()
                if row:
                    record_id = str(row.id)
                    logger.debug(
                        f"Logged LLM analysis: {analysis.ticker} {analysis.action} (score: {analysis.sentiment_score})"
                    )
                    return record_id

            return None

        except Exception as e:
            logger.error(f"Failed to log LLM analysis: {e}")
            return None

    @staticmethod
    async def update_signal_link(
        analysis_id: str,
        signal_id: str | None,
        signal_approved: bool,
        reject_reason: str | None = None,
    ) -> None:
        """Update LLM analysis record with signal ID and approval status.

        Args:
            analysis_id: UUID of LLM analysis record
            signal_id: UUID of generated signal
            signal_approved: Whether signal passed all filters
            reject_reason: Reason for rejection (if not approved)
        """
        try:
            client = await PostgresClient.get_instance()

            # Ensure empty strings are treated as None for UUID fields
            if not signal_id:
                signal_id = None

            data = {
                "id": analysis_id,
                "signal_id": signal_id,
                "signal_generated": True if signal_id else False,
                "signal_approved": signal_approved,
            }

            update_parts = [
                "signal_id = :signal_id",
                "signal_generated = :signal_generated",
                "signal_approved = :signal_approved"
            ]

            if reject_reason:
                data["technical_filter_reason"] = reject_reason
                update_parts.append("technical_filter_reason = :technical_filter_reason")

            stmt = text(f"""
                UPDATE llm_analysis_log
                SET {', '.join(update_parts)}
                WHERE id = :id
            """)

            async with client._connection() as conn:
                await conn.execute(stmt, data)

            logger.debug(f"Updated LLM analysis {analysis_id} with signal link")

        except Exception as e:
            logger.error(f"Failed to update LLM analysis signal link: {e}")


# Global singleton instance
_news_llm_logger = None


def get_news_llm_logger() -> NewsLLMLogger:
    """Get or create the NewsLLMLogger singleton.

    Returns:
        NewsLLMLogger instance
    """
    global _news_llm_logger
    if _news_llm_logger is None:
        _news_llm_logger = NewsLLMLogger()
    return _news_llm_logger
