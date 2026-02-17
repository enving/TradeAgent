#!/usr/bin/env python3
"""
Agent Health Check Script
Use this script to quickly verify the operational status of the TradeAgent system.
It checks:
1. Local environment variables
2. PostgreSQL connection
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.database.postgres_client import PostgresClient
except ImportError as e:
    print(f"❌ Missing dependencies or project structure issue: {e}")
    sys.exit(1)


def check_local_env():
    print("\n🔍 Checking Local Environment...")
    load_dotenv()

    required_vars = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "POSTGRES_HOST", "POSTGRES_PORT"]

    # Check for POSTGRES_URL as an alternative or addition
    if not os.getenv("POSTGRES_URL"):
         # Construct it or check individual parts
         pass

    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False

    print("✅ Local environment variables found.")
    return True


async def check_postgres():
    print("\n🔍 Checking PostgreSQL Connection...")
    
    try:
        client = await PostgresClient.get_instance()
        # Verify connection by running a simple query
        async with client._connection() as conn:
            await conn.execute("SELECT 1")
            
        print("✅ PostgreSQL connection successful.")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {str(e)}")
        return False


async def main():
    print("🤖 TradeAgent Health Check")
    print("==========================")

    env_ok = check_local_env()
    if not env_ok:
        sys.exit(1)

    postgres_ok = await check_postgres()
    if not postgres_ok:
        sys.exit(1)

    print("\nSummary: Basic checks completed.")


if __name__ == "__main__":
    asyncio.run(main())
