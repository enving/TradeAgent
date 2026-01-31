#!/usr/bin/env python3
"""
Agent Health Check Script
Use this script to quickly verify the operational status of the TradeAgent system.
It checks:
1. Local environment variables
2. Supabase connection
3. (Optional) SSH connection to Raspberry Pi if configured
"""

import os
import sys
from dotenv import load_dotenv

try:
    from supabase import create_client
    import paramiko
except ImportError:
    print("❌ Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)


def check_local_env():
    print("\n🔍 Checking Local Environment...")
    load_dotenv()

    required_vars = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY"]

    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False

    print("✅ Local environment variables found.")
    return True


def check_supabase():
    print("\n🔍 Checking Supabase Connection...")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("⚠️ Skipping Supabase check (credentials missing)")
        return False

    try:
        client = create_client(url, key)
        # Just try to fetch one row from trades to verify connection
        # Using count='exact' and head=True (limit 0) to verify table access without fetching data
        client.table("trades").select("*", count="exact").limit(0).execute()
        print("✅ Supabase connection successful.")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False


def check_pi_connection():
    print("\n🔍 Checking Raspberry Pi Connection (Optional)...")
    user = os.getenv("PI_USERNAME") or os.getenv("user_name")
    pw = os.getenv("PI_PASSWORD") or os.getenv("user_pw")
    host = os.getenv("PI_HOST", "raspberrypi.local")

    if not user or not pw:
        print("ℹ️  Skipping Pi check (PI_USERNAME/PI_PASSWORD not set)")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"   Connecting to {user}@{host}...")
        ssh.connect(
            host, username=user, password=pw, look_for_keys=False, allow_agent=False, timeout=5
        )

        # Check service status
        stdin, stdout, stderr = ssh.exec_command("pgrep -f 'python.*event_driven'")
        pid = stdout.read().decode("utf-8").strip()

        if pid:
            print(f"✅ TradeAgent Service is RUNNING on Pi (PID: {pid})")
        else:
            print("⚠️  TradeAgent Service is STOPPED on Pi")

        ssh.close()
        return True
    except Exception as e:
        print(f"⚠️  Could not connect to Pi: {str(e)}")
        return False


def main():
    print("🤖 TradeAgent Health Check")
    print("==========================")

    env_ok = check_local_env()
    if not env_ok:
        sys.exit(1)

    check_supabase()
    check_pi_connection()

    print("\nSummary: Basic checks completed.")


if __name__ == "__main__":
    main()
