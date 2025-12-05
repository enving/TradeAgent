-- Migration: Add News and LLM Analysis Logging (Clean Version)
-- Created: 2025-12-03
-- Purpose: Store ALL news articles and LLM analyses (not just signals)

-- ============================================================================
-- 1. NEWS ARTICLES ARCHIVE
-- ============================================================================
CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Article identification
    ticker VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(100) NOT NULL,
    url TEXT NOT NULL,

    -- Timestamps
    published_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),

    -- Deduplication
    UNIQUE(url)
);

CREATE INDEX IF NOT EXISTS idx_news_articles_ticker ON news_articles(ticker);
CREATE INDEX IF NOT EXISTS idx_news_articles_published ON news_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_fetched ON news_articles(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source);

-- ============================================================================
-- 2. LLM SENTIMENT ANALYSIS LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_analysis_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Analysis context
    ticker VARCHAR(10) NOT NULL,
    analysis_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- LLM output
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'HOLD')),
    sentiment_score DECIMAL(4,2) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    impact VARCHAR(10) NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW')),
    reasoning TEXT NOT NULL,

    -- Context
    article_count INT NOT NULL DEFAULT 0,
    lookback_days INT NOT NULL DEFAULT 2,

    -- Signal generation flow
    signal_generated BOOLEAN DEFAULT FALSE,
    signal_approved BOOLEAN DEFAULT FALSE,
    technical_filter_reason TEXT,

    -- Link to signal if generated
    signal_id UUID,

    -- Model metadata
    llm_model VARCHAR(50) DEFAULT 'claude-3.5-sonnet',
    llm_provider VARCHAR(50) DEFAULT 'openrouter',
    llm_tokens_used INT,
    llm_cost_usd DECIMAL(10,6)
);

CREATE INDEX IF NOT EXISTS idx_llm_analysis_ticker ON llm_analysis_log(ticker);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_timestamp ON llm_analysis_log(analysis_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_action ON llm_analysis_log(action);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_impact ON llm_analysis_log(impact);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_signal_gen ON llm_analysis_log(signal_generated);
CREATE INDEX IF NOT EXISTS idx_llm_analysis_flow ON llm_analysis_log(signal_generated, signal_approved);

-- ============================================================================
-- 3. UPDATE EXISTING TABLES TO SUPPORT 'news_sentiment'
-- ============================================================================

-- Drop old constraints (if they exist)
ALTER TABLE trades DROP CONSTRAINT IF EXISTS trades_strategy_check;
ALTER TABLE signals DROP CONSTRAINT IF EXISTS signals_strategy_check;
ALTER TABLE strategy_metrics DROP CONSTRAINT IF EXISTS strategy_metrics_strategy_check;

-- Add new constraints with 'news_sentiment'
ALTER TABLE trades ADD CONSTRAINT trades_strategy_check
CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment'));

ALTER TABLE signals ADD CONSTRAINT signals_strategy_check
CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment'));

ALTER TABLE strategy_metrics ADD CONSTRAINT strategy_metrics_strategy_check
CHECK (strategy IN ('defensive', 'momentum', 'news_anomaly', 'news_sentiment'));

-- Add metadata column to signals table if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'signals' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE signals ADD COLUMN metadata JSONB;
    END IF;
END $$;

-- ============================================================================
-- 4. ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_analysis_log ENABLE ROW LEVEL SECURITY;

-- Create policies (only if they don't exist)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'news_articles' AND policyname = 'Service role full access'
    ) THEN
        CREATE POLICY "Service role full access"
        ON news_articles FOR ALL TO service_role
        USING (true) WITH CHECK (true);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'llm_analysis_log' AND policyname = 'Service role full access'
    ) THEN
        CREATE POLICY "Service role full access"
        ON llm_analysis_log FOR ALL TO service_role
        USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ============================================================================
-- 5. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE news_articles IS 'Archive of all news articles fetched from Yahoo Finance, Finnhub, and NewsAPI';
COMMENT ON TABLE llm_analysis_log IS 'Complete log of every LLM sentiment analysis, including rejected signals';
COMMENT ON COLUMN llm_analysis_log.reasoning IS 'Full explanation from Claude on why BUY/SELL/HOLD was recommended';
COMMENT ON COLUMN llm_analysis_log.technical_filter_reason IS 'If signal_generated=TRUE but signal_approved=FALSE, why was it rejected?';
COMMENT ON COLUMN llm_analysis_log.sentiment_score IS 'Range -1.0 (bearish) to +1.0 (bullish)';
