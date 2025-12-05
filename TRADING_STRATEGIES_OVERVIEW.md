# 🎯 TradeAgent - Trading Strategies Overview

**Last Updated:** 2025-12-03
**System Status:** ✅ FULLY OPERATIONAL with LLM Features

---

## 🔄 Active Trading Strategies (3 Total)

### 1. **Defensive Core Strategy** (30% Allocation)
**File:** `src/strategies/defensive_core.py`
**Purpose:** Stable foundation with broad market exposure

#### Allocation:
- **VTI** (US Total Market): 25%
- **VGK** (European Markets): 15% → Adjusted to 10% for optimization
- **GLD** (Gold): 10%

#### Rebalancing Triggers:
1. First trading day of each month (uses market calendar, not hardcoded)
2. Portfolio drift > 5% from target allocations

#### Logic:
```python
# Pure deterministic - no AI
if is_first_trading_day() or drift > 5%:
    target_value = portfolio_value * allocation_pct
    current_value = get_position_value(ticker)
    shares_to_trade = (target_value - current_value) / price
    execute_rebalance_order(shares_to_trade)
```

---

### 2. **Momentum Trading Strategy** (50% Allocation)
**File:** `src/strategies/momentum_trading.py`
**Purpose:** Capture technical breakouts with systematic rules

#### Entry Criteria (ALL must be TRUE):
1. **RSI:** 45-75 (widened range for more opportunities)
2. **MACD Histogram:** > 0 (positive momentum)
3. **Price:** > 50-day SMA (uptrend confirmation)
4. **Golden Cross:** SMA20 > SMA50 (strong trend)
5. **Volume:** > 1.1x average (institutional interest)

#### Exit Conditions:
1. **Stop-loss:** 3% below entry (risk management)
2. **Take-profit:** 8% above entry (realistic target)
3. **RSI > 75:** Overbought, manual exit
4. **Holding period:** > 30 days (prevent bag-holding)

#### Watchlist (15 stocks, diversified):
- **Tech:** AAPL, MSFT, NVDA, GOOGL, META
- **Growth:** TSLA, AMD, NFLX, AVGO
- **Finance:** JPM, BAC
- **Energy:** XOM, CVX
- **Healthcare:** LLY, JNJ

#### Risk Management:
- Max 5 concurrent positions
- 10% max position size per trade
- 2:1 minimum risk/reward ratio

#### Data Source:
- **Primary:** yfinance (unlimited, free)
- **Fallback:** Alpha Vantage (5 calls/min)

---

### 3. **🤖 News-Driven Strategy** (20% Allocation) ⭐ NEW
**File:** `src/strategies/news_driven.py`
**Purpose:** LLM-powered sentiment analysis for high-conviction trades

#### How It Works:

**Step 1: News Aggregation**
```python
# Multi-source news collection
sources = [
    "Yahoo Finance",   # Real-time company news
    "Finnhub",        # Earnings, SEC filings
    "NewsAPI"         # General financial news
]
articles = aggregate_news(ticker, days=2)
```

**Step 2: LLM Sentiment Analysis**
```python
# Claude 3.5 Sonnet analyzes news
prognosis = llm.analyze_news(ticker, articles)

# Returns:
{
    "action": "BUY" | "SELL" | "HOLD",
    "sentiment_score": 0.85,  # -1.0 to 1.0
    "confidence": 0.9,        # 0.0 to 1.0
    "impact": "HIGH" | "MEDIUM" | "LOW",
    "reasoning": "Strong earnings beat with guidance raise..."
}
```

**Step 3: Technical Confirmation**
```python
# Only proceed if sentiment is bullish
if prognosis.action == "BUY" and \
   prognosis.sentiment_score >= 0.7 and \
   prognosis.impact == "HIGH":

    # Verify with technicals
    if current_price > sma20:
        generate_buy_signal()
```

#### Entry Criteria:
1. **Sentiment Score:** ≥ 0.7 (strong bullish)
2. **Impact Rating:** "HIGH" (material news)
3. **LLM Confidence:** ≥ 0.8 (high certainty)
4. **Technical:** Price > SMA20 (uptrend)

#### Exit Strategy:
- **Stop-loss:** 5% below entry
- **Take-profit:** 15% above entry (news trades can run)
- **Time-based:** 14 days max holding

#### Example Signal:
```json
{
    "ticker": "AAPL",
    "action": "BUY",
    "entry_price": 185.50,
    "confidence": 0.92,
    "strategy": "news_sentiment",
    "metadata": {
        "sentiment_score": 0.85,
        "impact": "HIGH",
        "reasoning": "Apple announces record iPhone 15 sales in China,
                     beating analyst expectations by 12%. Strong demand
                     indicates continued market dominance.",
        "source_count": 8
    }
}
```

---

## 📊 Strategy Allocation Breakdown

| Strategy         | Allocation | Max Positions | Risk/Trade | Data Source        |
|------------------|------------|---------------|------------|--------------------|
| Defensive Core   | 30%        | 3 (fixed)     | N/A        | Alpaca/yfinance    |
| Momentum         | 50%        | 5             | 3%         | yfinance           |
| News-Driven      | 20%        | 2             | 5%         | Multi-source + LLM |

**Total Portfolio:** $100,000 (Paper Trading)

---

## 🔄 Daily Trading Loop Workflow

```python
async def daily_trading_loop():
    # 1. Market Check
    if not market_is_open():
        return

    # 2. Portfolio State
    portfolio = fetch_portfolio_from_alpaca()

    # 3. Defensive Core (Monthly)
    if is_first_trading_day_of_month():
        rebalance_signals = check_defensive_rebalancing()
        execute_orders(rebalance_signals)

    # 4. Momentum Scanning
    momentum_signals = scan_momentum_watchlist()
    approved_signals = risk_filter(momentum_signals)

    # 5. News-Driven Scanning (NEW)
    if ENABLE_NEWS_SIGNALS:
        news_signals = scan_news_driven_watchlist()
        approved_news = risk_filter(news_signals)
        approved_signals.extend(approved_news)

    # 6. Execute Approved Signals
    for signal in approved_signals:
        order = create_bracket_order(signal)
        execute_order(order)
        log_to_supabase(signal)
        collect_ml_features(signal)  # For future ML training

    # 7. Check Exit Conditions
    for position in open_positions:
        if should_exit(position):
            close_position(position)

    # 8. Daily Analytics
    analyze_performance()

    # 9. Weekly Report (Sundays)
    if is_sunday():
        generate_weekly_report()
```

---

## 🧠 ML Data Collection (Passive Learning)

Every trade automatically logs:

### Technical Features:
- RSI, MACD, Volume Ratio
- SMA20, SMA50 crossovers
- Price momentum

### News/Sentiment Features:
- LLM sentiment score
- News article count
- Impact rating (HIGH/MEDIUM/LOW)
- Source diversity

### Meta Features:
- Strategy type
- Entry/exit prices
- Time of day
- Market volatility (VIX)

### Labeling (Future):
- **7-day return:** Short-term outcome
- **14-day return:** Medium-term outcome
- **30-day return:** Long-term outcome

**Purpose:** After 3-6 months of data, train ML models to:
1. Optimize entry/exit timing
2. Predict signal success rates
3. Adjust position sizing dynamically
4. Identify best market conditions for each strategy

---

## 🎯 Current Performance Metrics

| Metric                  | Target | Current Status          |
|-------------------------|--------|-------------------------|
| Portfolio Value         | N/A    | $101,553.97             |
| Open Positions          | ≤ 5    | 3                       |
| Defensive Allocation    | 30%    | ✅ Balanced             |
| Momentum Allocation     | 50%    | Active (0 signals today)|
| News-Driven Allocation  | 20%    | ⚡ NEW - Testing        |
| Daily Loss Limit        | -3%    | Circuit breaker active  |
| Max Position Size       | 10%    | Enforced                |

---

## 🚀 Recent Enhancements (2025-12-03)

1. ✅ **LLM Integration** - OpenRouter + Claude 3.5 Sonnet
2. ✅ **Multi-Source News** - Yahoo, Finnhub, NewsAPI aggregation
3. ✅ **News-Driven Strategy** - Sentiment-based signal generation
4. ✅ **Timezone Fixes** - All datetime operations now timezone-aware
5. ✅ **Row Level Security** - Supabase RLS enabled on all tables
6. ✅ **yfinance Migration** - Unlimited free data for momentum scanning

---

## 📈 Strategy Success Criteria

### Defensive Core:
- ✅ Maintains 30% allocation ±2%
- ✅ Rebalances monthly
- ✅ Zero manual intervention

### Momentum:
- 🎯 60%+ win rate (tracking)
- 🎯 2:1 avg reward/risk (tracking)
- 🎯 Max 5% portfolio drawdown

### News-Driven:
- 🎯 70%+ win rate (NEW - collecting data)
- 🎯 High-impact news only
- 🎯 LLM confidence ≥ 0.8

---

## 🛡️ Risk Management Rules

### Hard Limits:
- **Max Positions:** 5 (momentum) + 2 (news) = 7 total
- **Max Position Size:** 10% per trade
- **Daily Loss Limit:** -3% (circuit breaker)
- **Max Daily Risk:** 2% per new position

### Filters:
1. **Correlation Check:** No duplicate sector exposure
2. **News Verification:** Momentum signals verified with sentiment if enabled
3. **Volume Check:** Minimum liquidity requirements
4. **Market Hours:** Only trade during regular hours

---

## 📝 Notes

- All strategies are **100% deterministic** (except news-driven sentiment analysis)
- LLM is used for **analysis only**, not execution decisions
- Final buy/sell decisions still require technical confirmation
- All trades logged to Supabase for transparency
- ML models will be trained offline, never in production loop

---

**Documentation:** `PLANNING.md`, `CLAUDE.md`, `TASK.md`
**Dashboard:** https://supabase.com/dashboard/project/fwdwdbcirkojdhzvpnsz
**Alpaca:** https://app.alpaca.markets/paper/dashboard/overview
