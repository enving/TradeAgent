"""Technical indicators using ta library.

All functions are pure mathematical calculations with no LLM involvement.
Uses ta library for reliable indicator calculations.
"""

import pandas as pd
from ta import momentum, trend


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate RSI - Relative Strength Index.

    Pure math indicator showing overbought/oversold conditions.

    Args:
        df: DataFrame with 'close' column containing price data
        period: Lookback period for RSI calculation (default 14)

    Returns:
        Series with RSI values ranging from 0-100

    Note:
        - RSI < 30: Oversold (potential buy)
        - RSI > 70: Overbought (potential sell)
        - RSI 50: Neutral momentum
    """
    # CRITICAL: ta library syntax
    rsi_indicator = momentum.RSIIndicator(close=df["close"], window=period)
    return rsi_indicator.rsi()


def calculate_macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD - Moving Average Convergence Divergence.

    Pure math indicator showing trend changes and momentum.

    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line EMA period (default 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)

    Note:
        - Histogram > 0: Bullish momentum
        - Histogram < 0: Bearish momentum
        - Crossovers signal trend changes
    """
    # CRITICAL: ta library returns individual series
    macd_indicator = trend.MACD(
        close=df["close"], window_slow=slow, window_fast=fast, window_sign=signal
    )

    macd_line = macd_indicator.macd()
    signal_line = macd_indicator.macd_signal()
    histogram = macd_indicator.macd_diff()

    return macd_line, signal_line, histogram


def calculate_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate SMA - Simple Moving Average.

    Pure math indicator showing average price trend.

    Args:
        df: DataFrame with 'close' column
        period: Lookback period (default 20)

    Returns:
        Series with SMA values

    Note:
        - Price > SMA: Uptrend
        - Price < SMA: Downtrend
    """
    sma_indicator = trend.SMAIndicator(close=df["close"], window=period)
    return sma_indicator.sma_indicator()


def calculate_ema(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """Calculate EMA - Exponential Moving Average.

    Pure math indicator giving more weight to recent prices.

    Args:
        df: DataFrame with 'close' column
        period: Lookback period (default 12)

    Returns:
        Series with EMA values

    Note:
        - Responds faster to price changes than SMA
        - Used in MACD calculation
    """
    ema_indicator = trend.EMAIndicator(close=df["close"], window=period)
    return ema_indicator.ema_indicator()


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate volume ratio vs average volume.

    Pure math indicator showing relative trading activity.

    Args:
        df: DataFrame with 'volume' column
        period: Lookback period for average (default 20)

    Returns:
        Series with volume ratio values

    Note:
        - Ratio > 1.0: Above average volume
        - Ratio < 1.0: Below average volume
        - High volume confirms price moves
    """
    # Calculate average volume over period
    avg_volume = df["volume"].rolling(window=period).mean()

    # Calculate ratio of current volume to average
    volume_ratio = df["volume"] / avg_volume

    return volume_ratio


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to a DataFrame.

    Convenience function to calculate all indicators at once.
    CRITICAL: Always call dropna() after this to remove NaN values
    from indicator warmup period.

    Args:
        df: DataFrame with 'close' and 'volume' columns

    Returns:
        DataFrame with added indicator columns

    Example:
        df = add_all_indicators(bars_df)
        df = df.dropna()  # Remove NaN rows from indicator warmup
    """
    # Add RSI
    df["rsi"] = calculate_rsi(df)

    # Add MACD components
    df["macd"], df["macd_signal"], df["macd_histogram"] = calculate_macd(df)

    # Add moving averages
    df["sma_20"] = calculate_sma(df, period=20)
    df["ema_12"] = calculate_ema(df, period=12)

    # Add volume ratio
    df["volume_ratio"] = calculate_volume_ratio(df)

    return df


def validate_indicators(df: pd.DataFrame) -> bool:
    """Validate that indicators are calculated correctly.

    Checks for common issues like NaN values or out-of-range values.

    Args:
        df: DataFrame with indicator columns

    Returns:
        True if all indicators are valid, False otherwise
    """
    # Check for required columns
    required_cols = ["rsi", "macd_histogram", "sma_20", "volume_ratio"]
    for col in required_cols:
        if col not in df.columns:
            return False

        # Check for all NaN
        if df[col].isna().all():
            return False

    # Check RSI range (should be 0-100)
    if "rsi" in df.columns:
        rsi_valid = df["rsi"].dropna()
        if len(rsi_valid) > 0:
            if (rsi_valid < 0).any() or (rsi_valid > 100).any():
                return False

    return True
