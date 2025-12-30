-- Fix Schema Issues
-- 1. Drop and recreate parameter_changes with correct schema
-- 2. Create missing orchestrator_decisions table

-- Drop old parameter_changes table
DROP TABLE IF EXISTS parameter_changes CASCADE;

-- Recreate with correct schema
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_parameter_changes_strategy ON parameter_changes(strategy);
CREATE INDEX IF NOT EXISTS idx_parameter_changes_changed_at ON parameter_changes(changed_at DESC);

-- Enable RLS
ALTER TABLE parameter_changes ENABLE ROW LEVEL SECURITY;

-- Create policy (only if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'parameter_changes' AND policyname = 'Service role full access'
    ) THEN
        CREATE POLICY "Service role full access" ON parameter_changes FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- Create missing orchestrator_decisions table
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

-- Create policy (only if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'orchestrator_decisions' AND policyname = 'Service role full access'
    ) THEN
        CREATE POLICY "Service role full access" ON orchestrator_decisions FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- Add comments
COMMENT ON TABLE parameter_changes IS 'Tracks adaptive parameter optimization changes';
COMMENT ON TABLE orchestrator_decisions IS 'Audit trail of all AI orchestrator decisions';
