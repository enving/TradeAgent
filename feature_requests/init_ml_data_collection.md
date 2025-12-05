# Feature Request: ML Data Collection for Self-Learning Trading System

**Date:** 2025-11-19
**Status:** 🚧 Design Phase
**Priority:** High (Foundation for future AI improvements)

---

## Problem Statement

Currently, the trading system operates on **fixed rules** (RSI, MACD, Volume thresholds). We want to build a **self-learning system** that:

1. Collects data from every trade decision
2. Labels outcomes (profitable vs unprofitable)
3. Trains custom time-series models
4. Improves trading decisions over time

**Key Insight from User:**
> "Kaufindikatoren identifizieren bei jedemmal oder nach einem tag. Dann prognose und wider schauen etc. Wir erstellen quasi ein labeled data. Müssen schauen welche daten representativ sind und dann könnten wir darauf ein eigenes time series modell trainieren zb mit fast api."

---

## Proposed Solution: Event-Driven Feature Collection

### What to Collect (Features)

**NOT just technical indicators** - but **event-driven context**:

#### 1. News & Sentiment (at trade time)
- 📰 Recent news headlines for the ticker (last 24h)
- 💬 Sentiment score (FinBERT or similar)
- 📊 News volume (how many articles?)
- 🔥 Breaking news flag (major event detected)

#### 2. Market Events
- 📅 Earnings announcement (within 5 days?)
- 🏛️ Fed meeting / FOMC decision
- 🌍 Macro events (GDP, unemployment, CPI)
- 🏢 Sector-specific events (tech earnings week, etc.)

#### 3. Market Context
- 📉 VIX level (volatility index)
- 📊 SPY performance (overall market trend)
- 🏭 Sector performance (tech, energy, finance)
- 💰 Market breadth (% stocks above SMA50)

#### 4. Technical Indicators (as reference)
- RSI, MACD, Volume (what we already use)
- Price action patterns
- Support/resistance levels

#### 5. Trade Metadata
- Entry price, timestamp
- Why we entered (which rules triggered)
- Portfolio state at entry time

---

## Database Schema Design

### Option 1: Extend `trades` table with JSON

```sql
ALTER TABLE trades
ADD COLUMN features JSONB;

-- Example features JSON:
{
  "news": {
    "headlines": ["Apple announces new iPhone", "AAPL beats earnings"],
    "sentiment_score": 0.75,
    "news_count_24h": 12,
    "breaking_news": true
  },
  "events": {
    "earnings_soon": true,
    "earnings_days_away": 3,
    "fed_meeting": false,
    "macro_event": "CPI_RELEASE"
  },
  "market_context": {
    "vix": 18.5,
    "spy_return_1d": -0.5,
    "sector_performance": {"tech": 1.2, "energy": -0.8},
    "market_breadth": 0.62
  },
  "technicals": {
    "rsi": 65.3,
    "macd_histogram": 0.45,
    "volume_ratio": 1.8,
    "price_vs_sma20": 1.05
  },
  "meta": {
    "strategy": "momentum",
    "trigger_reason": "rsi_macd_volume_match",
    "portfolio_value": 100000,
    "position_count": 3
  }
}
```

### Option 2: Separate `trade_features` table

```sql
CREATE TABLE trade_features (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  trade_id UUID REFERENCES trades(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- News & Sentiment
  news_headlines TEXT[],
  sentiment_score FLOAT,
  news_count_24h INT,
  breaking_news BOOLEAN,

  -- Events
  earnings_soon BOOLEAN,
  earnings_days_away INT,
  fed_meeting BOOLEAN,
  macro_event TEXT,

  -- Market Context
  vix FLOAT,
  spy_return_1d FLOAT,
  sector_performance JSONB,
  market_breadth FLOAT,

  -- Technicals
  rsi FLOAT,
  macd_histogram FLOAT,
  volume_ratio FLOAT,
  price_vs_sma20 FLOAT,

  -- Raw feature vector for ML
  feature_vector JSONB
);
```

### Option 3: Separate `ml_training_data` table

```sql
CREATE TABLE ml_training_data (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  ticker TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,

  -- Input features (X)
  features JSONB NOT NULL,

  -- Labels (Y) - filled in later
  label_timestamp TIMESTAMPTZ,  -- When we labeled it
  hold_period_days INT,         -- 7, 14, 30 days
  outcome TEXT,                  -- 'profitable', 'unprofitable'
  return_pct FLOAT,              -- Actual return
  max_drawdown_pct FLOAT,        -- Worst point during hold

  -- Trade reference (if executed)
  trade_id UUID REFERENCES trades(id),

  -- For filtering training data
  is_labeled BOOLEAN DEFAULT FALSE,
  is_train BOOLEAN,              -- Train/test split
  model_version TEXT             -- Which model was trained on this
);
```

---

## Data Collection Pipeline

### Phase 1: Capture Features at Trade Time

```python
# In src/core/feature_collector.py

class FeatureCollector:
    """Collects event-driven features for ML training."""

    async def collect_features(self, ticker: str) -> dict:
        """Collect all features at current moment."""
        return {
            "news": await self._collect_news(ticker),
            "events": await self._collect_events(ticker),
            "market_context": await self._collect_market_context(),
            "technicals": await self._collect_technicals(ticker),
            "meta": self._collect_meta()
        }

    async def _collect_news(self, ticker: str) -> dict:
        """Fetch recent news and sentiment."""
        # Use MarketAux API (free tier)
        # Or Alpha Vantage NEWS_SENTIMENT endpoint
        headlines = await news_api.get_headlines(ticker, hours=24)
        sentiment = await sentiment_model.analyze(headlines)

        return {
            "headlines": [h["title"] for h in headlines],
            "sentiment_score": sentiment,
            "news_count_24h": len(headlines),
            "breaking_news": any(h["urgency"] == "high" for h in headlines)
        }

    async def _collect_events(self, ticker: str) -> dict:
        """Check for upcoming events."""
        # Use Alpha Vantage EARNINGS_CALENDAR
        # Or FMP API (financialmodelingprep.com)
        earnings = await calendar_api.get_next_earnings(ticker)

        return {
            "earnings_soon": earnings["days_away"] <= 5,
            "earnings_days_away": earnings["days_away"],
            "fed_meeting": await self._check_fed_calendar(),
            "macro_event": await self._check_macro_calendar()
        }
```

### Phase 2: Store Features in Database

```python
# When creating a trade signal:

from src.core.feature_collector import FeatureCollector

async def scan_for_signals(alpaca_client):
    feature_collector = FeatureCollector()

    for ticker in WATCHLIST:
        # ... existing logic ...

        if all(entry_conditions):
            # Collect features BEFORE creating signal
            features = await feature_collector.collect_features(ticker)

            signal = Signal(
                ticker=ticker,
                action="BUY",
                entry_price=entry_price,
                # ... other fields ...
                features=features  # NEW FIELD
            )
```

### Phase 3: Labeling Script (Run Daily)

```python
# scripts/label_trades.py

async def label_trades():
    """Go through unlabeled trades and check outcomes."""

    # Get all trades from 7, 14, 30 days ago
    for hold_period in [7, 14, 30]:
        cutoff_date = datetime.now(UTC) - timedelta(days=hold_period)

        unlabeled = await db.get_unlabeled_trades(
            before_date=cutoff_date,
            hold_period=hold_period
        )

        for trade in unlabeled:
            # Get current price
            current_price = await alpaca.get_latest_quote(trade.ticker)

            # Calculate return
            return_pct = (current_price - trade.entry_price) / trade.entry_price

            # Label
            label = {
                "hold_period_days": hold_period,
                "outcome": "profitable" if return_pct > 0.05 else "unprofitable",
                "return_pct": return_pct,
                "is_labeled": True,
                "label_timestamp": datetime.now(UTC)
            }

            await db.update_trade_label(trade.id, label)
```

---

## Data Sources (Free/Low-Cost)

### News & Sentiment
1. **MarketAux** (https://marketaux.com/)
   - Free tier: 100 requests/day
   - Real-time news with sentiment

2. **Alpha Vantage NEWS_SENTIMENT**
   - Already have API key
   - 25 requests/day (same limit as bars)

3. **FinBERT** (Local sentiment model)
   - Hugging Face model
   - Run locally on CPU
   - No API costs

### Events Calendar
1. **Alpha Vantage EARNINGS_CALENDAR**
   - Free (within 25/day limit)

2. **Financial Modeling Prep (FMP)**
   - Free tier: 250 requests/day
   - Earnings, economic calendar

### Market Context
1. **Alpha Vantage** (VIX, SPY)
   - Already using for bars

2. **FRED API** (Federal Reserve Economic Data)
   - Free
   - Macro indicators (GDP, CPI, unemployment)

---

## ML Training Pipeline (Future - Phase 2)

### Once we have 3-6 months of data:

```python
# models/train_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import AutoModelForSequenceClassification

# Load labeled data
df = await db.get_ml_training_data(is_labeled=True)

# Feature engineering
X = df['features'].apply(lambda x: feature_engineer(x))
y = df['outcome'].map({'profitable': 1, 'unprofitable': 0})

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Option 1: Fine-tune FinBERT on our data
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
# ... training code ...

# Option 2: Time-series model (LSTM/Transformer)
# ... time-series training code ...

# Save model
model.save("models/trade_predictor_v1")
```

### FastAPI Inference Server

```python
# api/main.py

from fastapi import FastAPI
from transformers import pipeline

app = FastAPI()
model = pipeline("sentiment-analysis", model="./models/trade_predictor_v1")

@app.post("/predict")
async def predict_trade(ticker: str, features: dict):
    """Predict if trade will be profitable."""
    prediction = model(features)
    return {
        "ticker": ticker,
        "should_enter": prediction["label"] == "profitable",
        "confidence": prediction["score"]
    }
```

---

## Implementation Roadmap

### Sprint 1: Data Collection Infrastructure (1-2 weeks)
- [ ] Design final database schema (Option 3 recommended)
- [ ] Create `ml_training_data` table in Supabase
- [ ] Implement `FeatureCollector` class
- [ ] Integrate MarketAux or Alpha Vantage NEWS_SENTIMENT
- [ ] Add FinBERT sentiment analysis (local)
- [ ] Update Signal model to include features
- [ ] Update trade execution to store features

### Sprint 2: Labeling & Storage (1 week)
- [ ] Create daily labeling script
- [ ] Set up cron job to run labeling script
- [ ] Implement train/test split logic
- [ ] Create data export script (for ML training)

### Sprint 3: Initial Data Collection (3-6 months)
- [ ] Run system in production
- [ ] Collect at least 100-200 labeled trades
- [ ] Monitor data quality
- [ ] Adjust feature collection as needed

### Sprint 4: ML Training (Future)
- [ ] Export training data
- [ ] Feature engineering
- [ ] Train baseline model
- [ ] Evaluate performance
- [ ] Deploy FastAPI inference server
- [ ] Integrate predictions into trading loop

---

## Expected Outcomes

### After 3 months:
- 100-200 labeled trade examples
- Rich feature dataset with news, events, market context
- Understanding of which features are predictive

### After 6 months:
- 300-500 labeled examples
- First ML model trained
- Baseline performance vs rule-based system

### After 12 months:
- 1000+ labeled examples
- Production ML model
- Continuous improvement loop
- FinBERT fine-tuned on our specific use case

---

## Open Questions

1. **Hold Period:** Should we label at 7, 14, or 30 days? Or all three?
2. **Profit Threshold:** What counts as "profitable"? +5%? +10%?
3. **Feature Priority:** Which features are most important to collect first?
4. **News API:** MarketAux vs Alpha Vantage NEWS_SENTIMENT?
5. **Storage:** JSONB vs separate columns for features?
6. **Model Type:** Time-series (LSTM) or NLP-based (FinBERT)?

---

## Cost Estimate

**API Costs (Monthly):**
- MarketAux Free Tier: $0 (100 req/day)
- Alpha Vantage: $0 (already using, 25/day)
- FinBERT (local): $0 (runs on CPU)
- FMP Free Tier: $0 (250 req/day)
- **Total: $0-5/month**

**Compute Costs (for training):**
- Local CPU: $0
- Cloud GPU (when needed): ~$50-100 for training runs
- FastAPI hosting: $5-10/month (Digital Ocean, Render, etc.)

**Total Monthly:** $0 during collection, $50-100 when training models

---

## Next Steps

1. **Approve database schema** (recommend Option 3: `ml_training_data` table)
2. **Choose news API** (recommend MarketAux for free tier)
3. **Implement FeatureCollector** (start collecting data immediately)
4. **Set up labeling script** (run daily)
5. **Start data collection** (let it run for 3-6 months)

This is a **long-term investment** - but will enable truly adaptive, self-learning trading strategies.
