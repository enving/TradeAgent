-- =============================================================================
-- TradeAgent Complete Database Schema
-- Combined schema for new Supabase project setup
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PART 1: Base Tables (Core Trading System)
-- -----------------------------------------------------------------------------

-- Daily Performance Metrics
CREATE TABLE IF NOT EXISTS daily_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL UNIQUE,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
    daily_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    profit_factor DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_win DECIMAL(12,2) NOT NULL DEFAULT 0,
    avg_loss DECIMAL(12,2) NOT NULL DEFAULT 0,
    portfolio_value DECIMAL(15,2),
    cash DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trade Execution Log
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    action VARCHAR(4) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity DECIMAL(15,6) NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    exit_price DECIMAL(12,4),
    exit_reason VARCHAR(20) CHECK (exit_reason IN ('stop_loss', 'take_profit', 'technical_exit', 'rebalance')),
    pnl DECIMAL(12,2),
    pnl_pct DECIMAL(8,4),
    strategy VARCHAR(50) NOT NULL CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment')),
    rsi DECIMAL(5,2),
    macd_histogram DECIMAL(12,6),
    volume_ratio DECIMAL(8,4),
    alpaca_order_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trading Signals Log
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(3,2) NOT NULL,
    entry_price DECIMAL(12,4) NOT NULL,
    stop_loss DECIMAL(12,4),
    take_profit DECIMAL(12,4),
    rsi DECIMAL(5,2),
    macd_histogram DECIMAL(12,6),
    volume_ratio DECIMAL(8,4),
    strategy VARCHAR(50) NOT NULL CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment')),
    executed BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Strategy Performance Metrics
CREATE TABLE IF NOT EXISTS strategy_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy VARCHAR(50) NOT NULL CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment')),
    date DATE NOT NULL,
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    avg_win DECIMAL(12,2),
    avg_loss DECIMAL(12,2),
    profit_factor DECIMAL(10,4),
    sharpe_ratio DECIMAL(5,3),
    max_drawdown DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(strategy, date)
);

-- Weekly Performance Reports
CREATE TABLE IF NOT EXISTS weekly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_ending DATE NOT NULL UNIQUE,
    total_trades INTEGER NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    best_performers JSONB,
    worst_performers JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- PART 2: ML Training Data Collection
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ml_training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    timestamp TIMESTAMPTZ NOT NULL,
    entry_price DECIMAL(12, 4) NOT NULL,
    strategy TEXT NOT NULL,
    features JSONB NOT NULL,
    label_timestamp TIMESTAMPTZ,
    hold_period_days INT,
    exit_price DECIMAL(12, 4),
    outcome TEXT CHECK (outcome IN ('profitable', 'unprofitable', 'neutral', NULL)),
    return_pct DECIMAL(8, 4),
    max_drawdown_pct DECIMAL(8, 4),
    max_gain_pct DECIMAL(8, 4),
    is_labeled BOOLEAN DEFAULT FALSE,
    is_train BOOLEAN,
    model_version TEXT,
    prediction_at_entry DECIMAL(8, 4),
    trade_id UUID REFERENCES trades(id),
    signal_id UUID REFERENCES signals(id),
    sharpe_ratio DECIMAL(8, 4)
);

-- -----------------------------------------------------------------------------
-- PART 3: News & LLM Analysis Logging
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(url)
);

CREATE TABLE IF NOT EXISTS llm_analysis_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) NOT NULL,
    analysis_timestamp TIMESTAMPTZ DEFAULT NOW(),
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
    sentiment_score DECIMAL(4,2) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    impact VARCHAR(10) NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW')),
    reasoning TEXT NOT NULL,
    article_count INT NOT NULL DEFAULT 0,
    lookback_days INT NOT NULL DEFAULT 2,
    signal_generated BOOLEAN DEFAULT FALSE,
    signal_approved BOOLEAN DEFAULT FALSE,
    technical_filter_reason TEXT,
    signal_id UUID,
    llm_model VARCHAR(50) DEFAULT 'claude-3.5-sonnet',
    llm_provider VARCHAR(50) DEFAULT 'openrouter',
    llm_tokens_used INT,
    llm_cost_usd DECIMAL(10,6)
);

-- -----------------------------------------------------------------------------
-- PART 4: Parameter Changes (Adaptive Optimization)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS parameter_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy VARCHAR(50) NOT NULL,
    old_params JSONB NOT NULL,
    new_params JSONB NOT NULL,
    reason TEXT,
    performance_metrics JSONB,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- PART 5: AI Orchestrator Decisions
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_type TEXT NOT NULL,
    input_data JSONB,
    output_data JSONB,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES for Performance
-- =============================================================================

-- Base tables
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date DESC);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_strategy_metrics_date ON strategy_metrics(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_performance_date ON daily_performance(date DESC);

-- ML training data
CREATE INDEX IF NOT EXISTS idx_ml_training_ticker ON ml_training_data(ticker);
CREATE INDEX IF NOT EXISTS idx_ml_training_timestamp ON ml_training_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_ml_training_labeled ON ml_training_data(is_labeled);
CREATE INDEX IF NOT EXISTS idx_ml_training_strategy ON ml_training_data(strategy);
CREATE INDEX IF NOT EXISTS idx_ml_training_outcome ON ml_training_data(outcome);
CREATE INDEX IF NOT EXISTS idx_ml_training_labeling ON ml_training_data(is_labeled, timestamp) WHERE is_labeled = FALSE;
CREATE INDEX IF NOT EXISTS idx_ml_training_split ON ml_training_data(is_train) WHERE is_train IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ml_training_features ON ml_training_data USING GIN (features);

-- News & LLM
CREATE INDEX IF NOT EXISTS idx_news_articles_ticker ON news_articles(ticker);
CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_fetched ON news_articles(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_ticker ON llm_analysis_log(ticker);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_timestamp ON llm_analysis_log(analysis_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_action ON llm_analysis_log(action);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_impact ON llm_analysis_log(impact);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_signal_gen ON llm_analysis_log(signal_generated);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_flow ON llm_analysis_log(signal_generated, signal_approved);

-- Parameter changes
CREATE INDEX IF NOT EXISTS idx_parameter_changes_strategy ON parameter_changes(strategy);
CREATE INDEX IF NOT EXISTS idx_parameter_changes_changed_at ON parameter_changes(changed_at DESC);

-- Orchestrator
CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_timestamp ON orchestrator_decisions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_type ON orchestrator_decisions(decision_type);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

ALTER TABLE daily_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_training_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_analysis_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE parameter_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE orchestrator_decisions ENABLE ROW LEVEL SECURITY;

-- Service role policies (full access)
CREATE POLICY "Service role full access" ON daily_performance FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON trades FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON signals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON strategy_metrics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON weekly_reports FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON ml_training_data FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON news_articles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON llm_analysis_log FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON parameter_changes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON orchestrator_decisions FOR ALL USING (true) WITH CHECK (true);

-- =============================================================================
-- COMMENTS (Documentation)
-- =============================================================================

COMMENT ON TABLE daily_performance IS 'Daily aggregated performance metrics across all strategies';
COMMENT ON TABLE trades IS 'Complete log of all executed trades with entry/exit details';
COMMENT ON TABLE signals IS 'Log of all trading signals generated by strategies';
COMMENT ON TABLE strategy_metrics IS 'Performance metrics broken down by strategy type';
COMMENT ON TABLE weekly_reports IS 'Weekly performance summaries and analysis';
COMMENT ON TABLE ml_training_data IS 'ML training data with features and labels for self-learning models';
COMMENT ON TABLE news_articles IS 'Archive of all news articles fetched from various sources';
COMMENT ON TABLE llm_analysis_log IS 'Complete log of every LLM sentiment analysis';
COMMENT ON TABLE parameter_changes IS 'Tracks adaptive parameter optimization changes';
COMMENT ON TABLE orchestrator_decisions IS 'Audit trail of all AI orchestrator decisions';
