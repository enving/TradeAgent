# TradeAgent - Erkenntnisse & Optimierungen

**Erstellt:** 2025-11-18
**Letzte Aktualisierung:** 2025-11-18

Dieses Dokument dient zur kontinuierlichen Verbesserung des Trading-Systems durch Dokumentation von Erkenntnissen, Analysen und Optimierungsmöglichkeiten.

---

## 📊 Alpaca Market Data - Verfügbare Daten

### Übersicht der Alpaca Data API

Unser System nutzt zwei Alpaca SDK Clients:

1. **TradingClient** - Für Trading-Operationen
2. **StockHistoricalDataClient** - Für Marktdaten

### Verfügbare Datenendpunkte

#### 1. Historical OHLCV Bars (`get_bars`)
**Was wir bekommen:**
- Open, High, Low, Close, Volume (OHLCV)
- Verschiedene Timeframes: 1Day, 1Hour, 1Minute, etc.
- Historische Daten für technische Analyse

**Implementierung:**
```python
async def get_bars(symbol: str, days: int = 30, timeframe: str = "1Day") -> pd.DataFrame
```

**Verwendung:**
- Berechnung technischer Indikatoren (RSI, MACD, SMA)
- Momentum Signal Scanning
- Exit Condition Checks

**Einschränkungen (Free Tier):**
- ❌ Kein Zugriff auf "recent SIP data" (aktuelle Börsendaten)
- ⚠️ Delayed data möglich (15-20 Minuten Verzögerung)
- ✅ Ausreichend für Paper Trading und Backtesting

#### 2. Latest Quotes (`get_latest_quote`)
**Was wir bekommen:**
```python
{
    "symbol": "AAPL",
    "bid": 268.00,      # Highest buy price
    "ask": 268.05,      # Lowest sell price
    "last": 268.05,     # Last traded price
    "price": 268.05     # Alias for compatibility
}
```

**Verwendung:**
- Defensive Core Rebalancing (Preis-Fetching)
- Position Sizing Calculations
- Real-time Entry Price Determination

#### 3. Account Information (`get_account`)
**Was wir bekommen:**
```python
Portfolio(
    cash=Decimal("48175.64"),
    portfolio_value=Decimal("99973.73"),
    buying_power=Decimal("148149.37"),
    equity=Decimal("99973.73")
)
```

**Verwendung:**
- Portfolio Value Berechnung
- Buying Power Checks
- Position Sizing (10% max von portfolio_value)

#### 4. Positions (`get_positions`)
**Was wir bekommen:**
```python
Position(
    symbol="AAPL",
    quantity=Decimal("5"),
    avg_entry_price=Decimal("270.33"),
    current_price=Decimal("268.00"),
    market_value=Decimal("1340.00"),
    unrealized_pnl=Decimal("-11.65"),
    unrealized_pnl_pct=Decimal("-0.0086")
)
```

**Verwendung:**
- Portfolio Rebalancing Checks
- Exit Condition Monitoring
- Risk Management (MAX_POSITIONS Limit)

### Rate Limiting
- **Limit:** 200 API calls pro Minute (sliding window)
- **Implementierung:** ALPACA_LIMITER (rate_limiter.py)
- **Best Practice:** Batch-Abfragen wo möglich

---

## 💰 Verkaufslogik - "Verkaufen wir auch?"

**Antwort: JA, wir verkaufen in 2 Szenarien:**

### 1. Defensive Core Rebalancing (SELL Signals)

**Wann verkaufen wir?**
- Wenn die tatsächliche Allokation > Ziel-Allokation ist
- Nur wenn Differenz > $100 (vermeidet unnötige Trades)

**Beispiel:**
```python
# Ziel-Allokation VTI: 25% von Portfolio ($100k)
target_value = $25,000

# Aktuelle Position
current_value = $28,000

# Differenz
diff = $25,000 - $28,000 = -$3,000

# Signal generiert
action = "SELL"  # da diff < 0
quantity = abs(-$3,000) / current_price
```

**Trigger:**
- Erster Tag des Monats (monatliches Rebalancing)
- Portfolio Drift > 5% von Ziel-Allokation

**Code-Referenz:** `src/strategies/defensive_core.py:74-144`

---

### 2. Momentum Trading Exits (4 Exit-Bedingungen)

#### Exit-Bedingung 1: Stop-Loss Hit (-5%)
```python
if pnl_pct <= -5%:
    return (True, "stop_loss")
```

**Zweck:** Verluste begrenzen bei fallenden Kursen
**Automatisch:** Ja, via Alpaca Bracket Order

#### Exit-Bedingung 2: Take-Profit Hit (+15%)
```python
if pnl_pct >= +15%:
    return (True, "take_profit")
```

**Zweck:** Gewinne sichern bei steigenden Kursen
**Automatisch:** Ja, via Alpaca Bracket Order

#### Exit-Bedingung 3: RSI Overbought (>75)
```python
if latest["rsi"] > 75:
    return (True, "technical_exit")
```

**Zweck:** Exit bei überkauftem Markt (Korrektur wahrscheinlich)
**Automatisch:** Nein, manuell via daily_trading_loop check

#### Exit-Bedingung 4: MACD Momentum Umkehr
```python
if latest["histogram"] < 0:
    return (True, "technical_exit")
```

**Zweck:** Exit bei negativem Momentum (Trend dreht)
**Automatisch:** Nein, manuell via daily_trading_loop check

**Code-Referenz:** `src/strategies/momentum_trading.py:142-200`

---

## 🎯 Aktuelle Strategy Parameters

### Momentum Trading Parameters
```python
STRATEGY_PARAMS = {
    "rsi_min": 50,              # RSI Untergrenze für Entry
    "rsi_max": 70,              # RSI Obergrenze für Entry (nicht überkauft)
    "stop_loss_pct": 0.05,      # -5% Stop-Loss
    "take_profit_pct": 0.15,    # +15% Take-Profit
    "min_volume_ratio": 1.0,    # Min. Volume vs. Average
}
```

**Optimierungspotenzial:**
- Diese Parameter können durch Performance-Analyse angepasst werden
- Funktion `update_strategy_parameters()` erlaubt dynamische Anpassung
- Backtesting könnte optimale Werte identifizieren

### Risk Management Parameters
```python
MAX_POSITIONS = 5                      # Max. 5 gleichzeitige Momentum-Positionen
MAX_POSITION_SIZE_PCT = 0.10          # Max. 10% pro Position
MAX_DAILY_RISK_PCT = 0.02             # Max. 2% Risk pro Trade
DAILY_LOSS_LIMIT_PCT = 0.03           # Circuit Breaker bei -3%
```

---

## 📈 Erkenntnisse aus erstem Live-Trading (2025-11-18)

### Erfolgreiche Defensive Core Etablierung
**Trades ausgeführt:**
- VTI: 76.87 Shares @ $325.14 = $24,993.13 (Target: 25%)
- VGK: 189.04 Shares @ $79.32 = $14,994.65 (Target: 15%)
- GLD: 26.70 Shares @ $374.60 = $10,001.82 (Target: 10%)

**Gesamtallokation:** ~50% des Portfolios ✅

**Erkenntnisse:**
1. ✅ Position Sizing funktioniert korrekt (Shares = Dollar Amount / Price)
2. ✅ Bracket Orders werden korrekt erstellt
3. ✅ Supabase Logging erfolgreich
4. ✅ Rate Limiting verhindert API-Überlastung

### Bugs gefunden und behoben
1. **Position Sizing Bug** - System berechnete Dollar-Betrag statt Shares
   - **Lösung:** Dual-Mode Logic (Defensive vs Momentum)

2. **Async Rebalancing** - Funktion benötigte Preis-Fetching
   - **Lösung:** `calculate_rebalancing_orders` zu async gemacht

3. **Supabase Project Mismatch** - .env hatte falsches Project Ref
   - **Lösung:** JWT Token dekodiert, korrektes Ref ermittelt

---

## 🔍 Optimierungsmöglichkeiten

### 1. Momentum Strategy Verbesserungen

#### Problem: Free Tier Limitation blockiert Scanning
**Aktueller Status:**
- Alpaca Free Tier erlaubt kein "recent SIP data"
- Momentum Scanning funktioniert nicht mit delayed data

**Mögliche Lösungen:**
- [ ] Upgrade auf Alpaca Paid Tier ($9/Monat für Unlimited Data)
- [ ] Alternative Datenquelle nutzen (Yahoo Finance, Alpha Vantage)
- [ ] Delayed Data akzeptieren (15-20 Min Verzögerung)

#### Watchlist Optimization
**Aktuelle Watchlist (10 Stocks):**
```python
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "META",
             "TSLA", "AMZN", "AMD", "NFLX", "AVGO"]
```

**Optimierungsmöglichkeiten:**
- [ ] Dynamische Watchlist basierend auf Volumen/Volatilität
- [ ] Sektor-Rotation (Tech, Healthcare, Energy rotieren)
- [ ] ETF Momentum (QQQ, SPY, IWM)

### 2. Risk Management Verbesserungen

#### Korrelations-Analyse
**Aktuell:** Keine Korrelation zwischen Positionen berücksichtigt

**Verbesserung:**
- [ ] Portfolio-Korrelationsmatrix berechnen
- [ ] Vermeidung von hochkorrelierten Positionen
- [ ] Sektor-Diversifikation erzwingen

**Code-Referenz:** `src/core/risk_manager.py:201-240` (calculate_portfolio_risk_metrics)

#### Drawdown Monitoring
**Aktuell:** Nur täglicher Loss Limit (-3%)

**Verbesserung:**
- [ ] Max Drawdown Tracking über Zeit
- [ ] Wöchentlicher/Monatlicher Drawdown Limit
- [ ] Automatische Position-Reduzierung bei hohem Drawdown

### 3. Performance Analytics

#### Sharpe Ratio Berechnung
**Formel:**
```python
sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std_dev
```

**Implementation:**
- [ ] Tägliche Returns tracken
- [ ] Volatilität (Std Dev) berechnen
- [ ] Sharpe Ratio in performance_metrics speichern

#### Win Rate & Profit Factor
**Metriken die fehlen:**
- [ ] Win Rate (% profitable Trades)
- [ ] Average Win vs. Average Loss
- [ ] Profit Factor (Gross Profit / Gross Loss)
- [ ] Maximum Consecutive Losses

**Zweck:** Strategie-Validierung und Parameter-Optimierung

### 4. Backtesting Framework

**Aktuell:** Kein Backtesting implementiert

**Vorgeschlagene Implementierung:**
```python
# pseudocode
async def backtest_strategy(
    start_date: date,
    end_date: date,
    initial_capital: Decimal = Decimal("100000"),
    strategy_params: dict = STRATEGY_PARAMS
) -> dict:
    """Run historical backtest."""
    # 1. Fetch historical data
    # 2. Simulate daily_trading_loop
    # 3. Track performance metrics
    # 4. Return results (Sharpe, Max DD, Win Rate, etc.)
```

**Nutzen:**
- Parameter-Optimierung (Grid Search)
- Walk-Forward Analysis
- Strategy-Vergleich

---

## 📊 Datensammlung & Monitoring

### Aktuell gesammelte Daten (Supabase)

#### Tabelle: `trades` ✅
**Felder:**
- date, ticker, action, quantity, entry_price, exit_price
- pnl, pnl_pct, strategy, rsi, macd_histogram, volume_ratio
- alpaca_order_id, exit_reason

**Verwendung:** Trade History, Performance Analyse
**Status:** Funktioniert vollständig (Decimal → String Konvertierung implementiert)

#### Tabelle: `signals` ✅
**Felder:**
- date, ticker, action, confidence, strategy
- rsi, macd_histogram, volume_ratio

**Verwendung:** Signal Quality Tracking
**Status:** Funktioniert vollständig

#### Tabelle: `daily_performance` ✅
**Felder:**
- date, total_trades, winning_trades, losing_trades
- win_rate, daily_pnl, profit_factor, avg_win, avg_loss

**Verwendung:** Tägliche Performance-Analyse
**Status:** Implementiert und getestet

#### Tabelle: `strategy_metrics` ✅
**Felder:**
- strategy, date, total_trades, win_rate, total_pnl

**Verwendung:** Per-Strategy Performance Tracking
**Status:** Implementiert und getestet

#### Tabelle: `weekly_reports` ✅
**Felder:**
- week_ending, total_trades, win_rate, total_pnl
- best_performers, worst_performers

**Verwendung:** Wöchentliche Performance Reports
**Status:** Implementiert und getestet (erste Report gespeichert: $284 P&L, 66.7% Win Rate)

#### Tabelle: `parameter_changes` ✅
**Felder:**
- date, reason, old_params, new_params

**Verwendung:** Strategie-Parameter Änderungen tracken
**Status:** Implementiert (noch nicht ausgelöst, braucht 5 Tage Daten)

### Fehlende Metriken

**Was wir noch tracken sollten:**
- [ ] Tägliche Portfolio Returns
- [ ] Volatilität (rolling 30-day std dev)
- [ ] Korrelation zwischen Positionen
- [ ] Sector Exposure (% in Tech, Healthcare, etc.)
- [ ] Average Holding Period
- [ ] Slippage (Difference zwischen Signal Price und Fill Price)

---

## 🚀 Nächste Schritte zur Optimierung

### Priorität 1: Datenqualität verbessern
1. [ ] Alpaca Paid Tier testen ($9/Monat) - Für Momentum Strategy
2. [ ] Alternative Datenquelle evaluieren (Yahoo Finance API, Alpha Vantage)
3. [ ] Delayed Data Handling implementieren

### Priorität 2: Performance Analytics erweitern ✅ ABGESCHLOSSEN
1. [x] `analyze_daily_performance()` vervollständigen ✅
2. [x] Win Rate, Profit Factor berechnen ✅
3. [x] Weekly Reports implementieren ✅
4. [ ] Sharpe Ratio hinzufügen (noch ausstehend)
5. [ ] Max Drawdown Tracking (noch ausstehend)
6. [ ] Performance Dashboard (Web UI) erstellen

### Priorität 3: Backtesting Framework
1. [ ] Historical Data Fetching (1+ Jahre)
2. [ ] Backtest Engine implementieren
3. [ ] Parameter Optimization (Grid Search)
4. [ ] Walk-Forward Analysis

### Priorität 4: Risk Management erweitern
1. [ ] Korrelationsmatrix implementieren
2. [ ] Sektor-Diversifikation erzwingen
3. [ ] Drawdown Monitoring verbessern
4. [ ] VaR (Value at Risk) Berechnung

---

## 💡 Ideen für weitere Features

### 1. Multi-Strategy Portfolio
**Konzept:** Mehrere Strategien parallel laufen lassen
- Defensive Core (50%)
- Momentum Trading (30%)
- Mean Reversion (10%)
- Pairs Trading (10%)

**Vorteil:** Diversifikation, reduzierte Volatilität

### 2. Machine Learning Integration
**Use Cases:**
- Signal Filtering (ML-Modell filtert schwache Signale)
- Position Sizing Optimization (Reinforcement Learning)
- Regime Detection (Bull vs. Bear Market)

**Wichtig:** Nicht für Trading-Entscheidungen, nur für Optimierung!

### 3. Social Trading & Copy Trading
**Konzept:** Top-Performing Portfolios identifizieren und kopieren
- Alpaca Community Portfolio Tracking
- Copy-Trading mit Risk Scaling

### 4. Tax-Loss Harvesting
**Konzept:** Verluste realisieren für Steuervorteil
- Automatische Identifikation von Loss Positions
- Tax-Lot Optimization

---

## 📝 Lessons Learned

### Debugging Best Practices
1. **JWT Token Decoding** - Bei Supabase Fehlern immer Project Ref prüfen
2. **Async/Await** - Alle API-Calls müssen async sein für Rate Limiting
3. **Decimal vs Float** - Immer Decimal für Geld/Preise verwenden (Rundungsfehler!)
4. **Position Sizing** - Dollar Amount ≠ Shares (shares = dollar / price)

### Code Quality
1. **Type Hints** - Helfen beim Debugging (Pydantic validation)
2. **Logging** - Ausführliches Logging spart Debugging-Zeit
3. **Error Handling** - Try/Except in allen API-Calls (resilience)

### Testing
1. **Integration Tests** - Wichtiger als Unit Tests für Trading Systems
2. **Mock Limitations** - Async Mocking ist kompliziert, Real API Tests bevorzugen
3. **Paper Trading** - Perfekt für Live Testing ohne Risiko

---

## 🔄 Changelog

### 2025-11-19 - Performance Analytics Implementation
- ✅ **Kritischen Bug behoben**: Decimal JSON Serialization Fehler
  - Problem: Decimal-Objekte waren nicht JSON-serializable
  - Lösung: Decimal → String Konvertierung in allen Supabase-Methoden
  - Resultat: Trades werden jetzt erfolgreich in Datenbank gespeichert

- ✅ **Performance Analytics vollständig implementiert**
  - Daily Performance Analysis: Win Rate, Profit Factor, Avg Win/Loss
  - Strategy Metrics: Per-Strategy Performance Tracking
  - Weekly Reports: Best/Worst Performers, Weekly P&L
  - Parameter Adjustment: Automatische Strategie-Optimierung

- ✅ **None-Handling verbessert**
  - Problem: P&L None-Werte verursachten Crashes
  - Lösung: `t.get("pnl") or 0` statt `t.get("pnl", 0)`
  - Betrifft: Entry-Trades (haben noch kein P&L)

- ✅ **Database-Struktur validiert**
  - Tabellen: trades, signals, daily_performance, strategy_metrics, weekly_reports, parameter_changes
  - Alle Logging-Methoden funktionieren
  - Test-Daten erfolgreich eingefügt

- ✅ **Test-Daten erstellt**
  - 6 Entry Trades (AAPL, GLD, SAP, VGK, VTI)
  - 3 Closed Trades mit P&L (TSLA +15%, NVDA +10%, NFLX -5%)
  - Weekly Report: 9 Trades, 66.7% Win Rate (von Closed Trades), $284 P&L

### 2025-11-18 - Initial Documentation
- ✅ Dokumentation erstellt
- ✅ Alpaca Market Data analysiert
- ✅ Verkaufslogik dokumentiert (2 Szenarien, 6 Exit-Bedingungen)
- ✅ Optimierungsmöglichkeiten identifiziert
- ✅ Performance Analytics Lücken erkannt

---

## 📚 Referenzen & Ressourcen

### Alpaca API Documentation
- [Alpaca Trading API](https://alpaca.markets/docs/api-references/trading-api/)
- [Alpaca Market Data API](https://alpaca.markets/docs/api-references/market-data-api/)
- [alpaca-py SDK](https://github.com/alpacahq/alpaca-py)

### Technical Analysis
- [RSI Indicator](https://www.investopedia.com/terms/r/rsi.asp)
- [MACD Indicator](https://www.investopedia.com/terms/m/macd.asp)
- [ta-lib Python](https://github.com/bukosabino/ta)

### Risk Management
- [Modern Portfolio Theory](https://www.investopedia.com/terms/m/modernportfoliotheory.asp)
- [Sharpe Ratio](https://www.investopedia.com/terms/s/sharperatio.asp)
- [Value at Risk (VaR)](https://www.investopedia.com/terms/v/var.asp)

---

**Ende der Insights-Dokumentation**

_Dieses Dokument wird kontinuierlich aktualisiert mit neuen Erkenntnissen aus Live-Trading und Optimierungen._
