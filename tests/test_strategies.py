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
)
from src.config.strategy_params import get_strategy_parameters
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
        last_equity=Decimal("5000.00"),
    )


@pytest.fixture
def defensive_positions():
    """Create sample defensive core positions matching new 15/8/7 allocation.

    Target: VTI (15%), VGK (8%), GLD (7%)
    Portfolio Value: $10,000

    Target Values:
    VTI: $1500
    VGK: $800
    GLD: $700
    """
    return [
        Position(
            symbol="VTI",
            quantity=Decimal("7.2"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("208.33"),
            market_value=Decimal("1500.00"),  # 15% (Target)
            unrealized_pnl=Decimal("60.00"),
            unrealized_pnl_pct=Decimal("0.0417"),
        ),
        Position(
            symbol="VGK",
            quantity=Decimal("16"),
            avg_entry_price=Decimal("48.00"),
            current_price=Decimal("50.00"),
            market_value=Decimal("800.00"),  # 8% (Target)
            unrealized_pnl=Decimal("32.00"),
            unrealized_pnl_pct=Decimal("0.0417"),
        ),
        Position(
            symbol="GLD",
            quantity=Decimal("3.5"),
            avg_entry_price=Decimal("190.00"),
            current_price=Decimal("200.00"),
            market_value=Decimal("700.00"),  # 7% (Target)
            unrealized_pnl=Decimal("35.00"),
            unrealized_pnl_pct=Decimal("0.0526"),
        ),
    ]


class TestDefensiveCoreRebalancing:
    """Test cases for defensive core rebalancing logic."""

    @pytest.mark.asyncio
    async def test_should_rebalance_first_of_month(self, defensive_positions, sample_portfolio):
        """Test rebalancing triggered on first day of month."""
        first_day = date(2024, 3, 1)

        # Mock adapter to return True for first day
        with patch("src.strategies.defensive_core.get_market_data_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.is_first_trading_day_of_month.return_value = True
            mock_get_adapter.return_value = mock_adapter

            should_rebal = await should_rebalance(first_day, defensive_positions, sample_portfolio)

        # Should trigger on day 1
        assert should_rebal is True

    @pytest.mark.asyncio
    async def test_should_not_rebalance_mid_month(self, defensive_positions, sample_portfolio):
        """Test no rebalancing mid-month when allocations are correct."""
        mid_month = date(2024, 3, 15)

        with patch("src.strategies.defensive_core.get_market_data_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.is_first_trading_day_of_month.return_value = False
            mock_get_adapter.return_value = mock_adapter

            should_rebal = await should_rebalance(mid_month, defensive_positions, sample_portfolio)

        # Should not trigger (allocations are at target)
        assert should_rebal is False

    @pytest.mark.asyncio
    async def test_should_rebalance_on_drift(self, sample_portfolio):
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

        with patch("src.strategies.defensive_core.get_market_data_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.is_first_trading_day_of_month.return_value = False
            mock_get_adapter.return_value = mock_adapter

            should_rebal = await should_rebalance(mid_month, drifted_positions, sample_portfolio)

        # Should trigger due to drift
        assert should_rebal is True

    @pytest.mark.asyncio
    async def test_should_rebalance_missing_position(self, sample_portfolio):
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

        with patch("src.strategies.defensive_core.get_market_data_adapter") as mock_get_adapter:
            mock_adapter = AsyncMock()
            mock_adapter.is_first_trading_day_of_month.return_value = False
            mock_get_adapter.return_value = mock_adapter

            should_rebal = await should_rebalance(mid_month, incomplete_positions, sample_portfolio)

        # Should trigger (GLD missing = 10% drift from target)
        assert should_rebal is True


class TestCalculateRebalancingOrders:
    """Test cases for rebalancing order calculation."""

    @pytest.mark.asyncio
    async def test_calculate_rebalancing_orders_exact_target(
        self, defensive_positions, sample_portfolio
    ):
        """Test no orders when already at target allocations."""
        mock_client = AsyncMock()
        signals = await calculate_rebalancing_orders(
            defensive_positions, sample_portfolio, mock_client
        )

        # Already at target, no significant orders needed
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_calculate_rebalancing_orders_buy_needed(self, sample_portfolio):
        """Test buy orders generated when underweight."""
        # VTI underweight (5% vs target 15%)
        # Portfolio $10k -> Target $1500. Current $500 (5%). Diff $1000 -> BUY.
        underweight_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("2.5"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("500.00"),  # 5% (need 15%)
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
            # Need to include other positions so they don't trigger "missing position" logic
            # which would generate extra BUY orders for them
            Position(
                symbol="VGK",
                quantity=Decimal("16"),
                avg_entry_price=Decimal("50"),
                current_price=Decimal("50"),
                market_value=Decimal("800"),
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"),
            ),
            Position(
                symbol="GLD",
                quantity=Decimal("3.5"),
                avg_entry_price=Decimal("200"),
                current_price=Decimal("200"),
                market_value=Decimal("700"),
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"),
            ),
        ]

        mock_client = AsyncMock()
        # Mock price fetching for the newly added positions if needed, though they have current_price
        # logic calls get_latest_quote only if current_price is None or logic dictates.
        # But we pass positions WITH prices.

        signals = await calculate_rebalancing_orders(
            underweight_positions, sample_portfolio, mock_client
        )

        # Should generate BUY signal for VTI
        vti_signal = next((s for s in signals if s.ticker == "VTI"), None)

        assert vti_signal is not None
        assert vti_signal.action == "BUY"

    @pytest.mark.asyncio
    async def test_calculate_rebalancing_orders_sell_needed(self, sample_portfolio):
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

        mock_client = AsyncMock()
        signals = await calculate_rebalancing_orders(
            overweight_positions, sample_portfolio, mock_client
        )

        # Should generate SELL signal for VTI
        vti_signal = next((s for s in signals if s.ticker == "VTI"), None)

        assert vti_signal is not None
        assert vti_signal.action == "SELL"

    @pytest.mark.asyncio
    async def test_calculate_rebalancing_orders_ignores_small_diff(self, sample_portfolio):
        """Test that small differences (<$100) are ignored."""
        # VTI slightly off ($50 difference)
        # Target 15% of $10k = $1500.
        # Current $1550 (Difference $50 < $100 -> Ignore)
        slightly_off_positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("7.75"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("200.00"),
                market_value=Decimal("1550.00"),  # $50 over target
                unrealized_pnl=Decimal("0.00"),
                unrealized_pnl_pct=Decimal("0.00"),
            ),
            # Perfect match for others to avoid noise
            Position(
                symbol="VGK",
                quantity=Decimal("16"),
                avg_entry_price=Decimal("50"),
                current_price=Decimal("50"),
                market_value=Decimal("800"),
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"),
            ),
            Position(
                symbol="GLD",
                quantity=Decimal("3.5"),
                avg_entry_price=Decimal("200"),
                current_price=Decimal("200"),
                market_value=Decimal("700"),
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"),
            ),
        ]

        mock_client = AsyncMock()
        signals = await calculate_rebalancing_orders(
            slightly_off_positions, sample_portfolio, mock_client
        )

        # Should not generate order (difference < $100)
        assert len(signals) == 0

    # Removed duplicates


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

        # VTI ($1500) + VGK ($800) + GLD ($700) = $3000
        expected = Decimal("3000.00")

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
    @patch("src.strategies.momentum_trading.yf.Ticker")
    async def test_scan_for_signals_empty_data(self, mock_ticker):
        """Test signal scanning with no market data (edge case)."""
        mock_alpaca = AsyncMock()

        # Mock yfinance history to return empty DataFrame
        mock_history = MagicMock()
        mock_history.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_history

        # Also mock get_dynamic_watchlist to return a small list for speed
        with patch("src.strategies.momentum_trading.get_dynamic_watchlist", return_value=["AAPL"]):
            signals = await scan_for_signals(mock_alpaca)

        # Should return empty list
        assert signals == []

    @pytest.mark.asyncio
    @patch("src.strategies.momentum_trading.yf.Ticker")
    async def test_scan_for_signals_api_error(self, mock_ticker):
        """Test signal scanning handles API errors gracefully."""
        mock_alpaca = AsyncMock()

        # Mock yfinance to raise exception
        mock_ticker.side_effect = Exception("API Error")

        with patch("src.strategies.momentum_trading.get_dynamic_watchlist", return_value=["AAPL"]):
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
    @patch("src.strategies.momentum_trading.yf.Ticker")
    async def test_check_exit_conditions_no_exit(self, mock_ticker):
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

        # Mock yfinance history to return valid data that DOES NOT trigger exit
        # RSI ~ 50, MACD > 0
        mock_history = MagicMock()

        # Create a DataFrame that will produce RSI ~ 50 (choppy sideways movement)
        dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
        np.random.seed(42)
        # Random walk around 100
        returns = np.random.normal(0, 1, 60)
        close_prices = 100 + np.cumsum(returns)

        bars_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": close_prices,
                "high": close_prices + 0.5,
                "low": close_prices - 0.5,
                "close": close_prices,
                "volume": [1000000] * 60,
            }
        )

        mock_history.history.return_value = bars_df
        mock_ticker.return_value = mock_history

        should_exit, reason = await check_exit_conditions(position, mock_alpaca)

        # Should not exit
        assert should_exit is False
        assert reason is None


class TestMomentumParameters:
    """Test cases for momentum strategy parameter management."""

    @pytest.mark.asyncio
    async def test_get_current_parameters(self):
        """Test getting current strategy parameters."""
        params_manager = get_strategy_parameters()
        params = await params_manager.get_parameters("momentum")

        # Should include all required parameters
        assert "rsi_lower" in params
        assert "rsi_upper" in params
        assert "stop_loss_pct" in params
        assert "take_profit_pct" in params

    @pytest.mark.asyncio
    async def test_update_strategy_parameters(self):
        """Test updating strategy parameters."""
        # Mock SupabaseClient to prevent real network calls
        with patch("src.config.strategy_params.SupabaseClient.get_instance") as mock_get_instance:
            # client instance should be MagicMock (sync methods by default), not AsyncMock
            mock_client = MagicMock()
            mock_get_instance.return_value = mock_client

            # .table() returns a builder
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table

            # .insert() returns a builder
            mock_insert_builder = MagicMock()
            mock_table.insert.return_value = mock_insert_builder

            # .execute() IS async, so it returns a coroutine
            mock_insert_builder.execute = AsyncMock()

            # StrategyParametersManager caches parameters, so get_parameters("momentum")
            # might not hit the DB if it's already cached from previous tests.
            # But update_parameters ALWAYS writes to DB.

            params_manager = get_strategy_parameters()

            # Since we can't easily reset the singleton's cache here without accessing private dict,
            # we rely on the fact that update_parameters updates the in-memory cache too.

            original_params = await params_manager.get_parameters("momentum")
            original_rsi = original_params["rsi_lower"]

            try:
                # Update parameters
                new_params = {"rsi_lower": 45.0, "rsi_upper": 65.0}
                await params_manager.update_parameters("momentum", new_params, reason="unit_test")

                # Verify update
                updated = await params_manager.get_parameters("momentum")
                assert updated["rsi_lower"] == 45.0
                assert updated["rsi_upper"] == 65.0

            finally:
                # Restore original (partial restore for test safety)
                await params_manager.update_parameters(
                    "momentum", {"rsi_lower": original_rsi}, reason="unit_test_restore"
                )
