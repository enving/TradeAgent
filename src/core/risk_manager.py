"""Risk management with hard-coded position limits.

Pure deterministic logic - no LLM involvement.
All risk calculations are mathematical and rule-based.
"""

from decimal import Decimal

from ..models.portfolio import Portfolio, Position
from ..models.trade import Signal
from ..risk.correlation_monitor import get_correlation_monitor
from ..risk.position_sizer import get_position_sizer
from ..utils.logger import logger

# CRITICAL: Hard-coded risk limits (no LLM decisions)
MAX_POSITIONS = 5  # Maximum concurrent momentum positions
MAX_POSITION_SIZE_PCT = Decimal("0.10")  # 10% of portfolio per position
MAX_DAILY_RISK_PCT = Decimal("0.02")  # 2% of portfolio risk per trade
DAILY_LOSS_LIMIT_PCT = Decimal("0.03")  # Circuit breaker at -3% daily loss


async def filter_signals_by_risk(
    signals: list[Signal], portfolio: Portfolio, current_positions: list[Position]
) -> list[Signal]:
    """Apply risk filters and sort signals by confidence.

    Pure logic function - filters signals based on:
    1. Maximum position limit
    2. Signal confidence (highest first)
    3. Portfolio correlation (prevents over-concentration)
    4. Sector diversification (max 40% per sector)
    5. Available portfolio slots

    Args:
        signals: List of trading signals to filter
        portfolio: Current portfolio state
        current_positions: List of open positions

    Returns:
        Filtered list of signals within risk limits
    """
    # Count momentum positions (exclude defensive core: VTI, VGK, GLD)
    defensive_symbols = {"VTI", "VGK", "GLD"}
    momentum_positions = [p for p in current_positions if p.symbol not in defensive_symbols]

    # Check position limit
    if len(momentum_positions) >= MAX_POSITIONS:
        logger.warning(
            f"Maximum positions reached ({MAX_POSITIONS}), " f"cannot open new momentum positions"
        )
        return []

    # Sort signals by confidence (highest first)
    signals.sort(key=lambda s: s.confidence, reverse=True)

    # Calculate available slots
    available_slots = MAX_POSITIONS - len(momentum_positions)

    # Filter signals through correlation/sector checks
    correlation_monitor = get_correlation_monitor()
    approved_signals = []
    rejected_count = 0

    for signal in signals:
        if len(approved_signals) >= available_slots:
            break  # Reached available slots

        # Check correlation and sector concentration
        approved, reason = await correlation_monitor.check_new_signal(
            signal, current_positions, portfolio.portfolio_value
        )

        if approved:
            approved_signals.append(signal)
        else:
            rejected_count += 1
            logger.info(
                f"Signal rejected for {signal.ticker}: {reason}"
            )

    logger.info(
        f"Risk filter: {len(approved_signals)}/{len(signals)} signals approved, "
        f"{rejected_count} rejected (correlation/sector), "
        f"({available_slots} slots available)"
    )

    return approved_signals


def calculate_position_size(signal: Signal, portfolio: Portfolio) -> Decimal:
    """Calculate safe position size based on portfolio value.

    Pure math calculation with hard-coded limits.

    For defensive core: Uses target_value to calculate exact shares needed.
    For momentum: Uses 10% max position size limit.

    Args:
        signal: Trading signal with entry price
        portfolio: Current portfolio state

    Returns:
        Number of shares to buy (rounded down)

    Example:
        Portfolio value: $10,000
        Max position size: 10% = $1,000
        Entry price: $100/share
        Position size: 10 shares
    """
    # For defensive core rebalancing: use exact target value
    if signal.strategy == "defensive" and signal.target_value is not None:
        # Calculate dollar amount needed
        target_dollar_amount = abs(signal.target_value - (signal.current_value or Decimal("0")))

        # Calculate shares needed
        shares = target_dollar_amount / signal.entry_price
        shares = shares.quantize(Decimal("0.01"))  # Round to 2 decimal places

        logger.debug(
            f"Defensive rebalancing for {signal.ticker}: "
            f"target=${signal.target_value:.2f}, "
            f"current=${signal.current_value:.2f}, "
            f"entry_price=${signal.entry_price:.2f}, "
            f"shares={shares}"
        )

        return shares

    # For momentum/news strategies: use dynamic Kelly sizing
    position_sizer = get_position_sizer()
    shares, reasoning = position_sizer.calculate_quantity(signal, portfolio)

    logger.info(
        f"Dynamic position sizing for {signal.ticker}: "
        f"{shares} shares @ ${signal.entry_price:.2f} "
        f"({reasoning})"
    )

    return shares


def check_daily_loss_limit(daily_pnl: Decimal, portfolio_value: Decimal) -> bool:
    """Check if daily loss limit has been hit (circuit breaker).

    Pure boolean logic - stops trading if losses exceed 3% in a day.

    Args:
        daily_pnl: Profit/loss for the current day
        portfolio_value: Total portfolio value

    Returns:
        True if circuit breaker triggered (stop trading), False otherwise
    """
    daily_loss_pct = daily_pnl / portfolio_value

    if daily_loss_pct <= -DAILY_LOSS_LIMIT_PCT:
        logger.error(
            f"CIRCUIT BREAKER TRIGGERED: Daily loss {daily_loss_pct:.2%} "
            f"exceeds limit of {DAILY_LOSS_LIMIT_PCT:.2%}. "
            f"Trading halted for today."
        )
        return True

    return False


def validate_signal_risk(signal: Signal, portfolio: Portfolio) -> tuple[bool, str]:
    """Validate that a signal meets risk requirements.

    Checks:
    1. Entry price is positive
    2. Stop-loss is below entry (if provided)
    3. Take-profit is above entry (if provided)
    4. Position size won't exceed limits

    Args:
        signal: Trading signal to validate
        portfolio: Current portfolio state

    Returns:
        Tuple of (is_valid, reason)
    """
    # Check entry price
    if signal.entry_price <= 0:
        return (False, "Invalid entry price (must be > 0)")

    # Check stop-loss
    if signal.stop_loss and signal.stop_loss >= signal.entry_price:
        return (False, "Stop-loss must be below entry price")

    # Check take-profit
    if signal.take_profit and signal.take_profit <= signal.entry_price:
        return (False, "Take-profit must be above entry price")

    # Check if we have enough buying power
    position_size = calculate_position_size(signal, portfolio)
    required_capital = position_size * signal.entry_price

    if required_capital > portfolio.buying_power:
        return (False, f"Insufficient buying power (need ${required_capital:.2f})")

    # Check risk/reward ratio if both SL and TP provided
    if signal.stop_loss and signal.take_profit:
        risk = signal.entry_price - signal.stop_loss
        reward = signal.take_profit - signal.entry_price
        risk_reward_ratio = reward / risk

        if risk_reward_ratio < Decimal("2.0"):
            return (
                False,
                f"Risk/reward ratio too low ({risk_reward_ratio:.2f}, " f"minimum 2.0 required)",
            )

    return (True, "Signal passes all risk checks")


def calculate_portfolio_risk_metrics(
    positions: list[Position], portfolio_value: Decimal
) -> dict[str, Decimal]:
    """Calculate current portfolio risk metrics.

    Pure math calculations for portfolio analysis.

    Args:
        positions: List of open positions
        portfolio_value: Total portfolio value

    Returns:
        Dictionary with risk metrics:
        - total_exposure: Total market value of positions
        - exposure_pct: Positions value / portfolio value
        - largest_position_pct: Largest position as % of portfolio
        - num_positions: Number of open positions
    """
    total_exposure = sum(p.market_value for p in positions)
    exposure_pct = total_exposure / portfolio_value if portfolio_value > 0 else Decimal("0")

    largest_position = max((p.market_value for p in positions), default=Decimal("0"))
    largest_position_pct = (
        largest_position / portfolio_value if portfolio_value > 0 else Decimal("0")
    )

    metrics = {
        "total_exposure": total_exposure,
        "exposure_pct": exposure_pct,
        "largest_position_pct": largest_position_pct,
        "num_positions": Decimal(len(positions)),
    }

    logger.debug(
        f"Portfolio risk: {exposure_pct:.2%} exposed, "
        f"{len(positions)} positions, "
        f"largest: {largest_position_pct:.2%}"
    )

    return metrics
