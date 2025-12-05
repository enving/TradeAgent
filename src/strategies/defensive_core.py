"""Defensive core strategy: Buy & Hold ETFs with monthly rebalancing.

100% deterministic - no LLM decisions.
Allocates 50% of portfolio to stable ETFs (VTI, VGK, GLD).
"""

from datetime import date
from decimal import Decimal

from ..adapters.market_data_adapter import get_market_data_adapter
from ..models.portfolio import Portfolio, Position
from ..models.trade import Signal
from ..utils.logger import logger

# Import to get current prices
import asyncio

# Target allocations for defensive core (30% of total portfolio)
# OPTIMIZED: Reduced from 50% to free up capital for active trading
TARGET_ALLOCATIONS = {
    "VTI": Decimal("0.15"),  # 15% - US Total Market (was 25%)
    "VGK": Decimal("0.08"),  # 8% - Europe (was 15%)
    "GLD": Decimal("0.07"),  # 7% - Gold (was 10%)
}
# Total: 30% defensive, 70% available for active momentum trading

# Rebalancing threshold (portfolio drift)
REBALANCE_DRIFT_THRESHOLD = Decimal("0.05")  # 5% drift triggers rebalancing


async def should_rebalance(today: date, positions: list[Position], portfolio: Portfolio) -> bool:
    """Check if portfolio rebalancing is needed.

    Rebalancing triggers:
    1. First trading day of the month
    2. Portfolio drift > 5% from target allocations

    Args:
        today: Current date
        positions: List of open positions
        portfolio: Current portfolio state

    Returns:
        True if rebalancing is needed, False otherwise
    """
    # Trigger 1: First trading day of month (using market calendar)
    adapter = await get_market_data_adapter()
    if await adapter.is_first_trading_day_of_month(today):
        logger.info("Rebalancing triggered: First trading day of month")
        return True

    # Trigger 2: Check for portfolio drift
    for symbol, target_pct in TARGET_ALLOCATIONS.items():
        # Find current position
        position = next((p for p in positions if p.symbol == symbol), None)

        if position is None:
            current_pct = Decimal("0")
            current_value = Decimal("0")
        else:
            current_value = position.market_value
            current_pct = current_value / portfolio.portfolio_value

        # Calculate drift from target
        drift = abs(current_pct - target_pct)

        if drift > REBALANCE_DRIFT_THRESHOLD:
            logger.info(
                f"Rebalancing triggered: {symbol} drift {drift:.2%} "
                f"(current: {current_pct:.2%}, target: {target_pct:.2%})"
            )
            return True

    logger.debug("No rebalancing needed")
    return False


async def calculate_rebalancing_orders(
    positions: list[Position], portfolio: Portfolio, alpaca_client
) -> list[Signal]:
    """Calculate buy/sell orders to reach target allocations.

    Pure math - calculates exact orders needed to rebalance portfolio.

    Args:
        positions: List of open positions
        portfolio: Current portfolio state
        alpaca_client: Alpaca client to fetch current prices

    Returns:
        List of trading signals to execute rebalancing
    """
    signals = []

    for symbol, target_pct in TARGET_ALLOCATIONS.items():
        # Calculate target value
        target_value = portfolio.portfolio_value * target_pct

        # Find current position
        position = next((p for p in positions if p.symbol == symbol), None)

        if position is None:
            current_value = Decimal("0")
            current_price = None
        else:
            current_value = position.market_value
            current_price = position.current_price

        # Calculate difference
        diff = target_value - current_value

        # Only create order if difference is significant (>$100)
        if abs(diff) > Decimal("100"):
            action = "BUY" if diff > 0 else "SELL"

            # Fetch current price if we don't have it
            if current_price is None:
                try:
                    quote = await alpaca_client.get_latest_quote(symbol)
                    current_price = Decimal(str(quote.get("ask", quote.get("price", 1.0))))
                    logger.debug(f"Fetched {symbol} price: ${current_price}")
                except Exception as e:
                    logger.warning(f"Could not fetch price for {symbol}: {e}")
                    current_price = Decimal("1.0")  # Fallback

            # Calculate target dollar amount for this order
            target_dollar_amount = abs(diff)

            signal = Signal(
                ticker=symbol,
                action=action,
                entry_price=current_price,
                confidence=Decimal("1.0"),  # Deterministic
                strategy="defensive",
            )

            # Store target dollar amount as metadata (we'll use it for position sizing)
            signal.target_value = target_value
            signal.current_value = current_value

            signals.append(signal)

            logger.info(
                f"Rebalance {symbol}: {action} ${target_dollar_amount:.2f} to reach "
                f"${target_value:.2f} (current: ${current_value:.2f})"
            )

    return signals


def get_defensive_symbols() -> set[str]:
    """Get set of defensive core ticker symbols.

    Used to identify which positions are part of defensive core.

    Returns:
        Set of ticker symbols
    """
    return set(TARGET_ALLOCATIONS.keys())


def calculate_defensive_exposure(positions: list[Position]) -> Decimal:
    """Calculate total exposure to defensive core positions.

    Args:
        positions: List of open positions

    Returns:
        Total market value of defensive positions
    """
    defensive_symbols = get_defensive_symbols()

    defensive_positions = [p for p in positions if p.symbol in defensive_symbols]

    total_exposure = sum(p.market_value for p in defensive_positions)

    logger.debug(f"Defensive core exposure: ${total_exposure:.2f}")

    return total_exposure


def validate_allocation_percentages() -> bool:
    """Validate that target allocations sum to expected value.

    Defensive core should be 30% of portfolio total.

    Returns:
        True if allocations are valid
    """
    total = sum(TARGET_ALLOCATIONS.values())
    expected = Decimal("0.30")  # 30% of portfolio (reduced from 50%)

    if total != expected:
        logger.error(
            f"Invalid defensive core allocations: {total:.2%} " f"(expected {expected:.2%})"
        )
        return False

    return True
