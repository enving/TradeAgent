# Alpaca Features Analysis - Ungenutztes Potenzial

**Datum:** 2025-11-19
**Status:** Feature Gap Analysis

---

## 🎯 Aktuell genutzte Features

### ✅ **Bereits implementiert:**

1. **get_account()** - Account Information
   - Portfolio Value, Cash, Buying Power
   - ✅ Verwendet in: main.py, check_positions.py

2. **get_all_positions()** - Current Positions
   - Symbol, Quantity, P&L, Market Value
   - ✅ Verwendet in: main.py, defensive_core.py

3. **submit_order()** - Market Orders
   - Buy/Sell Orders mit Bracket Orders (Stop-Loss, Take-Profit)
   - ✅ Verwendet in: main.py

4. **close_position()** - Close Position
   - Exit momentum positions
   - ✅ Verwendet in: main.py

5. **get_stock_bars()** - Historical OHLCV Data
   - ⚠️ Blockiert durch Free Tier (recent SIP data)
   - ✅ Verwendet in: momentum_trading.py

6. **get_stock_latest_quote()** - Latest Quote
   - Real-time Bid/Ask
   - ✅ Verwendet in: defensive_core.py

7. **cancel_order_by_id()** - Cancel Order
   - ✅ Implementiert, aber nicht aktiv genutzt

---

## 🚀 Ungenutztes Potenzial - Alpaca Features

### **1. Portfolio History** ⭐⭐⭐⭐⭐ HIGH VALUE

**Alpaca API:**
```python
client.get_portfolio_history(
    period="1M",  # 1 day, 1 week, 1 month, etc.
    timeframe="1D",  # 1Min, 5Min, 15Min, 1H, 1D
    date_start=None,
    date_end=None,
    extended_hours=False
)
```

**Was es liefert:**
- Historische Portfolio Value über Zeit
- Equity Curve
- P&L History
- Profit/Loss Zeitreihen

**Use Cases:**
- ✅ **Sharpe Ratio Berechnung** (brauchen wir Returns über Zeit)
- ✅ **Max Drawdown Tracking** (Peak-to-Trough)
- ✅ **Equity Curve Visualisierung**
- ✅ **Performance Charts für Reports**

**Implementierungs-Aufwand:** 🟢 Niedrig (1-2 Stunden)

**Empfehlung:** ⭐⭐⭐⭐⭐ **SOFORT IMPLEMENTIEREN**

---

### **2. Orders History** ⭐⭐⭐⭐ HIGH VALUE

**Alpaca API:**
```python
client.get_orders(
    status="all",  # open, closed, all
    limit=500,
    after=None,
    until=None,
    direction="desc",
    nested=True  # Include child orders (bracket orders)
)
```

**Was es liefert:**
- Alle Orders (filled, cancelled, pending)
- Order Status Tracking
- Fill Prices vs. Limit Prices (Slippage)
- Timestamps (Order vs. Fill Time)

**Use Cases:**
- ✅ **Slippage Analysis** (Order Price vs. Fill Price)
- ✅ **Order Execution Quality**
- ✅ **Fill Rate Tracking**
- ✅ **Bracket Order Monitoring** (welche Stop-Loss/Take-Profit wurden getriggert?)

**Implementierungs-Aufwand:** 🟢 Niedrig (2-3 Stunden)

**Empfehlung:** ⭐⭐⭐⭐ **IMPLEMENTIEREN**

---

### **3. Market Calendar** ⭐⭐⭐⭐ MEDIUM VALUE

**Alpaca API:**
```python
client.get_calendar(start=None, end=None)
```

**Was es liefert:**
- Trading Days (Market Open/Close)
- Holidays
- Half Days

**Use Cases:**
- ✅ **Smart Scheduling** (nur an Trading Days ausführen)
- ✅ **Rebalancing Timing** (erste Trading Day des Monats)
- ✅ **Avoid Running on Holidays**

**Aktuelles Problem:**
```python
# defensive_core.py:44
if today.day == 1:  # ❌ Könnte ein Feiertag sein!
    rebalance()
```

**Besserer Ansatz:**
```python
if is_first_trading_day_of_month():  # ✅ Prüft Trading Calendar
    rebalance()
```

**Implementierungs-Aufwand:** 🟢 Niedrig (1 Stunde)

**Empfehlung:** ⭐⭐⭐⭐ **IMPLEMENTIEREN**

---

### **4. Market Clock** ⭐⭐⭐ MEDIUM VALUE

**Alpaca API:**
```python
client.get_clock()
```

**Was es liefert:**
```python
{
    "timestamp": "2025-11-19T14:30:00Z",
    "is_open": True,
    "next_open": "2025-11-20T09:30:00Z",
    "next_close": "2025-11-19T16:00:00Z"
}
```

**Use Cases:**
- ✅ **Pre-Market Check** (nur während Market Hours traden)
- ✅ **Smart Retries** (wenn Market closed, warte bis next_open)
- ✅ **Logging** (Market Status in Logs)

**Aktuelles Problem:**
System läuft auch außerhalb Market Hours → Orders werden rejected

**Lösung:**
```python
async def should_trade() -> bool:
    clock = client.get_clock()
    if not clock.is_open:
        logger.info(f"Market closed. Next open: {clock.next_open}")
        return False
    return True
```

**Implementierungs-Aufwand:** 🟢 Niedrig (30 Min)

**Empfehlung:** ⭐⭐⭐ **IMPLEMENTIEREN**

---

### **5. Watchlists** ⭐⭐⭐ LOW-MEDIUM VALUE

**Alpaca API:**
```python
# Create watchlist
client.create_watchlist(name="Momentum", symbols=["AAPL", "MSFT"])

# Get watchlist
client.get_watchlist_by_name("Momentum")

# Add/Remove symbols
client.add_asset_to_watchlist(watchlist_id, symbol)
client.remove_asset_from_watchlist(watchlist_id, symbol)
```

**Use Cases:**
- ✅ **Dynamic Watchlist** (statt hard-coded WATCHLIST)
- ✅ **Multi-Strategy Watchlists** (Momentum, Value, Growth)
- ✅ **Performance-Based Filtering** (nur Top Performer in Watchlist)

**Aktuell:**
```python
# momentum_trading.py:16
WATCHLIST = ["AAPL", "MSFT", "NVDA", ...]  # ❌ Hard-coded
```

**Besser:**
```python
async def get_momentum_watchlist():
    watchlist = client.get_watchlist_by_name("Momentum")
    return [asset.symbol for asset in watchlist.assets]
```

**Implementierungs-Aufwand:** 🟡 Medium (2-3 Stunden)

**Empfehlung:** ⭐⭐⭐ **Optional, später**

---

### **6. Assets Info** ⭐⭐ LOW VALUE

**Alpaca API:**
```python
client.get_asset(symbol="AAPL")
```

**Was es liefert:**
```python
{
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "tradable": True,
    "shortable": True,
    "marginable": True,
    "fractionable": True,
    "status": "active"
}
```

**Use Cases:**
- ✅ **Pre-Trade Validation** (ist Symbol tradable?)
- ✅ **Symbol Info für Reports**

**Implementierungs-Aufwand:** 🟢 Niedrig (30 Min)

**Empfehlung:** ⭐⭐ **Nice-to-have**

---

### **7. Crypto Trading** ⭐⭐ LOW VALUE

**Alpaca API:**
```python
from alpaca.trading.enums import AssetClass

# Crypto orders
client.submit_order(
    symbol="BTCUSD",
    qty=0.1,
    side=OrderSide.BUY,
    type=OrderType.MARKET,
    time_in_force=TimeInForce.GTC
)
```

**Use Cases:**
- ✅ **24/7 Trading** (Crypto markets nie geschlossen)
- ✅ **Diversifikation** (BTC/ETH als defensive Asset)

**Aktueller Status:**
- System ist rein auf Stocks ausgelegt
- Würde neue Strategie benötigen

**Implementierungs-Aufwand:** 🔴 Hoch (1-2 Wochen)

**Empfehlung:** ⭐⭐ **Nicht prioritär**

---

### **8. Corporate Actions & News** ⭐⭐⭐⭐ HIGH VALUE (mit Paid Plan)

**Alpaca API:**
```python
from alpaca.data.historical import NewsClient

news_client = NewsClient(api_key, secret_key)

news = news_client.get_news(
    symbol="AAPL",
    start=datetime.now() - timedelta(days=1),
    end=datetime.now(),
    limit=10
)
```

**Was es liefert:**
- News Headlines
- Corporate Actions (Earnings, Splits, Dividends)
- Timestamps

**Use Cases:**
- ✅ **Event-Driven Trading** (kaufe vor Earnings)
- ✅ **Risk Management** (exit vor negativen News)
- ✅ **LLM Sentiment Analysis Input** (combine mit OpenRouter)

**Problem:**
- Erfordert Paid Alpaca Plan ($99+/Monat)
- Free Tier hat kein News

**Implementierungs-Aufwand:** 🟡 Medium (3-4 Stunden)

**Empfehlung:** ⭐⭐⭐⭐ **Implementieren wenn Paid Plan**

---

## 🎯 Priorisierte Implementierungs-Roadmap

### **Phase 1: Quick Wins (1-2 Tage)**

1. **Market Clock Integration** ⭐⭐⭐
   - Prüfe Market Status vor Trading
   - Verhindere Orders außerhalb Market Hours
   - **Code:** `src/utils/market_status.py`

2. **Market Calendar Integration** ⭐⭐⭐⭐
   - Prüfe Trading Days
   - Erste Trading Day des Monats für Rebalancing
   - **Code:** `src/utils/market_calendar.py`

3. **Portfolio History** ⭐⭐⭐⭐⭐
   - Hole Portfolio Value History
   - Berechne Sharpe Ratio & Max Drawdown
   - **Code:** `src/core/portfolio_analyzer.py`

### **Phase 2: Performance Analytics (3-5 Tage)**

4. **Orders History** ⭐⭐⭐⭐
   - Slippage Analysis
   - Fill Rate Tracking
   - Bracket Order Monitoring
   - **Code:** `src/core/execution_analyzer.py`

5. **Advanced Metrics** ⭐⭐⭐⭐⭐
   - Sharpe Ratio (mit Portfolio History)
   - Max Drawdown
   - Calmar Ratio
   - **Code:** `src/core/performance_analyzer.py` (erweitern)

### **Phase 3: Advanced Features (1-2 Wochen, später)**

6. **Dynamic Watchlists** ⭐⭐⭐
   - Performance-basierte Watchlist Updates
   - Multi-Strategy Watchlists
   - **Code:** `src/strategies/watchlist_manager.py`

7. **News Integration** ⭐⭐⭐⭐ (nur mit Paid Plan)
   - Event-Driven Trading
   - LLM Sentiment Analysis
   - **Code:** `src/llm/news_analyzer.py`

---

## 💡 Konkrete Code-Beispiele

### **Example 1: Portfolio History für Sharpe Ratio**

```python
# src/core/portfolio_analyzer.py

from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient

async def calculate_sharpe_ratio(days: int = 30) -> float:
    """Calculate Sharpe Ratio using Alpaca Portfolio History.

    Args:
        days: Lookback period

    Returns:
        Sharpe Ratio (annualized)
    """
    client = TradingClient(...)

    # Get portfolio history
    history = client.get_portfolio_history(
        period=f"{days}D",
        timeframe="1D"
    )

    # Calculate daily returns
    equity = history.equity
    returns = [(equity[i] - equity[i-1]) / equity[i-1]
               for i in range(1, len(equity))]

    # Calculate Sharpe Ratio
    avg_return = sum(returns) / len(returns)
    std_return = stdev(returns)

    # Annualize (assuming 252 trading days)
    sharpe_ratio = (avg_return / std_return) * sqrt(252)

    return sharpe_ratio
```

### **Example 2: Market Status Check**

```python
# src/utils/market_status.py

async def is_market_open() -> bool:
    """Check if market is currently open."""
    client = TradingClient(...)
    clock = client.get_clock()

    if not clock.is_open:
        logger.info(f"Market closed. Next open: {clock.next_open}")
        return False

    return True

# In main.py
async def daily_trading_loop():
    if not await is_market_open():
        logger.info("Skipping trading - market closed")
        return

    # ... rest of trading logic
```

### **Example 3: First Trading Day of Month**

```python
# src/utils/market_calendar.py

async def is_first_trading_day_of_month() -> bool:
    """Check if today is first trading day of month."""
    client = TradingClient(...)
    today = datetime.now().date()

    # Get this month's calendar
    calendar = client.get_calendar(
        start=today.replace(day=1),
        end=today
    )

    trading_days = [day.date for day in calendar]

    return today == trading_days[0] if trading_days else False

# In defensive_core.py
async def should_rebalance(...):
    # Trigger 1: First trading day of month
    if await is_first_trading_day_of_month():
        logger.info("Rebalancing triggered: First trading day of month")
        return True
```

---

## 📊 Feature Value Matrix

| Feature | Value | Aufwand | Priority | Status |
|---------|-------|---------|----------|--------|
| **Portfolio History** | ⭐⭐⭐⭐⭐ | 🟢 Low | P1 | ❌ Not Implemented |
| **Market Calendar** | ⭐⭐⭐⭐ | 🟢 Low | P1 | ❌ Not Implemented |
| **Market Clock** | ⭐⭐⭐ | 🟢 Low | P1 | ❌ Not Implemented |
| **Orders History** | ⭐⭐⭐⭐ | 🟢 Low | P2 | ❌ Not Implemented |
| **Watchlists** | ⭐⭐⭐ | 🟡 Med | P3 | ❌ Not Implemented |
| **Assets Info** | ⭐⭐ | 🟢 Low | P4 | ❌ Not Implemented |
| **News API** | ⭐⭐⭐⭐ | 🟡 Med | P5 | ❌ Requires Paid Plan |
| **Crypto Trading** | ⭐⭐ | 🔴 High | P6 | ❌ Not Planned |

---

## 🚀 Nächste Schritte

### **Empfehlung: Starte mit Phase 1**

1. **Heute:** Market Clock + Market Calendar
   - Verhindere Orders außerhalb Trading Hours
   - Korrigiere Rebalancing Trigger

2. **Diese Woche:** Portfolio History
   - Implementiere Sharpe Ratio
   - Implementiere Max Drawdown
   - Füge zu Performance Reports hinzu

3. **Nächste Woche:** Orders History
   - Slippage Analysis
   - Fill Rate Tracking

**Aufwand:** ~3-4 Tage für Phase 1+2
**Nutzen:** Massiv verbesserte Analytics & Reliability

---

**Erstellt von:** Claude Code (Sonnet 4.5)
**Datum:** 2025-11-19

---

**Ende der Feature Analysis**
