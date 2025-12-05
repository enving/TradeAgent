"""Backtesting engine for simulating trading strategies."""

from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import yfinance as yf

from src.models.portfolio import Portfolio, Position
from src.strategies.momentum_trading import scan_for_signals, check_exit_conditions
from src.core.risk_manager import filter_signals_by_risk, validate_signal_risk, calculate_position_size
from src.utils.logger import logger

class MockAlpacaClient:
    """Mock Alpaca client for backtesting."""
    
    def __init__(self, data_cache: dict):
        self.data_cache = data_cache
        self.current_date = None

    async def get_latest_quote(self, symbol: str) -> dict:
        """Get 'latest' quote from historical data."""
        if symbol not in self.data_cache:
            return {"price": 0}
        
        df = self.data_cache[symbol]
        # Find row for current date
        try:
            row = df.loc[self.current_date]
            return {"price": float(row["Close"])}
        except KeyError:
            # If no data for date (weekend/holiday), try previous day
            # Simplified: just return 0 or handle in engine
            return {"price": 0}

class BacktestEngine:
    """Simulates trading over a historical period."""

    def __init__(self, start_date: datetime, end_date: datetime, initial_capital: float = 10000.0):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = Decimal(str(initial_capital))
        
        self.portfolio = Portfolio(
            portfolio_value=self.initial_capital,
            cash=self.initial_capital,
            buying_power=self.initial_capital,
            equity=Decimal(0),
            positions=[]
        )
        self.positions: list[Position] = []
        self.trade_history = []
        self.daily_values = []
        
        self.data_cache = {}

    async def load_data(self, tickers: list[str]):
        """Pre-load historical data for all tickers."""
        logger.info("Loading historical data...")
        for ticker in tickers:
            # Fetch data with buffer for indicators
            start_buffer = self.start_date - timedelta(days=100)
            df = yf.download(ticker, start=start_buffer, end=self.end_date, progress=False)
            self.data_cache[ticker] = df
        logger.info("Data loaded.")

    async def run(self):
        """Run the backtest simulation."""
        logger.info(f"Starting backtest from {self.start_date.date()} to {self.end_date.date()}")
        
        current_date = self.start_date
        mock_client = MockAlpacaClient(self.data_cache)

        while current_date <= self.end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            mock_client.current_date = current_date.strftime("%Y-%m-%d")
            logger.info(f"--- Simulating {current_date.date()} ---")

            # 1. Update Portfolio Value
            total_value = self.portfolio.cash
            for pos in self.positions:
                quote = await mock_client.get_latest_quote(pos.symbol)
                price = Decimal(str(quote["price"]))
                if price > 0:
                    pos.current_price = price
                    pos.market_value = price * pos.quantity
                    pos.unrealized_pnl = (price - pos.avg_entry_price) * pos.quantity
                    pos.unrealized_pnl_pct = (price - pos.avg_entry_price) / pos.avg_entry_price
                    total_value += pos.market_value
            
            self.portfolio.portfolio_value = total_value
            self.portfolio.equity = total_value - self.portfolio.cash
            self.portfolio.buying_power = self.portfolio.cash # Simplified
            self.daily_values.append({"date": current_date, "value": float(total_value)})

            # 2. Check Exits
            active_positions = []
            for pos in self.positions:
                should_exit, reason = await check_exit_conditions(pos, mock_client)
                if should_exit:
                    # Execute Sell
                    proceeds = pos.quantity * pos.current_price
                    self.portfolio.cash += proceeds
                    
                    trade_record = {
                        "date": current_date,
                        "ticker": pos.symbol,
                        "action": "SELL",
                        "price": float(pos.current_price),
                        "shares": float(pos.quantity),
                        "reason": reason,
                        "pnl": float(proceeds - (pos.quantity * pos.avg_entry_price))
                    }
                    self.trade_history.append(trade_record)
                    logger.info(f"SELL {pos.symbol} ({reason}): ${float(pos.current_price):.2f}")
                else:
                    active_positions.append(pos)
            self.positions = active_positions

            # 3. Scan for Entries
            for ticker, df in self.data_cache.items():
                try:
                    # Get data up to today
                    hist = df.loc[:current_date]
                    if len(hist) < 50: continue
                    
                    # Calculate Indicators
                    # RSI
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs)).iloc[-1]
                    
                    # MACD
                    exp12 = hist['Close'].ewm(span=12, adjust=False).mean()
                    exp26 = hist['Close'].ewm(span=26, adjust=False).mean()
                    macd = exp12 - exp26
                    signal_line = macd.ewm(span=9, adjust=False).mean()
                    histogram = (macd - signal_line).iloc[-1]
                    
                    # SMAs
                    sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                    sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
                    price = hist['Close'].iloc[-1]
                    
                    # Volume Ratio
                    vol_avg = hist['Volume'].rolling(window=20).mean().iloc[-1]
                    vol_ratio = hist['Volume'].iloc[-1] / vol_avg if vol_avg > 0 else 0
                    
                    # New Strict Entry Criteria
                    # 1. RSI 55-70
                    # 2. MACD > 0
                    # 3. Price > SMA50
                    # 4. SMA20 > SMA50 (Golden Cross alignment)
                    # 5. Volume > 1.2x avg
                    
                    if (55 < rsi < 70 and 
                        histogram > 0 and 
                        price > sma50 and 
                        sma20 > sma50 and 
                        vol_ratio > 1.2):
                        # Check if already owned
                        if any(p.symbol == ticker for p in self.positions):
                            continue
                            
                        # Generate Signal
                        signal = type('Signal', (), {})() # Dummy object
                        signal.ticker = ticker
                        signal.entry_price = Decimal(str(price))
                        signal.stop_loss = signal.entry_price * Decimal("0.95")
                        signal.take_profit = signal.entry_price * Decimal("1.15")
                        signal.strategy = "backtest_momentum"
                        signal.target_value = None # Required for calc
                        signal.current_value = None # Required for calc
                        
                        # Sizing
                        shares = calculate_position_size(signal, self.portfolio)
                        
                        if shares > 0:
                            cost = shares * signal.entry_price
                            self.portfolio.cash -= cost
                            
                            new_pos = Position(
                                symbol=ticker,
                                quantity=shares,
                                avg_entry_price=signal.entry_price,
                                current_price=signal.entry_price,
                                market_value=cost,
                                unrealized_pnl=Decimal(0),
                                unrealized_pnl_pct=Decimal(0)
                            )
                            self.positions.append(new_pos)
                            
                            self.trade_history.append({
                                "date": current_date,
                                "ticker": ticker,
                                "action": "BUY",
                                "price": float(price),
                                "shares": float(shares)
                            })
                            logger.info(f"BUY {ticker}: ${float(price):.2f}")

                except Exception as e:
                    continue

            current_date += timedelta(days=1)

        return self.daily_values, self.trade_history
