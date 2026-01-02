#!/usr/bin/env python3
"""
Create missing Supabase tables
Requires PostgreSQL connection (psycopg2)
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# This script requires the PostgreSQL connection string
# Get it from: Supabase Dashboard → Settings → Database → Connection String

POSTGRES_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

if not POSTGRES_URL:
    print("❌ Missing DATABASE_URL or POSTGRES_URL in .env")
    print("\nTo get it:")
    print("1. Go to Supabase Dashboard → Settings → Database")
    print("2. Copy 'Connection String' (URI format)")
    print("3. Add to .env: DATABASE_URL=postgresql://postgres......")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed")
    print("Install it: pip install psycopg2-binary")
    sys.exit(1)

# SQL to create orchestrator_decisions table
CREATE_TABLE_SQL = """
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
"""

def main():
    print("="*60)
    print("  Creating Missing Supabase Tables")
    print("="*60)

    try:
        print("\nConnecting to Supabase PostgreSQL...")
        conn = psycopg2.connect(POSTGRES_URL)
        cursor = conn.cursor()

        print("✅ Connected!")

        print("\nCreating orchestrator_decisions table...")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()

        print("✅ Table created successfully!")

        # Verify
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'orchestrator_decisions'
        """)
        count = cursor.fetchone()[0]

        if count > 0:
            print("\n✅ Verification: Table exists in database")
        else:
            print("\n⚠️  Table creation may have failed")

        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("  ✅ Success!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
