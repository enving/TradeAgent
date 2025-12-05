"""Test Advanced Analytics (Sharpe/Drawdown)."""

import asyncio
from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import date

from src.models.performance import DailyPerformance
from src.core.performance_analyzer import analyze_daily_performance

async def test_advanced_analytics():
    print("Testing Advanced Analytics...")
    
    # Mock Supabase
    with patch("src.core.performance_analyzer.SupabaseClient") as MockSupabase:
        # Make get_instance return a mock that is already resolved
        mock_instance = MagicMock()
        future = asyncio.Future()
        future.set_result(mock_instance)
        MockSupabase.get_instance.return_value = future

        # Mock static methods
        future_log = asyncio.Future()
        future_log.set_result(None)
        MockSupabase.log_daily_performance.return_value = future_log
        
        future_strat = asyncio.Future()
        future_strat.set_result(None)
        MockSupabase.log_strategy_metrics.return_value = future_strat

        # Mock adjust_parameters_if_needed (it's called internally, but we might need to mock supabase calls inside it)
        # Actually, adjust_parameters_if_needed calls get_strategy_performance on the instance
        future_perf = asyncio.Future()
        future_perf.set_result([])
        mock_instance.get_strategy_performance.return_value = future_perf
        
        # Mock today's trades
        # select().eq().execute()
        future_trades = asyncio.Future()
        future_trades.set_result(MagicMock(data=[
            {"pnl": 100.0, "strategy": "momentum"},
            {"pnl": -50.0, "strategy": "momentum"}
        ]))
        mock_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = future_trades
        
        # Mock historical performance (last 10 days)
        history = []
        for i in range(10):
            history.append({
                "date": f"2023-01-{i+1:02d}",
                "daily_pnl": 100.0 if i % 2 == 0 else -50.0
            })
        
        future_history = asyncio.Future()
        future_history.set_result(MagicMock(data=history))
        mock_instance.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = future_history
        
        # Run analysis
        await analyze_daily_performance()
        
        # Verify log_daily_performance was called with Sharpe/DD
        call_args = MockSupabase.log_daily_performance.call_args
        if call_args:
            perf = call_args[0][0]
            print(f"✅ DailyPerformance saved:")
            print(f"   Sharpe Ratio: {perf.sharpe_ratio}")
            print(f"   Max Drawdown: {perf.max_drawdown}")
            
            if perf.sharpe_ratio is not None and perf.max_drawdown is not None:
                print("✅ Advanced metrics calculated successfully")
            else:
                print("❌ Advanced metrics missing")
        else:
            print("❌ log_daily_performance not called")

if __name__ == "__main__":
    asyncio.run(test_advanced_analytics())
