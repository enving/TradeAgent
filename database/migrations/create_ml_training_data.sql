-- ML Training Data Collection Table
-- Created: 2025-11-19
-- Purpose: Store features and labels for self-learning trading models

CREATE TABLE IF NOT EXISTS ml_training_data (
  -- Primary key
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Trade identification
  ticker TEXT NOT NULL,
  action TEXT NOT NULL, -- 'BUY' or 'SELL'
  timestamp TIMESTAMPTZ NOT NULL,

  -- Entry details
  entry_price DECIMAL(12, 4) NOT NULL,
  strategy TEXT NOT NULL, -- 'momentum', 'defensive_core', etc.

  -- Feature vector (collected at trade time)
  features JSONB NOT NULL,

  -- Labels (filled in later by labeling script)
  label_timestamp TIMESTAMPTZ,
  hold_period_days INT, -- 7, 14, or 30 days
  exit_price DECIMAL(12, 4),
  outcome TEXT, -- 'profitable', 'unprofitable', 'neutral'
  return_pct DECIMAL(8, 4),
  max_drawdown_pct DECIMAL(8, 4),
  max_gain_pct DECIMAL(8, 4),

  -- Labeling status
  is_labeled BOOLEAN DEFAULT FALSE,

  -- ML pipeline metadata
  is_train BOOLEAN, -- Train/test split
  model_version TEXT, -- Which model was trained on this
  prediction_at_entry DECIMAL(8, 4), -- If we had a model, what did it predict?

  -- Link to actual trade (if executed)
  trade_id UUID REFERENCES trades(id),
  signal_id UUID REFERENCES signals(id),

  -- Performance tracking
  sharpe_ratio DECIMAL(8, 4), -- For this specific trade

  -- Indexes for fast queries
  CONSTRAINT valid_outcome CHECK (outcome IN ('profitable', 'unprofitable', 'neutral', NULL)),
  CONSTRAINT valid_action CHECK (action IN ('BUY', 'SELL'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ml_training_ticker ON ml_training_data(ticker);
CREATE INDEX IF NOT EXISTS idx_ml_training_timestamp ON ml_training_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_ml_training_labeled ON ml_training_data(is_labeled);
CREATE INDEX IF NOT EXISTS idx_ml_training_strategy ON ml_training_data(strategy);
CREATE INDEX IF NOT EXISTS idx_ml_training_outcome ON ml_training_data(outcome);

-- Index for labeling script (find unlabeled trades from X days ago)
CREATE INDEX IF NOT EXISTS idx_ml_training_labeling
ON ml_training_data(is_labeled, timestamp)
WHERE is_labeled = FALSE;

-- Index for train/test queries
CREATE INDEX IF NOT EXISTS idx_ml_training_split
ON ml_training_data(is_train)
WHERE is_train IS NOT NULL;

-- GIN index for fast JSONB queries on features
CREATE INDEX IF NOT EXISTS idx_ml_training_features ON ml_training_data USING GIN (features);

-- Comments for documentation
COMMENT ON TABLE ml_training_data IS 'Stores features and labels for ML model training. Features collected at trade time, labels added later.';
COMMENT ON COLUMN ml_training_data.features IS 'JSONB containing: {news, events, market_context, technicals, meta}';
COMMENT ON COLUMN ml_training_data.is_labeled IS 'TRUE after labeling script has evaluated trade outcome';
COMMENT ON COLUMN ml_training_data.hold_period_days IS 'How many days we held before labeling (7, 14, or 30)';
COMMENT ON COLUMN ml_training_data.outcome IS 'profitable (>5%), unprofitable (<-2%), neutral (between)';

-- Example features structure:
/*
{
  "news": {
    "headlines": ["Apple announces new iPhone", "AAPL beats earnings"],
    "sentiment_score": 0.75,
    "sentiment_label": "positive",
    "news_count_24h": 12,
    "breaking_news": true,
    "top_topics": ["earnings", "product_launch"]
  },
  "events": {
    "earnings_soon": true,
    "earnings_days_away": 3,
    "fed_meeting_soon": false,
    "fed_days_away": null,
    "macro_event": "CPI_RELEASE",
    "sector_event": null
  },
  "market_context": {
    "vix": 18.5,
    "vix_change_1d": -1.2,
    "spy_return_1d": -0.5,
    "spy_return_5d": 2.1,
    "sector_performance": {
      "technology": 1.2,
      "energy": -0.8,
      "financials": 0.3
    },
    "market_breadth": 0.62,
    "put_call_ratio": 0.85
  },
  "technicals": {
    "rsi": 65.3,
    "macd_histogram": 0.45,
    "volume_ratio": 1.8,
    "price_vs_sma20": 1.05,
    "price_vs_sma50": 1.12,
    "bollinger_position": 0.7,
    "atr": 3.5
  },
  "meta": {
    "strategy": "momentum",
    "trigger_reason": "rsi_macd_volume_match",
    "portfolio_value": 100000,
    "position_count": 3,
    "cash_available": 50000,
    "market_hours": "regular",
    "day_of_week": "Monday"
  }
}
*/
