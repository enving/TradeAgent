"""Pydantic models for market data (clock, calendar, history).

These models provide a stable interface independent of Alpaca API changes.
"""

from datetime import date, datetime, time
from decimal import Decimal
from math import sqrt
from statistics import stdev

from pydantic import BaseModel, Field


class MarketClock(BaseModel):
    """Market clock status.

    Attributes:
        timestamp: Current timestamp
        is_open: Whether market is currently open
        next_open: Next market open time
        next_close: Next market close time
    """

    timestamp: datetime = Field(description="Current timestamp")
    is_open: bool = Field(description="Whether market is open")
    next_open: datetime = Field(description="Next market open time")
    next_close: datetime = Field(description="Next market close time")


class MarketDay(BaseModel):
    """Single trading day information.

    Attributes:
        trading_date: Trading date
        open_time: Market open time
        close_time: Market close time
        session_open: Session open (including pre-market)
        session_close: Session close (including after-hours)
    """

    trading_date: date = Field(description="Trading date")
    open_time: time = Field(description="Market open time")
    close_time: time = Field(description="Market close time")
    session_open: time = Field(description="Session open time")
    session_close: time = Field(description="Session close time")


class Calendar(BaseModel):
    """Market calendar with trading days.

    Attributes:
        start_date: Start date of calendar
        end_date: End date of calendar
        days: List of trading days
    """

    start_date: date = Field(description="Start date")
    end_date: date = Field(description="End date")
    days: list[MarketDay] = Field(description="Trading days", default_factory=list)

    def get_trading_days(self) -> list[date]:
        """Get list of trading dates.

        Returns:
            List of dates that are trading days
        """
        return [day.trading_date for day in self.days]

    def is_trading_day(self, check_date: date) -> bool:
        """Check if date is a trading day.

        Args:
            check_date: Date to check

        Returns:
            True if trading day
        """
        return check_date in self.get_trading_days()


class PortfolioHistory(BaseModel):
    """Portfolio value history over time.

    Attributes:
        timestamps: List of timestamps
        equity: Portfolio equity values
        profit_loss: Profit/loss values (optional)
        profit_loss_pct: Profit/loss percentages (optional)
        base_value: Base portfolio value
        timeframe: Timeframe of data points
    """

    timestamps: list[datetime] = Field(description="Timestamps")
    equity: list[Decimal] = Field(description="Equity values")
    profit_loss: list[Decimal] | None = Field(default=None, description="P&L values")
    profit_loss_pct: list[Decimal] | None = Field(default=None, description="P&L percentages")
    base_value: Decimal = Field(description="Base portfolio value")
    timeframe: str = Field(description="Timeframe (1D, 1H, etc.)")

    def calculate_returns(self) -> list[Decimal]:
        """Calculate daily returns.

        Returns:
            List of returns (each return = (equity[i] - equity[i-1]) / equity[i-1])
        """
        if len(self.equity) < 2:
            return []

        returns = []
        for i in range(1, len(self.equity)):
            if self.equity[i - 1] > 0:
                ret = (self.equity[i] - self.equity[i - 1]) / self.equity[i - 1]
                returns.append(ret)

        return returns

    def calculate_sharpe_ratio(self, risk_free_rate: Decimal = Decimal("0.04")) -> Decimal:
        """Calculate Sharpe Ratio (annualized).

        Args:
            risk_free_rate: Annual risk-free rate (default: 4%)

        Returns:
            Sharpe Ratio

        Formula:
            Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns * sqrt(252)
        """
        returns = self.calculate_returns()

        if not returns or len(returns) < 2:
            return Decimal("0")

        # Convert to float for statistics
        returns_float = [float(r) for r in returns]

        avg_return = sum(returns_float) / len(returns_float)
        std_return = stdev(returns_float)

        if std_return == 0:
            return Decimal("0")

        # Annualize (252 trading days per year)
        daily_rf_rate = float(risk_free_rate) / 252
        sharpe_ratio = (avg_return - daily_rf_rate) / std_return * sqrt(252)

        return Decimal(str(sharpe_ratio))

    def calculate_max_drawdown(self) -> tuple[Decimal, datetime | None, datetime | None]:
        """Calculate maximum drawdown.

        Returns:
            Tuple of (max_drawdown_pct, peak_date, trough_date)

        Example:
            max_dd, peak, trough = history.calculate_max_drawdown()
            print(f"Max drawdown: {max_dd:.2%} from {peak} to {trough}")
        """
        if len(self.equity) < 2:
            return (Decimal("0"), None, None)

        max_drawdown = Decimal("0")
        peak_value = self.equity[0]
        peak_date = self.timestamps[0]
        trough_date = None

        for i, value in enumerate(self.equity):
            # Update peak
            if value > peak_value:
                peak_value = value
                peak_date = self.timestamps[i]

            # Calculate drawdown from peak
            if peak_value > 0:
                drawdown = (peak_value - value) / peak_value

                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    trough_date = self.timestamps[i]

        return (max_drawdown, peak_date, trough_date)

    def calculate_calmar_ratio(self, risk_free_rate: Decimal = Decimal("0.04")) -> Decimal:
        """Calculate Calmar Ratio.

        Formula:
            Calmar = Annualized Return / Max Drawdown

        Returns:
            Calmar Ratio (0 if insufficient data or zero drawdown)
        """
        if len(self.equity) < 2:
            return Decimal("0")

        # Handle zero starting equity
        if self.equity[0] == 0:
            return Decimal("0")

        # Calculate annualized return
        total_return = (self.equity[-1] - self.equity[0]) / self.equity[0]
        days = len(self.equity)
        annualized_return = total_return * Decimal(str(252 / days))

        # Get max drawdown
        max_dd, _, _ = self.calculate_max_drawdown()

        # If no drawdown, return 0 (can't divide by zero)
        if max_dd == 0:
            return Decimal("0")

        calmar_ratio = annualized_return / max_dd

        return calmar_ratio


class OrderHistory(BaseModel):
    """Historical order information.

    Attributes:
        order_id: Alpaca order ID
        client_order_id: Client-provided order ID
        created_at: Order creation time
        filled_at: Order fill time (if filled)
        symbol: Trading symbol
        side: Buy or Sell
        quantity: Order quantity
        filled_quantity: Filled quantity
        order_type: Market, Limit, etc.
        limit_price: Limit price (if limit order)
        filled_avg_price: Average fill price
        status: Order status (filled, cancelled, etc.)
    """

    order_id: str = Field(description="Alpaca order ID")
    client_order_id: str | None = Field(default=None, description="Client order ID")
    created_at: datetime = Field(description="Order creation time")
    filled_at: datetime | None = Field(default=None, description="Order fill time")
    symbol: str = Field(description="Trading symbol")
    side: str = Field(description="Buy or Sell")
    quantity: Decimal = Field(description="Order quantity", gt=0)
    filled_quantity: Decimal = Field(description="Filled quantity", ge=0)
    order_type: str = Field(description="Order type")
    limit_price: Decimal | None = Field(default=None, description="Limit price")
    filled_avg_price: Decimal | None = Field(default=None, description="Average fill price")
    status: str = Field(description="Order status")

    def calculate_slippage(self, expected_price: Decimal) -> Decimal | None:
        """Calculate slippage vs. expected price.

        Args:
            expected_price: Expected execution price

        Returns:
            Slippage in dollars (positive = worse than expected)

        Example:
            Expected: $100, Filled: $100.50 → Slippage: $0.50
        """
        if self.filled_avg_price is None or self.filled_quantity == 0:
            return None

        if self.side.lower() == "buy":
            # For buys: paid more than expected = positive slippage
            slippage = self.filled_avg_price - expected_price
        else:
            # For sells: received less than expected = positive slippage
            slippage = expected_price - self.filled_avg_price

        return slippage

    def calculate_slippage_pct(self, expected_price: Decimal) -> Decimal | None:
        """Calculate slippage percentage.

        Args:
            expected_price: Expected execution price

        Returns:
            Slippage as percentage

        Example:
            Expected: $100, Filled: $100.50 → Slippage: 0.5%
        """
        slippage = self.calculate_slippage(expected_price)

        if slippage is None or expected_price == 0:
            return None

        slippage_pct = (slippage / expected_price) * Decimal("100")
        return slippage_pct
