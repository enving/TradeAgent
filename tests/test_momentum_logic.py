import pytest
import pandas as pd
from src.strategies.momentum_trading import check_momentum_entry


@pytest.fixture
def mock_params():
    return {
        "rsi_lower": 50,
        "rsi_upper": 75,
        "macd_threshold": 0.0,
        "volume_ratio": 1.1,
        "volatility_threshold": 0.04,
    }


@pytest.fixture
def valid_bar():
    return pd.Series(
        {
            "rsi": 60,
            "histogram": 0.5,
            "close": 150.0,
            "sma50": 140.0,
            "sma20": 145.0,
            "volume_ratio": 1.5,
            "high": 152.0,
            "low": 148.0,
        }
    )


def test_valid_entry(valid_bar, mock_params):
    assert check_momentum_entry(valid_bar, mock_params) is True


def test_rsi_too_low(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["rsi"] = 40
    assert check_momentum_entry(bar, mock_params) is False


def test_rsi_too_high(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["rsi"] = 80
    assert check_momentum_entry(bar, mock_params) is False


def test_macd_negative(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["histogram"] = -0.1
    assert check_momentum_entry(bar, mock_params) is False


def test_below_sma50(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["close"] = 130.0
    assert check_momentum_entry(bar, mock_params) is False


def test_death_cross(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["sma20"] = 135.0
    assert check_momentum_entry(bar, mock_params) is False


def test_low_volume(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["volume_ratio"] = 1.0
    assert check_momentum_entry(bar, mock_params) is False


def test_high_volatility(valid_bar, mock_params):
    bar = valid_bar.copy()
    bar["high"] = 160.0
    bar["low"] = 140.0
    assert check_momentum_entry(bar, mock_params) is False
