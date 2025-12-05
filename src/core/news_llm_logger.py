"""News and LLM Analysis Logger.

Stores ALL news articles and LLM analyses in the database,
not just the ones that generate signals.
"""

from datetime import datetime, timezone
from typing import List

from ..database.supabase_client import SupabaseClient
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
            client = await SupabaseClient.get_instance()

            # Convert to dict format
            records = []
            for article in articles:
                records.append({
                    "ticker": article.ticker,
                    "title": article.title,
                    "summary": article.summary,
                    "source": article.source,
                    "url": article.url,
                    "published_at": article.published_at.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })

            # Bulk insert (upsert on conflict)
            response = await client.table("news_articles").upsert(
                records, on_conflict="url"
            ).execute()

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
            client = await SupabaseClient.get_instance()

            # Convert to dict
            data = {
                "ticker": analysis.ticker,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
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
                "llm_cost_usd": float(analysis.llm_cost_usd)
                if analysis.llm_cost_usd
                else None,
            }

            response = await client.table("llm_analysis_log").insert(data).execute()

            if response.data and len(response.data) > 0:
                record_id = response.data[0].get("id")
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
        analysis_id: str, signal_id: str, signal_approved: bool, reject_reason: str | None = None
    ) -> None:
        """Update LLM analysis record with signal ID and approval status.

        Args:
            analysis_id: UUID of LLM analysis record
            signal_id: UUID of generated signal
            signal_approved: Whether signal passed all filters
            reject_reason: Reason for rejection (if not approved)
        """
        try:
            client = await SupabaseClient.get_instance()

            data = {
                "signal_id": signal_id,
                "signal_generated": True,
                "signal_approved": signal_approved,
            }

            if reject_reason:
                data["technical_filter_reason"] = reject_reason

            await client.table("llm_analysis_log").update(data).eq(
                "id", analysis_id
            ).execute()

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
