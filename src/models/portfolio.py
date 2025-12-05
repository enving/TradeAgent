"""Pydantic models for portfolio and position data."""

from decimal import Decimal

from pydantic import BaseModel, Field


class Position(BaseModel):
    """Represents a single portfolio position.

    Attributes:
        symbol: Stock/ETF ticker symbol
        quantity: Number of shares held
        avg_entry_price: Average entry price per share
        current_price: Current market price
        market_value: Current position value (quantity * current_price)
        unrealized_pnl: Unrealized profit/loss
        unrealized_pnl_pct: Unrealized P&L percentage
    """

    symbol: str = Field(description="Stock/ETF ticker symbol")
    quantity: Decimal = Field(description="Number of shares held", ge=0)
    avg_entry_price: Decimal = Field(description="Average entry price per share", gt=0)
    current_price: Decimal = Field(description="Current market price", gt=0)
    market_value: Decimal = Field(description="Current position value")
    unrealized_pnl: Decimal = Field(description="Unrealized profit/loss")
    unrealized_pnl_pct: Decimal = Field(description="Unrealized P&L percentage")


class Portfolio(BaseModel):
    """Represents complete portfolio state.

    Attributes:
        cash: Available cash
        portfolio_value: Total portfolio value (cash + positions)
        buying_power: Available buying power for trading
        equity: Total equity value (positions only, excluding cash)
        positions: List of open positions
    """

    cash: Decimal = Field(description="Available cash", ge=0)
    portfolio_value: Decimal = Field(description="Total portfolio value", ge=0)
    buying_power: Decimal = Field(description="Available buying power", ge=0)
    equity: Decimal = Field(description="Total equity value", ge=0)
    positions: list[Position] = Field(default_factory=list, description="List of open positions")
