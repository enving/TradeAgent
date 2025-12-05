"""Alpaca client wrapper for paper trading operations.

Uses alpaca-py SDK for all trading operations.
Implements rate limiting and error handling for robust trading.
"""

from decimal import Decimal
from typing import Any, Literal

import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    ClosePositionRequest,
    GetPortfolioHistoryRequest,
    MarketOrderRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from ..models.portfolio import Portfolio, Position
from ..utils.config import config
from ..utils.logger import logger
from .data_client import ALPACA_LIMITER


class AlpacaMCPClient:
    """Wrapper for Alpaca SDK (Paper Trading).

    Provides async methods for all trading operations:
    - Account information and buying power
    - Position management
    - Order submission (market, bracket orders)
    - Historical market data (OHLCV bars)
    - Real-time quotes

    Example:
        client = AlpacaMCPClient()
        portfolio = await client.get_account()
        positions = await client.get_positions()
    """

    def __init__(self) -> None:
        """Initialize Alpaca SDK clients (paper trading)."""
        # Trading client for orders, positions, account
        self.trading_client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True,  # CRITICAL: Paper trading only
        )

        # Data client for historical bars and quotes
        self.data_client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
        )

        logger.info("Alpaca SDK clients initialized (Paper Trading)")

    async def get_account(self) -> Portfolio:
        """Get current account state from Alpaca.

        Returns portfolio value, cash, buying power, and positions.

        Returns:
            Portfolio object with current account state

        Raises:
            Exception: If SDK call fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            logger.info("Fetching account information from Alpaca")

            # Get account from Alpaca SDK
            account = self.trading_client.get_account()

            # Convert to our Portfolio model
            portfolio = Portfolio(
                cash=Decimal(str(account.cash)),
                portfolio_value=Decimal(str(account.portfolio_value)),
                buying_power=Decimal(str(account.buying_power)),
                equity=Decimal(str(account.equity)),
            )

            logger.debug(f"Portfolio value: ${portfolio.portfolio_value}")

            return portfolio

        except Exception as e:
            logger.error(f"Failed to get account from Alpaca: {e}")
            raise

    async def get_positions(self) -> list[Position]:
        """Get all open positions from Alpaca.

        Returns:
            List of Position objects

        Raises:
            Exception: If SDK call fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            logger.info("Fetching positions from Alpaca")

            # Get positions from Alpaca SDK
            alpaca_positions = self.trading_client.get_all_positions()

            # Convert to our Position models
            positions = []
            for pos in alpaca_positions:
                position = Position(
                    symbol=pos.symbol,
                    quantity=Decimal(str(pos.qty)),
                    avg_entry_price=Decimal(str(pos.avg_entry_price)),
                    current_price=Decimal(str(pos.current_price)),
                    market_value=Decimal(str(pos.market_value)),
                    unrealized_pnl=Decimal(str(pos.unrealized_pl)),
                    unrealized_pnl_pct=Decimal(str(pos.unrealized_plpc)),
                )
                positions.append(position)

            logger.debug(f"Found {len(positions)} open positions")

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions from Alpaca: {e}")
            raise

    async def submit_market_order(
        self,
        symbol: str,
        qty: Decimal,
        side: Literal["buy", "sell"],
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> str:
        """Submit a market order to Alpaca.

        CRITICAL: Uses bracket orders if stop_loss/take_profit provided.
        This ensures risk management is built into every trade.

        Args:
            symbol: Stock ticker symbol
            qty: Number of shares to trade
            side: "buy" or "sell"
            stop_loss: Stop-loss price (optional)
            take_profit: Take-profit price (optional)

        Returns:
            Alpaca order ID

        Raises:
            Exception: If order submission fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            # Determine order side
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # Build market order request
            # Note: Bracket orders require whole share quantities
            quantity = float(qty)
            if stop_loss or take_profit:
                # Round to whole shares for bracket orders
                quantity = int(round(quantity))

            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=TimeInForce.DAY,
            )

            # Add bracket orders if stop-loss/take-profit specified
            if stop_loss or take_profit:
                order_data.order_class = OrderClass.BRACKET
                if stop_loss:
                    # Round to 2 decimal places (Alpaca requirement)
                    order_data.stop_loss = {"stop_price": round(float(stop_loss), 2)}
                if take_profit:
                    # Round to 2 decimal places (Alpaca requirement)
                    order_data.take_profit = {"limit_price": round(float(take_profit), 2)}

            logger.info(
                f"Submitting order: {side.upper()} {qty} {symbol} "
                f"(SL: {stop_loss}, TP: {take_profit})"
            )

            # Submit order via Alpaca SDK
            order = self.trading_client.submit_order(order_data)

            logger.info(f"Order submitted successfully: {order.id}")

            return str(order.id)

        except Exception as e:
            logger.error(f"Failed to submit order for {symbol}: {e}")
            raise

    async def close_position(self, symbol: str) -> bool:
        """Close an entire position.

        Args:
            symbol: Stock ticker symbol to close

        Returns:
            True if successful

        Raises:
            Exception: If close position fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            logger.info(f"Closing position for {symbol}")

            # Close position via Alpaca SDK
            self.trading_client.close_position(symbol)

            logger.info(f"Position closed successfully: {symbol}")

            return True

        except Exception as e:
            logger.error(f"Failed to close position for {symbol}: {e}")
            raise

    async def get_bars(self, symbol: str, days: int = 30, timeframe: str = "1Day") -> pd.DataFrame:
        """Get historical OHLCV bars for a symbol.

        Args:
            symbol: Stock ticker symbol
            days: Number of days of history
            timeframe: Bar timeframe (1Day, 1Hour, etc.)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Raises:
            Exception: If bars fetch fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            from datetime import datetime, timedelta

            logger.debug(f"Fetching {days}d bars for {symbol} ({timeframe})")

            # Calculate start date
            end = datetime.now()
            start = end - timedelta(days=days)

            # Create bars request
            # Paper Trading uses different data feed (no feed parameter needed)
            request_params = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day if timeframe == "1Day" else TimeFrame.Hour,
                start=start,
                end=end,
            )

            # Fetch bars from Alpaca
            bars = self.data_client.get_stock_bars(request_params)

            # Convert to DataFrame
            if symbol in bars:
                df = bars[symbol].df
                # Reset index to make timestamp a column
                df = df.reset_index()
                return df
            else:
                # Return empty DataFrame with correct schema
                return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            raise

    async def get_latest_quote(self, symbol: str) -> dict[str, Any]:
        """Get latest quote for a symbol.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with bid, ask, last price, etc.

        Raises:
            Exception: If quote fetch fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            from alpaca.data.requests import StockLatestQuoteRequest

            logger.debug(f"Fetching latest quote for {symbol}")

            # Create quote request
            request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)

            # Fetch quote from Alpaca
            quotes = self.data_client.get_stock_latest_quote(request_params)

            if symbol in quotes:
                q = quotes[symbol]
                quote = {
                    "symbol": symbol,
                    "bid": float(q.bid_price),
                    "ask": float(q.ask_price),
                    "last": float(q.ask_price),  # Use ask as last for compatibility
                    "price": float(q.ask_price),  # For compatibility
                }
                return quote
            else:
                # Return empty quote
                return {
                    "symbol": symbol,
                    "bid": 0.0,
                    "ask": 0.0,
                    "last": 0.0,
                    "price": 0.0,
                }

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        Args:
            order_id: Alpaca order ID to cancel

        Returns:
            True if successful

        Raises:
            Exception: If cancellation fails
        """
        await ALPACA_LIMITER.acquire()

        try:
            logger.info(f"Cancelling order {order_id}")

            # Cancel order via Alpaca SDK
            self.trading_client.cancel_order_by_id(order_id)

            logger.info(f"Order cancelled successfully: {order_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
