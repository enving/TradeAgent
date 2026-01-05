import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.llm.sentiment_tracker import get_sentiment_tracker
from src.database.supabase_client import SupabaseClient
from src.utils.logger import logger
from src.backtest.engine import BacktestEngine, MockAlpacaClient


async def setup_historical_sentiment(start_date: datetime, end_date: datetime):
    supabase = await SupabaseClient.get_instance()
    tickers = ["AAPL", "NVDA"]

    try:
        await (
            supabase.table("llm_analysis_log")
            .delete()
            .eq("reasoning", "Historical simulation")
            .execute()
        )
    except:
        pass

    current = start_date
    while current <= end_date:
        for ticker in tickers:
            if current < datetime(2024, 7, 31, tzinfo=timezone.utc):
                score = np.random.uniform(0.6, 0.8)
                action = "BUY"
            elif current < datetime(2024, 8, 4, tzinfo=timezone.utc):
                score = np.random.uniform(0.0, 0.3)
                action = "HOLD"
            elif current < datetime(2024, 8, 6, tzinfo=timezone.utc):
                score = np.random.uniform(-0.9, -0.7)
                action = "SELL"
            elif current < datetime(2024, 8, 11, tzinfo=timezone.utc):
                score = np.random.uniform(-0.4, 0.0)
                action = "HOLD"
            else:
                score = np.random.uniform(0.4, 0.7)
                action = "BUY"

            try:
                await (
                    supabase.table("llm_analysis_log")
                    .insert(
                        {
                            "ticker": ticker,
                            "sentiment_score": score,
                            "action": action,
                            "confidence": 0.8,
                            "impact": "HIGH",
                            "reasoning": "Historical simulation",
                            "created_at": current.isoformat(),
                        }
                    )
                    .execute()
                )
            except:
                pass
        current += timedelta(days=1)


async def run_tracking_bot_simulation():
    start_date = datetime(2024, 7, 15, tzinfo=timezone.utc)
    end_date = datetime(2024, 8, 30, tzinfo=timezone.utc)

    print("Setting up historical sentiment data...")
    await setup_historical_sentiment(start_date, end_date)

    tracker = get_sentiment_tracker()

    print(
        f"\n{'DATE':<12} | {'TICKER':<6} | {'DIRECTION':<10} | {'MOMENTUM':<8} | {'INFLECT':<7} | {'ACTION'}"
    )
    print("-" * 65)

    current = start_date + timedelta(days=7)
    while current <= end_date:
        if current.weekday() < 5:
            for ticker in ["AAPL", "NVDA"]:
                trend = await tracker.analyze_sentiment_trend(ticker, reference_date=current)
                if trend:
                    signals = await tracker.generate_sentiment_signals(
                        [ticker], reference_date=current
                    )
                    action = "BUY" if signals else "WAIT"
                    inflect = "YES" if trend.inflection_detected else "NO"
                    print(
                        f"{current.date()} | {ticker:<6} | {trend.trend_direction:<10} | {trend.momentum_score:>8.2f} | {inflect:<7} | {action}"
                    )
        current += timedelta(days=1)


if __name__ == "__main__":
    asyncio.run(run_tracking_bot_simulation())
