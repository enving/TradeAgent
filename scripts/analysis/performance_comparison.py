"""Performance comparison script for trading strategies.

Analyzes and compares bot performance metrics:
- Win rate and average P&L
- Sharpe ratio and max drawdown
- Trade frequency and duration
- Strategy-specific metrics

Usage:
    python performance_comparison.py --days 30
"""

import asyncio
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List

from src.database.supabase_client import SupabaseClient
from src.utils.logger import logger


async def fetch_performance_data(days: int = 30) -> Dict:
    """Fetch performance data from Supabase.
    
    Args:
        days: Number of days to analyze (default: 30)
        
    Returns:
        Dictionary with trades and daily performance data
    """
    supabase = await SupabaseClient.get_instance()
    
    # Calculate date range
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"Fetching data from {start_date} to {end_date}")
    
    # Fetch trades
    trades_response = await supabase.table("trades").select("*").gte(
        "date", start_date.isoformat()
    ).lte("date", end_date.isoformat()).order("date", desc=False).execute()
    
    # Fetch daily performance
    perf_response = await supabase.table("daily_performance").select("*").gte(
        "date", start_date.isoformat()
    ).lte("date", end_date.isoformat()).order("date", desc=False).execute()
    
    return {
        "trades": trades_response.data,
        "daily_performance": perf_response.data,
        "start_date": start_date,
        "end_date": end_date,
    }


def calculate_trade_metrics(trades: List[Dict]) -> Dict:
    """Calculate trading metrics from trade data.
    
    Args:
        trades: List of trade records
        
    Returns:
        Dictionary with calculated metrics
    """
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "total_pnl": 0,
        }
    
    # Filter for closed trades (have exit_price and pnl)
    closed_trades = [t for t in trades if t.get("pnl") is not None]
    
    if not closed_trades:
        return {
            "total_trades": len(trades),
            "closed_trades": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "total_pnl": 0,
        }
    
    # Calculate metrics
    wins = [t for t in closed_trades if float(t["pnl"]) > 0]
    losses = [t for t in closed_trades if float(t["pnl"]) <= 0]
    
    total_pnl = sum(float(t["pnl"]) for t in closed_trades)
    avg_pnl = total_pnl / len(closed_trades)
    
    win_rate = len(wins) / len(closed_trades) if closed_trades else 0
    avg_win = sum(float(t["pnl"]) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(float(t["pnl"]) for t in losses) / len(losses) if losses else 0
    
    return {
        "total_trades": len(trades),
        "closed_trades": len(closed_trades),
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "total_pnl": total_pnl,
        "wins": len(wins),
        "losses": len(losses),
    }


def calculate_strategy_breakdown(trades: List[Dict]) -> Dict[str, Dict]:
    """Calculate metrics broken down by strategy.
    
    Args:
        trades: List of trade records
        
    Returns:
        Dictionary mapping strategy name to metrics
    """
    strategy_trades = defaultdict(list)
    
    for trade in trades:
        strategy = trade.get("strategy", "unknown")
        strategy_trades[strategy].append(trade)
    
    breakdown = {}
    for strategy, strat_trades in strategy_trades.items():
        breakdown[strategy] = calculate_trade_metrics(strat_trades)
    
    return breakdown


def calculate_portfolio_metrics(daily_perf: List[Dict]) -> Dict:
    """Calculate portfolio-level metrics.
    
    Args:
        daily_perf: List of daily performance records
        
    Returns:
        Dictionary with portfolio metrics
    """
    if not daily_perf:
        return {
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "avg_daily_pnl": None,
        }
    
    # Get latest metrics
    latest = daily_perf[-1]
    
    # Calculate average daily P&L
    daily_pnls = [float(d.get("daily_pnl", 0)) for d in daily_perf if d.get("daily_pnl")]
    avg_daily_pnl = sum(daily_pnls) / len(daily_pnls) if daily_pnls else 0
    
    # Calculate total return
    if len(daily_perf) > 1:
        start_value = float(daily_perf[0].get("portfolio_value", 0))
        end_value = float(latest.get("portfolio_value", 0))
        total_return = (end_value - start_value) / start_value if start_value > 0 else 0
    else:
        total_return = 0
    
    return {
        "sharpe_ratio": latest.get("sharpe_ratio"),
        "max_drawdown": latest.get("max_drawdown"),
        "total_return": total_return,
        "avg_daily_pnl": avg_daily_pnl,
        "current_portfolio_value": float(latest.get("portfolio_value", 0)),
    }


def print_report(data: Dict, metrics: Dict, strategy_breakdown: Dict, portfolio_metrics: Dict):
    """Print formatted performance report.
    
    Args:
        data: Raw data dictionary
        metrics: Overall trade metrics
        strategy_breakdown: Strategy-specific metrics
        portfolio_metrics: Portfolio-level metrics
    """
    print("\n" + "="*80)
    print("TRADING PERFORMANCE REPORT")
    print("="*80)
    
    print(f"\nPeriod: {data['start_date']} to {data['end_date']}")
    print(f"Days analyzed: {(data['end_date'] - data['start_date']).days}")
    
    print("\n" + "-"*80)
    print("OVERALL METRICS")
    print("-"*80)
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Closed Trades: {metrics['closed_trades']}")
    print(f"Win Rate: {metrics['win_rate']:.1%}")
    print(f"Total P&L: ${metrics['total_pnl']:.2f}")
    print(f"Average P&L per Trade: ${metrics['avg_pnl']:.2f}")
    print(f"Average Win: ${metrics['avg_win']:.2f}")
    print(f"Average Loss: ${metrics['avg_loss']:.2f}")
    print(f"Wins/Losses: {metrics['wins']}/{metrics['losses']}")
    
    print("\n" + "-"*80)
    print("STRATEGY BREAKDOWN")
    print("-"*80)
    for strategy, strat_metrics in strategy_breakdown.items():
        print(f"\n{strategy.upper()}:")
        print(f"  Trades: {strat_metrics['closed_trades']}")
        print(f"  Win Rate: {strat_metrics['win_rate']:.1%}")
        print(f"  Total P&L: ${strat_metrics['total_pnl']:.2f}")
        print(f"  Avg P&L: ${strat_metrics['avg_pnl']:.2f}")
    
    print("\n" + "-"*80)
    print("PORTFOLIO METRICS")
    print("-"*80)
    print(f"Current Portfolio Value: ${portfolio_metrics['current_portfolio_value']:.2f}")
    print(f"Total Return: {portfolio_metrics['total_return']:.2%}")
    print(f"Average Daily P&L: ${portfolio_metrics['avg_daily_pnl']:.2f}")
    
    if portfolio_metrics['sharpe_ratio'] is not None:
        print(f"Sharpe Ratio: {portfolio_metrics['sharpe_ratio']:.2f}")
    else:
        print("Sharpe Ratio: N/A (insufficient data)")
    
    if portfolio_metrics['max_drawdown'] is not None:
        print(f"Max Drawdown: {portfolio_metrics['max_drawdown']:.2%}")
    else:
        print("Max Drawdown: N/A (insufficient data)")
    
    print("\n" + "="*80 + "\n")


async def main(days: int = 30):
    """Main entry point.
    
    Args:
        days: Number of days to analyze
    """
    try:
        # Fetch data
        data = await fetch_performance_data(days)
        
        # Calculate metrics
        overall_metrics = calculate_trade_metrics(data["trades"])
        strategy_breakdown = calculate_strategy_breakdown(data["trades"])
        portfolio_metrics = calculate_portfolio_metrics(data["daily_performance"])
        
        # Print report
        print_report(data, overall_metrics, strategy_breakdown, portfolio_metrics)
        
    except Exception as e:
        logger.error(f"Error generating performance report: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze trading performance")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    args = parser.parse_args()
    
    asyncio.run(main(args.days))
