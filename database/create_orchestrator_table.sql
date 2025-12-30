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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_timestamp ON orchestrator_decisions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_orchestrator_decisions_type ON orchestrator_decisions(decision_type);

-- Enable RLS
ALTER TABLE orchestrator_decisions ENABLE ROW LEVEL SECURITY;

-- Create policy for service role
DROP POLICY IF EXISTS "Service role full access" ON orchestrator_decisions;
CREATE POLICY "Service role full access" ON orchestrator_decisions
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Add comment
COMMENT ON TABLE orchestrator_decisions IS 'Audit trail of all AI orchestrator decisions';
