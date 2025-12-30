-- Migration: Add orchestrator_decisions table
-- Purpose: Log all AI orchestrator decisions for audit trail and analysis
-- Date: 2025-12-30

-- Create orchestrator_decisions table
CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decision_type TEXT NOT NULL,
    input_data JSONB,
    output_data JSONB,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_timestamp
    ON orchestrator_decisions(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_type
    ON orchestrator_decisions(decision_type);

-- Enable Row Level Security
ALTER TABLE orchestrator_decisions ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (full access)
CREATE POLICY "Service role has full access to orchestrator_decisions"
    ON orchestrator_decisions
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Add comment
COMMENT ON TABLE orchestrator_decisions IS 'Audit trail of all AI orchestrator decisions including market regime analysis, signal scoring, and strategy adjustments';

COMMENT ON COLUMN orchestrator_decisions.decision_type IS 'Type of decision: market_regime_analysis, signal_quality_scoring, signal_prioritization, trade_decision_explanation, strategy_weight_adjustment';
COMMENT ON COLUMN orchestrator_decisions.input_data IS 'Input data used for the decision (market data, signals, portfolio state)';
COMMENT ON COLUMN orchestrator_decisions.output_data IS 'Output/result of the decision (scores, rankings, recommendations)';
COMMENT ON COLUMN orchestrator_decisions.reasoning IS 'LLM-generated reasoning for the decision';
