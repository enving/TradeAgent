# Scharfstellung: Von Paper Trading zu Live Trading

Dieser Guide beschreibt den Weg vom aggressiven Paper Trading zum konservativen Live Trading mit echtem Geld.

## 🎯 Architektur-Konzept

**Prinzip:** Ein System, zwei Modi - minimaler Overhead, maximale Sicherheit.

```
┌─────────────────────────────────────┐
│   Raspberry Pi (eine Codebasis)    │
│                                     │
│  ┌─────────────────────────────┐  │
│  │  Trading Bot (main branch)  │  │
│  │  Mode: $TRADING_MODE env    │  │
│  └─────────────────────────────┘  │
│           │              │          │
│      PAPER MODE      LIVE MODE     │
│   (aggressiv test)  (conservative) │
└─────────┬──────────────┬───────────┘
          │              │
          ▼              ▼
    ┌──────────┐   ┌──────────┐
    │ Paper    │   │ Live     │
    │ Alpaca   │   │ Alpaca   │
    └──────────┘   └──────────┘
          │              │
          └──────┬───────┘
                 ▼
         ┌──────────────┐
         │  Supabase    │
         │ trading_mode │
         │   column     │
         └──────────────┘
```

## 📋 Deployment-Phasen

### Phase 1: Vorbereitung (jetzt)

**Ziel:** Code für beide Modi vorbereiten, ohne Paper Trading zu unterbrechen.

#### 1.1 Datenbank-Migration

```sql
-- In Supabase SQL Editor ausführen:

-- Trades Tabelle erweitern
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'paper';

-- Signals Tabelle erweitern
ALTER TABLE signals
ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'paper';

-- ML Training Data erweitern
ALTER TABLE ml_training_data
ADD COLUMN IF NOT EXISTS trading_mode TEXT DEFAULT 'paper';

-- Indices für Performance
CREATE INDEX IF NOT EXISTS idx_trades_mode
ON trades(trading_mode, date DESC);

CREATE INDEX IF NOT EXISTS idx_signals_mode
ON signals(trading_mode, date DESC);

-- Historische Daten als 'paper' markieren
UPDATE trades SET trading_mode = 'paper' WHERE trading_mode IS NULL;
UPDATE signals SET trading_mode = 'paper' WHERE trading_mode IS NULL;
UPDATE ml_training_data SET trading_mode = 'paper' WHERE trading_mode IS NULL;
```

#### 1.2 Code-Änderungen

**A) Config erweitern** (`src/utils/config.py`):

```python
# Trading Mode Detection
TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # 'paper' oder 'live'

# Mode-spezifische Parameter
if TRADING_MODE == "live":
    # Conservative für echtes Geld
    MAX_POSITION_SIZE_USD = 500
    MAX_DAILY_LOSS_PCT = 1.0
    MAX_CONCURRENT_POSITIONS = 2
    MIN_CONFIDENCE_THRESHOLD = 0.85
    ENABLE_PREMARKET = False
    ENABLE_AFTERHOURS = False
else:
    # Aggressiv für Paper Testing
    MAX_POSITION_SIZE_USD = 5000
    MAX_DAILY_LOSS_PCT = 3.0
    MAX_CONCURRENT_POSITIONS = 5
    MIN_CONFIDENCE_THRESHOLD = 0.70
    ENABLE_PREMARKET = True
    ENABLE_AFTERHOURS = True
```

**B) Trade Logging erweitern** (`src/database/supabase_client.py`):

```python
@staticmethod
async def log_trade(trade: Trade) -> None:
    """Log trade with trading mode tag."""
    from ..utils.config import config

    trade_data = {
        "date": trade.date.isoformat(),
        "ticker": trade.ticker,
        "action": trade.action,
        "quantity": str(trade.quantity),
        "entry_price": str(trade.entry_price),
        "strategy": trade.strategy,
        "trading_mode": config.TRADING_MODE,  # Neu!
        # ... rest
    }
```

**C) Safety Checks implementieren** (`src/core/risk_manager.py`):

```python
async def validate_live_trade(signal: Signal) -> Tuple[bool, str]:
    """Extra validation layer for live trading.

    Returns:
        (approved: bool, reason: str)
    """
    from ..utils.config import config

    # Paper Mode: keine extra checks
    if config.TRADING_MODE != "live":
        return True, "Paper mode - no restrictions"

    # 1. Position Size Check
    position_value = signal.quantity * signal.entry_price
    if position_value > Decimal(str(config.MAX_POSITION_SIZE_USD)):
        return False, f"Position ${position_value:.2f} exceeds limit ${config.MAX_POSITION_SIZE_USD}"

    # 2. Daily Loss Limit
    if await check_daily_loss_limit():
        return False, "Daily loss limit reached - trading halted"

    # 3. Market Hours Only (no pre/post market)
    market_clock = await get_market_clock()
    if not market_clock.is_open:
        return False, "Market is closed"

    # 4. Confidence Threshold
    if signal.confidence < Decimal(str(config.MIN_CONFIDENCE_THRESHOLD)):
        return False, f"Confidence {signal.confidence:.2f} below threshold {config.MIN_CONFIDENCE_THRESHOLD}"

    # 5. Maximum Concurrent Positions
    current_positions = await get_open_positions_count()
    if current_positions >= config.MAX_CONCURRENT_POSITIONS:
        return False, f"Already at max positions ({config.MAX_CONCURRENT_POSITIONS})"

    return True, "All safety checks passed"
```

**D) Adaptive Optimizer anpassen** (`src/ml/adaptive_optimizer.py`):

```python
async def _fetch_recent_trades(
    self, strategy: str, lookback_days: int
) -> List[Dict[str, Any]]:
    """Fetch recent trades for analysis.

    IMPORTANT: Always uses PAPER trades for optimization,
    even when running in LIVE mode. This allows aggressive
    experimentation in paper while live runs conservative.
    """
    client = await SupabaseClient.get_instance()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    response = (
        await client.table("trades")
        .select("*")
        .eq("strategy", strategy)
        .eq("trading_mode", "paper")  # Immer paper für Optimierung!
        .gte("date", cutoff_date.isoformat())
        .order("date", desc=True)
        .execute()
    )

    return response.data if response.data else []
```

**E) Logging erweitern** (für Sichtbarkeit):

```python
# In src/main.py - am Anfang von daily_trading_loop()
logger.info(
    f"🤖 Trading Loop Started - Mode: {config.TRADING_MODE.upper()}, "
    f"Max Position: ${config.MAX_POSITION_SIZE_USD}, "
    f"Max Positions: {config.MAX_CONCURRENT_POSITIONS}"
)
```

#### 1.3 .env Datei vorbereiten

Auf dem Raspberry Pi `.env` erweitern:

```bash
# Trading Mode
TRADING_MODE=paper  # 'paper' oder 'live'

# Alpaca API (für Live später ändern)
ALPACA_API_KEY=<paper_key>
ALPACA_SECRET_KEY=<paper_secret>
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Mode-spezifische Limits (in Code, nicht hier)
# Aber zur Dokumentation:
# Paper: $5000/position, 5 positions, 3% daily loss
# Live:  $500/position,  2 positions, 1% daily loss
```

### Phase 2: Testing & Observation (2-4 Wochen)

**Ziel:** System mit neuen Safety Features testen, während Paper weiterläuft.

#### 2.1 Code deployen

```bash
# Lokal committen und pushen
git add .
git commit -m "feat: add dual-mode support for paper/live trading"
git push origin main

# Pi pulled automatisch innerhalb 5 Min
# TRADING_MODE bleibt auf 'paper'
```

#### 2.2 Beobachten

**Logs prüfen:**
```bash
ssh USER@raspberrypi.local "tail -f ~/tradeagent/logs/trading.log | grep -E '(Trading Loop Started|Safety check|BLOCKED)'"
```

**Erwartete Ausgaben:**
```
🤖 Trading Loop Started - Mode: PAPER, Max Position: $5000, Max Positions: 5
✅ AAPL Signal - Safety check passed: Paper mode - no restrictions
```

**In Supabase prüfen:**
```sql
-- Alle Trades sollten trading_mode='paper' haben
SELECT trading_mode, COUNT(*)
FROM trades
GROUP BY trading_mode;

-- Parameter Optimierung läuft weiter
SELECT * FROM parameter_changes
ORDER BY changed_at DESC LIMIT 5;
```

#### 2.3 Performance-Metriken sammeln

**KPIs beobachten (mindestens 2-4 Wochen):**
- Win Rate stabilisiert sich bei >55%
- Sharpe Ratio >1.5
- Max Drawdown <10%
- Keine kritischen Fehler in Logs
- Parameter-Optimierung zeigt Verbesserung

### Phase 3: Live Switch (wenn bereit)

**⚠️ KRITISCH: Nur durchführen wenn Phase 2 erfolgreich!**

#### 3.1 Backup erstellen

```bash
# SSH zum Pi
ssh USER@raspberrypi.local

# Backup der aktuellen Config
cp ~/tradeagent/.env ~/tradeagent/.env.paper_backup
cp ~/tradeagent/logs/trading.log ~/tradeagent/logs/trading_paper_final.log

# Supabase Backup (via Web UI)
# → Settings → Database → Backup → Create Backup
```

#### 3.2 Alpaca Live API Keys anlegen

1. **Alpaca Website:** https://alpaca.markets
2. **Account verlinken:** Echtes Broker-Konto verbinden
3. **Live API Keys generieren:**
   - API Key ID: `AK...` (Live)
   - Secret Key: `...` (Live)
   - ⚠️ **Nicht** die Paper Keys!

4. **Permissions prüfen:**
   - ✅ Account Activities (READ)
   - ✅ Account Configurations (READ)
   - ✅ Orders (READ + WRITE)
   - ✅ Positions (READ)
   - ✅ Market Data (READ)

#### 3.3 .env auf Live umstellen

```bash
# SSH zum Pi
ssh USER@raspberrypi.local
nano ~/tradeagent/.env
```

**Änderungen:**
```bash
# Trading Mode auf LIVE umstellen
TRADING_MODE=live  # ← ÄNDERN!

# Alpaca Live API
ALPACA_API_KEY=AK...                    # ← ÄNDERN (Live Key)
ALPACA_SECRET_KEY=...                   # ← ÄNDERN (Live Secret)
ALPACA_BASE_URL=https://api.alpaca.markets  # ← ÄNDERN (kein 'paper-')

# Rest bleibt gleich (Supabase, LLM, etc.)
```

#### 3.4 Service neu starten

```bash
# Manueller Restart (sicherer als Auto-Update)
cd ~/tradeagent
pkill -f "python.*event_driven_service"

# Warten bis Prozess gestoppt
sleep 3

# Neu starten
source venv/bin/activate
nohup python -m src.event_driven_service > logs/service.log 2>&1 &

# Logs live verfolgen
tail -f logs/trading.log
```

#### 3.5 Erste Trades verifizieren

**Erwartete Log-Ausgaben:**
```
🤖 Trading Loop Started - Mode: LIVE, Max Position: $500, Max Positions: 2
🔍 AAPL Signal generated - checking safety...
✅ AAPL Signal APPROVED: All safety checks passed
💰 BUY 5 AAPL @ $150.00 (Live Mode)
```

**In Alpaca Dashboard prüfen:**
- Orders erscheinen in Live Account
- Positions werden korrekt angezeigt
- Cash Balance wird reduziert

**In Supabase prüfen:**
```sql
-- Erste Live Trades sehen
SELECT * FROM trades
WHERE trading_mode = 'live'
ORDER BY date DESC
LIMIT 10;
```

### Phase 4: Monitoring (kontinuierlich)

#### 4.1 Tägliche Checks

**Morgens (vor Market Open):**
```sql
-- Overnight Positionen
SELECT ticker, quantity, entry_price, strategy
FROM trades
WHERE trading_mode = 'live'
AND action = 'BUY'
AND exit_price IS NULL;

-- Gestrige Performance
SELECT
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(pnl) as total_pnl
FROM trades
WHERE trading_mode = 'live'
AND DATE(date) = CURRENT_DATE - INTERVAL '1 day';
```

**Abends (nach Market Close):**
```bash
# Logs prüfen
ssh USER@raspberrypi.local "tail -100 ~/tradeagent/logs/trading.log | grep -E '(LIVE|ERROR|BLOCKED)'"
```

#### 4.2 Wöchentliche Reviews

**Sonntags (nach Parameter-Optimierung):**
```sql
-- Letzte Woche Performance
SELECT
    trading_mode,
    strategy,
    COUNT(*) as trades,
    AVG(pnl_pct) as avg_return,
    SUM(pnl) as total_pnl
FROM trades
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY trading_mode, strategy;

-- Parameter Changes (paper-basiert)
SELECT * FROM parameter_changes
ORDER BY changed_at DESC LIMIT 3;
```

#### 4.3 Alerts einrichten (optional)

**Supabase Edge Function für Critical Alerts:**
```typescript
// alert_on_large_loss.ts
// Triggered bei loss > $100 in Live Mode
```

## 🛡️ Safety Features Übersicht

| Feature | Paper Mode | Live Mode | Implementierung |
|---------|-----------|-----------|----------------|
| **Max Position Size** | $5,000 | $500 | `config.MAX_POSITION_SIZE_USD` |
| **Max Concurrent** | 5 | 2 | `config.MAX_CONCURRENT_POSITIONS` |
| **Daily Loss Limit** | 3% | 1% | `config.MAX_DAILY_LOSS_PCT` |
| **Min Confidence** | 70% | 85% | `config.MIN_CONFIDENCE_THRESHOLD` |
| **Pre/Post Market** | ✅ Ja | ❌ Nein | `config.ENABLE_PREMARKET` |
| **Extra Validation** | ❌ Nein | ✅ Ja | `validate_live_trade()` |

## 📊 Datenfluss

### Paper Mode (aggressive Experimente):
```
Momentum Strategy → Signal (confidence=0.72)
→ Paper Trade → Supabase (trading_mode='paper')
→ Parameter Optimizer (verwendet paper trades)
→ Verbesserte Parameter
```

### Live Mode (conservative, nutzt paper learnings):
```
Momentum Strategy (mit optimierten Parametern)
→ Signal (confidence=0.87)
→ validate_live_trade() ✅
→ Live Trade → Supabase (trading_mode='live')
→ Echtes Geld bewegt
```

### Adaptive Learning Loop:
```
Paper Trades (aggressiv, viele)
→ Weekly Optimization (Sonntags)
→ Bessere Parameter
→ Live nutzt bessere Parameter (conservative)
→ Weniger Risiko, bessere Returns
```

## 🎯 Rollback-Strategie

**Wenn Live Trading Probleme macht:**

```bash
# 1. Service stoppen
ssh USER@raspberrypi.local "pkill -f 'python.*event_driven'"

# 2. .env zurück auf Paper
ssh USER@raspberrypi.local "cp ~/tradeagent/.env.paper_backup ~/tradeagent/.env"

# 3. Offene Live Positionen schließen (manuell in Alpaca Dashboard)

# 4. Service neu starten
ssh USER@raspberrypi.local "cd ~/tradeagent && source venv/bin/activate && nohup python -m src.event_driven_service > logs/service.log 2>&1 &"
```

## 🔮 Zukunft: Dual Mode (optional)

**Wenn Raspberry Pi genug Ressourcen hat:**

```bash
# Zwei Prozesse parallel:
# 1. Paper Bot (aggressiv, Port 8001)
TRADING_MODE=paper python -m src.event_driven_service

# 2. Live Bot (conservative, Port 8002)
TRADING_MODE=live python -m src.event_driven_service
```

**Vorteile:**
- Paper testet weiter aggressiv
- Live profitiert sofort von Optimierungen
- Beide nutzen gleiche Codebasis

**Nachteil:**
- 2x RAM/CPU Verbrauch
- Pi könnte überfordert sein

## 📝 Checkliste vor Live-Switch

- [ ] Phase 1 komplett: Code deployed, `trading_mode` column existiert
- [ ] Phase 2 komplett: 2-4 Wochen Paper Testing, stabile Performance
- [ ] Backup erstellt: `.env`, logs, Supabase snapshot
- [ ] Alpaca Live Keys angelegt und getestet
- [ ] Safety checks implementiert und getestet
- [ ] Win Rate >55% über letzten Monat
- [ ] Sharpe Ratio >1.5
- [ ] Keine kritischen Bugs in Logs
- [ ] Du bist mental bereit für echtes Geld
- [ ] Notfall-Plan (Rollback) verstanden

## ⚠️ Wichtige Hinweise

1. **Start klein:** Beginne mit 2 Positionen à $500, nicht mehr!
2. **Beobachte täglich:** Erste Woche = tägliche Log-Checks
3. **Paper läuft weiter:** Optimierung basiert auf Paper, nicht Live
4. **Kein FOMO:** Wenn unsicher → zurück auf Paper
5. **Repos bleibt öffentlich:** Keine API Keys committen!

## 🆘 Support & Debugging

**Logs prüfen:**
```bash
# Alle Live Trades
ssh USER@raspberrypi.local "grep 'LIVE' ~/tradeagent/logs/trading.log | tail -50"

# Blockierte Trades
ssh USER@raspberrypi.local "grep 'BLOCKED' ~/tradeagent/logs/trading.log | tail -20"
```

**Supabase Queries:**
```sql
-- Live Performance Today
SELECT * FROM trades
WHERE trading_mode = 'live'
AND DATE(date) = CURRENT_DATE;

-- Safety Check Failures (in llm_analysis_log)
SELECT ticker, technical_filter_reason
FROM llm_analysis_log
WHERE signal_approved = false
ORDER BY created_at DESC LIMIT 20;
```

---

**Erstellt:** 2026-01-08
**Version:** 1.0
**Maintainer:** AI Agent / Developer
**Status:** Ready for Phase 1 Implementation
