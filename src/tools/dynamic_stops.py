"""Dynamic Stop-Loss and Take-Profit Calculator.

Uses ATR (Average True Range) instead of fixed percentages.
Adapts to each stock's volatility.

Benefits:
- Tight stops on low-volatility stocks
- Wider stops on high-volatility stocks
- Better risk/reward ratios
"""

from decimal import Decimal
from typing import Tuple
import yfinance as yf
import pandas as pd

from ..utils.logger import logger


def calculate_atr(ticker: str, period: int = 14, days: int = 60) -> float:
    """Calculate Average True Range for a ticker.

    Args:
        ticker: Stock symbol
        period: ATR period (default 14 days)
        days: Historical days to fetch

    Returns:
        ATR value
    """
    try:
        # Fetch historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")

        if hist.empty or len(hist) < period:
            logger.warning(f"Insufficient data for {ticker} ATR calculation")
            return 0.0

        # Calculate True Range
        hist["H-L"] = hist["High"] - hist["Low"]
        hist["H-PC"] = abs(hist["High"] - hist["Close"].shift(1))
        hist["L-PC"] = abs(hist["Low"] - hist["Close"].shift(1))

        hist["TR"] = hist[["H-L", "H-PC", "L-PC"]].max(axis=1)

        # Calculate ATR (simple moving average of TR)
        atr = hist["TR"].rolling(window=period).mean().iloc[-1]

        return float(atr) if not pd.isna(atr) else 0.0

    except Exception as e:
        logger.error(f"Error calculating ATR for {ticker}: {e}")
        return 0.0


def calculate_dynamic_stops(
    ticker: str,
    entry_price: Decimal,
    risk_multiplier: float = 2.0,
    reward_multiplier: float = 3.0,
    fallback_stop_pct: float = 0.03,
    fallback_target_pct: float = 0.08,
) -> Tuple[Decimal, Decimal]:
    """Calculate dynamic stop-loss and take-profit based on ATR.

    Uses volatility-adjusted stops instead of fixed percentages.

    Args:
        ticker: Stock symbol
        entry_price: Entry price for the trade
        risk_multiplier: ATR multiplier for stop-loss (default 2.0)
        reward_multiplier: ATR multiplier for take-profit (default 3.0)
        fallback_stop_pct: Fallback stop-loss % if ATR fails (default 3%)
        fallback_target_pct: Fallback take-profit % if ATR fails (default 8%)

    Returns:
        Tuple of (stop_loss, take_profit)

    Example:
        AAPL trading at $180, ATR = $3
        Stop-Loss = $180 - (2 * $3) = $174
        Take-Profit = $180 + (3 * $3) = $189
        Risk/Reward = 1.5:1
    """
    try:
        # Calculate ATR
        atr = calculate_atr(ticker)

        if atr == 0.0 or atr > float(entry_price) * 0.5:
            # ATR calculation failed or unrealistic - use fallback
            logger.warning(
                f"ATR unavailable or unrealistic for {ticker} (ATR={atr}), using fallback stops"
            )
            stop_loss = entry_price * Decimal(str(1 - fallback_stop_pct))
            take_profit = entry_price * Decimal(str(1 + fallback_target_pct))
            return stop_loss, take_profit

        # Calculate dynamic stops based on ATR
        atr_decimal = Decimal(str(atr))
        stop_loss = entry_price - (atr_decimal * Decimal(str(risk_multiplier)))
        take_profit = entry_price + (atr_decimal * Decimal(str(reward_multiplier)))

        # Ensure stops are reasonable (min 1%, max 10%)
        min_stop = entry_price * Decimal("0.99")  # Max 1% stop
        max_stop = entry_price * Decimal("0.90")  # Min 10% stop

        if stop_loss > min_stop:
            logger.debug(
                f"{ticker}: ATR stop ({stop_loss}) too tight, using min 1%"
            )
            stop_loss = min_stop
        elif stop_loss < max_stop:
            logger.debug(
                f"{ticker}: ATR stop ({stop_loss}) too wide, using max 10%"
            )
            stop_loss = max_stop

        # Ensure take-profit is at least 1.5x risk (min risk/reward ratio)
        risk = entry_price - stop_loss
        min_take_profit = entry_price + (risk * Decimal("1.5"))

        if take_profit < min_take_profit:
            logger.debug(
                f"{ticker}: ATR target too low, adjusting to 1.5x risk/reward"
            )
            take_profit = min_take_profit

        # Log the calculation
        risk_pct = float((entry_price - stop_loss) / entry_price * 100)
        reward_pct = float((take_profit - entry_price) / entry_price * 100)
        risk_reward = reward_pct / risk_pct if risk_pct > 0 else 0

        logger.info(
            f"{ticker} Dynamic Stops: Entry=${entry_price:.2f}, "
            f"Stop=${stop_loss:.2f} (-{risk_pct:.1f}%), "
            f"Target=${take_profit:.2f} (+{reward_pct:.1f}%), "
            f"R/R={risk_reward:.2f}:1, ATR=${atr:.2f}"
        )

        return stop_loss, take_profit

    except Exception as e:
        logger.error(f"Error calculating dynamic stops for {ticker}: {e}")
        # Fallback to fixed percentages
        stop_loss = entry_price * Decimal(str(1 - fallback_stop_pct))
        take_profit = entry_price * Decimal(str(1 + fallback_target_pct))
        return stop_loss, take_profit


def calculate_trailing_stop(
    ticker: str,
    entry_price: Decimal,
    current_price: Decimal,
    initial_stop: Decimal,
    atr_multiplier: float = 2.0,
) -> Decimal:
    """Calculate trailing stop-loss that moves with profitable trades.

    Args:
        ticker: Stock symbol
        entry_price: Original entry price
        current_price: Current market price
        initial_stop: Initial stop-loss level
        atr_multiplier: ATR multiplier for trailing distance

    Returns:
        New trailing stop-loss level
    """
    try:
        # Only trail if in profit
        if current_price <= entry_price:
            return initial_stop

        # Calculate ATR
        atr = calculate_atr(ticker)

        if atr == 0.0:
            # Fallback: trail by 50% of profit
            profit = current_price - entry_price
            new_stop = current_price - (profit * Decimal("0.5"))
        else:
            # ATR-based trailing
            atr_decimal = Decimal(str(atr))
            new_stop = current_price - (atr_decimal * Decimal(str(atr_multiplier)))

        # Never lower the stop (only trail up)
        trailing_stop = max(initial_stop, new_stop)

        logger.debug(
            f"{ticker} Trailing Stop: Entry=${entry_price:.2f}, "
            f"Current=${current_price:.2f}, "
            f"Stop=${trailing_stop:.2f}"
        )

        return trailing_stop

    except Exception as e:
        logger.error(f"Error calculating trailing stop for {ticker}: {e}")
        return initial_stop
