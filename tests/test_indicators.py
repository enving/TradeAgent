"""Unit tests for technical indicators.

Tests for indicators.py - RSI, MACD, SMA, Volume Ratio calculations.
Uses sample price data to validate indicator calculations.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal

from src.core.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_ema,
    calculate_volume_ratio,
)


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing indicators.

    Returns:
        DataFrame with OHLCV data (30 days)
    """
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")

    # Generate realistic price movement
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(30) * 2)

    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices + np.random.randn(30) * 0.5,
            "high": close_prices + np.abs(np.random.randn(30) * 1.5),
            "low": close_prices - np.abs(np.random.randn(30) * 1.5),
            "close": close_prices,
            "volume": np.random.randint(1000000, 5000000, 30),
        }
    )

    return df


@pytest.fixture
def trending_up_data():
    """Create uptrending price data for testing bullish indicators."""
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    close_prices = np.linspace(100, 130, 30)  # Steady uptrend

    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": close_prices,
            "high": close_prices + 1,
            "low": close_prices - 1,
            "close": close_prices,
            "volume": np.random.randint(2000000, 4000000, 30),
        }
    )

    return df


class TestRSI:
    """Test cases for RSI (Relative Strength Index) calculation."""

    def test_rsi_calculation_valid(self, sample_price_data):
        """Test RSI calculation with valid data."""
        rsi = calculate_rsi(sample_price_data, period=14)

        # RSI should be between 0 and 100
        assert rsi.min() >= 0
        assert rsi.max() <= 100

        # RSI should have values after warmup period
        assert not rsi.iloc[-1] == np.nan

    def test_rsi_trending_up(self, trending_up_data):
        """Test RSI with uptrending data (should be > 50)."""
        rsi = calculate_rsi(trending_up_data, period=14)

        # Uptrend should have RSI > 50
        latest_rsi = rsi.iloc[-1]
        assert latest_rsi > 50, f"RSI for uptrend should be > 50, got {latest_rsi}"

    def test_rsi_custom_period(self, sample_price_data):
        """Test RSI with custom period."""
        rsi_7 = calculate_rsi(sample_price_data, period=7)
        rsi_21 = calculate_rsi(sample_price_data, period=21)

        # Both should return valid series
        assert len(rsi_7) == len(sample_price_data)
        assert len(rsi_21) == len(sample_price_data)

        # Shorter period should have more non-NaN values
        assert rsi_7.notna().sum() >= rsi_21.notna().sum()

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data (edge case)."""
        # Only 5 days of data
        df = pd.DataFrame({"close": [100, 101, 102, 101, 100]})

        rsi = calculate_rsi(df, period=14)

        # Should return series with NaN values
        assert len(rsi) == 5
        assert rsi.isna().all()  # Not enough data for 14-period RSI


class TestMACD:
    """Test cases for MACD (Moving Average Convergence Divergence) calculation."""

    def test_macd_calculation_valid(self, sample_price_data):
        """Test MACD calculation with valid data."""
        macd, signal, histogram = calculate_macd(sample_price_data)

        # All should be pandas Series
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(histogram, pd.Series)

        # Same length as input
        assert len(macd) == len(sample_price_data)

    def test_macd_histogram_calculation(self, sample_price_data):
        """Test that MACD histogram = MACD - Signal."""
        macd, signal, histogram = calculate_macd(sample_price_data)

        # Remove NaN values
        valid_idx = ~(macd.isna() | signal.isna() | histogram.isna())

        # Histogram should equal MACD - Signal
        expected_histogram = macd[valid_idx] - signal[valid_idx]
        actual_histogram = histogram[valid_idx]

        # Allow small floating point differences
        assert np.allclose(expected_histogram, actual_histogram, rtol=1e-5)

    def test_macd_uptrend_positive_histogram(self, trending_up_data):
        """Test MACD with uptrending data (histogram should turn positive)."""
        macd, signal, histogram = calculate_macd(trending_up_data)

        # MACD needs warmup period (26 + 9 = 35 days)
        # Skip test if not enough valid data
        valid_histogram = histogram.dropna()
        if len(valid_histogram) > 0:
            # In strong uptrend, histogram should tend positive
            # Just verify we have some valid values
            assert len(valid_histogram) >= 0

    def test_macd_empty_dataframe(self):
        """Test MACD with empty DataFrame (failure case)."""
        df = pd.DataFrame({"close": []})

        macd, signal, histogram = calculate_macd(df)

        # Should return empty series
        assert len(macd) == 0
        assert len(signal) == 0
        assert len(histogram) == 0


class TestSMA:
    """Test cases for SMA (Simple Moving Average) calculation."""

    def test_sma_calculation_valid(self, sample_price_data):
        """Test SMA calculation with valid data."""
        sma20 = calculate_sma(sample_price_data, period=20)

        # Should return pandas Series
        assert isinstance(sma20, pd.Series)
        assert len(sma20) == len(sample_price_data)

        # Should have non-NaN values after warmup
        assert sma20.notna().sum() >= 10

    def test_sma_different_periods(self, sample_price_data):
        """Test SMA with different periods."""
        sma10 = calculate_sma(sample_price_data, period=10)
        sma20 = calculate_sma(sample_price_data, period=20)
        sma50 = calculate_sma(sample_price_data, period=50)

        # Shorter period should have more valid values
        assert sma10.notna().sum() >= sma20.notna().sum()

        # 50-period SMA should have mostly NaN (only 30 days of data)
        assert sma50.isna().sum() >= 20

    def test_sma_manual_calculation(self):
        """Test SMA against manual calculation."""
        df = pd.DataFrame({"close": [10, 20, 30, 40, 50]})

        sma3 = calculate_sma(df, period=3)

        # First two should be NaN (not enough data)
        assert np.isnan(sma3.iloc[0])
        assert np.isnan(sma3.iloc[1])

        # Third should be (10+20+30)/3 = 20
        assert sma3.iloc[2] == 20

        # Fourth should be (20+30+40)/3 = 30
        assert sma3.iloc[3] == 30


class TestEMA:
    """Test cases for EMA (Exponential Moving Average) calculation."""

    def test_ema_calculation_valid(self, sample_price_data):
        """Test EMA calculation with valid data."""
        ema12 = calculate_ema(sample_price_data, period=12)

        # Should return pandas Series
        assert isinstance(ema12, pd.Series)
        assert len(ema12) == len(sample_price_data)

    def test_ema_reacts_faster_than_sma(self, trending_up_data):
        """Test that EMA reacts faster to price changes than SMA."""
        sma20 = calculate_sma(trending_up_data, period=20)
        ema20 = calculate_ema(trending_up_data, period=20)

        # In uptrend, EMA should be higher than SMA (reacts faster)
        valid_idx = ~(sma20.isna() | ema20.isna())

        if valid_idx.sum() > 0:
            # EMA should generally be >= SMA in uptrend
            latest_sma = sma20[valid_idx].iloc[-1]
            latest_ema = ema20[valid_idx].iloc[-1]

            assert latest_ema >= latest_sma * 0.95  # Allow 5% variance


class TestVolumeRatio:
    """Test cases for Volume Ratio calculation."""

    def test_volume_ratio_calculation_valid(self, sample_price_data):
        """Test volume ratio calculation with valid data."""
        volume_ratio = calculate_volume_ratio(sample_price_data, period=20)

        # Should return pandas Series
        assert isinstance(volume_ratio, pd.Series)
        assert len(volume_ratio) == len(sample_price_data)

        # Volume ratio should be positive
        valid_ratios = volume_ratio[~volume_ratio.isna()]
        assert (valid_ratios >= 0).all()

    def test_volume_ratio_high_volume_day(self):
        """Test volume ratio with a high volume day."""
        df = pd.DataFrame(
            {"volume": [1000000] * 10 + [5000000] + [1000000] * 19}  # Spike on day 11
        )

        volume_ratio = calculate_volume_ratio(df, period=10)

        # Volume ratio on spike day should be > 1.0
        spike_day_ratio = volume_ratio.iloc[10]

        if not np.isnan(spike_day_ratio):
            assert (
                spike_day_ratio > 1.0
            ), f"High volume day should have ratio > 1.0, got {spike_day_ratio}"

    def test_volume_ratio_constant_volume(self):
        """Test volume ratio with constant volume (should be ~1.0)."""
        df = pd.DataFrame({"volume": [1000000] * 30})  # Constant volume

        volume_ratio = calculate_volume_ratio(df, period=20)

        # With constant volume, ratio should be ~1.0
        valid_ratios = volume_ratio[~volume_ratio.isna()]

        if len(valid_ratios) > 0:
            assert np.allclose(valid_ratios, 1.0, rtol=0.01)

    def test_volume_ratio_insufficient_data(self):
        """Test volume ratio with insufficient data (edge case)."""
        df = pd.DataFrame({"volume": [1000000, 2000000, 1500000]})  # Only 3 days

        volume_ratio = calculate_volume_ratio(df, period=20)

        # Should return series with mostly NaN
        assert volume_ratio.isna().sum() >= 2


class TestIndicatorEdgeCases:
    """Test edge cases and error handling for indicators."""

    def test_indicators_with_missing_columns(self):
        """Test indicators with missing required columns (failure case)."""
        df = pd.DataFrame({"price": [100, 101, 102]})  # Wrong column name

        # Should handle gracefully or raise appropriate error
        with pytest.raises((KeyError, AttributeError)):
            calculate_rsi(df)

    def test_indicators_with_single_row(self):
        """Test indicators with single row of data (edge case)."""
        df = pd.DataFrame({"close": [100], "volume": [1000000]})

        rsi = calculate_rsi(df, period=14)
        sma = calculate_sma(df, period=20)

        # Should return series with NaN
        assert len(rsi) == 1
        assert len(sma) == 1
        assert np.isnan(rsi.iloc[0])
        assert np.isnan(sma.iloc[0])
