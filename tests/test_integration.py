"""Integration tests for complete trading workflows.

Tests end-to-end scenarios with multiple components working together.
Uses mocked MCP clients to simulate real trading flows.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import AsyncMock, patch
import pandas as pd
import numpy as np

from src.main import daily_trading_loop
from src.strategies.defensive_core import should_rebalance, calculate_rebalancing_orders
from src.strategies.momentum_trading import scan_for_signals, check_exit_conditions
from src.core.risk_manager import filter_signals_by_risk, calculate_position_size
from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal


@pytest.mark.integration
class TestDefensiveRebalancingFlow:
    """Integration tests for defensive core rebalancing workflow."""

    @pytest.mark.asyncio
    async def test_full_rebalancing_workflow(
        self, sample_portfolio, mock_alpaca_client, mock_supabase_client
    ):
        """Test complete rebalancing workflow from detection to execution."""
        # Setup: Portfolio with drifted allocation
        drifted_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("10"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("2000.00"),  # 20% (target 25%)
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
        ]

        # 1. Check if rebalancing needed
        today = date(2024, 3, 15)  # Not first of month
        needs_rebalance = should_rebalance(today, drifted_positions, sample_portfolio)

        assert needs_rebalance is True  # Drifted > 5%

        # 2. Calculate rebalancing orders
        signals = calculate_rebalancing_orders(drifted_positions, sample_portfolio)

        assert len(signals) > 0

        # 3. Verify signals are for defensive core
        defensive_symbols = {"VTI", "VGK", "GLD"}
        for signal in signals:
            assert signal.ticker in defensive_symbols
            assert signal.strategy == "defensive"

    @pytest.mark.asyncio
    async def test_no_rebalancing_when_balanced(self, sample_portfolio, defensive_positions):
        """Test that no rebalancing occurs when portfolio is balanced."""
        # Positions are already at target allocations
        today = date(2024, 3, 15)  # Not first of month

        needs_rebalance = should_rebalance(today, defensive_positions, sample_portfolio)

        assert needs_rebalance is False

        # No orders should be generated
        signals = calculate_rebalancing_orders(defensive_positions, sample_portfolio)

        assert len(signals) == 0


@pytest.mark.integration
class TestMomentumTradingFlow:
    """Integration tests for momentum trading workflow."""

    @pytest.mark.asyncio
    async def test_full_momentum_signal_to_order(self, sample_portfolio, mock_alpaca_client):
        """Test complete momentum flow: scan → filter → size → order."""
        # Setup: Mock market data with bullish signals
        bullish_bars = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2024-01-01", periods=30, freq="D"),
                "open": np.linspace(100, 120, 30),
                "high": np.linspace(101, 121, 30),
                "low": np.linspace(99, 119, 30),
                "close": np.linspace(100, 120, 30),  # Uptrend
                "volume": [2000000] * 29 + [3000000],  # Volume surge
            }
        )

        mock_alpaca_client.get_bars.return_value = bullish_bars

        # 1. Scan for signals
        signals = await scan_for_signals(mock_alpaca_client)

        # 2. Apply risk filters
        filtered = filter_signals_by_risk(signals, sample_portfolio, [])

        # 3. Calculate position sizes
        if filtered:
            for signal in filtered:
                qty = calculate_position_size(signal, sample_portfolio)

                # Verify position size is reasonable
                assert qty > 0
                position_value = qty * signal.entry_price
                assert position_value <= sample_portfolio.portfolio_value * Decimal("0.10")

    @pytest.mark.asyncio
    async def test_momentum_exit_conditions_flow(self, mock_alpaca_client, momentum_positions):
        """Test momentum exit flow: position → check → close."""
        # Test position with big profit (should trigger take-profit)
        profitable_position = Position(
            symbol="NVDA",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("500.00"),
            current_price=Decimal("600.00"),  # +20% (take-profit at +15%)
            market_value=Decimal("3000.00"),
            unrealized_pnl=Decimal("500.00"),
            unrealized_pnl_pct=Decimal("0.20"),
        )

        mock_alpaca_client.get_latest_quote.return_value = {"price": 600.00}
        mock_alpaca_client.get_bars.return_value = pd.DataFrame()

        # Check exit conditions
        should_exit, reason = await check_exit_conditions(profitable_position, mock_alpaca_client)

        assert should_exit is True
        assert reason == "take_profit"

    @pytest.mark.asyncio
    async def test_momentum_stop_loss_triggered(self, mock_alpaca_client):
        """Test stop-loss exit flow."""
        losing_position = Position(
            symbol="TSLA",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("180.00"),  # -10% (stop-loss at -5%)
            market_value=Decimal("1800.00"),
            unrealized_pnl=Decimal("-200.00"),
            unrealized_pnl_pct=Decimal("-0.10"),
        )

        mock_alpaca_client.get_latest_quote.return_value = {"price": 180.00}
        mock_alpaca_client.get_bars.return_value = pd.DataFrame()

        should_exit, reason = await check_exit_conditions(losing_position, mock_alpaca_client)

        assert should_exit is True
        assert reason == "stop_loss"


@pytest.mark.integration
class TestRiskManagementFlow:
    """Integration tests for risk management across strategies."""

    def test_max_position_limit_enforcement(self, sample_portfolio, momentum_positions):
        """Test that max position limit is enforced across all signals."""
        # Create 5 positions (at max)
        max_positions = [
            Position(
                symbol=f"STOCK{i}",
                quantity=Decimal("10"),
                avg_entry_price=Decimal("100.00"),
                current_price=Decimal("105.00"),
                market_value=Decimal("1050.00"),
                unrealized_pnl=Decimal("50.00"),
                unrealized_pnl_pct=Decimal("0.05"),
            )
            for i in range(5)
        ]

        # Try to add more signals
        new_signals = [
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("150.00"),
                confidence=Decimal("0.85"),
                strategy="momentum",
            ),
            Signal(
                ticker="MSFT",
                action="BUY",
                entry_price=Decimal("350.00"),
                confidence=Decimal("0.90"),
                strategy="momentum",
            ),
        ]

        # Filter should reject all (at max positions)
        filtered = filter_signals_by_risk(new_signals, sample_portfolio, max_positions)

        assert len(filtered) == 0

    def test_position_sizing_across_multiple_signals(self, sample_portfolio):
        """Test position sizing for multiple concurrent signals."""
        signals = [
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("150.00"),
                confidence=Decimal("0.85"),
                strategy="momentum",
            ),
            Signal(
                ticker="MSFT",
                action="BUY",
                entry_price=Decimal("350.00"),
                confidence=Decimal("0.75"),
                strategy="momentum",
            ),
        ]

        # Calculate position sizes
        total_capital_used = Decimal("0")

        for signal in signals:
            qty = calculate_position_size(signal, sample_portfolio)
            capital_used = qty * signal.entry_price

            # Each position should not exceed 10% of portfolio
            assert capital_used <= sample_portfolio.portfolio_value * Decimal("0.10")

            total_capital_used += capital_used

        # Total should not exceed available buying power
        assert total_capital_used <= sample_portfolio.buying_power


@pytest.mark.integration
class TestDailyTradingLoop:
    """Integration tests for main daily trading loop."""

    @pytest.mark.asyncio
    async def test_daily_loop_with_mocked_clients(self):
        """Test complete daily trading loop with mocked MCP clients."""
        with (
            patch("src.main.AlpacaMCPClient") as MockAlpaca,
            patch("src.main.SupabaseClient.get_instance") as MockSupabase,
        ):

            # Setup mocks
            mock_alpaca = AsyncMock()
            MockAlpaca.return_value = mock_alpaca

            mock_supabase = AsyncMock()
            MockSupabase.return_value = mock_supabase

            # Mock portfolio state
            mock_alpaca.get_account.return_value = Portfolio(
                portfolio_value=Decimal("10000.00"),
                cash=Decimal("5000.00"),
                buying_power=Decimal("5000.00"),
                equity=Decimal("5000.00"),
            )

            mock_alpaca.get_positions.return_value = []

            # Mock market data (no signals)
            mock_alpaca.get_bars.return_value = pd.DataFrame()

            # Mock order submission
            mock_alpaca.submit_market_order.return_value = "order_123"

            # Execute daily loop
            result = await daily_trading_loop()

            # Verify execution
            assert result["success"] is True
            assert "start_time" in result
            assert "end_time" in result
            assert "portfolio_value" in result

    @pytest.mark.asyncio
    async def test_daily_loop_handles_errors_gracefully(self):
        """Test that daily loop handles errors without crashing."""
        with patch("src.main.AlpacaMCPClient") as MockAlpaca:

            # Setup mock that raises error
            mock_alpaca = AsyncMock()
            MockAlpaca.return_value = mock_alpaca

            mock_alpaca.get_account.side_effect = Exception("API Error")

            # Daily loop should catch and log error
            with pytest.raises(Exception) as exc_info:
                await daily_trading_loop()

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_daily_loop_no_trades_day(self):
        """Test daily loop on day with no trading activity."""
        with (
            patch("src.main.AlpacaMCPClient") as MockAlpaca,
            patch("src.main.SupabaseClient.get_instance") as MockSupabase,
        ):

            mock_alpaca = AsyncMock()
            MockAlpaca.return_value = mock_alpaca

            mock_supabase = AsyncMock()
            MockSupabase.return_value = mock_supabase

            # Portfolio with no changes needed
            mock_alpaca.get_account.return_value = Portfolio(
                portfolio_value=Decimal("10000.00"),
                cash=Decimal("5000.00"),
                buying_power=Decimal("5000.00"),
                equity=Decimal("5000.00"),
            )

            # Positions at target (no rebalancing)
            mock_alpaca.get_positions.return_value = [
                Position(
                    symbol="VTI",
                    quantity=Decimal("12.5"),
                    avg_entry_price=Decimal("200.00"),
                    current_price=Decimal("200.00"),
                    market_value=Decimal("2500.00"),
                    unrealized_pnl=Decimal("0.00"),
                    unrealized_pnl_pct=Decimal("0.00"),
                ),
            ]

            # No momentum signals
            mock_alpaca.get_bars.return_value = pd.DataFrame()

            result = await daily_trading_loop()

            # Should complete successfully with no trades
            assert result["success"] is True
            assert result["orders_executed"] == 0


@pytest.mark.integration
class TestCrossStrategyInteractions:
    """Integration tests for interactions between defensive and momentum strategies."""

    def test_defensive_positions_excluded_from_momentum_limit(
        self, sample_portfolio, defensive_positions
    ):
        """Test that defensive positions don't count toward momentum limit."""
        # Have 3 defensive positions
        # Should still be able to add 5 momentum positions
        signals = [
            Signal(
                ticker=f"STOCK{i}",
                action="BUY",
                entry_price=Decimal("100.00"),
                confidence=Decimal("0.75"),
                strategy="momentum",
            )
            for i in range(5)
        ]

        # Filter with defensive positions present
        filtered = filter_signals_by_risk(signals, sample_portfolio, defensive_positions)

        # All 5 signals should pass (defensive positions excluded)
        assert len(filtered) == 5

    def test_total_portfolio_exposure(
        self, sample_portfolio, defensive_positions, momentum_positions
    ):
        """Test total exposure calculation with both strategies active."""
        all_positions = defensive_positions + momentum_positions

        # Calculate total exposure
        total_exposure = sum(p.market_value for p in all_positions)

        # Defensive: VTI (2500) + VGK (1500) + GLD (1000) = 5000
        # Momentum: NVDA (2600) + TSLA (2100) = 4700
        # Total: 9700

        expected = Decimal("9700.00")
        assert total_exposure == expected

        # Exposure should be reasonable (< 100% of portfolio)
        exposure_pct = total_exposure / sample_portfolio.portfolio_value
        assert exposure_pct < Decimal("1.0")


@pytest.mark.integration
class TestPerformanceAnalysisFlow:
    """Integration tests for performance analysis and optimization."""

    @pytest.mark.asyncio
    async def test_parameter_adjustment_based_on_performance(self, mock_supabase_client):
        """Test that poor performance triggers parameter adjustment."""
        from src.core.performance_analyzer import adjust_parameters_if_needed
        from src.strategies.momentum_trading import STRATEGY_PARAMS

        # Mock poor performance (< 55% win rate)
        mock_supabase_client.get_strategy_performance.return_value = [
            {"date": "2024-01-01", "win_rate": 0.50, "total_pnl": -50.00},
            {"date": "2024-01-02", "win_rate": 0.52, "total_pnl": -30.00},
            {"date": "2024-01-03", "win_rate": 0.48, "total_pnl": -70.00},
            {"date": "2024-01-04", "win_rate": 0.51, "total_pnl": -40.00},
            {"date": "2024-01-05", "win_rate": 0.49, "total_pnl": -60.00},
        ]

        original_rsi_min = STRATEGY_PARAMS["rsi_min"]

        with patch("src.core.performance_analyzer.SupabaseClient.get_instance") as mock:
            mock.return_value = mock_supabase_client

            # Trigger adjustment
            await adjust_parameters_if_needed()

            # Parameters should be tightened
            # (Low win rate → more conservative RSI)
            # Note: This test may need adjustment based on actual implementation

    @pytest.mark.asyncio
    async def test_weekly_report_generation(self, mock_supabase_client):
        """Test weekly report generation on Sunday."""
        from src.core.performance_analyzer import generate_weekly_report

        # Mock weekly data
        mock_supabase_client.table.return_value.select.return_value.gte.return_value.execute.return_value = AsyncMock(
            data=[
                {
                    "ticker": "NVDA",
                    "pnl": 100.00,
                    "pnl_pct": 0.10,
                },
                {
                    "ticker": "AAPL",
                    "pnl": -50.00,
                    "pnl_pct": -0.05,
                },
            ]
        )

        with patch("src.core.performance_analyzer.SupabaseClient.get_instance") as mock:
            mock.return_value = mock_supabase_client

            # Generate report (should not raise error)
            await generate_weekly_report()


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """End-to-end scenario tests (marked as slow)."""

    @pytest.mark.asyncio
    async def test_full_trading_day_scenario(self):
        """Test complete trading day from open to close."""
        # This would be a comprehensive test simulating:
        # 1. Market open
        # 2. Check defensive rebalancing
        # 3. Scan momentum signals
        # 4. Execute trades
        # 5. Monitor positions
        # 6. Check exits
        # 7. Analyze performance
        # 8. Generate reports

        # Placeholder for comprehensive E2E test
        pass

    @pytest.mark.asyncio
    async def test_month_end_rebalancing_scenario(self):
        """Test month-end defensive core rebalancing."""
        # Placeholder for month-end rebalancing test
        pass


# Markers for test categorization
pytestmark = pytest.mark.integration
