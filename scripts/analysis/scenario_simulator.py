import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.indicators import calculate_rsi, calculate_macd, calculate_sma, calculate_volume_ratio
from src.utils.logger import logger

DEFAULT_PARAMS = {
    "rsi_lower": 45,
    "rsi_upper": 75,
    "stop_loss_pct": 0.03,
    "take_profit_pct": 0.08,
    "volume_ratio": 1.1,
    "macd_threshold": 0.0,
}


def generate_base_data(n_days: int = 200, base_price: float = 100.0) -> pd.DataFrame:
    dates = [datetime.now() - timedelta(days=i) for i in range(n_days)]
    dates.reverse()

    prices = [base_price]
    for i in range(n_days - 1):
        daily_return = np.random.normal(0.002, 0.005)
        prices.append(prices[-1] * (1 + daily_return))

    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": [1000000 + int(np.random.normal(0, 100000)) for i in range(n_days)],
        },
        index=pd.Index(dates),
    )

    return df


def apply_scenario(df: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    if scenario_name == "Flash Crash":
        crash_start = n - 30
        for i in range(5):
            df.iloc[crash_start + i, df.columns.get_loc("close")] *= 1 - 0.04 * (i + 1)
            df.iloc[crash_start + i, df.columns.get_loc("low")] = (
                df.iloc[crash_start + i]["close"] * 0.97
            )
        for i in range(5):
            df.iloc[crash_start + 5 + i, df.columns.get_loc("close")] *= 0.80 * (1 + 0.02 * (i + 1))

    elif scenario_name == "Market Gap":
        gap_idx = n - 20
        df.iloc[gap_idx:, df.columns.get_loc("open")] *= 0.94
        df.iloc[gap_idx:, df.columns.get_loc("close")] *= 0.94

    elif scenario_name == "Earnings Whiplash":
        idx = n - 30
        df.iloc[idx, df.columns.get_loc("close")] *= 1.12
        df.iloc[idx, df.columns.get_loc("volume")] *= 6.0
        for i in range(1, 15):
            df.iloc[idx + i, df.columns.get_loc("close")] *= 1.12 - 0.02 * i

    elif scenario_name == "Slow Bleed":
        start = n - 50
        for i in range(30):
            df.iloc[start + i, df.columns.get_loc("close")] *= 1 - 0.006 * i

    elif scenario_name == "False Breakout":
        idx = n - 40
        df.iloc[idx - 10 : idx, df.columns.get_loc("close")] *= 1.08
        df.iloc[idx - 10 : idx, df.columns.get_loc("volume")] *= 2.0
        for i in range(15):
            df.iloc[idx + i, df.columns.get_loc("close")] *= 1 - 0.015 * i

    elif scenario_name == "RSI Exhaustion":
        idx = n - 60
        for i in range(15):
            df.iloc[idx + i, df.columns.get_loc("close")] *= 1 + 0.025 * i

        peak_price = df.iloc[idx + 15]["close"]
        for i in range(16, 40):
            df.iloc[idx + i, df.columns.get_loc("close")] = peak_price * (
                1 + np.random.normal(0, 0.003)
            )

    elif scenario_name == "FOMC Spike":
        idx = n - 20
        df.iloc[idx, df.columns.get_loc("high")] *= 1.08
        df.iloc[idx, df.columns.get_loc("low")] *= 0.91
        df.iloc[idx, df.columns.get_loc("close")] *= 0.93

    elif scenario_name == "Parabolic Move":
        idx = n - 60
        for i in range(60):
            df.iloc[idx + i, df.columns.get_loc("close")] *= 1 + 0.0012 * (i**1.6)

    elif scenario_name == "Wide Spreads":
        for i in range(n):
            df.iloc[i, df.columns.get_loc("high")] = df.iloc[i]["close"] * 1.06
            df.iloc[i, df.columns.get_loc("low")] = df.iloc[i]["close"] * 0.94

    elif scenario_name == "V-Shape Dip":
        idx = n - 50
        for i in range(15):
            df.iloc[idx + i, df.columns.get_loc("close")] *= 1 - 0.025 * i
        for i in range(15, 30):
            df.iloc[idx + i, df.columns.get_loc("close")] = df.iloc[idx + 14]["close"] * (
                1 + 0.03 * (i - 14)
            )

    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df["rsi"] = calculate_rsi(df)
    macd, signal, histogram = calculate_macd(df)
    df["histogram"] = histogram
    df["sma20"] = calculate_sma(df, period=20)
    df["sma50"] = calculate_sma(df, period=50)
    df["volume_ratio"] = calculate_volume_ratio(df)
    return df.dropna()


def simulate_strategy(df: pd.DataFrame, params: Dict) -> List[Dict]:
    trades = []
    position = None

    for i in range(len(df)):
        row = df.iloc[i]
        date = df.index[i]

        if position is None:
            is_rsi_valid = params["rsi_lower"] < row["rsi"] < params["rsi_upper"]
            is_macd_positive = row["histogram"] > params["macd_threshold"]
            is_above_sma50 = row["close"] > row["sma50"]
            is_sma_aligned = row["sma20"] > row["sma50"]
            is_volume_high = row["volume_ratio"] > params["volume_ratio"]

            range_ratio = (row["high"] - row["low"]) / row["close"]
            is_volatility_ok = range_ratio < 0.04

            if all(
                [
                    is_rsi_valid,
                    is_macd_positive,
                    is_above_sma50,
                    is_sma_aligned,
                    is_volume_high,
                    is_volatility_ok,
                ]
            ):
                position = {
                    "entry_date": date,
                    "entry_price": row["close"],
                    "stop_loss": row["close"] * (1 - params["stop_loss_pct"]),
                    "take_profit": row["close"] * (1 + params["take_profit_pct"]),
                }
        else:
            pnl_pct = (row["close"] - position["entry_price"]) / position["entry_price"]

            if row["low"] <= position["stop_loss"]:
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": date,
                        "entry_price": position["entry_price"],
                        "exit_price": position["stop_loss"],
                        "pnl_pct": (position["stop_loss"] - position["entry_price"])
                        / position["entry_price"],
                        "reason": "stop_loss",
                    }
                )
                position = None
            elif row["high"] >= position["take_profit"]:
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": date,
                        "entry_price": position["entry_price"],
                        "exit_price": position["take_profit"],
                        "pnl_pct": (position["take_profit"] - position["entry_price"])
                        / position["entry_price"],
                        "reason": "take_profit",
                    }
                )
                position = None
            elif row["rsi"] > 75 or row["histogram"] < 0:
                trades.append(
                    {
                        "entry_date": position["entry_date"],
                        "exit_date": date,
                        "entry_price": position["entry_price"],
                        "exit_price": row["close"],
                        "pnl_pct": pnl_pct,
                        "reason": "technical",
                    }
                )
                position = None

    return trades


def run_all_scenarios(params: Dict = DEFAULT_PARAMS, verbose: bool = True):
    scenarios = [
        "Flash Crash",
        "Market Gap",
        "Earnings Whiplash",
        "Slow Bleed",
        "False Breakout",
        "RSI Exhaustion",
        "FOMC Spike",
        "Parabolic Move",
        "Wide Spreads",
        "V-Shape Dip",
    ]

    summary = []

    if verbose:
        print(f"\n{'SCENARIO':<20} | {'TRADES':<6} | {'NET P&L':<10} | {'WIN RATE':<8}")
        print("-" * 55)

    for name in scenarios:
        data = generate_base_data()
        data = apply_scenario(data, name)
        data = add_indicators(data)

        trades = simulate_strategy(data, params)

        total_pnl = sum(t["pnl_pct"] for t in trades)
        win_count = len([t for t in trades if t["pnl_pct"] > 0])
        win_rate = win_count / len(trades) if trades else 0

        summary.append(
            {"name": name, "trades": len(trades), "pnl": total_pnl, "win_rate": win_rate}
        )

        if verbose:
            print(f"{name:<20} | {len(trades):<6} | {total_pnl:>9.2%} | {win_rate:>7.1%}")

    return summary


def optimize_params():
    best_pnl = -float("inf")
    best_params = None

    for sl in [0.02, 0.03, 0.05]:
        for tp in [0.05, 0.08, 0.12]:
            for rsi_l in [40, 45, 50]:
                params = DEFAULT_PARAMS.copy()
                params.update({"stop_loss_pct": sl, "take_profit_pct": tp, "rsi_lower": rsi_l})

                results = run_all_scenarios(params, verbose=False)
                total_pnl = sum(r["pnl"] for r in results)

                if total_pnl > best_pnl:
                    best_pnl = total_pnl
                    best_params = params

    print("\nBEST PARAMETERS FOUND:")
    if best_params:
        for k, v in best_params.items():
            print(f"  {k}: {v}")
    print(f"TOTAL P&L: {best_pnl:.2%}")

    return best_params or DEFAULT_PARAMS


if __name__ == "__main__":
    best = optimize_params()
    print("\nRUNNING BEST PARAMS:")
    run_all_scenarios(best)
