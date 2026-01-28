"""Async Supabase client for trade logging and performance tracking."""

from typing import Any, List, Dict
from decimal import Decimal
from datetime import datetime, UTC, timedelta
import sys

from supabase import Client, acreate_client

from ..models.ml_data import MLDataLabel, MLTrainingData
from ..models.performance import DailyPerformance, ParameterChange, StrategyMetrics, WeeklyReport
from ..models.trade import Signal, Trade
from ..utils.config import config


class SupabaseClient:
    """Singleton async Supabase client for database operations."""

    _instance: Any = None

    @classmethod
    async def get_instance(cls) -> Any:
        """Get or create the Supabase client instance."""
        if cls._instance is None:
            # Import here to avoid early config loading issues
            from supabase import acreate_client

            cls._instance = await acreate_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        return cls._instance

    @classmethod
    async def log_system_event(
        cls,
        level: str,
        module: str,
        message: str,
        trace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a system event to the database with console fallback."""
        try:
            client = await cls.get_instance()
            data: Dict[str, Any] = {
                "level": level.upper(),
                "module": module,
                "message": message,
                "timestamp": "now()",
            }
            if trace:
                data["trace"] = trace
            if metadata:
                data["metadata"] = metadata

            await client.table("system_logs").insert(data).execute()
        except Exception as e:
            # Fallback to stderr if DB logging fails
            print(
                f"FAILED TO LOG TO DB: {level} [{module}] {message} (Error: {e})", file=sys.stderr
            )

    @classmethod
    async def log_trade(cls, trade: Trade) -> dict:
        client = await cls.get_instance()
        trade_data = trade.model_dump(exclude_none=True, exclude={"id"})
        if "date" in trade_data:
            trade_data["date"] = trade_data["date"].isoformat()
        for key, value in trade_data.items():
            if isinstance(value, Decimal):
                trade_data[key] = str(value)
        response = await client.table("trades").insert(trade_data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_signal(cls, signal: Signal) -> dict:
        client = await cls.get_instance()
        signal_data = {
            "date": "now()",
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
        response = await client.table("signals").insert(signal_data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_daily_performance(cls, performance: DailyPerformance) -> dict:
        client = await cls.get_instance()
        perf_data = performance.model_dump()
        perf_data["date"] = perf_data["date"].isoformat()
        for key, value in perf_data.items():
            if isinstance(value, Decimal):
                perf_data[key] = str(value)
        response = await client.table("daily_performance").insert(perf_data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_strategy_metrics(cls, metrics: StrategyMetrics) -> dict:
        client = await cls.get_instance()
        metrics_data = metrics.model_dump()
        metrics_data["date"] = metrics_data["date"].isoformat()
        for key, value in metrics_data.items():
            if isinstance(value, Decimal):
                metrics_data[key] = str(value)
        response = await client.table("strategy_metrics").insert(metrics_data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_parameter_change(cls, change: ParameterChange) -> dict:
        client = await cls.get_instance()
        change_data = change.model_dump()
        change_data["date"] = change_data["date"].isoformat()
        response = await client.table("parameter_changes").insert(change_data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_ml_training_data(cls, ml_data: MLTrainingData) -> dict:
        client = await cls.get_instance()
        data_dict = ml_data.model_dump(exclude_none=True, exclude={"id", "created_at"})
        if "timestamp" in data_dict:
            data_dict["timestamp"] = data_dict["timestamp"].isoformat()

        def convert_decimals(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_decimals(i) for i in obj]
            return obj

        for key, value in data_dict.items():
            data_dict[key] = convert_decimals(value)
        response = await client.table("ml_training_data").insert(data_dict).execute()
        return getattr(response, "data", {})

    @classmethod
    async def log_orchestrator_decision(
        cls,
        decision_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        reasoning: str,
    ) -> dict:
        """Log orchestrator decision to database."""
        client = await cls.get_instance()
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "decision_type": decision_type,
            "input_data": input_data,
            "output_data": output_data,
            "reasoning": reasoning,
        }
        response = await client.table("orchestrator_decisions").insert(data).execute()
        return getattr(response, "data", {})

    @classmethod
    async def get_recent_trades(cls, days: int = 5) -> list:
        client = await cls.get_instance()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        response = (
            await client.table("trades")
            .select("*")
            .gte("date", cutoff_date)
            .order("date", desc=True)
            .execute()
        )
        return getattr(response, "data", [])

    @classmethod
    async def get_strategy_performance(cls, strategy: str, days: int = 5) -> list:
        client = await cls.get_instance()
        cutoff_date = (datetime.now() - timedelta(days=days)).date().isoformat()
        response = (
            await client.table("strategy_metrics")
            .select("*")
            .eq("strategy", strategy)
            .gte("date", cutoff_date)
            .order("date", desc=True)
            .execute()
        )
        return getattr(response, "data", [])

    @classmethod
    async def get_unlabeled_ml_data(cls, days_ago: int, hold_period: int) -> list:
        client = await cls.get_instance()
        target_date = datetime.now() - timedelta(days=days_ago)
        start = target_date.replace(hour=0, minute=0, second=0).isoformat()
        end = target_date.replace(hour=23, minute=59, second=59).isoformat()
        response = (
            await client.table("ml_training_data")
            .select("*")
            .eq("is_labeled", False)
            .gte("timestamp", start)
            .lte("timestamp", end)
            .execute()
        )
        return getattr(response, "data", [])

    @classmethod
    async def update_ml_label(cls, record_id: str, label: MLDataLabel) -> dict:
        client = await cls.get_instance()
        label_dict = label.model_dump(exclude_none=True)
        if "label_timestamp" in label_dict:
            label_dict["label_timestamp"] = label_dict["label_timestamp"].isoformat()
        for key, value in label_dict.items():
            if isinstance(value, Decimal):
                label_dict[key] = str(value)
        label_dict["is_labeled"] = True
        response = (
            await client.table("ml_training_data").update(label_dict).eq("id", record_id).execute()
        )
        return getattr(response, "data", {})

    @classmethod
    async def get_ml_training_dataset(
        cls, is_labeled: bool = True, limit: int | None = None
    ) -> list:
        client = await cls.get_instance()
        query = client.table("ml_training_data").select("*")
        if is_labeled:
            query = query.eq("is_labeled", True)
        if limit:
            query = query.limit(limit)
        response = await query.order("timestamp", desc=True).execute()
        return getattr(response, "data", [])
