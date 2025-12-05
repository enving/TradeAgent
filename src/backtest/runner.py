"""Run backtest simulation."""

import asyncio
from datetime import datetime, timedelta
from src.backtest.engine import BacktestEngine

async def main():
    # Backtest last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMD"]
    
    engine = BacktestEngine(start_date, end_date)
    await engine.load_data(tickers)
    
    daily_values, trades = await engine.run()
    
    print("\n=== Backtest Results ===")
    print(f"Initial Capital: $10,000.00")
    print(f"Final Value: ${daily_values[-1]['value']:.2f}")
    print(f"Total Return: {((daily_values[-1]['value'] - 10000) / 10000):.2%}")
    print(f"Total Trades: {len(trades)}")
    
    print("\nTrade History:")
    for t in trades:
        print(f"{t['date'].date()} {t['action']} {t['ticker']} @ ${t['price']:.2f} ({t.get('reason', 'Entry')})")

if __name__ == "__main__":
    asyncio.run(main())
