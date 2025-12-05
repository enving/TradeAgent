"""Market Data Adapter - Robust abstraction for Alpaca API.

This adapter provides a stable interface for market data operations,
protecting against API changes and providing graceful degradation.

Design Philosophy:
1. Single Responsibility - Each method does one thing
2. Fail Gracefully - Always return a result, use fallbacks
3. Version Agnostic - Support multiple API versions
4. Logging - Track API changes and errors
5. Type Safe - Clear interfaces with Pydantic models
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetCalendarRequest, GetOrdersRequest, GetPortfolioHistoryRequest

from ..models.market import Calendar, MarketClock, MarketDay, OrderHistory, PortfolioHistory
from ..utils.config import config
from ..utils.logger import logger


class MarketDataAdapter:
    """Robust adapter for Alpaca market data operations.

    Handles:
    - API version detection
    - Graceful degradation
    - Error recovery
    - Response normalization

    Example:
        adapter = MarketDataAdapter()
        clock = await adapter.get_market_clock()
        if clock.is_open:
            # Trade logic
    """

    def __init__(self):
        """Initialize market data adapter."""
        self.client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True,
        )
        self._api_version = self._detect_api_version()
        logger.info(f"MarketDataAdapter initialized (API version: {self._api_version})")

    def _detect_api_version(self) -> str:
        """Detect Alpaca API version.

        Returns:
            Version string (e.g., 'v2', 'v3')
        """
        try:
            # Check for version-specific methods
            if hasattr(self.client, "get_clock"):
                return "v2"
            else:
                return "v1"
        except Exception as e:
            logger.warning(f"Could not detect API version: {e}")
            return "unknown"

    async def get_market_clock(self) -> MarketClock | None:
        """Get current market clock status.

        Returns:
            MarketClock with status, or None if unavailable

        Example:
            clock = await adapter.get_market_clock()
            if clock and clock.is_open:
                print("Market is open!")
        """
        try:
            # Try to get clock from Alpaca
            clock_data = self.client.get_clock()

            # Normalize response to our model
            market_clock = MarketClock(
                timestamp=clock_data.timestamp,
                is_open=clock_data.is_open,
                next_open=clock_data.next_open,
                next_close=clock_data.next_close,
            )

            logger.debug(
                f"Market clock: {'OPEN' if market_clock.is_open else 'CLOSED'} "
                f"(next_open: {market_clock.next_open})"
            )

            return market_clock

        except AttributeError as e:
            # API method not available (old version?)
            logger.warning(f"get_clock() not available: {e}")
            return self._fallback_market_clock()

        except Exception as e:
            # Other errors (network, auth, etc.)
            logger.error(f"Failed to get market clock: {e}")
            return self._fallback_market_clock()

    def _fallback_market_clock(self) -> MarketClock:
        """Fallback market clock when API unavailable.

        Uses EST market hours (9:30 AM - 4:00 PM) as approximation.

        Returns:
            Estimated MarketClock
        """
        now = datetime.now()
        now_est = now  # Simplified, should convert to EST

        # Market hours: 9:30 AM - 4:00 PM EST, Mon-Fri
        market_open = time(9, 30)
        market_close = time(16, 0)

        is_weekday = now.weekday() < 5  # Mon=0, Fri=4
        is_market_hours = market_open <= now_est.time() <= market_close
        is_open = is_weekday and is_market_hours

        # Calculate next open/close (simplified)
        if is_open:
            next_close = datetime.combine(now.date(), market_close)
            next_open = next_close + timedelta(days=1)
        else:
            if now_est.time() < market_open:
                next_open = datetime.combine(now.date(), market_open)
            else:
                next_open = datetime.combine(now.date() + timedelta(days=1), market_open)
            next_close = datetime.combine(next_open.date(), market_close)

        logger.warning("Using fallback market clock (API unavailable)")

        return MarketClock(
            timestamp=now,
            is_open=is_open,
            next_open=next_open,
            next_close=next_close,
        )

    async def get_market_calendar(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> Calendar | None:
        """Get market calendar (trading days).

        Args:
            start_date: Start date (default: today)
            end_date: End date (default: today + 30 days)

        Returns:
            Calendar with trading days, or None if unavailable

        Example:
            calendar = await adapter.get_market_calendar(
                start_date=date(2025, 11, 1),
                end_date=date(2025, 11, 30)
            )
            trading_days = calendar.get_trading_days()
        """
        try:
            # Default date range
            if start_date is None:
                start_date = datetime.now().date()
            if end_date is None:
                end_date = start_date + timedelta(days=30)

            # Get calendar from Alpaca using request object
            calendar_request = GetCalendarRequest(start=start_date, end=end_date)
            calendar_data = self.client.get_calendar(filters=calendar_request)

            # Normalize to our model
            market_days = [
                MarketDay(
                    trading_date=day.date,
                    open_time=day.open.time() if isinstance(day.open, datetime) else day.open,
                    close_time=day.close.time()
                    if isinstance(day.close, datetime)
                    else day.close,
                    session_open=(
                        day.session_open.time()
                        if hasattr(day, "session_open") and isinstance(day.session_open, datetime)
                        else (
                            day.session_open
                            if hasattr(day, "session_open")
                            else (day.open.time() if isinstance(day.open, datetime) else day.open)
                        )
                    ),
                    session_close=(
                        day.session_close.time()
                        if hasattr(day, "session_close")
                        and isinstance(day.session_close, datetime)
                        else (
                            day.session_close
                            if hasattr(day, "session_close")
                            else (
                                day.close.time() if isinstance(day.close, datetime) else day.close
                            )
                        )
                    ),
                )
                for day in calendar_data
            ]

            calendar = Calendar(start_date=start_date, end_date=end_date, days=market_days)

            logger.debug(f"Calendar fetched: {len(market_days)} trading days")

            return calendar

        except AttributeError as e:
            logger.warning(f"get_calendar() not available: {e}")
            return self._fallback_market_calendar(start_date, end_date)

        except Exception as e:
            logger.error(f"Failed to get market calendar: {e}")
            return self._fallback_market_calendar(start_date, end_date)

    def _fallback_market_calendar(
        self, start_date: date, end_date: date
    ) -> Calendar:
        """Fallback calendar when API unavailable.

        Assumes Mon-Fri are trading days (ignores holidays).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Estimated Calendar
        """
        market_days = []
        current = start_date

        while current <= end_date:
            # Skip weekends
            if current.weekday() < 5:  # Mon-Fri
                market_days.append(
                    MarketDay(
                        trading_date=current,
                        open_time=time(9, 30),
                        close_time=time(16, 0),
                        session_open=time(4, 0),  # Pre-market
                        session_close=time(20, 0),  # After-hours
                    )
                )
            current += timedelta(days=1)

        logger.warning(
            f"Using fallback calendar (API unavailable): {len(market_days)} estimated trading days"
        )

        return Calendar(start_date=start_date, end_date=end_date, days=market_days)

    async def get_portfolio_history(
        self, period: str = "1M", timeframe: str = "1D"
    ) -> PortfolioHistory | None:
        """Get portfolio value history.

        Args:
            period: Lookback period (1D, 5D, 1M, 3M, 1Y, all)
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1H, 1D)

        Returns:
            PortfolioHistory with equity curve, or None if unavailable

        Example:
            history = await adapter.get_portfolio_history(period="1M", timeframe="1D")
            sharpe_ratio = history.calculate_sharpe_ratio()
        """
        try:
            # Get portfolio history from Alpaca using request object
            history_request = GetPortfolioHistoryRequest(period=period, timeframe=timeframe)
            history_data = self.client.get_portfolio_history(history_filter=history_request)

            # Normalize to our model
            portfolio_history = PortfolioHistory(
                timestamps=[datetime.fromtimestamp(ts) for ts in history_data.timestamp],
                equity=[Decimal(str(val)) for val in history_data.equity],
                profit_loss=[Decimal(str(val)) for val in history_data.profit_loss]
                if history_data.profit_loss
                else None,
                profit_loss_pct=[Decimal(str(val)) for val in history_data.profit_loss_pct]
                if history_data.profit_loss_pct
                else None,
                base_value=Decimal(str(history_data.base_value)),
                timeframe=timeframe,
            )

            logger.debug(
                f"Portfolio history fetched: {len(portfolio_history.timestamps)} data points"
            )

            return portfolio_history

        except AttributeError as e:
            logger.warning(f"get_portfolio_history() not available: {e}")
            return None

        except Exception as e:
            logger.error(f"Failed to get portfolio history: {e}")
            return None

    async def get_orders_history(
        self,
        status: str = "all",
        limit: int = 100,
        after: datetime | None = None,
        until: datetime | None = None,
        nested: bool = True,
    ) -> list[OrderHistory]:
        """Get historical orders with execution details.

        Args:
            status: Order status filter ('open', 'closed', 'all')
            limit: Maximum number of orders to fetch (default: 100)
            after: Start date for order history
            until: End date for order history
            nested: Include child orders (bracket orders)

        Returns:
            List of OrderHistory objects, or empty list if unavailable

        Example:
            # Get last 50 filled orders
            orders = await adapter.get_orders_history(status="closed", limit=50)

            # Calculate slippage
            for order in orders:
                if order.filled_avg_price:
                    slippage = order.calculate_slippage(expected_price)
                    print(f"{order.symbol}: {slippage:.2f} slippage")
        """
        try:
            # Map string status to enum
            status_enum = None
            if status == "open":
                status_enum = QueryOrderStatus.OPEN
            elif status == "closed":
                status_enum = QueryOrderStatus.CLOSED
            elif status == "all":
                status_enum = QueryOrderStatus.ALL

            # Create request
            order_request = GetOrdersRequest(
                status=status_enum,
                limit=limit,
                after=after,
                until=until,
                nested=nested,
            )

            # Fetch orders from Alpaca
            orders_data = self.client.get_orders(filter=order_request)

            # Normalize to our model
            order_history = []
            for order in orders_data:
                try:
                    order_hist = OrderHistory(
                        order_id=str(order.id),
                        client_order_id=order.client_order_id,
                        created_at=order.created_at,
                        filled_at=order.filled_at if hasattr(order, "filled_at") else None,
                        symbol=order.symbol,
                        side=order.side.value if hasattr(order.side, "value") else str(order.side),
                        quantity=Decimal(str(order.qty)),
                        filled_quantity=Decimal(str(order.filled_qty))
                        if order.filled_qty
                        else Decimal("0"),
                        order_type=order.type.value
                        if hasattr(order.type, "value")
                        else str(order.type),
                        limit_price=Decimal(str(order.limit_price))
                        if order.limit_price
                        else None,
                        filled_avg_price=Decimal(str(order.filled_avg_price))
                        if order.filled_avg_price
                        else None,
                        status=order.status.value
                        if hasattr(order.status, "value")
                        else str(order.status),
                    )
                    order_history.append(order_hist)
                except Exception as e:
                    logger.warning(f"Failed to normalize order {order.id}: {e}")
                    continue

            logger.debug(f"Orders history fetched: {len(order_history)} orders")

            return order_history

        except AttributeError as e:
            logger.warning(f"get_orders() not available: {e}")
            return []

        except Exception as e:
            logger.error(f"Failed to get orders history: {e}")
            return []

    async def is_market_open(self) -> bool:
        """Check if market is currently open.

        Returns:
            True if market is open, False otherwise

        Example:
            if await adapter.is_market_open():
                # Execute trades
        """
        clock = await self.get_market_clock()
        if clock is None:
            logger.warning("Could not determine market status, assuming closed")
            return False

        return clock.is_open

    async def is_first_trading_day_of_month(self, check_date: date | None = None) -> bool:
        """Check if date is first trading day of the month.

        Args:
            check_date: Date to check (default: today)

        Returns:
            True if first trading day of month

        Example:
            if await adapter.is_first_trading_day_of_month():
                # Trigger monthly rebalancing
        """
        if check_date is None:
            check_date = datetime.now().date()

        # Get month's calendar
        month_start = check_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        calendar = await self.get_market_calendar(start_date=month_start, end_date=month_end)

        if calendar is None or not calendar.days:
            logger.warning("Could not get calendar, falling back to day==1 check")
            return check_date.day == 1 and check_date.weekday() < 5

        # Check if today is the first trading day
        first_trading_day = calendar.days[0].trading_date
        return check_date == first_trading_day


# Global instance
_adapter = None


async def get_market_data_adapter() -> MarketDataAdapter:
    """Get or create global MarketDataAdapter instance.

    Returns:
        MarketDataAdapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = MarketDataAdapter()
    return _adapter
