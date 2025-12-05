-- Migration: Add parameter_changes table for Adaptive Strategy Optimizer
-- Date: 2025-12-04
-- Purpose: Track parameter optimization changes over time

-- Drop existing table if it exists (to recreate with correct schema)
DROP TABLE IF EXISTS parameter_changes CASCADE;

-- Create parameter_changes table with correct schema
CREATE TABLE parameter_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy VARCHAR(50) NOT NULL,
    old_params JSONB NOT NULL,
    new_params JSONB NOT NULL,
    reason TEXT,
    performance_metrics JSONB,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_parameter_changes_strategy
    ON parameter_changes(strategy);

CREATE INDEX IF NOT EXISTS idx_parameter_changes_changed_at
    ON parameter_changes(changed_at DESC);

-- Enable RLS (Row Level Security)
ALTER TABLE parameter_changes ENABLE ROW LEVEL SECURITY;

-- Create RLS policy (allow all for now, can be restricted per user later)
CREATE POLICY "Enable read access for all users" ON parameter_changes
    FOR SELECT USING (true);

CREATE POLICY "Enable insert access for all users" ON parameter_changes
    FOR INSERT WITH CHECK (true);

-- Add helpful comments
COMMENT ON TABLE parameter_changes IS 'Tracks adaptive parameter optimization changes';
COMMENT ON COLUMN parameter_changes.strategy IS 'Strategy name (momentum, news_sentiment, etc.)';
COMMENT ON COLUMN parameter_changes.old_params IS 'Previous parameter values (JSON)';
COMMENT ON COLUMN parameter_changes.new_params IS 'New optimized parameter values (JSON)';
COMMENT ON COLUMN parameter_changes.reason IS 'Reason for parameter change';
COMMENT ON COLUMN parameter_changes.performance_metrics IS 'Performance metrics that led to this change (Sharpe ratio, etc.)';
