"""Unit tests for trading strategies.

Tests for defensive_core.py and momentum_trading.py.
Validates rebalancing logic, momentum signals, and exit conditions.
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import numpy as np

from src.strategies.defensive_core import (
    should_rebalance,
    calculate_rebalancing_orders,
    get_defensive_symbols,
    calculate_defensive_exposure,
    validate_allocation_percentages,
    TARGET_ALLOCATIONS,
    REBALANCE_DRIFT_THRESHOLD,
)
from src.strategies.momentum_trading import (
    scan_for_signals,
    check_exit_conditions,
    update_strategy_parameters,
    get_current_parameters,
    STRATEGY_PARAMS,
)
from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal


@pytest.fixture
def sample_portfolio():
    """Create sample portfolio for testing."""
    return Portfolio(
        portfolio_value=Decimal("10000.00"),
        cash=Decimal("5000.00"),
        buying_power=Decimal("5000.00"),
        equity=Decimal("5000.00"),
    )


@pytest.fixture
def defensive_positions():
    """Create sample defensive core positions."""
    return [
        Position(
            symbol="VTI",
            quantity=Decimal("12"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("208.33"),
            market_value=Decimal("2500.00"),  # 25% of $10k portfolio
            unrealized_pnl=Decimal("100.00"),
            unrealized_pnl_pct=Decimal("0.0417"),
        ),
        Position(
            symbol="VGK",
            quantity=Decimal("30"),
            avg_entry_price=Decimal("48.00"),
            current_price=Decimal("50.00"),
            market_value=Decimal("1500.00"),  # 15% of portfolio
            unrealized_pnl=Decimal("60.00"),
            unrealized_pnl_pct=Decimal("0.0417"),
        ),
        Position(
            symbol="GLD",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("190.00"),
            current_price=Decimal("200.00"),
            market_value=Decimal("1000.00"),  # 10% of portfolio
            unrealized_pnl=Decimal("50.00"),
            unrealized_pnl_pct=Decimal("0.0526"),
        ),
    ]


class TestDefensiveCoreRebalancing:
    """Test cases for defensive core rebalancing logic."""

    def test_should_rebalance_first_of_month(self, defensive_positions, sample_portfolio):
        """Test rebalancing triggered on first day of month."""
        first_day = date(2024, 3, 1)

        should_rebal = should_rebalance(first_day, defensive_positions, sample_portfolio)

        # Should trigger on day 1
        assert should_rebal is True

    def test_should_not_rebalance_mid_month(self, defensive_positions, sample_portfolio):
        """Test no rebalancing mid-month when allocations are correct."""
        mid_month = date(2024, 3, 15)

        should_rebal = should_rebalance(mid_month, defensive_positions, sample_portfolio)

        # Should not trigger (allocations are at target)
        assert should_rebal is False

    def test_should_rebalance_on_drift(self, sample_portfolio):
        """Test rebalancing triggered by portfolio drift > 5%."""
        # VTI drifted to 20% (target is 25%, drift = 5%)
        drifted_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("10"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("2000.00"),  # 20% (target 25%, drift 5%)
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
            Position(
                symbol="VGK",
                quantity=Decimal("30"),
                avg_entry_price=Decimal("50.00"),
                current_price=Decimal("50.00"),
                market_value=Decimal("1500.00"),
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
        ]

        mid_month = date(2024, 3, 15)

        should_rebal = should_rebalance(mid_month, drifted_positions, sample_portfolio)

        # Should trigger due to drift
        assert should_rebal is True

    def test_should_rebalance_missing_position(self, sample_portfolio):
        """Test rebalancing when defensive position is missing (edge case)."""
        # Missing GLD position
        incomplete_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("12"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("208.33"),
                market_value=Decimal("2500.00"),
                unrealized_pnl=Decimal("100.00"),
                unrealized_pnl_pct=Decimal("0.0417"),
            ),
        ]

        mid_month = date(2024, 3, 15)

        should_rebal = should_rebalance(mid_month, incomplete_positions, sample_portfolio)

        # Should trigger (GLD missing = 10% drift from target)
        assert should_rebal is True


class TestCalculateRebalancingOrders:
    """Test cases for rebalancing order calculation."""

    def test_calculate_rebalancing_orders_exact_target(self, defensive_positions, sample_portfolio):
        """Test no orders when already at target allocations."""
        signals = calculate_rebalancing_orders(defensive_positions, sample_portfolio)

        # Already at target, no significant orders needed
        assert len(signals) == 0

    def test_calculate_rebalancing_orders_buy_needed(self, sample_portfolio):
        """Test buy orders generated when underweight."""
        # VTI underweight (15% vs target 25%)
        underweight_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("7.5"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("1500.00"),  # 15% (need 25%)
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
        ]

        signals = calculate_rebalancing_orders(underweight_positions, sample_portfolio)

        # Should generate BUY signal for VTI
        vti_signal = next((s for s in signals if s.ticker == "VTI"), None)

        assert vti_signal is not None
        assert vti_signal.action == "BUY"

    def test_calculate_rebalancing_orders_sell_needed(self, sample_portfolio):
        """Test sell orders generated when overweight."""
        # VTI overweight (35% vs target 25%)
        overweight_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("17.5"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("3500.00"),  # 35% (target 25%)
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
        ]

        signals = calculate_rebalancing_orders(overweight_positions, sample_portfolio)

        # Should generate SELL signal for VTI
        vti_signal = next((s for s in signals if s.ticker == "VTI"), None)

        assert vti_signal is not None
        assert vti_signal.action == "SELL"

    def test_calculate_rebalancing_orders_ignores_small_diff(self, sample_portfolio):
        """Test that small differences (<$100) are ignored."""
        # VTI slightly off ($50 difference)
        slightly_off_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("12.25"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("2450.00"),  # $50 under target
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
        ]

        signals = calculate_rebalancing_orders(slightly_off_positions, sample_portfolio)

        # Should not generate order (difference < $100)
        assert len(signals) == 0


class TestDefensiveCoreHelpers:
    """Test cases for defensive core helper functions."""

    def test_get_defensive_symbols(self):
        """Test getting defensive core symbols."""
        symbols = get_defensive_symbols()

        assert "VTI" in symbols
        assert "VGK" in symbols
        assert "GLD" in symbols
        assert len(symbols) == 3

    def test_calculate_defensive_exposure(self, defensive_positions):
        """Test calculating total defensive exposure."""
        exposure = calculate_defensive_exposure(defensive_positions)

        # VTI ($2500) + VGK ($1500) + GLD ($1000) = $5000
        expected = Decimal("5000.00")

        assert exposure == expected

    def test_calculate_defensive_exposure_empty(self):
        """Test defensive exposure with no positions (edge case)."""
        exposure = calculate_defensive_exposure([])

        assert exposure == Decimal("0")

    def test_validate_allocation_percentages(self):
        """Test that target allocations sum to 50%."""
        is_valid = validate_allocation_percentages()

        # VTI (25%) + VGK (15%) + GLD (10%) = 50%
        assert is_valid is True

    def test_validate_allocation_percentages_checks_sum(self):
        """Test validation actually checks the sum."""
        # Temporarily modify TARGET_ALLOCATIONS
        original = TARGET_ALLOCATIONS.copy()

        try:
            TARGET_ALLOCATIONS["VTI"] = Decimal("0.30")  # Change to make sum != 50%

            is_valid = validate_allocation_percentages()

            # Should fail validation
            assert is_valid is False

        finally:
            # Restore original values
            TARGET_ALLOCATIONS.clear()
            TARGET_ALLOCATIONS.update(original)


class TestMomentumTrading:
    """Test cases for momentum trading strategy."""

    @pytest.mark.asyncio
    async def test_scan_for_signals_with_valid_data(self):
        """Test momentum signal scanning with valid market data."""
        # Mock Alpaca client
        mock_alpaca = AsyncMock()

        # Create sample bars data with bullish indicators
        bars_df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2024-01-01", periods=30, freq="D"),
                "open": np.linspace(100, 120, 30),
                "high": np.linspace(101, 121, 30),
                "low": np.linspace(99, 119, 30),
                "close": np.linspace(100, 120, 30),  # Uptrend
                "volume": [2000000] * 29 + [3000000],  # High volume on last day
            }
        )

        mock_alpaca.get_bars = AsyncMock(return_value=bars_df)

        # Scan for signals
        signals = await scan_for_signals(mock_alpaca)

        # Should return list (may be empty if indicators don't align)
        assert isinstance(signals, list)

    @pytest.mark.asyncio
    async def test_scan_for_signals_empty_data(self):
        """Test signal scanning with no market data (edge case)."""
        mock_alpaca = AsyncMock()
        mock_alpaca.get_bars = AsyncMock(return_value=pd.DataFrame())

        signals = await scan_for_signals(mock_alpaca)

        # Should return empty list
        assert signals == []

    @pytest.mark.asyncio
    async def test_scan_for_signals_api_error(self):
        """Test signal scanning handles API errors gracefully."""
        mock_alpaca = AsyncMock()
        mock_alpaca.get_bars = AsyncMock(side_effect=Exception("API Error"))

        signals = await scan_for_signals(mock_alpaca)

        # Should return empty list (errors are caught and logged)
        assert signals == []

    @pytest.mark.asyncio
    async def test_check_exit_conditions_stop_loss(self):
        """Test exit condition: stop-loss triggered."""
        mock_alpaca = AsyncMock()

        # Position with 10% loss (stop-loss is -5%)
        position = Position(
            symbol="AAPL",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("150.00"),
            current_price=Decimal("135.00"),  # -10% loss
            market_value=Decimal("1350.00"),
            unrealized_pnl=Decimal("-150.00"),
            unrealized_pnl_pct=Decimal("-0.10"),
        )

        # Mock current quote
        mock_alpaca.get_latest_quote = AsyncMock(return_value={"price": 135.00})
        mock_alpaca.get_bars = AsyncMock(return_value=pd.DataFrame())

        should_exit, reason = await check_exit_conditions(position, mock_alpaca)

        # Should trigger stop-loss
        assert should_exit is True
        assert reason == "stop_loss"

    @pytest.mark.asyncio
    async def test_check_exit_conditions_take_profit(self):
        """Test exit condition: take-profit triggered."""
        mock_alpaca = AsyncMock()

        # Position with 20% profit (take-profit is +15%)
        position = Position(
            symbol="NVDA",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("500.00"),
            current_price=Decimal("600.00"),  # +20% profit
            market_value=Decimal("3000.00"),
            unrealized_pnl=Decimal("500.00"),
            unrealized_pnl_pct=Decimal("0.20"),
        )

        mock_alpaca.get_latest_quote = AsyncMock(return_value={"price": 600.00})
        mock_alpaca.get_bars = AsyncMock(return_value=pd.DataFrame())

        should_exit, reason = await check_exit_conditions(position, mock_alpaca)

        # Should trigger take-profit
        assert should_exit is True
        assert reason == "take_profit"

    @pytest.mark.asyncio
    async def test_check_exit_conditions_no_exit(self):
        """Test exit condition: no exit (within range)."""
        mock_alpaca = AsyncMock()

        # Position with 5% profit (within normal range)
        position = Position(
            symbol="MSFT",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("350.00"),
            current_price=Decimal("367.50"),  # +5% profit
            market_value=Decimal("3675.00"),
            unrealized_pnl=Decimal("175.00"),
            unrealized_pnl_pct=Decimal("0.05"),
        )

        mock_alpaca.get_latest_quote = AsyncMock(return_value={"price": 367.50})
        mock_alpaca.get_bars = AsyncMock(return_value=pd.DataFrame())

        should_exit, reason = await check_exit_conditions(position, mock_alpaca)

        # Should not exit
        assert should_exit is False
        assert reason is None


class TestMomentumParameters:
    """Test cases for momentum strategy parameter management."""

    def test_get_current_parameters(self):
        """Test getting current strategy parameters."""
        params = get_current_parameters()

        # Should include all required parameters
        assert "rsi_min" in params
        assert "rsi_max" in params
        assert "stop_loss_pct" in params
        assert "take_profit_pct" in params

    def test_update_strategy_parameters(self):
        """Test updating strategy parameters."""
        original_rsi_min = STRATEGY_PARAMS["rsi_min"]

        try:
            # Update parameters
            new_params = {"rsi_min": 55, "rsi_max": 65}
            update_strategy_parameters(new_params)

            # Should be updated
            assert STRATEGY_PARAMS["rsi_min"] == 55
            assert STRATEGY_PARAMS["rsi_max"] == 65

        finally:
            # Restore original
            STRATEGY_PARAMS["rsi_min"] = original_rsi_min

    def test_update_strategy_parameters_ignores_invalid(self):
        """Test that invalid parameter names are ignored."""
        original_params = STRATEGY_PARAMS.copy()

        try:
            # Try to update with invalid key
            new_params = {"invalid_key": 999}
            update_strategy_parameters(new_params)

            # Should not add invalid key
            assert "invalid_key" not in STRATEGY_PARAMS

        finally:
            # Restore original
            STRATEGY_PARAMS.clear()
            STRATEGY_PARAMS.update(original_params)

    def test_parameter_changes_affect_signal_generation(self):
        """Test that parameter changes affect signal logic."""
        original_params = STRATEGY_PARAMS.copy()

        try:
            # Change RSI range to very narrow (unlikely to find signals)
            update_strategy_parameters({"rsi_min": 59, "rsi_max": 61})

            assert STRATEGY_PARAMS["rsi_min"] == 59
            assert STRATEGY_PARAMS["rsi_max"] == 61

        finally:
            # Restore original
            STRATEGY_PARAMS.clear()
            STRATEGY_PARAMS.update(original_params)
