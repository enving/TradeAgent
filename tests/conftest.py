"""Pytest configuration and shared fixtures.

Provides reusable fixtures for all test modules.
Configures async testing and test environment.
"""

import os

# Set test environment variables BEFORE any module imports
os.environ["ALPACA_API_KEY"] = "test_alpaca_key"
os.environ["ALPACA_SECRET_KEY"] = "test_alpaca_secret"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test_supabase_key"
os.environ["ENVIRONMENT"] = "test"

import pytest
import pytest_asyncio
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock

from src.models.portfolio import Portfolio, Position
from src.models.trade import Signal, Trade
from src.models.performance import DailyPerformance, StrategyMetrics


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def sample_portfolio():
    """Create sample portfolio for testing.

    Returns:
        Portfolio with $10,000 total value, $5,000 cash
    """
    return Portfolio(
        portfolio_value=Decimal("10000.00"),
        cash=Decimal("5000.00"),
        buying_power=Decimal("5000.00"),
        equity=Decimal("5000.00"),
    )


@pytest.fixture
def small_portfolio():
    """Create small portfolio for edge case testing.

    Returns:
        Portfolio with $1,000 total value, $500 cash
    """
    return Portfolio(
        portfolio_value=Decimal("1000.00"),
        cash=Decimal("500.00"),
        buying_power=Decimal("500.00"),
        equity=Decimal("500.00"),
    )


@pytest.fixture
def large_portfolio():
    """Create large portfolio for testing.

    Returns:
        Portfolio with $100,000 total value, $50,000 cash
    """
    return Portfolio(
        portfolio_value=Decimal("100000.00"),
        cash=Decimal("50000.00"),
        buying_power=Decimal("50000.00"),
        equity=Decimal("50000.00"),
    )


@pytest.fixture
def sample_position():
    """Create sample position for testing.

    Returns:
        Position in AAPL with profit
    """
    return Position(
        symbol="AAPL",
        quantity=Decimal("10"),
        avg_entry_price=Decimal("150.00"),
        current_price=Decimal("155.00"),
        market_value=Decimal("1550.00"),
        unrealized_pnl=Decimal("50.00"),
        unrealized_pnl_pct=Decimal("0.0333"),
    )


@pytest.fixture
def defensive_positions():
    """Create defensive core positions (VTI, VGK, GLD).

    Returns:
        List of defensive positions at target allocations
    """
    return [
        Position(
            symbol="VTI",
            quantity=Decimal("12.5"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("200.00"),
            market_value=Decimal("2500.00"),  # 25% of $10k
            unrealized_pnl=Decimal("0.00"),
            unrealized_pnl_pct=Decimal("0.00"),
        ),
        Position(
            symbol="VGK",
            quantity=Decimal("30"),
            avg_entry_price=Decimal("50.00"),
            current_price=Decimal("50.00"),
            market_value=Decimal("1500.00"),  # 15% of $10k
            unrealized_pnl=Decimal("0.00"),
            unrealized_pnl_pct=Decimal("0.00"),
        ),
        Position(
            symbol="GLD",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("200.00"),
            market_value=Decimal("1000.00"),  # 10% of $10k
            unrealized_pnl=Decimal("0.00"),
            unrealized_pnl_pct=Decimal("0.00"),
        ),
    ]


@pytest.fixture
def momentum_positions():
    """Create momentum trading positions.

    Returns:
        List of momentum positions
    """
    return [
        Position(
            symbol="NVDA",
            quantity=Decimal("5"),
            avg_entry_price=Decimal("500.00"),
            current_price=Decimal("520.00"),
            market_value=Decimal("2600.00"),
            unrealized_pnl=Decimal("100.00"),
            unrealized_pnl_pct=Decimal("0.04"),
        ),
        Position(
            symbol="TSLA",
            quantity=Decimal("10"),
            avg_entry_price=Decimal("200.00"),
            current_price=Decimal("210.00"),
            market_value=Decimal("2100.00"),
            unrealized_pnl=Decimal("100.00"),
            unrealized_pnl_pct=Decimal("0.05"),
        ),
    ]


@pytest.fixture
def sample_signal():
    """Create sample trading signal.

    Returns:
        BUY signal for AAPL with stop-loss and take-profit
    """
    return Signal(
        ticker="AAPL",
        action="BUY",
        entry_price=Decimal("150.00"),
        stop_loss=Decimal("142.50"),  # -5%
        take_profit=Decimal("172.50"),  # +15%
        confidence=Decimal("0.75"),
        strategy="momentum",
        rsi=Decimal("60.0"),
        macd_histogram=Decimal("0.5"),
        volume_ratio=Decimal("1.3"),
    )


@pytest.fixture
def high_confidence_signal():
    """Create high confidence trading signal.

    Returns:
        Signal with 0.90 confidence
    """
    return Signal(
        ticker="NVDA",
        action="BUY",
        entry_price=Decimal("500.00"),
        stop_loss=Decimal("475.00"),
        take_profit=Decimal("575.00"),
        confidence=Decimal("0.90"),
        strategy="momentum",
    )


@pytest.fixture
def sample_trade():
    """Create sample completed trade.

    Returns:
        Trade with entry and exit data
    """
    return Trade(
        date=datetime.now(),
        ticker="META",
        action="BUY",
        quantity=Decimal("10"),
        entry_price=Decimal("300.00"),
        exit_price=Decimal("330.00"),
        pnl=Decimal("300.00"),
        pnl_pct=Decimal("0.10"),
        strategy="momentum",
        exit_reason="take_profit",
    )


@pytest.fixture
def sample_bars():
    """Create sample OHLCV bars data.

    Returns:
        DataFrame with 30 days of realistic price data
    """
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")

    # Generate realistic price movement
    close_prices = 100 + np.cumsum(np.random.randn(30) * 2)

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices + np.random.randn(30) * 0.5,
            "high": close_prices + np.abs(np.random.randn(30) * 1.5),
            "low": close_prices - np.abs(np.random.randn(30) * 1.5),
            "close": close_prices,
            "volume": np.random.randint(1000000, 5000000, 30),
        }
    )


@pytest.fixture
def trending_up_bars():
    """Create uptrending price data.

    Returns:
        DataFrame with steady uptrend (bullish)
    """
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    close_prices = np.linspace(100, 130, 30)  # +30% over 30 days

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices,
            "high": close_prices + 1,
            "low": close_prices - 1,
            "close": close_prices,
            "volume": np.random.randint(2000000, 4000000, 30),
        }
    )


@pytest.fixture
def trending_down_bars():
    """Create downtrending price data.

    Returns:
        DataFrame with steady downtrend (bearish)
    """
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    close_prices = np.linspace(100, 70, 30)  # -30% over 30 days

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices,
            "high": close_prices + 1,
            "low": close_prices - 1,
            "close": close_prices,
            "volume": np.random.randint(1000000, 3000000, 30),
        }
    )


@pytest.fixture
def volatile_bars():
    """Create highly volatile price data.

    Returns:
        DataFrame with high volatility
    """
    np.random.seed(123)
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")

    # High volatility
    close_prices = 100 + np.cumsum(np.random.randn(30) * 5)

    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices + np.random.randn(30) * 3,
            "high": close_prices + np.abs(np.random.randn(30) * 8),
            "low": close_prices - np.abs(np.random.randn(30) * 8),
            "close": close_prices,
            "volume": np.random.randint(5000000, 10000000, 30),
        }
    )


@pytest.fixture
def sample_daily_performance():
    """Create sample daily performance metrics.

    Returns:
        DailyPerformance with typical metrics
    """
    return DailyPerformance(
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


@pytest.fixture
def sample_strategy_metrics():
    """Create sample strategy metrics.

    Returns:
        StrategyMetrics for momentum strategy
    """
    return StrategyMetrics(
        strategy="momentum",
        date=date.today(),
        total_trades=5,
        win_rate=Decimal("0.60"),
        total_pnl=Decimal("150.00"),
    )


@pytest_asyncio.fixture
async def mock_alpaca_client():
    """Create mock Alpaca MCP client.

    Returns:
        AsyncMock Alpaca client with common methods
    """
    mock_client = AsyncMock()

    # Default return values
    mock_client.get_account.return_value = Portfolio(
        portfolio_value=Decimal("10000.00"),
        cash=Decimal("5000.00"),
        buying_power=Decimal("5000.00"),
        equity=Decimal("5000.00"),
    )

    mock_client.get_positions.return_value = []

    mock_client.submit_market_order.return_value = "order_123456"

    mock_client.close_position.return_value = True

    mock_client.get_bars.return_value = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2024-01-01", periods=30, freq="D"),
            "open": [100.0] * 30,
            "high": [105.0] * 30,
            "low": [95.0] * 30,
            "close": [102.0] * 30,
            "volume": [1000000] * 30,
        }
    )

    mock_client.get_latest_quote.return_value = {
        "symbol": "AAPL",
        "price": 150.00,
        "bid": 149.95,
        "ask": 150.05,
    }

    return mock_client


@pytest_asyncio.fixture
async def mock_supabase_client():
    """Create mock Supabase client.

    Returns:
        AsyncMock Supabase client with common methods
    """
    mock_client = AsyncMock()

    # Default return values
    mock_client.log_trade.return_value = True
    mock_client.log_signal.return_value = True
    mock_client.log_daily_performance.return_value = True
    mock_client.log_strategy_metrics.return_value = True
    mock_client.log_parameter_change.return_value = True
    mock_client.log_weekly_report.return_value = True

    mock_client.get_strategy_performance.return_value = [
        {"date": "2024-01-01", "win_rate": 0.60, "total_pnl": 100.00},
        {"date": "2024-01-02", "win_rate": 0.65, "total_pnl": 120.00},
    ]

    return mock_client


@pytest.fixture(autouse=True)
def reset_strategy_params():
    """Reset strategy parameters after each test.

    Ensures tests don't affect each other through global state.
    """
    from src.strategies.momentum_trading import STRATEGY_PARAMS

    # Store original values
    original_params = STRATEGY_PARAMS.copy()

    yield

    # Restore after test
    STRATEGY_PARAMS.clear()
    STRATEGY_PARAMS.update(original_params)


@pytest.fixture
def freeze_time(monkeypatch):
    """Freeze time for deterministic testing.

    Usage:
        def test_something(freeze_time):
            freeze_time("2024-03-01")
            # Test with frozen time
    """

    def _freeze(date_string):
        frozen_date = datetime.fromisoformat(date_string)

        class FrozenDateTime:
            @classmethod
            def now(cls, tz=None):
                return frozen_date

        monkeypatch.setattr("datetime.datetime", FrozenDateTime)

    return _freeze


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
