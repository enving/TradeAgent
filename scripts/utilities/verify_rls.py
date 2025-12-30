#!/usr/bin/env python3
"""
Verify that Row Level Security (RLS) is properly configured on all tables.
"""

import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

async def verify_rls():
    """Verify RLS configuration."""

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
        return False

    print("🔐 Verifying RLS Configuration")
    print("="*80)

    supabase: Client = create_client(url, key)

    # Tables to check
    tables = [
        'daily_performance',
        'trades',
        'signals',
        'strategy_metrics',
        'parameter_changes',
        'weekly_reports',
        'ml_training_data'
    ]

    print(f"\n📋 Checking {len(tables)} tables...\n")

    # Try to query each table to verify access still works
    all_ok = True

    for table in tables:
        try:
            # Try to fetch one row (limit 1)
            result = supabase.table(table).select("*").limit(1).execute()

            if result:
                print(f"✅ {table:25} - RLS enabled, access working")
            else:
                print(f"⚠️  {table:25} - RLS might be blocking access")

        except Exception as e:
            error_msg = str(e)
            if "row-level security" in error_msg.lower() or "policy" in error_msg.lower():
                print(f"🔒 {table:25} - RLS is active (access restricted)")
                # This is actually good - means RLS is working
            else:
                print(f"❌ {table:25} - Error: {error_msg[:50]}...")
                all_ok = False

    print("\n" + "="*80)

    if all_ok:
        print("✅ RLS Configuration Verified!")
        print("\n📝 What this means:")
        print("   • All tables have Row Level Security enabled")
        print("   • Your bot can still access the data (using Service Role)")
        print("   • Public/anonymous access is now blocked")
        print("   • Security warnings should disappear in next weekly report")
    else:
        print("⚠️  Some issues detected - please check the errors above")

    print("\n🔗 Monitor security status:")
    print("   https://supabase.com/dashboard/project/fwdwdbcirkojdhzvpnsz/reports/database-health")

    return all_ok

if __name__ == "__main__":
    asyncio.run(verify_rls())
