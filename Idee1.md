# Stock & ETF Trading Workflow mit Alpaca – Detaillierter Plan

## 🎯 Übersicht & Strategie

Dieser Workflow funktioniert ähnlich wie das Krypto-Pendant, konzentriert sich aber auf **US-Aktien und ETFs** mit direkter Tradingfunktionalität über Alpaca.

### Kernkomponenten:
1. **Macro-Kontext** (ähnlich wie Krypto)
2. **Stock-Analysen** (technisch + fundamental)
3. **Market-Signal-Analyse** (via LLM)
4. **Automatisiertes Trading** (Buy/Sell Orders)
5. **Portfolio Management** (Position Tracking)

---

## 📊 Workflow-Architektur

```
[Trigger: Manual oder Schedule]
    ↓
[API-Keys Setup (Alpaca, optional externe Data-APIs)]
    ↓
┌─────────────────────────────────────────────────┐
│           MACRO CONTEXT (Optional)              │
│  • Treasury Yields, Fed Funds Rate               │
│  • VIX Index, Market Sentiment                   │
│  • macroeconomic_brief (LLM-powered)             │
└──────────────────────┬──────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│      STOCK/ETF ANALYSIS LAYER                   │
│  • Get Quote (Price, Change %)                   │
│  • Get Bars (OHLCV für technische Analyse)       │
│  • Get Position (Offene Positionen)              │
│  • Calculate Indicators (SMA, RSI, MACD, etc)    │
└──────────────────────┬──────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│      SIGNAL GENERATION (LLM-basiert)            │
│  • Analysiere Preis, Volumen, Technische        │
│    Indikatoren                                   │
│  • Gebe Signal: BUY / HOLD / SELL                │
│  • Confidence Score (0-100)                      │
└──────────────────────┬──────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│      RISK MANAGEMENT & VALIDATION                │
│  • Check Account Buying Power                    │
│  • Check Position Size (% of Portfolio)          │
│  • Check Stop-Loss & Take-Profit Levels          │
│  • Validate Signal Confidence Threshold          │
└──────────────────────┬──────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│      ORDER EXECUTION                            │
│  • BUY: Place Limit Order (optional)             │
│  • SELL: Close Position oder Partial Sale        │
│  • SET: Stop-Loss & Take-Profit (OCO Orders)     │
└──────────────────────┬──────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│      NOTIFICATION & LOGGING                     │
│  • Send Webhook (Discord, Email, Slack)         │
│  • Log Transaction & Signal to DB                │
│  • Update Dashboard                              │
└─────────────────────────────────────────────────┘
```

---

## 🔑 Alpaca API Integration

### Kritische Endpoints:

| **Endpoint** | **Zweck** | **Parameter** |
|---|---|---|
| `POST /v2/orders` | Neue Order erstellen | symbol, qty, side, type, time_in_force |
| `GET /v2/orders/{order_id}` | Order-Status prüfen | order_id |
| `DELETE /v2/orders/{order_id}` | Order stornieren | order_id |
| `GET /v2/positions/{symbol}` | Position Daten abrufen | symbol |
| `GET /v2/account` | Account Infos (Buying Power, etc) | — |
| `GET /v2/clock` | Markt-Status (open/closed) | — |
| `GET /v2/bars/{symbol}` | OHLCV-Daten | symbol, timeframe, limit |
| `GET /v2/quotes/{symbol}` | Live Quote | symbol |
| `GET /v2/assets` | Asset-Liste | symbols (optional) |

### Authentication:
- **Header**: `APCA-API-KEY-ID` + `APCA-SECRET-KEY`
- **OR** OAuth Token via `issue_tokens` endpoint

---

## 📋 Node-Struktur für n8n

### 1. **Input & Setup**
- Manual Trigger oder Schedule
- Set API Keys (Alpaca Key + Secret)
- Optional: Set Macro Data API Key (z.B. Hunch Machine)

### 2. **Data Collection**
- **Quote Nodes** (parallel):
  - Get Quote: Symbol A (z.B. AAPL)
  - Get Quote: Symbol B (z.B. SPY)
  - Get Quote: Symbol C (z.B. QQQ)
  - Get Quote: VIX (Market Fear)

- **Historical Data Nodes** (parallel):
  - Get Bars: AAPL (1D, 50 candles)
  - Get Bars: SPY (1D, 50 candles)
  - Get Bars: QQQ (1D, 50 candles)

- **Account Status**:
  - Get Account Info
  - Get Positions
  - Get Orders

### 3. **Analysis Layer**
- **Technical Indicators Code Node**:
  - Berechne SMA (20, 50, 200)
  - Berechne RSI(14)
  - Berechne MACD
  - Berechne ATR (für Stop-Loss)
  
- **LLM Analysis**:
  - Input: Alle technischen Daten + Macro Context
  - Output: BUY/SELL/HOLD mit Confidence + Reasoning

- **Risk Check Code Node**:
  - Verfügbares Kapital prüfen
  - Position Size berechnen (2-5% pro Trade)
  - Stop-Loss Level (z.B. -2% ATR)
  - Take-Profit Level (z.B. +3-5%)

### 4. **Order Execution**
- **Condition Node**: Signal == "BUY" && Confidence > 70?
  - **YES** → Place Order (Limit oder Market)
  - **NO** → Skip oder Hold

- **Order Placement**:
  - Create BUY Order
  - Set OCO (One-Cancels-Other) für Stop/TP

- **Post-Trade**:
  - Log Transaction
  - Update Position Tracker
  - Send Notification

### 5. **Output & Reporting**
- Generate Daily Report
- Send Notification (Webhook/Email)
- Optional: Post to X (Twitter)

---

## 🚀 Implementation Steps in n8n

1. **Clone das Krypto-Workflow Template** (falls vorhanden)
2. **Ersetze Hunch Machine API** durch Alpaca Endpoints
3. **Füge die folgenden Custom Code Nodes hinzu**:
   - Technical Indicators Calculator
   - Risk Calculator
   - Order Logic Validator

4. **Teste mit Live-Daten** im "dry-run" Mode
5. **Aktiviere Paper Trading** erst, dann Live Trading (mit kleineren Positionen)

---

## ⚙️ Config-Parameter (In Set Node)

```json
{
  "alpaca_base_url": "https://api.alpaca.markets",
  "alpaca_api_key": "YOUR_KEY",
  "alpaca_secret_key": "YOUR_SECRET",
  "symbols": ["AAPL", "SPY", "QQQ", "TSLA"],
  "timeframe": "1D",
  "position_size_pct": 0.03,
  "risk_per_trade_pct": 0.02,
  "min_confidence": 70,
  "trading_enabled": false,
  "paper_trading": true
}
```

---

## 🛡️ Safety Checks (Wichtig!)

- ✅ Start mit **Paper Trading** (Alpaca: `paper` API endpoint)
- ✅ Small Position Sizes testen
- ✅ Kill-Switch implementieren (Emergency Stop Order)
- ✅ Max Drawdown Limit (z.B. 5% Portfolio)
- ✅ Logging aller Trades & Errors
- ✅ Rate Limiting respektieren (Alpaca: 200 req/min)

---

## 📝 Beispiel-Workflow Szenario

**Trigger**: Täglich um 09:30 UTC (Market Open)

1. Get AAPL Quote & 50-day bars → RSI = 35 (Oversold)
2. Get SPY Quote & SMA(200) → Trending Up
3. Macro: Fed Funds Stable, VIX < 20
4. **LLM Decision**: "AAPL ist oversold in bullischem Markt → BUY"
5. Risk Check: Buying Power = $50k, Position Size = $1.5k (3%)
6. **Place Limit Order**: 10 shares @ $150.50 (unter current price)
7. Set OCO: Stop @ $147 (ATR-based), TP @ $157 (2:1 RR)
8. Log & Notify: "Order #12345 placed for 10 AAPL @ $150.50"

---

## 🔄 Continuous Monitoring

Nach der Order:
- Check Order Status alle 5 Min
- If Filled → Monitor Position
- If Hit TP or SL → Close & Log Profit/Loss
- Update Portfolio Metrics

Optional: Trailing Stop implementieren nach X Profit %

---

