"""Dynamic strategy parameters storage.

Parameters can be updated by the adaptive optimizer and are persisted
to database. Falls back to defaults if no optimized parameters exist.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..database.supabase_client import SupabaseClient
from ..utils.logger import logger


class StrategyParameters:
    """Manages dynamic strategy parameters."""

    # Default parameters (fallback)
    DEFAULTS = {
        "momentum": {
            "rsi_lower": 45,
            "rsi_upper": 75,
            "macd_threshold": 0.0,
            "volume_ratio": 1.1,
            "stop_loss_pct": 0.03,  # 3%
            "take_profit_pct": 0.08,  # 8%
        },
        "news_sentiment": {
            "sentiment_threshold": 0.7,
            "confidence_threshold": 0.8,
            "impact_required": "HIGH",
            "stop_loss_pct": 0.05,  # 5%
            "take_profit_pct": 0.15,  # 15%
        },
        "defensive": {
            "vti_allocation": 0.25,
            "vgk_allocation": 0.10,
            "gld_allocation": 0.10,
            "rebalance_threshold": 0.05,  # 5% drift
        },
    }

    def __init__(self):
        """Initialize parameters manager."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_fetch: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1 hour cache

    async def get_parameters(self, strategy: str) -> Dict[str, Any]:
        """Get current parameters for strategy.

        Fetches from database if available, otherwise uses defaults.
        Caches results for 1 hour.

        Args:
            strategy: Strategy name ('momentum', 'news_sentiment', 'defensive')

        Returns:
            Parameter dictionary
        """
        # Check cache
        if strategy in self._cache:
            age = (datetime.now(timezone.utc) - self._last_fetch[strategy]).total_seconds()
            if age < self._cache_ttl:
                logger.debug(f"Using cached parameters for {strategy}")
                return self._cache[strategy]

        # Fetch latest from database
        try:
            client = await SupabaseClient.get_instance()
            response = (
                await client.table("parameter_changes")
                .select("new_params")
                .ilike("reason", f"%{strategy}%")
                .order("date", desc=True)
                .limit(1)
                .execute()
            )

            if response.data and len(response.data) > 0:
                params = response.data[0]["new_params"]
                logger.info(f"Loaded optimized parameters for {strategy} from database")
                self._cache[strategy] = params
                self._last_fetch[strategy] = datetime.now(timezone.utc)
                return params

        except Exception as e:
            logger.warning(f"Failed to fetch parameters for {strategy}: {e}")

        # Fallback to defaults
        logger.debug(f"Using default parameters for {strategy}")
        defaults = self.DEFAULTS.get(strategy, {})
        self._cache[strategy] = defaults
        self._last_fetch[strategy] = datetime.now(timezone.utc)
        return defaults

    async def update_parameters(
        self, strategy: str, new_params: Dict[str, Any], reason: str
    ) -> None:
        """Update strategy parameters.

        Args:
            strategy: Strategy name
            new_params: New parameter values
            reason: Reason for update
        """
        old_params = await self.get_parameters(strategy)

        try:
            client = await SupabaseClient.get_instance()
            await client.table("parameter_changes").insert(
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "reason": f"[{strategy}] {reason}",
                    "old_params": old_params,
                    "new_params": new_params,
                }
            ).execute()

            # Update cache
            self._cache[strategy] = new_params
            self._last_fetch[strategy] = datetime.now(timezone.utc)

            logger.info(f"Parameters updated for {strategy}: {reason}")

        except Exception as e:
            logger.error(f"Failed to update parameters: {e}")
            raise

    def invalidate_cache(self, strategy: Optional[str] = None) -> None:
        """Invalidate cached parameters.

        Args:
            strategy: Specific strategy to invalidate, or None for all
        """
        if strategy:
            self._cache.pop(strategy, None)
            self._last_fetch.pop(strategy, None)
        else:
            self._cache.clear()
            self._last_fetch.clear()

        logger.debug(f"Cache invalidated for {strategy or 'all strategies'}")


# Global singleton
_params_manager = None


def get_strategy_parameters() -> StrategyParameters:
    """Get or create the StrategyParameters singleton.

    Returns:
        StrategyParameters instance
    """
    global _params_manager
    if _params_manager is None:
        _params_manager = StrategyParameters()
    return _params_manager
