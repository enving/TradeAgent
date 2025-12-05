"""Pydantic models for performance tracking and metrics."""

from datetime import date as DateType
from decimal import Decimal

from pydantic import BaseModel, Field


class DailyPerformance(BaseModel):
    """Daily performance metrics.

    Attributes:
        date: Trading date
        total_trades: Total number of trades executed
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate percentage
        daily_pnl: Daily profit/loss
        profit_factor: Average win / average loss
        avg_win: Average profit per winning trade
        avg_loss: Average loss per losing trade
    """

    date: DateType = Field(description="Trading date")
    total_trades: int = Field(description="Total number of trades", ge=0)
    winning_trades: int = Field(description="Number of winning trades", ge=0)
    losing_trades: int = Field(description="Number of losing trades", ge=0)
    win_rate: Decimal = Field(description="Win rate percentage", ge=0, le=1)
    daily_pnl: Decimal = Field(description="Daily profit/loss")
    profit_factor: Decimal = Field(description="Avg win / avg loss", ge=0)
    avg_win: Decimal = Field(description="Average profit per winning trade", ge=0)
    avg_loss: Decimal = Field(description="Average loss per losing trade", le=0)
    sharpe_ratio: Decimal | None = Field(default=None, description="Rolling Sharpe Ratio")
    max_drawdown: Decimal | None = Field(default=None, description="Max Drawdown from peak")


class StrategyMetrics(BaseModel):
    """Performance metrics for a specific strategy.

    Attributes:
        strategy: Strategy name
        date: Metrics date
        total_trades: Total trades for this strategy
        win_rate: Win rate for this strategy
        total_pnl: Total P&L for this strategy
    """

    strategy: str = Field(description="Strategy name")
    date: DateType = Field(description="Metrics date")
    total_trades: int = Field(description="Total trades", ge=0)
    win_rate: Decimal = Field(description="Win rate", ge=0, le=1)
    total_pnl: Decimal = Field(description="Total P&L")


class WeeklyReport(BaseModel):
    """Weekly performance report.

    Attributes:
        week_ending: End date of the week
        total_trades: Total trades in the week
        win_rate: Weekly win rate
        total_pnl: Total P&L for the week
        best_performers: List of best performing tickers
        worst_performers: List of worst performing tickers
    """

    week_ending: DateType = Field(description="End date of the week")
    total_trades: int = Field(description="Total trades in the week", ge=0)
    win_rate: Decimal = Field(description="Weekly win rate", ge=0, le=1)
    total_pnl: Decimal = Field(description="Total P&L for the week")
    best_performers: list[str] = Field(description="Best performing tickers")
    worst_performers: list[str] = Field(description="Worst performing tickers")


class ParameterChange(BaseModel):
    """Record of strategy parameter adjustments.

    Attributes:
        date: Date of parameter change
        reason: Reason for the adjustment
        old_params: Previous parameter values
        new_params: New parameter values
    """

    date: DateType = Field(description="Date of parameter change")
    reason: str = Field(description="Reason for adjustment")
    old_params: dict[str, float] = Field(description="Previous parameter values")
    new_params: dict[str, float] = Field(description="New parameter values")
