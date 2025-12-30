"""Analyze strategy performance using Supabase data."""

import asyncio
import pandas as pd
from decimal import Decimal
from src.database.supabase_client import SupabaseClient

async def main():
    print("Connecting to Supabase...")
    supabase = await SupabaseClient.get_instance()
    
    # 1. Fetch Trades
    print("Fetching trades...")
    response = await supabase.table("trades").select("*").order("date", desc=True).execute()
    trades = response.data
    
    if not trades:
        print("No trades found.")
        return

    df_trades = pd.DataFrame(trades)
    
    # Convert numeric columns
    numeric_cols = ['pnl', 'pnl_pct', 'entry_price', 'exit_price', 'rsi', 'macd_histogram', 'volume_ratio']
    for col in numeric_cols:
        if col in df_trades.columns:
            df_trades[col] = pd.to_numeric(df_trades[col], errors='coerce')

    print("\n=== Overall Performance ===")
    total_trades = len(df_trades)
    winning_trades = df_trades[df_trades['pnl'] > 0]
    losing_trades = df_trades[df_trades['pnl'] < 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
    total_pnl = df_trades['pnl'].sum()
    avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
    avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Total P&L: ${total_pnl:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Avg Win: ${avg_win:.2f}")
    print(f"Avg Loss: ${avg_loss:.2f}")

    print("\n=== Strategy Breakdown ===")
    if 'strategy' in df_trades.columns:
        strategy_stats = df_trades.groupby('strategy').agg({
            'pnl': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean'
        })
        print(strategy_stats)

    print("\n=== Win Rate by Ticker ===")
    ticker_stats = df_trades.groupby('ticker').agg({
        'pnl': ['count', 'sum'],
        'pnl_pct': 'mean'
    })
    # Calculate win rate per ticker
    ticker_stats['win_rate'] = df_trades.groupby('ticker').apply(
        lambda x: (x['pnl'] > 0).sum() / len(x)
    )
    print(ticker_stats.sort_values(('pnl', 'sum'), ascending=False))

    print("\n=== Technical Analysis Correlation ===")
    # Check correlation between indicators and PnL
    if 'rsi' in df_trades.columns and 'macd_histogram' in df_trades.columns:
        corr = df_trades[['pnl', 'rsi', 'macd_histogram', 'volume_ratio']].corr()
        print(corr['pnl'])

    # 2. Fetch Signals (to see missed opportunities or false positives)
    # This would require joining with price data which we might not have easily here.
    # For now, let's look at signal confidence vs outcome if we have executed signals.
    
    print("\n=== Analysis & Recommendations ===")
    if win_rate < 0.5:
        print("- Win rate is low (<50%). Consider tightening entry criteria (e.g., higher RSI threshold).")
    
    if avg_loss < -avg_win: # Assuming avg_loss is negative
        print("- Avg Loss is larger than Avg Win. Review Stop-Loss settings.")
        
    if 'strategy' in df_trades.columns:
        momentum_trades = df_trades[df_trades['strategy'] == 'momentum']
        if not momentum_trades.empty:
            mom_win_rate = (momentum_trades['pnl'] > 0).sum() / len(momentum_trades)
            if mom_win_rate < 0.55:
                 print(f"- Momentum strategy struggling (Win Rate {mom_win_rate:.2%}). Check trend filters.")

if __name__ == "__main__":
    asyncio.run(main())
