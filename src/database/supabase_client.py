"""Async Supabase client for trade logging and performance tracking.

This module implements a Singleton pattern for the Supabase client to ensure
only one connection is maintained throughout the application lifecycle.
"""

from typing import Any

from supabase import Client, acreate_client

from ..models.ml_data import MLDataLabel, MLTrainingData
from ..models.performance import DailyPerformance, ParameterChange, StrategyMetrics, WeeklyReport
from ..models.trade import Signal, Trade
from ..utils.config import config
from ..utils.logger import logger


class SupabaseClient:
    """Singleton async Supabase client for database operations.

    This client handles all database operations including:
    - Logging trades
    - Logging signals
    - Storing performance metrics
    - Recording parameter changes
    - Saving weekly reports

    Example:
        client = await SupabaseClient.get_instance()
        await client.log_trade(trade_object)
    """

    _instance: Client | None = None

    @classmethod
    async def get_instance(cls) -> Client:
        """Get or create the Supabase client instance.

        Uses the Singleton pattern to ensure only one client exists.
        CRITICAL: Uses acreate_client() for async support (PRP requirement).

        Returns:
            Supabase client instance

        Raises:
            Exception: If client creation fails
        """
        if cls._instance is None:
            logger.info("Creating new Supabase client instance")
            cls._instance = await acreate_client(config.SUPABASE_URL, config.SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")

        return cls._instance

    @classmethod
    async def log_trade(cls, trade: Trade) -> dict[str, Any]:
        """Log an executed trade to the database.

        Args:
            trade: Trade object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        # Convert Pydantic model to dict for database insertion
        trade_data = trade.model_dump(exclude_none=True, exclude={"id"})

        # Convert datetime to ISO string for Supabase
        if "date" in trade_data:
            trade_data["date"] = trade_data["date"].isoformat()

        # Convert Decimal to string for JSON serialization
        for key, value in trade_data.items():
            if isinstance(value, Decimal):
                trade_data[key] = str(value)

        try:
            response = await client.table("trades").insert(trade_data).execute()
            logger.debug(f"Trade logged: {trade.ticker} {trade.action} {trade.quantity}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            raise

    @classmethod
    async def log_signal(cls, signal: Signal) -> dict[str, Any]:
        """Log a trading signal to the database.

        Args:
            signal: Signal object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal
        from datetime import datetime, UTC

        client = await cls.get_instance()

        # Convert Signal to database format
        signal_data = {
            "date": "now()",  # Use database timestamp
            "ticker": signal.ticker,
            "signal_type": signal.action,
            "confidence": float(signal.confidence),
            "entry_price": float(signal.entry_price),
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
            "rsi": float(signal.rsi) if signal.rsi else None,
            "macd_histogram": float(signal.macd_histogram) if signal.macd_histogram else None,
            "volume_ratio": float(signal.volume_ratio) if signal.volume_ratio else None,
            "strategy": signal.strategy,
            "executed": False,
        }

        try:
            response = await client.table("signals").insert(signal_data).execute()
            logger.debug(f"Signal logged: {signal.ticker} {signal.action}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
            raise

    @classmethod
    async def log_daily_performance(cls, performance: DailyPerformance) -> dict[str, Any]:
        """Log daily performance metrics.

        Args:
            performance: DailyPerformance object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        perf_data = performance.model_dump()
        # Convert date to string
        perf_data["date"] = perf_data["date"].isoformat()

        # Convert Decimal to string for JSON serialization
        for key, value in perf_data.items():
            if isinstance(value, Decimal):
                perf_data[key] = str(value)

        try:
            response = await client.table("daily_performance").insert(perf_data).execute()
            logger.debug(f"Daily performance logged for {performance.date}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log daily performance: {e}")
            raise

    @classmethod
    async def log_strategy_metrics(cls, metrics: StrategyMetrics) -> dict[str, Any]:
        """Log strategy-specific performance metrics.

        Args:
            metrics: StrategyMetrics object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        metrics_data = metrics.model_dump()
        metrics_data["date"] = metrics_data["date"].isoformat()

        # Convert Decimal to string for JSON serialization
        for key, value in metrics_data.items():
            if isinstance(value, Decimal):
                metrics_data[key] = str(value)

        try:
            response = await client.table("strategy_metrics").insert(metrics_data).execute()
            logger.debug(f"Strategy metrics logged: {metrics.strategy} on {metrics.date}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log strategy metrics: {e}")
            raise

    @classmethod
    async def log_parameter_change(cls, change: ParameterChange) -> dict[str, Any]:
        """Log a strategy parameter adjustment.

        Args:
            change: ParameterChange object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        client = await cls.get_instance()

        change_data = change.model_dump()
        change_data["date"] = change_data["date"].isoformat()

        try:
            response = await client.table("parameter_changes").insert(change_data).execute()
            logger.info(f"Parameter change logged: {change.reason}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log parameter change: {e}")
            raise

    @classmethod
    async def log_weekly_report(cls, report: WeeklyReport) -> dict[str, Any]:
        """Log a weekly performance report.

        Args:
            report: WeeklyReport object to log

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        report_data = report.model_dump()
        report_data["week_ending"] = report_data["week_ending"].isoformat()

        # Convert Decimal to string for JSON serialization
        for key, value in report_data.items():
            if isinstance(value, Decimal):
                report_data[key] = str(value)

        try:
            response = await client.table("weekly_reports").insert(report_data).execute()
            logger.info(f"Weekly report logged for week ending {report.week_ending}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log weekly report: {e}")
            raise

    @classmethod
    async def get_recent_trades(cls, days: int = 5) -> list[dict[str, Any]]:
        """Retrieve recent trades from the database.

        Args:
            days: Number of days to look back

        Returns:
            List of trade records

        Raises:
            Exception: If database query fails
        """
        from datetime import datetime, timedelta

        client = await cls.get_instance()

        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            response = (
                await client.table("trades")
                .select("*")
                .gte("date", cutoff_date)
                .order("date", desc=True)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to retrieve trades: {e}")
            raise

    @classmethod
    async def get_strategy_performance(cls, strategy: str, days: int = 5) -> list[dict[str, Any]]:
        """Retrieve strategy performance metrics.

        Args:
            strategy: Strategy name (defensive or momentum)
            days: Number of days to look back

        Returns:
            List of performance records

        Raises:
            Exception: If database query fails
        """
        from datetime import datetime, timedelta

        client = await cls.get_instance()

        try:
            # Calculate cutoff date
            cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()

            response = (
                await client.table("strategy_metrics")
                .select("*")
                .eq("strategy", strategy)
                .gte("date", cutoff_date)
                .order("date", desc=True)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to retrieve strategy performance: {e}")
            raise

    # ML Training Data Methods

    @classmethod
    async def log_ml_training_data(cls, ml_data: MLTrainingData) -> dict[str, Any]:
        """Log ML training data to database.

        Args:
            ml_data: MLTrainingData object with features

        Returns:
            Database response with inserted record

        Raises:
            Exception: If database insert fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        # Convert Pydantic model to dict
        data_dict = ml_data.model_dump(exclude_none=True, exclude={"id", "created_at"})

        # Convert datetime to ISO string
        if "timestamp" in data_dict:
            data_dict["timestamp"] = data_dict["timestamp"].isoformat()

        # Convert features to JSON
        if "features" in data_dict:
            # Convert TradeFeatures to dict
            data_dict["features"] = data_dict["features"]

        # Convert Decimal to string
        for key, value in data_dict.items():
            if isinstance(value, Decimal):
                data_dict[key] = str(value)

        try:
            response = await client.table("ml_training_data").insert(data_dict).execute()
            logger.debug(f"ML training data logged: {ml_data.ticker} {ml_data.action}")
            return response.data
        except Exception as e:
            logger.error(f"Failed to log ML training data: {e}")
            raise

    @classmethod
    async def get_unlabeled_ml_data(
        cls, days_ago: int, hold_period: int
    ) -> list[dict[str, Any]]:
        """Get unlabeled ML training data from X days ago.

        Used by labeling script to find trades that need outcome labels.

        Args:
            days_ago: How many days ago to look (e.g., 7, 14, 30)
            hold_period: Hold period for labeling (7, 14, or 30)

        Returns:
            List of unlabeled ML training records

        Raises:
            Exception: If database query fails
        """
        from datetime import datetime, timedelta

        client = await cls.get_instance()

        try:
            # Calculate date range
            target_date = datetime.now() - timedelta(days=days_ago)
            start_of_day = target_date.replace(hour=0, minute=0, second=0).isoformat()
            end_of_day = target_date.replace(hour=23, minute=59, second=59).isoformat()

            response = (
                await client.table("ml_training_data")
                .select("*")
                .eq("is_labeled", False)
                .gte("timestamp", start_of_day)
                .lte("timestamp", end_of_day)
                .execute()
            )

            logger.info(
                f"Found {len(response.data)} unlabeled trades from {days_ago} days ago"
            )
            return response.data

        except Exception as e:
            logger.error(f"Failed to get unlabeled ML data: {e}")
            raise

    @classmethod
    async def update_ml_label(
        cls, record_id: str, label: MLDataLabel
    ) -> dict[str, Any]:
        """Update ML training record with label.

        Args:
            record_id: UUID of the record to update
            label: MLDataLabel with outcome, return_pct, etc.

        Returns:
            Database response with updated record

        Raises:
            Exception: If database update fails
        """
        from decimal import Decimal

        client = await cls.get_instance()

        # Convert label to dict
        label_dict = label.model_dump(exclude_none=True)

        # Convert datetime to ISO string
        if "label_timestamp" in label_dict:
            label_dict["label_timestamp"] = label_dict["label_timestamp"].isoformat()

        # Convert Decimal to string
        for key, value in label_dict.items():
            if isinstance(value, Decimal):
                label_dict[key] = str(value)

        # Mark as labeled
        label_dict["is_labeled"] = True

        try:
            response = (
                await client.table("ml_training_data")
                .update(label_dict)
                .eq("id", record_id)
                .execute()
            )

            logger.debug(f"ML label updated for record {record_id}")
            return response.data

        except Exception as e:
            logger.error(f"Failed to update ML label: {e}")
            raise

    @classmethod
    async def get_ml_training_dataset(
        cls, is_labeled: bool = True, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get ML training dataset for model training.

        Args:
            is_labeled: Only return labeled data (default: True)
            limit: Optional limit on number of records

        Returns:
            List of ML training records

        Raises:
            Exception: If database query fails
        """
        client = await cls.get_instance()

        try:
            query = client.table("ml_training_data").select("*")

            if is_labeled:
                query = query.eq("is_labeled", True)

            if limit:
                query = query.limit(limit)

            query = query.order("timestamp", desc=True)

            response = await query.execute()

            logger.info(
                f"Retrieved {len(response.data)} ML training records (labeled={is_labeled})"
            )
            return response.data

        except Exception as e:
            logger.error(f"Failed to get ML training dataset: {e}")
            raise
