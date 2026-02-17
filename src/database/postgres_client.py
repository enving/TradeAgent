"""Async PostgreSQL client for trade logging and performance tracking.

Replaces SupabaseClient with direct PostgreSQL connection using SQLAlchemy.
"""
from __future__ import annotations

from typing import Any, List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import sys
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection
from sqlalchemy import text
from contextlib import asynccontextmanager

from ..models.ml_data import MLDataLabel, MLTrainingData
from ..models.performance import DailyPerformance, ParameterChange, StrategyMetrics, WeeklyReport
from ..models.trade import Signal, Trade
from ..utils.config import config
from ..utils.logger import logger


class PostgresClient:
    """Singleton async PostgreSQL client for database operations."""

    _instance: Any = None
    _engine: AsyncEngine | None = None

    @classmethod
    async def get_instance(cls) -> "PostgresClient":
        """Get or create the Postgres client instance."""
        if cls._instance is None:
            cls._instance = PostgresClient()
            await cls._instance._init_engine()
        return cls._instance

    async def _init_engine(self) -> None:
        """Initialize the SQLAlchemy async engine."""
        if not self._engine:
            try:
                self._engine = create_async_engine(
                    config.POSTGRES_URL,
                    echo=False,
                    pool_pre_ping=True,
                )
                logger.info("PostgreSQL engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL engine: {e}")
                raise

    @asynccontextmanager
    async def _connection(self):
        """Yields an async connection."""
        if not self._engine:
            await self._init_engine()
        
        async with self._engine.connect() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

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
            # Ensure table exists (simple check/create if not exists concept omitted for brevity, checks done in setup)
            
            stmt = text("""
                INSERT INTO system_logs (level, module, message, trace, metadata, timestamp)
                VALUES (:level, :module, :message, :trace, :metadata, NOW())
            """)
            
            # Serialize metadata to JSON if needed, but asyncpg handles dicts for JSONB
            import json
            meta_json = json.dumps(metadata) if metadata else None
            
            async with client._connection() as conn:
                await conn.execute(stmt, {
                    "level": level.upper(),
                    "module": module,
                    "message": message,
                    "trace": trace,
                    "metadata": meta_json
                })
        except Exception as e:
            # Fallback to stderr if DB logging fails
            print(
                f"FAILED TO LOG TO DB: {level} [{module}] {message} (Error: {e})", file=sys.stderr
            )

    @classmethod
    async def log_trade(cls, trade: Trade) -> dict:
        try:
            client = await cls.get_instance()
            trade_data = trade.model_dump(exclude_none=True, exclude={"id"})
            
            # Prepare fields and values
            columns = list(trade_data.keys())
            values = list(trade_data.values())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO trades ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, trade_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            return {}

    @classmethod
    async def log_signal(cls, signal: Signal) -> dict:
        try:
            client = await cls.get_instance()
            signal_data = {
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
            
            columns = list(signal_data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO signals (date, {', '.join(columns)})
                VALUES (NOW(), {', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, signal_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
            return {}

    @classmethod
    async def log_daily_performance(cls, performance: DailyPerformance) -> dict:
        try:
            client = await cls.get_instance()
            perf_data = performance.model_dump()
            
            columns = list(perf_data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO daily_performance ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, perf_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log daily performance: {e}")
            return {}

    @classmethod
    async def log_strategy_metrics(cls, metrics: StrategyMetrics) -> dict:
        try:
            client = await cls.get_instance()
            metrics_data = metrics.model_dump()
            
            columns = list(metrics_data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO strategy_metrics ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, metrics_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log strategy metrics: {e}")
            return {}

    @classmethod
    async def log_weekly_report(cls, report: WeeklyReport) -> dict:
        try:
            client = await cls.get_instance()
            report_data = report.model_dump()
            
            # JSON serialization for list fields (best/worst performers)
            import json
            report_data["best_performers"] = json.dumps(report_data.get("best_performers", []))
            report_data["worst_performers"] = json.dumps(report_data.get("worst_performers", []))
            
            columns = list(report_data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO weekly_reports ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, report_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log weekly report: {e}")
            return {}

    @classmethod
    async def log_parameter_change(cls, change: ParameterChange) -> dict:
        try:
            client = await cls.get_instance()
            change_data = change.model_dump()
            
            # JSONB creation
            import json
            change_data["old_params"] = json.dumps(change_data.get("old_params", {}))
            change_data["new_params"] = json.dumps(change_data.get("new_params", {}))

            columns = list(change_data.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO parameter_changes ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, change_data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log parameter change: {e}")
            return {}

    @classmethod
    async def log_ml_training_data(cls, ml_data: MLTrainingData) -> dict:
        try:
            client = await cls.get_instance()
            data_dict = ml_data.model_dump(exclude_none=True, exclude={"id", "created_at"})
            
            # Postgres needs standard types, but SQLALchemy/asyncpg handles basic ones.
            # Decimals might need string conversion if table expects numeric/decimal or float.
            # Assuming schema has correct types.
            
            columns = list(data_dict.keys())
            placeholders = [f":{k}" for k in columns]
            
            stmt = text(f"""
                INSERT INTO ml_training_data ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, data_dict)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log ML training data: {e}")
            return {}

    @classmethod
    async def log_orchestrator_decision(
        cls,
        decision_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        reasoning: str,
    ) -> dict:
        """Log orchestrator decision to database."""
        try:
            client = await cls.get_instance()
            import json
            data = {
                "decision_type": decision_type,
                "input_data": json.dumps(input_data),
                "output_data": json.dumps(output_data),
                "reasoning": reasoning,
            }
            
            stmt = text("""
                INSERT INTO orchestrator_decisions (timestamp, decision_type, input_data, output_data, reasoning)
                VALUES (NOW(), :decision_type, :input_data, :output_data, :reasoning)
                RETURNING *
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, data)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to log orchestrator decision: {e}")
            return {}

    @classmethod
    async def get_recent_trades(cls, days: int = 5) -> list:
        try:
            client = await cls.get_instance()
            cutoff_date = (datetime.now() - timedelta(days=days))
            
            stmt = text("""
                SELECT * FROM trades
                WHERE date >= :cutoff_date
                ORDER BY date DESC
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"cutoff_date": cutoff_date})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []

    @classmethod
    async def get_strategy_performance(cls, strategy: str, days: int = 5) -> list:
        try:
            client = await cls.get_instance()
            cutoff_date = (datetime.now() - timedelta(days=days)).date()
            
            stmt = text("""
                SELECT * FROM strategy_metrics
                WHERE strategy = :strategy AND date >= :cutoff_date
                ORDER BY date DESC
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"strategy": strategy, "cutoff_date": cutoff_date})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get strategy performance: {e}")
            return []

    @classmethod
    async def get_unlabeled_ml_data(cls, days_ago: int, hold_period: int) -> list:
        try:
            client = await cls.get_instance()
            target_date = datetime.now() - timedelta(days=days_ago)
            start = target_date.replace(hour=0, minute=0, second=0)
            end = target_date.replace(hour=23, minute=59, second=59)
            
            stmt = text("""
                SELECT * FROM ml_training_data
                WHERE is_labeled = FALSE
                  AND timestamp >= :start
                  AND timestamp <= :end
            """)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"start": start, "end": end})
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get unlabeled ml data: {e}")
            return []

    @classmethod
    async def update_ml_label(cls, record_id: str, label: MLDataLabel) -> dict:
        try:
            client = await cls.get_instance()
            label_dict = label.model_dump(exclude_none=True)
            label_dict["is_labeled"] = True
            
            # Construct dynamic update
            updates = []
            for k in label_dict.keys():
                updates.append(f"{k} = :{k}")
            
            update_clause = ", ".join(updates)
            
            stmt = text(f"""
                UPDATE ml_training_data
                SET {update_clause}
                WHERE id = :id
                RETURNING *
            """)
            
            params = label_dict.copy()
            params["id"] = record_id
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, params)
                row = result.fetchone()
                return dict(row._mapping) if row else {}
        except Exception as e:
            logger.error(f"Failed to update ml label: {e}")
            return {}

    @classmethod
    async def get_ml_training_dataset(
        cls, is_labeled: bool = True, limit: int | None = None
    ) -> list:
        try:
            client = await cls.get_instance()
            query = "SELECT * FROM ml_training_data"
            params = {}
            
            if is_labeled:
                query += " WHERE is_labeled = TRUE"
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT :limit"
                params["limit"] = limit
            
            stmt = text(query)
            
            async with client._connection() as conn:
                result = await conn.execute(stmt, params)
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get ml training dataset: {e}")
            return []
