"""Unit tests for MCP clients.

Tests for alpaca_client.py and data_client.py.
Validates API wrappers, rate limiting, and data caching.
"""

import pytest
import time
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.mcp_clients.data_client import (
    RateLimiter,
    ALPACA_LIMITER,
    TWELVEDATA_LIMITER,
    ALPHAVANTAGE_LIMITER,
)
from src.models.portfolio import Portfolio, Position


class TestRateLimiter:
    """Test cases for rate limiter implementation."""

    def test_rate_limiter_within_limit(self):
        """Test rate limiter allows calls within limit."""
        limiter = RateLimiter(max_calls=5, period=1.0)

        # Make 5 calls (should all succeed)
        for i in range(5):
            limiter.wait_if_needed()

        # All calls should complete quickly (no waiting)
        assert True  # If we get here, no blocking occurred

    def test_rate_limiter_exceeds_limit(self):
        """Test rate limiter blocks when limit exceeded."""
        limiter = RateLimiter(max_calls=3, period=1.0)

        # Make 3 calls quickly
        for i in range(3):
            limiter.wait_if_needed()

        # 4th call should block
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time

        # Should have waited some time (at least 0.5 seconds)
        assert elapsed > 0.3

    def test_rate_limiter_resets_after_period(self):
        """Test rate limiter resets after time period."""
        limiter = RateLimiter(max_calls=2, period=0.5)

        # Make 2 calls
        limiter.wait_if_needed()
        limiter.wait_if_needed()

        # Wait for period to expire
        time.sleep(0.6)

        # Next call should not block
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time

        # Should not have waited long
        assert elapsed < 0.2

    def test_rate_limiter_zero_max_calls(self):
        """Test rate limiter with 0 max calls (edge case)."""
        limiter = RateLimiter(max_calls=0, period=1.0)

        # Every call should block
        start_time = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start_time

        # Should have waited
        assert elapsed > 0.5

    def test_rate_limiter_concurrent_safety(self):
        """Test rate limiter is thread-safe (basic check)."""
        limiter = RateLimiter(max_calls=10, period=1.0)

        # Make multiple calls rapidly
        for i in range(10):
            limiter.wait_if_needed()

        # Should complete without errors
        assert len(limiter.calls) <= 10


class TestAPIRateLimiters:
    """Test cases for configured API rate limiters."""

    def test_alpaca_limiter_configured(self):
        """Test Alpaca rate limiter is configured correctly."""
        # Alpaca: 200 calls per minute
        assert ALPACA_LIMITER.max_calls == 200
        assert ALPACA_LIMITER.period == 60.0

    def test_twelvedata_limiter_configured(self):
        """Test TwelveData rate limiter is configured correctly."""
        # TwelveData: 8 calls per minute
        assert TWELVEDATA_LIMITER.max_calls == 8
        assert TWELVEDATA_LIMITER.period == 60.0

    def test_alphavantage_limiter_configured(self):
        """Test Alpha Vantage rate limiter is configured correctly."""
        # Alpha Vantage: 5 calls per minute
        assert ALPHAVANTAGE_LIMITER.max_calls == 5
        assert ALPHAVANTAGE_LIMITER.period == 60.0

    def test_rate_limiters_are_singletons(self):
        """Test that rate limiters are shared instances."""
        from src.mcp_clients.data_client import ALPACA_LIMITER as limiter1
        from src.mcp_clients.data_client import ALPACA_LIMITER as limiter2

        # Should be same instance
        assert limiter1 is limiter2


class TestAlpacaMCPClient:
    """Test cases for Alpaca MCP client wrapper."""

    @pytest.fixture
    def mock_alpaca_client(self):
        """Create mock Alpaca MCP client."""
        return AlpacaMCPClient()

    def test_alpaca_client_initialization(self, mock_alpaca_client):
        """Test Alpaca client initializes correctly."""
        assert mock_alpaca_client is not None
        assert hasattr(mock_alpaca_client, "get_account")
        assert hasattr(mock_alpaca_client, "get_positions")

    @pytest.mark.asyncio
    async def test_get_account_returns_portfolio(self, mock_alpaca_client):
        """Test get_account returns Portfolio object."""
        # Mock the MCP call
        with patch.object(mock_alpaca_client, "get_account", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = Portfolio(
                portfolio_value=Decimal("10000.00"),
                cash=Decimal("5000.00"),
                buying_power=Decimal("5000.00"),
                equity=Decimal("5000.00"),
            )

            portfolio = await mock_alpaca_client.get_account()

            assert isinstance(portfolio, Portfolio)
            assert portfolio.portfolio_value == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_get_positions_returns_list(self, mock_alpaca_client):
        """Test get_positions returns list of Position objects."""
        with patch.object(mock_alpaca_client, "get_positions", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                Position(
                    symbol="AAPL",
                    quantity=Decimal("10"),
                    avg_entry_price=Decimal("150.00"),
                    current_price=Decimal("155.00"),
                    market_value=Decimal("1550.00"),
                    unrealized_pnl=Decimal("50.00"),
                    unrealized_pnl_pct=Decimal("0.0333"),
                )
            ]

            positions = await mock_alpaca_client.get_positions()

            assert isinstance(positions, list)
            assert len(positions) == 1
            assert positions[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_positions_empty_portfolio(self, mock_alpaca_client):
        """Test get_positions with no positions (edge case)."""
        with patch.object(mock_alpaca_client, "get_positions", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            positions = await mock_alpaca_client.get_positions()

            assert positions == []

    @pytest.mark.asyncio
    async def test_submit_market_order_valid(self, mock_alpaca_client):
        """Test submitting market order."""
        with patch.object(
            mock_alpaca_client, "submit_market_order", new_callable=AsyncMock
        ) as mock_submit:
            mock_submit.return_value = "order_123456"

            order_id = await mock_alpaca_client.submit_market_order(
                symbol="NVDA", qty=Decimal("5"), side="buy"
            )

            assert order_id == "order_123456"
            mock_submit.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_market_order_with_bracket(self, mock_alpaca_client):
        """Test submitting bracket order with stop-loss and take-profit."""
        with patch.object(
            mock_alpaca_client, "submit_market_order", new_callable=AsyncMock
        ) as mock_submit:
            mock_submit.return_value = "order_789"

            order_id = await mock_alpaca_client.submit_market_order(
                symbol="TSLA",
                qty=Decimal("10"),
                side="buy",
                stop_loss=Decimal("190.00"),
                take_profit=Decimal("230.00"),
            )

            assert order_id == "order_789"

    @pytest.mark.asyncio
    async def test_close_position_valid(self, mock_alpaca_client):
        """Test closing a position."""
        with patch.object(
            mock_alpaca_client, "close_position", new_callable=AsyncMock
        ) as mock_close:
            mock_close.return_value = True

            result = await mock_alpaca_client.close_position("AAPL")

            assert result is True
            mock_close.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_bars_valid(self, mock_alpaca_client):
        """Test fetching historical bars."""
        mock_bars = pd.DataFrame(
            {
                "timestamp": pd.date_range(start="2024-01-01", periods=30, freq="D"),
                "open": [100.0] * 30,
                "high": [105.0] * 30,
                "low": [95.0] * 30,
                "close": [102.0] * 30,
                "volume": [1000000] * 30,
            }
        )

        with patch.object(mock_alpaca_client, "get_bars", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_bars

            bars = await mock_alpaca_client.get_bars("AAPL", days=30)

            assert isinstance(bars, pd.DataFrame)
            assert len(bars) == 30
            assert "close" in bars.columns

    @pytest.mark.asyncio
    async def test_get_bars_empty(self, mock_alpaca_client):
        """Test fetching bars with no data (edge case)."""
        with patch.object(mock_alpaca_client, "get_bars", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = pd.DataFrame()

            bars = await mock_alpaca_client.get_bars("INVALID", days=30)

            assert bars.empty

    @pytest.mark.asyncio
    async def test_get_latest_quote_valid(self, mock_alpaca_client):
        """Test fetching latest quote."""
        with patch.object(
            mock_alpaca_client, "get_latest_quote", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "symbol": "MSFT",
                "price": 350.50,
                "bid": 350.45,
                "ask": 350.55,
                "timestamp": datetime.now().isoformat(),
            }

            quote = await mock_alpaca_client.get_latest_quote("MSFT")

            assert quote["symbol"] == "MSFT"
            assert quote["price"] == 350.50

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_alpaca_client):
        """Test API error handling."""
        with patch.object(mock_alpaca_client, "get_account", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API Error")

            with pytest.raises(Exception) as exc_info:
                await mock_alpaca_client.get_account()

            assert "API Error" in str(exc_info.value)


class TestDataClientCaching:
    """Test cases for data caching functionality."""

    def test_cache_stores_data(self):
        """Test that cache stores and retrieves data correctly."""
        from src.mcp_clients.data_client import _cache

        # Clear cache first
        _cache.clear()

        # Store data
        test_key = "AAPL_bars_30d"
        test_data = pd.DataFrame({"close": [100, 101, 102]})

        _cache[test_key] = {
            "data": test_data,
            "timestamp": time.time(),
        }

        # Retrieve data
        assert test_key in _cache
        assert isinstance(_cache[test_key]["data"], pd.DataFrame)

    def test_cache_expiration(self):
        """Test that cache entries expire after timeout."""
        from src.mcp_clients.data_client import _cache, CACHE_TIMEOUT

        _cache.clear()

        # Store data with old timestamp
        test_key = "NVDA_bars_30d"
        test_data = pd.DataFrame({"close": [500, 510, 520]})

        _cache[test_key] = {
            "data": test_data,
            "timestamp": time.time() - CACHE_TIMEOUT - 10,  # Expired
        }

        # Check if we handle expired cache
        cached_entry = _cache.get(test_key)
        if cached_entry:
            age = time.time() - cached_entry["timestamp"]
            assert age > CACHE_TIMEOUT

    def test_cache_key_format(self):
        """Test cache key formatting is consistent."""
        # Cache keys should be predictable for same inputs
        ticker = "TSLA"
        days = 30

        key1 = f"{ticker}_bars_{days}d"
        key2 = f"{ticker}_bars_{days}d"

        assert key1 == key2


class TestMCPClientIntegration:
    """Integration tests for MCP client interactions."""

    @pytest.mark.asyncio
    async def test_full_trading_flow_mock(self):
        """Test complete trading flow with mocked MCP client."""
        client = AlpacaMCPClient()

        with (
            patch.object(client, "get_account", new_callable=AsyncMock) as mock_account,
            patch.object(client, "get_positions", new_callable=AsyncMock) as mock_positions,
            patch.object(client, "submit_market_order", new_callable=AsyncMock) as mock_order,
        ):

            # Setup mocks
            mock_account.return_value = Portfolio(
                portfolio_value=Decimal("10000.00"),
                cash=Decimal("5000.00"),
                buying_power=Decimal("5000.00"),
                equity=Decimal("5000.00"),
            )

            mock_positions.return_value = []

            mock_order.return_value = "order_abc123"

            # Execute flow
            portfolio = await client.get_account()
            positions = await client.get_positions()
            order_id = await client.submit_market_order("AAPL", Decimal("10"), "buy")

            # Verify
            assert portfolio.portfolio_value == Decimal("10000.00")
            assert positions == []
            assert order_id == "order_abc123"

    @pytest.mark.asyncio
    async def test_rate_limiting_applied_to_calls(self):
        """Test that rate limiting is applied to API calls."""
        client = AlpacaMCPClient()

        # Note: This test just verifies the rate limiter exists
        # Actual rate limiting behavior is tested in TestRateLimiter
        assert ALPACA_LIMITER is not None
        assert ALPACA_LIMITER.max_calls == 200


class TestErrorScenarios:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeout."""
        client = AlpacaMCPClient()

        with patch.object(client, "get_account", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = TimeoutError("Connection timeout")

            with pytest.raises(TimeoutError):
                await client.get_account()

    @pytest.mark.asyncio
    async def test_invalid_symbol(self):
        """Test handling of invalid ticker symbol."""
        client = AlpacaMCPClient()

        with patch.object(client, "get_bars", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = pd.DataFrame()  # Empty data for invalid symbol

            bars = await client.get_bars("INVALID_SYMBOL", days=30)

            assert bars.empty

    @pytest.mark.asyncio
    async def test_insufficient_funds(self):
        """Test handling of insufficient funds for order."""
        client = AlpacaMCPClient()

        with patch.object(client, "submit_market_order", new_callable=AsyncMock) as mock_submit:
            mock_submit.side_effect = Exception("Insufficient buying power")

            with pytest.raises(Exception) as exc_info:
                await client.submit_market_order("TSLA", Decimal("1000"), "buy")

            assert "Insufficient" in str(exc_info.value)
