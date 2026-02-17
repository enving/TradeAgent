"""Dynamic strategy parameters storage.

Parameters can be updated by the adaptive optimizer and are persisted
to database. Falls back to defaults if no optimized parameters exist.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional


from ..utils.config import config
from ..utils.logger import logger


class StrategyParameters:
    """Manages dynamic strategy parameters."""

    # Default parameters (fallback)
    DEFAULTS = {
        "momentum": {
            "rsi_lower": 50,
            "rsi_upper": 75,
            "macd_threshold": 0.0,
            "volume_ratio": 1.1,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.12 if config.AGGRESSIVE_MODE else 0.08,
            "volatility_threshold": 0.04,
        },
        "news_sentiment": {
            "sentiment_threshold": 0.7,
            "confidence_threshold": 0.8,
            "impact_required": "HIGH",
            "stop_loss_pct": 0.05,  # 5%
            "take_profit_pct": 0.20 if config.AGGRESSIVE_MODE else 0.15,
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
            from sqlalchemy import text
            from ..database.postgres_client import PostgresClient
            
            client = await PostgresClient.get_instance()
            
            # ILIKE is Postgres specific case-insensitive match
            stmt = text("""
                SELECT new_params FROM parameter_changes
                WHERE reason ILIKE :reason
                ORDER BY changed_at DESC
                LIMIT 1
            """)
            
            params_data = None
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"reason": f"%{strategy}%"})
                row = result.fetchone()
                if row:
                    params_data = row.new_params

            if params_data:
                # Ensure parsing? asyncpg/SQLAlchemy usually handles JSONB to dict conversion
                params = params_data
                if isinstance(params, str):
                    import json
                    params = json.loads(params)
                    
                # Merge with defaults to ensure all keys exist
                defaults = self.DEFAULTS.get(strategy, {})
                merged_params = {**defaults, **params}

                logger.info(f"Loaded optimized parameters for {strategy} from database")
                self._cache[strategy] = merged_params
                self._last_fetch[strategy] = datetime.now(timezone.utc)
                return merged_params

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
            from ..database.postgres_client import PostgresClient
            from ..models.performance import ParameterChange
            
            change = ParameterChange(
                changed_at=datetime.now(timezone.utc),
                strategy=strategy,
                reason=f"[{strategy}] {reason}",
                old_params=old_params,
                new_params=new_params
            )
            
            await PostgresClient.log_parameter_change(change)

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
