"""Dynamic Position Sizing using Kelly Criterion.

Calculates optimal position sizes based on signal confidence,
historical win rate, and risk/reward ratios.
"""

from decimal import Decimal
from typing import Optional

from ..models.portfolio import Portfolio
from ..models.trade import Signal
from ..utils.logger import logger


class PositionSizer:
    """Dynamic position sizing using Kelly Criterion."""

    # Position size constraints
    MAX_POSITION_SIZE_PCT = Decimal("0.15")  # 15% max per position
    MIN_POSITION_SIZE_PCT = Decimal("0.03")  # 3% min per position
    KELLY_FRACTION = Decimal("0.5")  # Use half-Kelly for safety

    # Historical performance (updated periodically)
    DEFAULT_WIN_RATE = Decimal("0.55")  # 55% win rate
    DEFAULT_AVG_WIN = Decimal("0.08")  # 8% avg win
    DEFAULT_AVG_LOSS = Decimal("0.03")  # 3% avg loss

    def __init__(
        self,
        win_rate: Optional[Decimal] = None,
        avg_win: Optional[Decimal] = None,
        avg_loss: Optional[Decimal] = None,
    ):
        """Initialize position sizer with historical performance metrics.

        Args:
            win_rate: Historical win rate (0-1). Defaults to 0.55.
            avg_win: Average winning trade percentage. Defaults to 0.08.
            avg_loss: Average losing trade percentage. Defaults to 0.03.
        """
        self.win_rate = win_rate or self.DEFAULT_WIN_RATE
        self.avg_win = avg_win or self.DEFAULT_AVG_WIN
        self.avg_loss = avg_loss or self.DEFAULT_AVG_LOSS

        # Calculate win/loss ratio
        if self.avg_loss > 0:
            self.win_loss_ratio = self.avg_win / self.avg_loss
        else:
            self.win_loss_ratio = Decimal("2.0")  # Default 2:1 ratio

        logger.info(
            f"PositionSizer initialized: "
            f"Win Rate={self.win_rate:.2%}, "
            f"Avg Win={self.avg_win:.2%}, "
            f"Avg Loss={self.avg_loss:.2%}, "
            f"Win/Loss Ratio={self.win_loss_ratio:.2f}"
        )

    def calculate_kelly_fraction(
        self, confidence: Decimal, stop_loss_pct: Decimal, take_profit_pct: Decimal
    ) -> Decimal:
        """Calculate Kelly Criterion position size fraction.

        Kelly Formula: f* = (p * b - q) / b
        Where:
            p = win probability (from confidence)
            q = 1 - p (loss probability)
            b = win/loss ratio (take_profit / stop_loss)
            f* = optimal position size fraction

        Args:
            confidence: Signal confidence (0-1)
            stop_loss_pct: Stop-loss percentage (e.g., 0.05 for 5%)
            take_profit_pct: Take-profit percentage (e.g., 0.15 for 15%)

        Returns:
            Kelly fraction (0-1) representing optimal position size
        """
        # Use confidence as win probability (scaled by historical win rate)
        p = confidence * self.win_rate

        # Loss probability
        q = Decimal("1") - p

        # Risk/reward ratio from this specific trade
        if stop_loss_pct > 0:
            b = take_profit_pct / stop_loss_pct
        else:
            b = self.win_loss_ratio  # Fallback to historical

        # Kelly Criterion: (p * b - q) / b
        numerator = p * b - q
        if b > 0:
            kelly = numerator / b
        else:
            kelly = Decimal("0")

        # Apply half-Kelly for reduced volatility
        kelly_adjusted = kelly * self.KELLY_FRACTION

        # Ensure non-negative
        kelly_adjusted = max(kelly_adjusted, Decimal("0"))

        logger.debug(
            f"Kelly Calculation: p={p:.3f}, q={q:.3f}, b={b:.2f}, "
            f"raw_kelly={kelly:.3f}, adjusted={kelly_adjusted:.3f}"
        )

        return kelly_adjusted

    def calculate_position_size(
        self, signal: Signal, portfolio: Portfolio
    ) -> tuple[Decimal, str]:
        """Calculate optimal position size for a signal.

        Args:
            signal: Trading signal with confidence and prices
            portfolio: Current portfolio state

        Returns:
            Tuple of (position_value, reasoning)
            position_value: Dollar amount to invest
            reasoning: Explanation of sizing decision
        """
        # Extract signal parameters
        confidence = signal.confidence
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss or (entry_price * Decimal("0.97"))  # Default 3% stop
        take_profit = signal.take_profit or (entry_price * Decimal("1.08"))  # Default 8% target

        # Calculate stop-loss and take-profit percentages
        stop_loss_pct = abs(entry_price - stop_loss) / entry_price
        take_profit_pct = abs(take_profit - entry_price) / entry_price

        # Calculate Kelly fraction
        kelly_fraction = self.calculate_kelly_fraction(
            confidence, stop_loss_pct, take_profit_pct
        )

        # Calculate position size as percentage of portfolio
        position_size_pct = kelly_fraction

        # Apply constraints (min 3%, max 15%)
        original_pct = position_size_pct
        position_size_pct = max(position_size_pct, self.MIN_POSITION_SIZE_PCT)
        position_size_pct = min(position_size_pct, self.MAX_POSITION_SIZE_PCT)

        # Convert to dollar value
        position_value = portfolio.portfolio_value * position_size_pct

        # Ensure we have enough cash
        max_affordable = portfolio.cash * Decimal("0.95")  # Use 95% of cash max
        if position_value > max_affordable:
            position_value = max_affordable
            position_size_pct = position_value / portfolio.portfolio_value

        # Generate reasoning
        reasoning = (
            f"Kelly sizing: {original_pct:.1%} "
            f"(confidence={confidence:.2f}, win_rate={self.win_rate:.1%}, "
            f"R:R={take_profit_pct/stop_loss_pct:.2f}x) "
            f"→ capped at {position_size_pct:.1%} of portfolio"
        )

        if original_pct < self.MIN_POSITION_SIZE_PCT:
            reasoning += f" [raised to minimum {self.MIN_POSITION_SIZE_PCT:.1%}]"
        elif original_pct > self.MAX_POSITION_SIZE_PCT:
            reasoning += f" [capped at maximum {self.MAX_POSITION_SIZE_PCT:.1%}]"

        logger.info(
            f"Position Size for {signal.ticker}: "
            f"${position_value:,.2f} ({position_size_pct:.1%} of portfolio) - "
            f"{reasoning}"
        )

        return position_value, reasoning

    def calculate_quantity(
        self, signal: Signal, portfolio: Portfolio
    ) -> tuple[Decimal, str]:
        """Calculate number of shares to buy based on Kelly sizing.

        Args:
            signal: Trading signal
            portfolio: Current portfolio state

        Returns:
            Tuple of (quantity, reasoning)
        """
        position_value, reasoning = self.calculate_position_size(signal, portfolio)

        # Calculate quantity
        quantity = position_value / signal.entry_price

        # Round to whole shares (bracket orders require whole shares)
        quantity = Decimal(int(quantity))

        # Ensure at least 1 share
        if quantity < 1:
            quantity = Decimal("1")
            reasoning += " [minimum 1 share]"

        return quantity, reasoning

    @classmethod
    async def from_historical_data(cls, supabase_client) -> "PositionSizer":
        """Create PositionSizer from historical trade data in Supabase.

        Args:
            supabase_client: Supabase client instance

        Returns:
            PositionSizer configured with historical performance
        """
        try:
            # Query closed trades (those with exit_price)
            response = (
                supabase_client.table("trades")
                .select("pnl_pct")
                .not_.is_("pnl_pct", "null")
                .order("date", desc=True)
                .limit(100)
                .execute()
            )

            if not response.data or len(response.data) < 10:
                logger.warning(
                    "Insufficient historical data for position sizing, using defaults"
                )
                return cls()

            # Calculate win rate and average returns
            pnl_values = [Decimal(str(trade["pnl_pct"])) for trade in response.data]
            wins = [pnl for pnl in pnl_values if pnl > 0]
            losses = [abs(pnl) for pnl in pnl_values if pnl < 0]

            win_rate = Decimal(len(wins)) / Decimal(len(pnl_values))
            avg_win = sum(wins) / Decimal(len(wins)) if wins else Decimal("0.08")
            avg_loss = sum(losses) / Decimal(len(losses)) if losses else Decimal("0.03")

            logger.info(
                f"Loaded historical performance: "
                f"{len(response.data)} trades, "
                f"win_rate={win_rate:.2%}, "
                f"avg_win={avg_win:.2%}, "
                f"avg_loss={avg_loss:.2%}"
            )

            return cls(win_rate=win_rate, avg_win=avg_win, avg_loss=avg_loss)

        except Exception as e:
            logger.error(f"Failed to load historical data: {e}, using defaults")
            return cls()


# Singleton instance (created on first use)
_position_sizer: Optional[PositionSizer] = None


def get_position_sizer() -> PositionSizer:
    """Get global PositionSizer instance (singleton pattern).

    Returns:
        PositionSizer instance
    """
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = PositionSizer()
    return _position_sizer


async def initialize_position_sizer(supabase_client) -> None:
    """Initialize position sizer with historical data from Supabase.

    Args:
        supabase_client: Supabase client instance
    """
    global _position_sizer
    _position_sizer = await PositionSizer.from_historical_data(supabase_client)
