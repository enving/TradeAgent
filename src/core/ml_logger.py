"""ML Training Data Logger - Collects and stores features for every trade signal.

This module automatically logs features when signals are generated,
enabling self-learning model training.
"""

from datetime import UTC, datetime
from decimal import Decimal

from ..core.feature_collector import FeatureCollector
from ..database.supabase_client import SupabaseClient
from ..models.ml_data import MLTrainingData, TechnicalFeatures, TradeFeatures
from ..models.trade import Signal
from ..utils.logger import logger


class MLLogger:
    """Logs trade signals with features for ML training."""

    def __init__(self):
        """Initialize ML logger."""
        self.feature_collector = FeatureCollector()
        self.enabled = True  # Can be disabled via config

    async def log_signal(
        self,
        signal: Signal,
        portfolio_value: Decimal,
        position_count: int,
        cash_available: Decimal,
        trigger_reason: str = "unknown",
    ) -> None:
        """Log a signal with full feature collection.

        Args:
            signal: Trading signal to log
            portfolio_value: Current portfolio value
            position_count: Number of open positions
            cash_available: Available cash
            trigger_reason: Why this signal was generated
        """
        if not self.enabled:
            return

        try:
            # Build technical features from signal
            technicals = {
                "rsi": float(signal.rsi) if signal.rsi else None,
                "macd_histogram": float(signal.macd_histogram) if signal.macd_histogram else None,
                "volume_ratio": float(signal.volume_ratio) if signal.volume_ratio else None,
            }

            # Collect features
            features = await self.feature_collector.collect_features(
                ticker=signal.ticker,
                strategy=signal.strategy,
                trigger_reason=trigger_reason,
                portfolio_value=portfolio_value,
                position_count=position_count,
                cash_available=cash_available,
                technicals=technicals,
            )

            # Create ML training record
            ml_data = MLTrainingData(
                ticker=signal.ticker,
                action=signal.action,
                timestamp=datetime.now(UTC),
                entry_price=signal.entry_price,
                strategy=signal.strategy,
                features=features,
                is_labeled=False,
            )

            # Store in database
            await SupabaseClient.log_ml_training_data(ml_data)

            logger.info(f"ML features logged for {signal.ticker} {signal.action}")

        except Exception as e:
            # Don't fail trading if ML logging fails
            logger.error(f"Failed to log ML features: {e}")


# Global singleton instance
_ml_logger = None


def get_ml_logger() -> MLLogger:
    """Get or create the ML logger singleton.

    Returns:
        MLLogger instance
    """
    global _ml_logger
    if _ml_logger is None:
        _ml_logger = MLLogger()
    return _ml_logger
