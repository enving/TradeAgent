"""Simple backtest script to compare old vs new strategy parameters.

Simulates trading with historical data to evaluate parameter changes:
- Old: RSI 55-70, 5% SL, 15% TP, 5 stocks, news verification
- New: RSI 45-75, 3% SL, 8% TP, 15 stocks, no news verification

Usage:
    python backtest_simple.py --start-date 2024-11-01 --end-date 2024-11-29
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
import yfinance as yf
import pandas as pd

from src.core.indicators import calculate_rsi, calculate_macd, calculate_sma, calculate_volume_ratio
from src.utils.logger import logger


# Old parameters (before optimization)
OLD_PARAMS = {
    "rsi_min": 55,
    "rsi_max": 70,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.15,
    "watchlist": ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"],
}

# New parameters (after optimization)
NEW_PARAMS = {
    "rsi_min": 45,
    "rsi_max": 75,
    "stop_loss_pct": 0.03,
    "take_profit_pct": 0.08,
    "watchlist": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "META",
        "TSLA", "AMD", "NFLX", "AVGO",
        "JPM", "BAC", "XOM", "CVX", "LLY", "JNJ"
    ],
}


def scan_for_signals_backtest(date: datetime, params: Dict, historical_data: Dict) -> List[Dict]:
    """Scan for momentum signals on a specific date using historical data.
    
    Args:
        date: Date to scan
        params: Strategy parameters
        historical_data: Pre-loaded historical data for all tickers
        
    Returns:
        List of signals found
    """
    signals = []
    
    for ticker in params["watchlist"]:
        try:
            # Get historical data up to this date
            if ticker not in historical_data:
                continue
            
            bars = historical_data[ticker]
            
            # Filter to only data up to current date
            bars_to_date = bars[bars.index <= date].copy()
            
            if len(bars_to_date) < 60:  # Need enough data for indicators
                continue
            
            # Calculate indicators
            bars_to_date["rsi"] = calculate_rsi(bars_to_date)
            macd, signal, histogram = calculate_macd(bars_to_date)
            bars_to_date["histogram"] = histogram
            bars_to_date["sma20"] = calculate_sma(bars_to_date, period=20)
            bars_to_date["sma50"] = calculate_sma(bars_to_date, period=50)
            bars_to_date["volume_ratio"] = calculate_volume_ratio(bars_to_date)
            
            bars_to_date = bars_to_date.dropna()
            
            if bars_to_date.empty:
                continue
            
            latest = bars_to_date.iloc[-1]
            
            # Entry criteria
            entry_conditions = [
                params["rsi_min"] < latest["rsi"] < params["rsi_max"],
                latest["histogram"] > 0,
                latest["close"] > latest["sma50"],
                latest["sma20"] > latest["sma50"],
                latest["volume_ratio"] > 1.1,
            ]
            
            if all(entry_conditions):
                entry_price = latest["close"]
                stop_loss = entry_price * (1 - params["stop_loss_pct"])
                take_profit = entry_price * (1 + params["take_profit_pct"])
                
                signals.append({
                    "ticker": ticker,
                    "date": date,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "rsi": latest["rsi"],
                })
        
        except Exception as e:
            logger.debug(f"Error scanning {ticker} on {date}: {e}")
            continue
    
    return signals


def simulate_trade(signal: Dict, historical_data: Dict, max_days: int = 30) -> Dict:
    """Simulate a trade from entry to exit.
    
    Args:
        signal: Entry signal
        historical_data: Historical price data
        max_days: Maximum holding period
        
    Returns:
        Trade result with P&L
    """
    ticker = signal["ticker"]
    entry_date = signal["date"]
    entry_price = signal["entry_price"]
    stop_loss = signal["stop_loss"]
    take_profit = signal["take_profit"]
    
    # Get future prices
    bars = historical_data[ticker]
    future_bars = bars[bars.index > entry_date].head(max_days)
    
    if future_bars.empty:
        return {"pnl": 0, "exit_reason": "no_data", "days_held": 0}
    
    # Check each day for exit
    for i, (date, row) in enumerate(future_bars.iterrows()):
        low = row["low"]
        high = row["high"]
        close = row["close"]
        
        # Check stop-loss
        if low <= stop_loss:
            pnl_pct = (stop_loss - entry_price) / entry_price
            return {
                "pnl_pct": pnl_pct,
                "exit_price": stop_loss,
                "exit_reason": "stop_loss",
                "days_held": i + 1,
            }
        
        # Check take-profit
        if high >= take_profit:
            pnl_pct = (take_profit - entry_price) / entry_price
            return {
                "pnl_pct": pnl_pct,
                "exit_price": take_profit,
                "exit_reason": "take_profit",
                "days_held": i + 1,
            }
    
    # Max holding period reached - exit at last close
    final_price = future_bars.iloc[-1]["close"]
    pnl_pct = (final_price - entry_price) / entry_price
    
    return {
        "pnl_pct": pnl_pct,
        "exit_price": final_price,
        "exit_reason": "max_days",
        "days_held": len(future_bars),
    }


def load_historical_data(tickers: List[str], start_date: str, end_date: str) -> Dict:
    """Load historical data for all tickers.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary mapping ticker to DataFrame
    """
    logger.info(f"Loading historical data for {len(tickers)} tickers...")
    
    historical_data = {}
    
    for ticker in tickers:
        try:
            yf_ticker = yf.Ticker(ticker)
            # Get extra data before start_date for indicator warmup
            warmup_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
            bars = yf_ticker.history(start=warmup_start, end=end_date, interval="1d")
            
            if not bars.empty:
                bars.columns = [c.lower() for c in bars.columns]
                historical_data[ticker] = bars
                logger.debug(f"Loaded {len(bars)} bars for {ticker}")
        
        except Exception as e:
            logger.warning(f"Failed to load data for {ticker}: {e}")
    
    logger.info(f"Loaded data for {len(historical_data)} tickers")
    return historical_data


def run_backtest(params: Dict, start_date: str, end_date: str) -> Dict:
    """Run backtest with given parameters.
    
    Args:
        params: Strategy parameters
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        Backtest results
    """
    logger.info(f"Running backtest: {start_date} to {end_date}")
    logger.info(f"Parameters: RSI {params['rsi_min']}-{params['rsi_max']}, "
                f"SL {params['stop_loss_pct']:.1%}, TP {params['take_profit_pct']:.1%}")
    
    # Load historical data
    all_tickers = list(set(OLD_PARAMS["watchlist"] + NEW_PARAMS["watchlist"]))
    historical_data = load_historical_data(all_tickers, start_date, end_date)
    
    # Generate trading dates (weekdays only)
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    current = start
    trades = []
    
    while current <= end:
        if current.weekday() < 5:  # Monday-Friday
            # Scan for signals
            signals = scan_for_signals_backtest(current, params, historical_data)
            
            # Simulate trades
            for signal in signals:
                result = simulate_trade(signal, historical_data)
                trades.append({
                    **signal,
                    **result,
                })
        
        current += timedelta(days=1)
    
    # Calculate metrics
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "total_return": 0,
        }
    
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    
    total_return = sum(t["pnl_pct"] for t in trades)
    avg_pnl = total_return / len(trades)
    win_rate = len(wins) / len(trades)
    
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    
    avg_days_held = sum(t["days_held"] for t in trades) / len(trades)
    
    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "total_return": total_return,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_days_held": avg_days_held,
        "trades": trades,
    }


def print_comparison(old_results: Dict, new_results: Dict):
    """Print comparison of backtest results.
    
    Args:
        old_results: Results from old parameters
        new_results: Results from new parameters
    """
    print("\n" + "="*80)
    print("BACKTEST COMPARISON: OLD vs NEW PARAMETERS")
    print("="*80)
    
    print("\n" + "-"*80)
    print("OLD PARAMETERS (Conservative)")
    print("-"*80)
    print(f"RSI Range: {OLD_PARAMS['rsi_min']}-{OLD_PARAMS['rsi_max']}")
    print(f"Stop-Loss: {OLD_PARAMS['stop_loss_pct']:.1%}, Take-Profit: {OLD_PARAMS['take_profit_pct']:.1%}")
    print(f"Watchlist: {len(OLD_PARAMS['watchlist'])} stocks")
    print(f"\nResults:")
    print(f"  Total Trades: {old_results['total_trades']}")
    print(f"  Win Rate: {old_results['win_rate']:.1%}")
    print(f"  Total Return: {old_results['total_return']:.2%}")
    print(f"  Avg P&L per Trade: {old_results['avg_pnl']:.2%}")
    print(f"  Avg Win: {old_results['avg_win']:.2%}")
    print(f"  Avg Loss: {old_results['avg_loss']:.2%}")
    print(f"  Avg Days Held: {old_results['avg_days_held']:.1f}")
    
    print("\n" + "-"*80)
    print("NEW PARAMETERS (Optimized)")
    print("-"*80)
    print(f"RSI Range: {NEW_PARAMS['rsi_min']}-{NEW_PARAMS['rsi_max']}")
    print(f"Stop-Loss: {NEW_PARAMS['stop_loss_pct']:.1%}, Take-Profit: {NEW_PARAMS['take_profit_pct']:.1%}")
    print(f"Watchlist: {len(NEW_PARAMS['watchlist'])} stocks")
    print(f"\nResults:")
    print(f"  Total Trades: {new_results['total_trades']}")
    print(f"  Win Rate: {new_results['win_rate']:.1%}")
    print(f"  Total Return: {new_results['total_return']:.2%}")
    print(f"  Avg P&L per Trade: {new_results['avg_pnl']:.2%}")
    print(f"  Avg Win: {new_results['avg_win']:.2%}")
    print(f"  Avg Loss: {new_results['avg_loss']:.2%}")
    print(f"  Avg Days Held: {new_results['avg_days_held']:.1f}")
    
    print("\n" + "-"*80)
    print("IMPROVEMENT")
    print("-"*80)
    
    trade_diff = new_results['total_trades'] - old_results['total_trades']
    trade_pct = (trade_diff / old_results['total_trades'] * 100) if old_results['total_trades'] > 0 else 0
    print(f"  More Trades: {trade_diff:+d} ({trade_pct:+.1f}%)")
    
    if old_results['total_trades'] > 0 and new_results['total_trades'] > 0:
        wr_diff = new_results['win_rate'] - old_results['win_rate']
        print(f"  Win Rate Change: {wr_diff:+.1%}")
        
        return_diff = new_results['total_return'] - old_results['total_return']
        print(f"  Total Return Change: {return_diff:+.2%}")
        
        avg_pnl_diff = new_results['avg_pnl'] - old_results['avg_pnl']
        print(f"  Avg P&L Change: {avg_pnl_diff:+.2%}")
    
    print("\n" + "="*80 + "\n")


def main(start_date: str, end_date: str):
    """Main entry point.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    try:
        # Run backtests
        logger.info("Running OLD parameters backtest...")
        old_results = run_backtest(OLD_PARAMS, start_date, end_date)
        
        logger.info("Running NEW parameters backtest...")
        new_results = run_backtest(NEW_PARAMS, start_date, end_date)
        
        # Print comparison
        print_comparison(old_results, new_results)
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest strategy parameter changes")
    parser.add_argument("--start-date", type=str, default="2024-11-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2024-11-29", help="End date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    main(args.start_date, args.end_date)
