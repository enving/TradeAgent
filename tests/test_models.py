"""Unit tests for Pydantic models.

Tests for portfolio.py, trade.py, and performance.py models.
Validates data validation, serialization, and edge cases.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
from pydantic import ValidationError

from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal, Trade
from src.models.performance import (
    DailyPerformance,
    StrategyMetrics,
    ParameterChange,
    WeeklyReport,
)


class TestPortfolioModel:
    """Test cases for Portfolio model."""

    def test_portfolio_creation_valid(self):
        """Test valid portfolio creation with all required fields."""
        portfolio = Portfolio(
            portfolio_value=Decimal("10000.00"),
            cash=Decimal("5000.00"),
            buying_power=Decimal("5000.00"),
            equity=Decimal("5000.00"),
        )

        assert portfolio.portfolio_value == Decimal("10000.00")
        assert portfolio.cash == Decimal("5000.00")
        assert portfolio.buying_power == Decimal("5000.00")

    def test_portfolio_negative_values_invalid(self):
        """Test that negative portfolio values are rejected."""
        with pytest.raises(ValidationError):
            Portfolio(
                portfolio_value=Decimal("-1000.00"),  # Invalid: negative
                cash=Decimal("5000.00"),
                buying_power=Decimal("5000.00"),
                equity=Decimal("5000.00"),
            )

    def test_portfolio_zero_values_valid(self):
        """Test that zero portfolio values are accepted (edge case)."""
        portfolio = Portfolio(
            portfolio_value=Decimal("0.00"),
            cash=Decimal("0.00"),
            buying_power=Decimal("0.00"),
            equity=Decimal("0.00"),
        )

        assert portfolio.portfolio_value == Decimal("0.00")


class TestPositionModel:
    """Test cases for Position model."""

    def test_position_creation_valid(self):
        """Test valid position creation."""
        position = Position(
            symbol="AAPL",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            market_value=Decimal("1550.00"),
            unrealized_pnl=Decimal("50.00"),
            unrealized_pnl_pct=Decimal("0.0333"),
        )

        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("10")
        assert position.unrealized_pnl == Decimal("50.00")

    def test_position_negative_quantity_invalid(self):
        """Test that negative quantity is rejected."""
        with pytest.raises(ValidationError):
            Position(
                symbol="AAPL",
                quantity=Decimal("-10"),  # Invalid: negative
                avg_entry_price=Decimal("150.00"),
                current_price=Decimal("155.00"),
                market_value=Decimal("1550.00"),
                unrealized_pnl=Decimal("50.00"),
                unrealized_pnl_pct=Decimal("0.0333"),
            )

    def test_position_zero_price_invalid(self):
        """Test that zero or negative prices are rejected."""
        with pytest.raises(ValidationError):
            Position(
                symbol="AAPL",
                quantity=Decimal("10"),
                avg_entry_price=Decimal("0.00"),  # Invalid: must be > 0
                current_price=Decimal("155.00"),
                market_value=Decimal("1550.00"),
                unrealized_pnl=Decimal("50.00"),
                unrealized_pnl_pct=Decimal("0.0333"),
            )


class TestSignalModel:
    """Test cases for Signal model."""

    def test_signal_creation_valid(self):
        """Test valid signal creation with required fields."""
        signal = Signal(
            ticker="NVDA",
            action="BUY",
            entry_price=Decimal("500.00"),
            confidence=Decimal("0.75"),
            strategy="momentum",
        )

        assert signal.ticker == "NVDA"
        assert signal.action == "BUY"
        assert signal.strategy == "momentum"

    def test_signal_with_stop_loss_take_profit(self):
        """Test signal with optional stop-loss and take-profit."""
        signal = Signal(
            ticker="TSLA",
            action="BUY",
            entry_price=Decimal("200.00"),
            stop_loss=Decimal("190.00"),
            take_profit=Decimal("230.00"),
            confidence=Decimal("0.85"),
            strategy="momentum",
        )

        assert signal.stop_loss == Decimal("190.00")
        assert signal.take_profit == Decimal("230.00")

    def test_signal_invalid_action(self):
        """Test that invalid action values are rejected."""
        with pytest.raises(ValidationError):
            Signal(
                ticker="AAPL",
                action="INVALID_ACTION",  # Invalid: must be BUY, SELL, or HOLD
                entry_price=Decimal("150.00"),
                confidence=Decimal("0.75"),
                strategy="momentum",
            )

    def test_signal_confidence_out_of_range(self):
        """Test that confidence outside 0-1 range is rejected."""
        with pytest.raises(ValidationError):
            Signal(
                ticker="AAPL",
                action="BUY",
                entry_price=Decimal("150.00"),
                confidence=Decimal("1.5"),  # Invalid: must be 0-1
                strategy="momentum",
            )


class TestTradeModel:
    """Test cases for Trade model."""

    def test_trade_creation_valid(self):
        """Test valid trade creation."""
        trade = Trade(
            date=datetime.now(),
            ticker="META",
            action="BUY",
            quantity=Decimal("15"),
            entry_price=Decimal("300.00"),
            strategy="momentum",
        )

        assert trade.ticker == "META"
        assert trade.action == "BUY"
        assert trade.quantity == Decimal("15")

    def test_trade_with_exit_data(self):
        """Test trade with exit price and P&L."""
        trade = Trade(
            date=datetime.now(),
            ticker="GOOGL",
            action="SELL",
            quantity=Decimal("10"),
            entry_price=Decimal("140.00"),
            exit_price=Decimal("150.00"),
            pnl=Decimal("100.00"),
            pnl_pct=Decimal("0.0714"),
            strategy="momentum",
            exit_reason="take_profit",
        )

        assert trade.exit_price == Decimal("150.00")
        assert trade.pnl == Decimal("100.00")
        assert trade.exit_reason == "take_profit"

    def test_trade_negative_quantity_invalid(self):
        """Test that negative quantity is rejected."""
        with pytest.raises(ValidationError):
            Trade(
                date=datetime.now(),
                ticker="AAPL",
                action="BUY",
                quantity=Decimal("-5"),  # Invalid: negative
                entry_price=Decimal("150.00"),
                strategy="momentum",
            )


class TestPerformanceModels:
    """Test cases for performance tracking models."""

    def test_daily_performance_creation_valid(self):
        """Test valid daily performance creation."""
        daily_perf = DailyPerformance(
            date=date.today(),
            total_trades=10,
            winning_trades=7,
            losing_trades=3,
            win_rate=Decimal("0.70"),
            daily_pnl=Decimal("250.00"),
            profit_factor=Decimal("2.5"),
            avg_win=Decimal("50.00"),
            avg_loss=Decimal("-20.00"),
        )

        assert daily_perf.total_trades == 10
        assert daily_perf.win_rate == Decimal("0.70")
        assert daily_perf.profit_factor == Decimal("2.5")

    def test_strategy_metrics_creation_valid(self):
        """Test valid strategy metrics creation."""
        metrics = StrategyMetrics(
            strategy="momentum",
            date=date.today(),
            total_trades=5,
            win_rate=Decimal("0.60"),
            total_pnl=Decimal("100.00"),
        )

        assert metrics.strategy == "momentum"
        assert metrics.win_rate == Decimal("0.60")

    def test_parameter_change_creation_valid(self):
        """Test valid parameter change logging."""
        change = ParameterChange(
            date=date.today(),
            reason="Low win rate: 52%",
            old_params={"rsi_min": 50, "rsi_max": 70},
            new_params={"rsi_min": 55, "rsi_max": 65},
        )

        assert change.reason == "Low win rate: 52%"
        assert change.old_params["rsi_min"] == 50
        assert change.new_params["rsi_min"] == 55

    def test_weekly_report_creation_valid(self):
        """Test valid weekly report creation."""
        report = WeeklyReport(
            week_ending=date.today(),
            total_trades=25,
            win_rate=Decimal("0.64"),
            total_pnl=Decimal("500.00"),
            best_performers=["NVDA", "META", "TSLA"],
            worst_performers=["NFLX", "AMD"],
        )

        assert report.total_trades == 25
        assert len(report.best_performers) == 3
        assert "NVDA" in report.best_performers

    def test_weekly_report_empty_performers(self):
        """Test weekly report with empty performer lists (edge case)."""
        report = WeeklyReport(
            week_ending=date.today(),
            total_trades=0,
            win_rate=Decimal("0.00"),
            total_pnl=Decimal("0.00"),
            best_performers=[],
            worst_performers=[],
        )

        assert report.total_trades == 0
        assert len(report.best_performers) == 0
