"""Momentum trading strategy: Technical breakout with RSI/MACD/trend following.

100% deterministic - no LLM decisions.
Uses technical indicators to identify entry/exit points.
Allocates 30% of portfolio to momentum trades (max 5 positions).
"""


from __future__ import annotations

import pandas as pd

from decimal import Decimal

from ..config.strategy_params import get_strategy_parameters
from ..core.indicators import calculate_macd, calculate_rsi, calculate_sma, calculate_volume_ratio
from ..mcp_clients.alpaca_client import AlpacaMCPClient
from ..models.portfolio import Position
from ..models.trade import Signal
from ..utils.config import config
from ..utils.logger import logger
import yfinance as yf

# Expanded Universe for Dynamic Selection
UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "META",
    "TSLA",
    "AMZN",
    "AMD",
    "NFLX",
    "AVGO",
    "JPM",
    "BAC",
    "WFC",
    "GS",
    "MS",  # Banks
    "XOM",
    "CVX",
    "COP",  # Energy
    "LLY",
    "JNJ",
    "PFE",  # Pharma
    "KO",
    "PEP",
    "MCD",  # Consumer
]


def get_dynamic_watchlist() -> list[str]:
    """Select top liquid stocks from universe for momentum scanning.

    Returns:
        List of 15 tickers across multiple sectors for diversified opportunity discovery.
        Uses yfinance (unlimited free tier) so no rate limit concerns.
    """
    # EXPANDED: Now using yfinance instead of Alpha Vantage
    # Can scan more stocks without hitting API limits
    # Diversified across sectors: Tech, Growth, Finance, Energy, Healthcare
    return [
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "META",  # Tech
        "TSLA",
        "AMD",
        "NFLX",
        "AVGO",  # Growth
        "JPM",
        "BAC",  # Finance
        "XOM",
        "CVX",  # Energy
        "LLY",
        "JNJ",  # Healthcare
    ]


# Strategy parameters (dynamically optimized by AdaptiveOptimizer)
# These defaults are used if no optimized parameters exist
DEFAULT_STRATEGY_PARAMS = {
    "rsi_lower": 50,
    "rsi_upper": 75,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.08,
    "volume_ratio": 1.1,
    "macd_threshold": 0.0,
    "volatility_threshold": 0.04,
}


def check_momentum_entry(latest_bar: pd.Series, params: dict[str, float]) -> bool:
    """Check if a bar meets momentum entry criteria.

    Args:
        latest_bar: Row with columns [rsi, histogram, close, sma50, sma20, volume_ratio, high, low]
        params: Strategy parameters

    Returns:
        True if all conditions met
    """
    range_ratio = (latest_bar["high"] - latest_bar["low"]) / latest_bar["close"]

    conditions = [
        params["rsi_lower"] < latest_bar["rsi"] < params["rsi_upper"],
        latest_bar["histogram"] > params["macd_threshold"],
        latest_bar["close"] > latest_bar["sma50"],  # Price above long-term trend
        latest_bar["sma20"] > latest_bar["sma50"],  # Golden Cross alignment
        latest_bar["volume_ratio"] > params["volume_ratio"],
        range_ratio < params.get("volatility_threshold", 0.04),
    ]

    return all(conditions)


async def scan_for_signals(
    alpaca_client: AlpacaMCPClient, tickers: list[str] | None = None
) -> list[Signal]:
    """Scan watchlist for momentum entry signals.

    Pure technical analysis - checks 4 criteria:
    1. RSI between 55-70 (strong momentum, not overbought)
    2. MACD histogram > 0 (positive momentum)
    3. Price > 50-day SMA & SMA20 > SMA50 (strong uptrend)
    4. Volume > 20% above average (institutional interest)

    Args:
        alpaca_client: Alpaca MCP client for market data (used for quotes only)
        tickers: Optional list of tickers to scan (overrides dynamic watchlist)

    Returns:
        List of buy signals meeting all criteria
    """
    signals = []

    # Load dynamic parameters (optimized or defaults)
    params_manager = get_strategy_parameters()
    params = await params_manager.get_parameters("momentum")

    logger.debug(
        f"Using momentum parameters: RSI [{params['rsi_lower']}-{params['rsi_upper']}], "
        f"MACD > {params['macd_threshold']}, Vol > {params['volume_ratio']}"
    )

    # Use yfinance for historical data (Unlimited & Free)
    # Alpha Vantage hit the 25 req/day limit.
    import yfinance as yf

    watchlist = tickers if tickers else get_dynamic_watchlist()

    for ticker in watchlist:
        try:
            # Get 60 days of historical bars from yfinance
            # interval='1d' is standard for daily momentum
            yf_ticker = yf.Ticker(ticker)
            bars = yf_ticker.history(period="3mo", interval="1d")

            # Skip if no data
            if bars.empty:
                logger.warning(f"No data available for {ticker}")
                continue

            # Normalize columns to lowercase for our indicators
            bars.columns = [c.lower() for c in bars.columns]
            # yfinance returns 'Stock Splits' and 'Dividends', we don't need them

            # Calculate indicators
            bars["rsi"] = calculate_rsi(bars)
            macd, signal, histogram = calculate_macd(bars)
            bars["macd"] = macd
            bars["macd_signal"] = signal
            bars["histogram"] = histogram
            bars["sma20"] = calculate_sma(bars, period=20)
            bars["sma50"] = calculate_sma(bars, period=50)
            bars["volume_ratio"] = calculate_volume_ratio(bars)

            # Remove NaN values from indicator warmup
            bars = bars.dropna()

            if bars.empty:
                logger.warning(f"Not enough data for {ticker} after indicator calculation")
                continue

            # Get latest values
            latest = bars.iloc[-1]

            # Entry criteria (ALL must be True) - pure boolean logic
            # Uses dynamically optimized parameters
            if check_momentum_entry(latest, params):
                # Calculate stop-loss and take-profit
                entry_price = Decimal(str(latest["close"]))
                stop_loss = entry_price * Decimal(str(1 - params["stop_loss_pct"]))
                take_profit = entry_price * Decimal(str(1 + params["take_profit_pct"]))

                # Calculate confidence (average of normalized indicators)
                # RSI: normalized to 0-1 based on dynamic range
                rsi_score = (latest["rsi"] - params["rsi_lower"]) / (
                    params["rsi_upper"] - params["rsi_lower"]
                )
                # MACD histogram: higher is better (cap at 1.0)
                macd_score = min(latest["histogram"] / 2, 1.0)
                # Volume ratio: > 1.0 is good (cap at 2.0 = 1.0 score)
                volume_score = min((latest["volume_ratio"] - 1.0) / 1.0, 1.0)

                confidence = (rsi_score + macd_score + volume_score) / 3

                signal = Signal(
                    ticker=ticker,
                    action="BUY",
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    confidence=Decimal(str(confidence)),
                    strategy="momentum",
                    rsi=Decimal(str(latest["rsi"])),
                    macd_histogram=Decimal(str(latest["histogram"])),
                    volume_ratio=Decimal(str(latest["volume_ratio"])),
                )

                signals.append(signal)

                logger.info(
                    f"Momentum signal: {ticker} @ ${entry_price:.2f} "
                    f"(RSI: {latest['rsi']:.1f}, "
                    f"MACD: {latest['histogram']:.3f}, "
                    f"confidence: {confidence:.2f})"
                )

        except Exception as e:
            logger.error(f"Error scanning {ticker}: {e}")
            continue

    logger.info(f"Momentum scan complete: {len(signals)} signals found")
    return signals


async def check_exit_conditions(
    position: Position, alpaca_client: AlpacaMCPClient
) -> tuple[bool, str | None]:
    """Check if a momentum position should be exited.

    Exit triggers:
    1. Stop-loss hit (-5%)
    2. Take-profit hit (+15%)
    3. Technical exit (RSI > 75 or MACD negative)

    Args:
        position: Open position to check
        alpaca_client: Alpaca MCP client for current quote

    Returns:
        Tuple of (should_exit, exit_reason)
    """
    try:
        # Load dynamic parameters
        params_manager = get_strategy_parameters()
        params = await params_manager.get_parameters("momentum")

        # Get current quote from Alpaca (this works even on free tier)
        quote = await alpaca_client.get_latest_quote(position.symbol)
        current_price = Decimal(str(quote.get("price", quote.get("last", 0))))

        # Check stop-loss (P&L <= -5%)
        pnl_pct = (current_price - position.avg_entry_price) / position.avg_entry_price

        if pnl_pct <= Decimal(str(-params["stop_loss_pct"])):
            logger.info(f"Stop-loss triggered for {position.symbol}: {pnl_pct:.2%}")
            return (True, "stop_loss")

        # Check take-profit (P&L >= +15%)
        if pnl_pct >= Decimal(str(params["take_profit_pct"])):
            logger.info(f"Take-profit triggered for {position.symbol}: {pnl_pct:.2%}")
            return (True, "take_profit")

        # Check technical exit using yfinance (Unlimited & Free)
        # Was previously using Alpha Vantage but hitting rate limits
        try:
            ticker = yf.Ticker(position.symbol)
            bars = ticker.history(period="3mo", interval="1d")

            if not bars.empty:
                # Normalize columns to lowercase
                bars.columns = [c.lower() for c in bars.columns]

                bars["rsi"] = calculate_rsi(bars)
                macd, signal, histogram = calculate_macd(bars)
                bars["histogram"] = histogram
                bars = bars.dropna()

                if not bars.empty:
                    latest = bars.iloc[-1]

                    # Exit if RSI > 75 (overbought) or MACD turns negative
                    # In aggressive mode, we are more patient with RSI and MACD
                    rsi_exit_threshold = 85 if config.AGGRESSIVE_MODE else 75
                    macd_exit_enabled = not config.AGGRESSIVE_MODE  # Skip MACD exit if aggressive

                    if latest["rsi"] > rsi_exit_threshold or (
                        macd_exit_enabled and latest["histogram"] < 0
                    ):
                        logger.info(
                            f"Technical exit for {position.symbol}: "
                            f"RSI={latest['rsi']:.1f}, MACD={latest['histogram']:.3f} "
                            f"(Aggressive={config.AGGRESSIVE_MODE})"
                        )
                        return (True, "technical_exit")
        except Exception as e:
            logger.error(f"Error checking technical exit for {position.symbol}: {e}")

        # No exit condition met
        return (False, None)

    except Exception as e:
        logger.error(f"Error checking exit for {position.symbol}: {e}")
        return (False, None)


def update_strategy_parameters(new_params: dict[str, float]) -> None:
    """Update strategy parameters based on performance analysis.

    DEPRECATED: This function is deprecated and should not be used.
    Parameters are now managed by StrategyParametersManager.

    Called by performance analyzer to adjust parameters.

    Args:
        new_params: Dictionary of parameter updates
    """
    logger.warning(
        "update_strategy_parameters is deprecated - parameters are managed by StrategyParametersManager"
    )


def get_current_parameters() -> dict[str, float]:
    """Get current strategy parameters.

    DEPRECATED: This function is deprecated and should not be used.
    Use get_strategy_parameters().get_parameters("momentum") instead.

    Returns:
        Dictionary of current parameter values
    """
    logger.warning(
        "get_current_parameters is deprecated - use get_strategy_parameters().get_parameters('momentum')"
    )
    return DEFAULT_STRATEGY_PARAMS.copy()
