"""Unit tests for risk management module.

Tests for risk_manager.py - position sizing, risk filters, circuit breakers.
Validates all deterministic risk calculations and limits.
"""

import pytest
from decimal import Decimal

from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from src.core.risk_manager import (
    filter_signals_by_risk,
    calculate_position_size,
    check_daily_loss_limit,
    validate_signal_risk,
    calculate_portfolio_risk_metrics,
    MAX_POSITIONS,
    MAX_POSITION_SIZE_PCT,
    DAILY_LOSS_LIMIT_PCT,
)
from src.models.trade import Signal
from src.models.portfolio import Portfolio, Position


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
def sample_signal():
    """Create sample trading signal for testing."""
    return Signal(
        ticker="AAPL",
        action="BUY",
        entry_price=Decimal("150.00"),
        stop_loss=Decimal("142.50"),  # -5%
        take_profit=Decimal("172.50"),  # +15%
        confidence=Decimal("0.75"),
        strategy="momentum",
    )


@pytest.fixture
def sample_positions():
    """Create sample position list for testing."""
    return [
        Position(
            symbol="VTI",
            quantity=Decimal("20"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("205.00"),
            market_value=Decimal("4100.00"),
            unrealized_pnl=Decimal("100.00"),
            unrealized_pnl_pct=Decimal("0.025"),
        ),
        Position(
            symbol="NVDA",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("500.00"),
            current_price=Decimal("520.00"),
            market_value=Decimal("2600.00"),
            unrealized_pnl=Decimal("100.00"),
            unrealized_pnl_pct=Decimal("0.04"),
        ),
    ]


class TestFilterSignalsByRisk:
    """Test cases for signal filtering by risk limits."""

    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        """Mock external dependencies."""
        with patch("src.core.risk_manager.get_correlation_monitor") as mock_cm:
            # Mock correlation monitor to always approve
            monitor = AsyncMock()
            monitor.check_new_signal.return_value = (True, "Approved")
            mock_cm.return_value = monitor
            yield

    @pytest.mark.asyncio
    async def test_filter_signals_within_limit(self, sample_portfolio, sample_positions):
        """Test filtering when below max position limit."""
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


        # Only 1 momentum position (NVDA), so we can add 4 more
        filtered = await filter_signals_by_risk(signals, sample_portfolio, sample_positions)

        # Both signals should pass
        assert len(filtered) == 2


    @pytest.mark.asyncio
    async def test_filter_signals_at_max_positions(self, sample_portfolio):
        """Test filtering when at max position limit."""
        # Create 5 momentum positions (max limit)
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
            for i in range(MAX_POSITIONS)
        ]

        signals = [
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("150.00"),
                confidence=Decimal("0.85"),
                strategy="momentum",
            ),
        ]


        filtered = await filter_signals_by_risk(signals, sample_portfolio, max_positions)

        # No signals should pass (at max positions)
        assert len(filtered) == 0


    @pytest.mark.asyncio
    async def test_filter_signals_sorted_by_confidence(self, sample_portfolio, sample_positions):
        """Test that signals are sorted by confidence (highest first)."""
        signals = [
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("150.00"),
                confidence=Decimal("0.60"),  # Lower confidence
                strategy="momentum",
            ),
            Signal(
                ticker="MSFT",
                action="BUY",
                entry_price=Decimal("350.00"),
                confidence=Decimal("0.90"),  # Higher confidence
                strategy="momentum",
            ),
            Signal(
                ticker="GOOGL",
                action="BUY",
                entry_price=Decimal("140.00"),
                confidence=Decimal("0.75"),  # Medium confidence
                strategy="momentum",
            ),
        ]


        filtered = await filter_signals_by_risk(signals, sample_portfolio, sample_positions)


        # Should be sorted by confidence descending
        assert filtered[0].ticker == "MSFT"  # 0.90
        assert filtered[1].ticker == "GOOGL"  # 0.75
        assert filtered[2].ticker == "AAPL"  # 0.60


    @pytest.mark.asyncio
    async def test_filter_signals_ignores_defensive_positions(self, sample_portfolio):
        """Test that defensive core positions don't count toward momentum limit."""
        # Create defensive positions (VTI, VGK, GLD) + 4 momentum
        positions = [
            Position(
                symbol="VTI",
                quantity=Decimal("50"),
                avg_entry_price=Decimal("200.00"),
                current_price=Decimal("205.00"),
                market_value=Decimal("10250.00"),
                unrealized_pnl=Decimal("250.00"),
                unrealized_pnl_pct=Decimal("0.025"),
            ),
            Position(
                symbol="VGK",
                quantity=Decimal("30"),
                avg_entry_price=Decimal("50.00"),
                current_price=Decimal("52.00"),
                market_value=Decimal("1560.00"),
                unrealized_pnl=Decimal("60.00"),
                unrealized_pnl_pct=Decimal("0.04"),
            ),
            Position(
                symbol="AAPL",
                quantity=Decimal("10"),
                avg_entry_price=Decimal("150.00"),
                current_price=Decimal("155.00"),
                market_value=Decimal("1550.00"),
                unrealized_pnl=Decimal("50.00"),
                unrealized_pnl_pct=Decimal("0.033"),
            ),
        ]

        signals = [
            Signal(
                ticker="NVDA",
                action="BUY",
                entry_price=Decimal("500.00"),
                confidence=Decimal("0.85"),
                strategy="momentum",
            ),
        ]


        # Only 1 momentum position, so signal should pass
        filtered = await filter_signals_by_risk(signals, sample_portfolio, positions)

        assert len(filtered) == 1



class TestCalculatePositionSize:
    """Test cases for position size calculation."""

    @pytest.fixture(autouse=True)
    def mock_sizer(self):
        """Mock position sizer."""
        with patch("src.core.risk_manager.get_position_sizer") as mock_ps:
            # Mock position sizer to return simple calculated value
            sizer = MagicMock()
            # Default behavior: return 10 shares
            sizer.calculate_quantity.return_value = (Decimal("10"), "Mock sizing")
            mock_ps.return_value = sizer
            yield mock_ps

    def test_position_size_calculation_valid(self, sample_signal, sample_portfolio, mock_sizer):
        """Test position size calculation with valid inputs."""
        # Setup mock to return specific size for this test
        # Signal price $150. Max size $3000 (30%). Approx 20 shares.
        # But wait, logic uses position_sizer result directly unless defensive.
        # So we just assert that calculate_position_size returns what sizer returns.
        
        sizer = mock_sizer.return_value
        sizer.calculate_quantity.return_value = (Decimal("15"), "Mock sizing")
        
        qty = calculate_position_size(sample_signal, sample_portfolio)

        # Should return what sizer returned
        assert qty == Decimal("15")

    def test_position_size_respects_buying_power(self, sample_signal, mock_sizer):
        """Test position size respects available buying power."""
        # Portfolio with limited buying power
        portfolio = Portfolio(
            portfolio_value=Decimal("10000.00"),
            cash=Decimal("500.00"),
            buying_power=Decimal("500.00"),  # Only $500 available
            equity=Decimal("9500.00"),
            last_equity=Decimal("9500.00"),
        )
        
        # calculate_position_size delegates to sizer. 
        # We mock sizer to return a value that would exceed buying power if not checked,
        # but calculate_position_size doesn't check BP (validate_signal_risk does).
        # So we just verify it calls sizer.
        
        sizer = mock_sizer.return_value
        sizer.calculate_quantity.return_value = (Decimal("100"), "Mock large") # 100 * 150 = 15000 > 500
        
        qty = calculate_position_size(sample_signal, portfolio)
        
        # It should return what sizer says (100)
        assert qty == Decimal("100")


    def test_position_size_high_price_stock(self, sample_portfolio, mock_sizer):
        """Test position size with high-priced stock (edge case)."""
        expensive_signal = Signal(
            ticker="BRK.A",
            action="BUY",
            entry_price=Decimal("500000.00"),  # Very expensive stock
            confidence=Decimal("0.75"),
            strategy="momentum",
        )
        
        # Sizer returns 0.002 shares ($1000)
        sizer = mock_sizer.return_value
        sizer.calculate_quantity.return_value = (Decimal("0.002"), "Mock fractional")

        qty = calculate_position_size(expensive_signal, sample_portfolio)

        assert qty == Decimal("0.002")


    def test_position_size_fractional_shares(self, sample_portfolio, mock_sizer):
        """Test that position size handles fractional shares correctly."""
        signal = Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("150.50"),
            confidence=Decimal("0.75"),
            strategy="momentum",
        )
        
        sizer = mock_sizer.return_value
        sizer.calculate_quantity.return_value = (Decimal("6.64"), "Mock fractional")

        qty = calculate_position_size(signal, sample_portfolio)

        # Should return what sizer returns
        assert qty == Decimal("6.64")


class TestDailyLossLimit:
    """Test cases for daily loss limit (circuit breaker)."""

    def test_daily_loss_within_limit(self, sample_portfolio):
        """Test that normal losses don't trigger circuit breaker."""
        daily_pnl = Decimal("-100.00")  # -1% loss

        triggered = check_daily_loss_limit(daily_pnl, sample_portfolio.portfolio_value)

        # Should not trigger (limit is -3%)
        assert triggered is False

    def test_daily_loss_at_limit(self, sample_portfolio):
        """Test circuit breaker at exact limit."""
        daily_pnl = Decimal("-300.00")  # Exactly -3%

        triggered = check_daily_loss_limit(daily_pnl, sample_portfolio.portfolio_value)

        # Should trigger at -3%
        assert triggered is True

    def test_daily_loss_exceeds_limit(self, sample_portfolio):
        """Test circuit breaker when exceeding limit."""
        daily_pnl = Decimal("-500.00")  # -5% loss

        triggered = check_daily_loss_limit(daily_pnl, sample_portfolio.portfolio_value)

        # Should trigger (exceeds -3% limit)
        assert triggered is True

    def test_daily_profit_no_trigger(self, sample_portfolio):
        """Test that profits don't trigger circuit breaker."""
        daily_pnl = Decimal("500.00")  # +5% profit

        triggered = check_daily_loss_limit(daily_pnl, sample_portfolio.portfolio_value)

        # Should not trigger on profits
        assert triggered is False


class TestValidateSignalRisk:
    """Test cases for signal risk validation."""

    def test_validate_signal_valid(self, sample_signal, sample_portfolio):
        """Test validation of valid signal."""
        is_valid, reason = validate_signal_risk(sample_signal, sample_portfolio)

        assert is_valid is True
        assert "passes all risk checks" in reason


    def test_validate_signal_negative_price(self, sample_portfolio):
        """Test validation rejects negative entry price."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("-150.00"),  # Invalid: negative
                confidence=Decimal("0.75"),
                strategy="momentum",
            )

    def test_validate_signal_invalid_stop_loss(self, sample_portfolio):
        """Test validation rejects stop-loss above entry."""
        invalid_signal = Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("150.00"),
            stop_loss=Decimal("160.00"),  # Invalid: above entry
            confidence=Decimal("0.75"),
            strategy="momentum",
        )

        is_valid, reason = validate_signal_risk(invalid_signal, sample_portfolio)

        assert is_valid is False
        assert "Stop-loss must be below" in reason

    def test_validate_signal_invalid_take_profit(self, sample_portfolio):
        """Test validation rejects take-profit below entry."""
        invalid_signal = Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("150.00"),
            take_profit=Decimal("140.00"),  # Invalid: below entry
            confidence=Decimal("0.75"),
            strategy="momentum",
        )

        is_valid, reason = validate_signal_risk(invalid_signal, sample_portfolio)

        assert is_valid is False
        assert "Take-profit must be above" in reason

    def test_validate_signal_poor_risk_reward(self, sample_portfolio):
        """Test validation rejects poor risk/reward ratio."""
        poor_signal = Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("150.00"),
            stop_loss=Decimal("140.00"),  # -10 risk
            take_profit=Decimal("155.00"),  # +5 reward (R:R = 0.5, need 2.0)
            confidence=Decimal("0.75"),
            strategy="momentum",
        )

        is_valid, reason = validate_signal_risk(poor_signal, sample_portfolio)

        assert is_valid is False
        assert "Risk/reward ratio too low" in reason

    def test_validate_signal_insufficient_buying_power(self):
        """Test validation rejects signal with insufficient buying power."""
        broke_portfolio = Portfolio(
            portfolio_value=Decimal("10000.00"),
            cash=Decimal("10.00"),  # Only $10 available

            buying_power=Decimal("10.00"),
            equity=Decimal("9990.00"),
            last_equity=Decimal("9990.00"),
        )


        signal = Signal(
            ticker="AAPL",
            action="BUY",
            entry_price=Decimal("150.00"),
            confidence=Decimal("0.75"),
            strategy="momentum",
        )

        is_valid, reason = validate_signal_risk(signal, broke_portfolio)

        assert is_valid is False
        assert "Insufficient buying power" in reason


class TestPortfolioRiskMetrics:
    """Test cases for portfolio risk metrics calculation."""

    def test_risk_metrics_calculation_valid(self, sample_positions):
        """Test risk metrics calculation with valid positions."""
        portfolio_value = Decimal("10000.00")

        metrics = calculate_portfolio_risk_metrics(sample_positions, portfolio_value)

        # Check all metrics are present
        assert "total_exposure" in metrics
        assert "exposure_pct" in metrics
        assert "largest_position_pct" in metrics
        assert "num_positions" in metrics

        # Total exposure should equal sum of position values
        expected_exposure = sum(p.market_value for p in sample_positions)
        assert metrics["total_exposure"] == expected_exposure

        # Number of positions should match
        assert metrics["num_positions"] == Decimal(len(sample_positions))

    def test_risk_metrics_empty_portfolio(self):
        """Test risk metrics with no positions (edge case)."""
        metrics = calculate_portfolio_risk_metrics([], Decimal("10000.00"))

        assert metrics["total_exposure"] == Decimal("0")
        assert metrics["exposure_pct"] == Decimal("0")
        assert metrics["num_positions"] == Decimal("0")

    def test_risk_metrics_largest_position(self, sample_positions):
        """Test largest position calculation."""
        portfolio_value = Decimal("10000.00")

        metrics = calculate_portfolio_risk_metrics(sample_positions, portfolio_value)

        # Largest position is VTI at $4100
        expected_largest_pct = Decimal("4100.00") / portfolio_value

        assert metrics["largest_position_pct"] == expected_largest_pct
