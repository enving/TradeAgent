## Goal:

- ein Trading Bot / automatic private flexible ETF der täglich Käufe und Verkäufe über die Alpaca MCP (Paper) mit dem Ziel der Gewinnmaximierung
- nutze state of the art und kenntnisse aus der Finnazwelt um gewinnmaximerung voranzutreiben...
(Nebeninfo: - ich konnte nur soviel prompten und zusammenstellen, komme aber nicht aus dem Finanzsektor. prüf du das ggf. passe an oder suche in deinem Wissensstand und denke nochmal genau nach wie die Strategieam besten ist, vielleicht suchst du nach Positivbeispielen)
- relativ technologieoffen... Pydantic AI agent, n8n workflow(s), python, rust, n8n ggf. am besten da du es dort direkt aufbauen und testen kannst über den n8n-mcp und ich so eine Übersicht direkt habe
- baue nicht endlose Sprachmodelle ein, immer wenn geht deterministisch arbeiten und nur wenn unbedingt nötig dann ein großes Sprachmodell. ggf. für kleinere nicht-deterministische Aufhaben ein kleines Sprachmodell vorschalten


## First Ideas for a Trade Strategy (should constantly be able to learn and be optimised with incoming daily data)
Deterministic Trading Bot with Strategic Analysis
FEATURE: Intelligent Paper Trading System for Wealth Building
Ein deterministischer Trading Bot, der primär durch mathematische Analyse und klare Regeln handelt, mit minimalem LLM-Einsatz nur für nicht-deterministische Edge Cases. Das System nutzt die Alpaca Paper Trading API über MCP für risikofreies Testing und Optimierung.
Core Objectives

Tägliche Trades über Alpaca MCP (Paper) mit klaren Entry/Exit-Regeln
Deterministisch-First: 80%+ der Entscheidungen ohne LLM
Schnelle Iteration: Daily runs für kontinuierliches Learning
Datengetrieben: Alle Trades in Supabase für Performance-Analyse
Profitabel: Realistische 15-20% jährliche Returns durch bewährte Strategien


STRATEGIC FRAMEWORK (Basierend auf Backtest-Erkenntnissen)
Lessons Learned aus vorherigen Analysen:
✅ Was funktioniert:

Apple (AAPL) Momentum Trading: +12.45% in 2 Monaten, 65% Win Rate
Technische Indikatoren (RSI, MACD) sind zuverlässiger als Sentiment
ETF-Basis (VGK, VTI) für Portfolio-Stabilität

❌ Was NICHT funktioniert:

SAP Gap-Trading: -11.21% (OTC-Aktien, keine Live-Daten)
Übermäßiger News-Sentiment-Fokus (zu langsam für Intraday)
Direkter deutscher Börsenhandel (Alpaca nur US-Märkte)

Trading Strategy Stack (Phase 1 Focus)
Layer 1: Defensive Core (50% Portfolio) - PURE DETERMINISTIC
yamlStrategie: Buy & Hold mit Monthly Rebalancing
Assets: 
  - VTI (US Total Market): 25%
  - VGK (Europe): 15%  
  - GLD (Gold): 10%

Rebalancing Logic:
  - Trigger: Monatlich (1. Handelstag) ODER Portfolio Drift > 5%
  - Berechnung: target_allocation - current_allocation
  - Execution: Market Orders via Alpaca MCP

LLM Usage: 0%
Expected Return: 8-12% annually
Max Drawdown: -10%
Layer 2: Momentum Trading (30% Portfolio) - HYBRID
yamlStrategie: Technical Breakout + Trend Following
Universe: Top 20 Liquid Stocks (AAPL, MSFT, NVDA, GOOGL, etc.)

Deterministic Screening (4 Criteria):
  1. RSI: 50 < RSI < 70 (bullish, not overbought)
  2. MACD: Histogram > 0 (momentum confirmed)
  3. Trend: Price > 20-day MA (uptrend)
  4. Volume: Today > 20-day avg (institutional interest)

Entry Signal: ALL 4 criteria TRUE
Exit Signal: 
  - RSI > 75 (overbought)
  - MACD < 0 (momentum loss)
  - Stop-Loss: -5% from entry
  - Take-Profit: +15% (3:1 R/R)

Position Sizing:
  - Max 10% portfolio per stock
  - Max 5 concurrent positions
  - Risk: 2% portfolio per trade

LLM Usage: <5% (nur bei widersprüchlichen Signalen)
Expected Return: 20-30% annually
Max Drawdown: -15%
Win Rate Target: 60-65%
Layer 3: Opportunistic (20% Portfolio) - LLM-ENHANCED
yamlStrategie: News Catalyst + Technical Confirmation
Status: PHASE 2 (später)

Trigger Events:
  - Earnings beats > 5%
  - Major product launches
  - Insider buying > $1M
  
Combined with Technical Filter (Layer 2 criteria)
LLM: Chart pattern confirmation via small model
```

---

### ARCHITECTURE DECISION

#### Primary: **Python-First Development**
```
Rationale:
✅ Full code control für deterministische Logik
✅ Besseres Testing Framework (pytest)
✅ Einfacher zu versionieren (Git)
✅ Performance-optimiert für Indicator Calculations
✅ Später portierbar zu n8n für UI/Monitoring

Start: Standalone Python Service
Later: n8n Workflows für Monitoring & Manual Overrides


## EXAMPLES:

- 'examples/n8nworkflows'sind einige n8n Workflows von anderen Leuten die ich im Internet gefunden habe... sie sind alle ein bischen anders, teilweise vieulzuviele Agenten und auch reduntant, teilweise auf Crypto spezialisiert, und alle keine MCP Server sondern viele Tool und API calls.. aber der "📈+Deep+Report+++Automatic+Trading_+Automate+Your+Stock+Trades+with+AI+Analysis" hat wohl zumindest in alpaca paper sehr gute ergebnisse erzielt laut Ersteller. 
- `examples/workflows` und `examples/building-blocks` read through all of the files here to understand best practices for creating Python AI agents that support different providers and LLMs, handling agent dependencies, and adding tools to the agent.

Don't copy any of these examples directly, it is for a different project entirely. But use this as inspiration and for best practices.

## DOCUMENTATION:

- '/Dokumentation/erste_strategie.md' - use this as base strategy, you can edit or go away from it but I wanted you to let it know 
- 'cd ..' - the folder above the repostitory has also some valuable information if you go the way to develop custom code with python for agents
- für technische Dokumentation zu zb n8n, openwebui etc. hast du Zugang zu context7 über mcp
- für infos wie und wo wir ein kleines Modell feintunen würden: https://docs.ionos.com/cloud/ai/ai-model-studio


## OTHER CONSIDERATIONS:


- N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE wurde bereits auf true gesetzt und der community mcp node client ist installiert hier ist dokumentation dazu was wir ihn nutzen können: https://www.npmjs.com/package/n8n-nodes-mcp bzw. https://github.com/nerding-io/n8n-nodes-mcp?tab=readme-ov-file
- https://doc.chart-img.com/ habe ich auch bereits einen API key falls du das nutzen magst genauso Alphavantage api key und twelvedata api key
- openrouter node in n8n ist auch bereits einsatzbereit wenn du den verwenden möchtest. habe credits hinterlegt und in n8n die credentials hinterlegt
-  
- supabase kannst du auch nutzen (habe es lokal und in n8n die credentials hinterlegt).. alles was es schon gibt ist als docker container mit docker compose einsehbar von claude code

- Include a .env.example, README with instructions for setup 
- Wir haben bereits API Zugang zu twelvedata, alpaca (sogar über mcp)
- Include the project structure in the README.
- Virtual environment müssteste du noch machen falls wir lokal etwas entwickeln 
- Use python_dotenv and load_env() for environment variables
- falls sinnvoll kannst du diese MCP Server nutzen, du hast bereits Zugang: docker mcp (library, context7), n8n-mcp (manage, create observe n8n workflows locally in instance), alpaca-docker
- und du hast Konnektoren zu: github
- mache keinen mega agenten. nutze statt tools immer mcps wenns geht (aber baue keine selber)
- super wäre es wenn wir später unseren service als mcp aber machen könntne und dann zb auf verschiedene clients und auf edge bereitstellen könnne zb whatsapp, telegram oder openwebui..
- wenn du es für sinnvoll erachtest können wir auch mit einem labeled dataset dass du erstellen müsstest als .jsonl in das ionos model ai studio gehen um dort ein kleines multimodales Sprachmodell zu finetunen zb auf Stock Bilder oder so... aber nur wenn du das nicht besser kannst und unbedingt notwendig ist



## Code Vorschläge:
DETERMINISTIC CORE LOGIC
Daily Execution Flow (9:00 AM EST)
pythonasync def daily_trading_loop():
    """
    100% deterministisch, kein LLM für Phase 1
    """
    # 1. Portfolio State
    portfolio = await alpaca_mcp.get_account()
    positions = await alpaca_mcp.get_positions()
    
    # 2. Defensive Core Check (math only)
    if is_rebalancing_day() or portfolio_drift(positions) > 0.05:
        rebalance_orders = calculate_rebalancing(
            current=positions,
            target={'VTI': 0.25, 'VGK': 0.15, 'GLD': 0.10}
        )
        await execute_orders(rebalance_orders)
    
    # 3. Momentum Scanner (pure indicators)
    watchlist = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 
                 'TSLA', 'AMZN', 'AMD', 'NFLX', 'AVGO']
    
    buy_signals = []
    for ticker in watchlist:
        bars = await twelvedata.get_bars(ticker, days=30)
        
        # Calculate indicators (deterministic)
        rsi = calculate_rsi(bars, period=14)
        macd, signal, histogram = calculate_macd(bars)
        ma20 = calculate_sma(bars, period=20)
        avg_volume = calculate_avg_volume(bars, period=20)
        
        # Entry Criteria (boolean logic only)
        if (50 < rsi < 70 and 
            histogram > 0 and 
            bars[-1].close > ma20 and
            bars[-1].volume > avg_volume):
            
            buy_signals.append({
                'ticker': ticker,
                'entry_price': bars[-1].close,
                'stop_loss': bars[-1].close * 0.95,
                'take_profit': bars[-1].close * 1.15,
                'confidence': calculate_signal_strength(rsi, histogram)
            })
    
    # 4. Risk Management (hard limits)
    filtered_signals = apply_risk_limits(
        buy_signals,
        max_positions=5,
        max_per_position=portfolio.portfolio_value * 0.10,
        max_total_risk=portfolio.portfolio_value * 0.02
    )
    
    # 5. Execute Orders (no LLM needed)
    for signal in filtered_signals:
        order = await alpaca_mcp.submit_order(
            symbol=signal['ticker'],
            qty=calculate_position_size(signal, portfolio),
            side='buy',
            type='market',
            time_in_force='day'
        )
        await supabase.log_trade(order, signal)
    
    # 6. Exit Management (check existing positions)
    for position in positions:
        if position['symbol'] not in ['VTI', 'VGK', 'GLD']:
            current_price = await alpaca_mcp.get_latest_quote(position['symbol'])
            entry_price = position['avg_entry_price']
            
            # Deterministic exit rules
            pnl_pct = (current_price - entry_price) / entry_price
            
            if pnl_pct <= -0.05:  # Stop-Loss
                await alpaca_mcp.close_position(position['symbol'])
                await supabase.log_exit(position, reason='stop_loss')
            
            elif pnl_pct >= 0.15:  # Take-Profit
                await alpaca_mcp.close_position(position['symbol'])
                await supabase.log_exit(position, reason='take_profit')
            
            # Check technical exit (RSI > 75 or MACD bearish)
            bars = await twelvedata.get_bars(position['symbol'], days=30)
            rsi = calculate_rsi(bars)
            _, _, histogram = calculate_macd(bars)
            
            if rsi > 75 or histogram < 0:
                await alpaca_mcp.close_position(position['symbol'])
                await supabase.log_exit(position, reason='technical_exit')
    
    # 7. Daily Performance Analysis
    performance = await calculate_daily_performance(portfolio, positions)
    await supabase.log_performance(performance)
    
    return {
        'new_positions': filtered_signals,
        'closed_positions': closed_today,
        'portfolio_value': portfolio.portfolio_value,
        'daily_pnl': performance['daily_pnl']
    }
Key Deterministic Functions (No LLM)
pythondef calculate_rsi(bars: list[Bar], period: int = 14) -> float:
    """Relative Strength Index - Pure Math"""
    gains = [max(bars[i].close - bars[i-1].close, 0) for i in range(1, len(bars))]
    losses = [max(bars[i-1].close - bars[i].close, 0) for i in range(1, len(bars))]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(bars: list[Bar]) -> tuple[float, float, float]:
    """MACD - Pure Math"""
    ema12 = calculate_ema(bars, 12)
    ema26 = calculate_ema(bars, 26)
    macd = ema12 - ema26
    signal = calculate_ema([Bar(close=m) for m in macd_history], 9)
    histogram = macd - signal
    return macd, signal, histogram

def apply_risk_limits(signals: list[Signal], max_positions: int, 
                     max_per_position: float, max_total_risk: float) -> list[Signal]:
    """Filter signals by risk constraints - Pure Logic"""
    # Sort by confidence
    signals.sort(key=lambda s: s['confidence'], reverse=True)
    
    # Take top N within position limit
    filtered = signals[:max_positions]
    
    # Adjust position sizes
    for signal in filtered:
        signal['position_size'] = min(
            signal['position_size'],
            max_per_position,
            max_total_risk / (signal['entry_price'] * signal['stop_loss_distance'])
        )
    
    return filtered

DATA FLOW & STORAGE
Supabase Schema
sql-- Performance Tracking
CREATE TABLE daily_performance (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    portfolio_value DECIMAL(12,2),
    cash DECIMAL(12,2),
    positions_value DECIMAL(12,2),
    daily_pnl DECIMAL(10,2),
    daily_pnl_pct DECIMAL(5,2),
    cumulative_return DECIMAL(10,2),
    sharpe_ratio DECIMAL(5,3),
    max_drawdown DECIMAL(5,2),
    win_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trade Logs
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL, -- BUY/SELL
    quantity INTEGER NOT NULL,
    entry_price DECIMAL(10,2) NOT NULL,
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    exit_reason VARCHAR(20), -- stop_loss, take_profit, technical_exit
    pnl DECIMAL(10,2),
    pnl_pct DECIMAL(5,2),
    
    -- Technical Context (for analysis)
    rsi DECIMAL(5,2),
    macd_histogram DECIMAL(10,4),
    volume_ratio DECIMAL(5,2),
    
    -- Metadata
    strategy VARCHAR(20) NOT NULL, -- defensive, momentum, opportunistic
    confidence DECIMAL(3,2),
    alpaca_order_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily Signals (for backtesting)
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    signal_type VARCHAR(10), -- BUY, SELL, HOLD
    rsi DECIMAL(5,2),
    macd_histogram DECIMAL(10,4),
    price DECIMAL(10,2),
    volume_ratio DECIMAL(5,2),
    executed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Strategy Performance
CREATE TABLE strategy_metrics (
    id SERIAL PRIMARY KEY,
    strategy VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,2),
    avg_win DECIMAL(10,2),
    avg_loss DECIMAL(10,2),
    profit_factor DECIMAL(5,2),
    sharpe_ratio DECIMAL(5,3),
    max_drawdown DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
Daily Analysis Loop
pythonasync def analyze_performance():
    """
    Runs after market close, analyzes day's performance
    Deterministisch - kein LLM
    """
    today = date.today()
    
    # Fetch today's trades
    trades = await supabase.get_trades(date=today)
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])
    
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(t['pnl'] for t in trades if t['pnl'] < 0) / losing_trades if losing_trades > 0 else 0
    
    # Store metrics per strategy
    for strategy in ['defensive', 'momentum']:
        strategy_trades = [t for t in trades if t['strategy'] == strategy]
        metrics = calculate_strategy_metrics(strategy_trades)
        await supabase.log_strategy_metrics(strategy, metrics)
    
    # Identify patterns
    best_performers = sorted(trades, key=lambda t: t['pnl_pct'], reverse=True)[:3]
    worst_performers = sorted(trades, key=lambda t: t['pnl_pct'])[:3]
    
    # Adaptive logic (deterministic rules)
    if win_rate < 0.55:
        print("⚠️ Win rate below target, tightening entry criteria")
        # Adjust RSI thresholds: 55 < RSI < 65 (more conservative)
    
    if avg_loss / avg_win > 0.5:  # Risk/Reward worsening
        print("⚠️ Average loss too high, widening stop-loss")
        # Adjust stop-loss: -5% → -7%
    
    return {
        'win_rate': win_rate,
        'profit_factor': avg_win / abs(avg_loss) if avg_loss != 0 else 0,
        'best_performers': best_performers,
        'worst_performers': worst_performers
    }
TESTING STRATEGY
Daily Paper Trading Runs
python# Every day at 9:00 AM EST
1. Run trading loop (live paper trading)
2. Log all decisions to Supabase
3. Evaluate performance at market close
4. Adjust parameters if needed (deterministic rules)

# Weekly Review (Sundays)
- Backtest strategy variants
- Compare vs SPY benchmark
- Optimize thresholds (RSI, MACD)
- Generate performance report
Metrics to Track
yamlPrimary:
  - Total Return vs SPY
  - Win Rate (target: 60%+)
  - Sharpe Ratio (target: >1.2)
  - Max Drawdown (target: <15%)

Secondary:
  - Profit Factor (Avg Win / Avg Loss)
  - Average Trade Duration
  - Best/Worst Performers
  - Strategy Breakdown (Defensive vs Momentum)
Continuous Improvement (Deterministic)
python# Rules for automatic adjustment
if win_rate < 0.55 for 5 consecutive days:
    tighten_entry_criteria()  # RSI 55-65 instead of 50-70

if max_drawdown > 0.12:
    reduce_position_sizes()  # 8% per position instead of 10%

if momentum_strategy_sharpe < defensive_sharpe:
    reallocate_capital()  # 40% defensive, 20% momentum

RISK MANAGEMENT (HARD CODED)
Position Limits
pythonMAX_POSITIONS = 5  # Excluding defensive core
MAX_POSITION_SIZE = 0.10  # 10% of portfolio
MAX_DAILY_RISK = 0.02  # 2% of portfolio per trade
DAILY_LOSS_LIMIT = 0.03  # Circuit breaker at -3%
Exit Rules (Automatic)
python# Stop-Loss
if current_price <= entry_price * 0.95:
    close_position()

# Take-Profit
if current_price >= entry_price * 1.15:
    close_position()

# Technical Exit
if rsi > 75 or macd_histogram < 0:
    close_position()

# Time-Based (Momentum only)
if days_held > 30 and pnl_pct < 0.05:
    close_position()  # Avoid dead capital
```

---

## PROJECT STRUCTURE (nur ein Vorschlag schau genau rein)
```
trading-bot/
├── .env.example                # API keys template
├── .env                        # Actual keys (gitignored)
├── README.md                   # Setup & architecture
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Supabase local dev
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Daily trading loop entry point
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── indicators.py       # RSI, MACD, SMA (pure math)
│   │   ├── risk_manager.py     # Position sizing, stop-loss
│   │   └── portfolio.py        # Rebalancing logic
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── defensive_core.py   # ETF rebalancing
│   │   └── momentum_trading.py # Technical breakout
│   │
│   ├── mcp_clients/
│   │   ├── __init__.py
│   │   ├── alpaca_client.py    # Wrapper for alpaca-docker MCP
│   │   └── data_client.py      # TwelveData, Alpha Vantage
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── portfolio.py        # Pydantic models for portfolio state
│   │   ├── trade.py            # Trade, Signal, Order models
│   │   └── performance.py      # Metrics, returns
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── supabase_client.py  # Async Supabase operations
│   │   └── models.py           # ORM models (if needed)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Structured logging
│       └── config.py           # Load env vars, validate
│
├── migrations/
│   └── 001_initial_schema.sql  # Supabase tables
│
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py      # Unit tests for RSI, MACD
│   ├── test_risk_manager.py
│   ├── test_strategies.py
│   └── fixtures/
│       └── sample_bars.json
│
├── scripts/
│   ├── backtest.py             # Historical performance analysis
│   ├── generate_report.py      # Weekly performance report
│   └── deploy_cron.sh          # Setup daily scheduler
│
├── notebooks/
│   └── strategy_analysis.ipynb # Jupyter for exploration
│
├── n8n_workflows/              # For later UI/monitoring
│   └── (future n8n JSON exports)
│
└── docs/
    ├── ARCHITECTURE.md
    ├── STRATEGY_GUIDE.md
    └── API_REFERENCE.md

SUCCESS CRITERIA (Phase 1 - Week 1)
Must Have

 Daily trading loop runs ohne Fehler (7 consecutive days)
 All trades logged to Supabase with full context
 Defensive Core rebalancing funktioniert (VTI/VGK/GLD)
 Momentum strategy executes >=1 trade/week
 Risk limits enforced (max 10% per position, max 5 positions)
 Paper trading account bleibt profitable (>0% return)

Nice to Have

 Win rate >55%
 Sharpe Ratio >1.0
 Max Drawdown <12%

Anti-Goals (DO NOT)

❌ Use LLMs for deterministic calculations
❌ Build complex multi-agent systems
❌ Trade crypto (focus on equities)
❌ Implement options strategies (Phase 1)
❌ Build custom MCP servers (use existing)
Dont use APIs that are expensive (Danelfin) and respect the free tier APIs conditions to call limitations that we use

