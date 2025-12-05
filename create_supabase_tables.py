"""Create Supabase tables directly using the Python client.

Uses Supabase Python SDK to execute SQL schema.
"""

import asyncio
from supabase import create_client
from src.utils.config import config
from src.utils.logger import logger
from pathlib import Path


async def create_tables():
    """Create all Supabase tables."""
    try:
        logger.info("Connecting to Supabase...")
        logger.info(f"URL: {config.SUPABASE_URL}")

        # Create synchronous client for SQL execution
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

        logger.info("Connected successfully!")

        # Read schema file
        schema_path = Path(__file__).parent / "src" / "database" / "schema.sql"
        schema_sql = schema_path.read_text()

        logger.info(f"Read schema from: {schema_path}")
        logger.info("")

        # Execute SQL via RPC or direct query
        # Supabase Python client doesn't have direct SQL execution
        # We need to use the REST API or execute via PostgREST

        logger.info("=" * 70)
        logger.info("SUPABASE DATABASE SETUP INSTRUCTIONS")
        logger.info("=" * 70)
        logger.info("")
        logger.info("The Python SDK doesn't support direct SQL execution.")
        logger.info("Please follow these steps:")
        logger.info("")
        logger.info("1. Go to Supabase SQL Editor:")
        logger.info("   https://supabase.com/dashboard/project/swaaegpotcnkphradxsx/sql")
        logger.info("")
        logger.info("2. Click 'New Query'")
        logger.info("")
        logger.info("3. Copy and paste the following SQL:")
        logger.info("   (File: src/database/schema.sql)")
        logger.info("")
        logger.info("4. Click 'RUN' to create all tables")
        logger.info("")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Tables to be created:")
        logger.info("  - trades (trade execution log)")
        logger.info("  - signals (trading signals)")
        logger.info("  - daily_performance (daily metrics)")
        logger.info("  - strategy_metrics (per-strategy performance)")
        logger.info("  - parameter_changes (parameter audit)")
        logger.info("  - weekly_reports (weekly summaries)")
        logger.info("")
        logger.info("=" * 70)
        logger.info("")

        # Test connection by checking if we can query
        try:
            result = supabase.table("trades").select("*").limit(1).execute()
            logger.info("SUCCESS: 'trades' table already exists!")
            logger.info("Database is ready to use.")
            return True
        except Exception as e:
            if "relation" in str(e).lower() or "does not exist" in str(e).lower():
                logger.warning("Tables not yet created - please follow instructions above")
                return False
            else:
                logger.error(f"Error checking tables: {e}")
                return False

    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        logger.error("")
        logger.error("Please check your .env file:")
        logger.error(f"  SUPABASE_URL={config.SUPABASE_URL}")
        logger.error("  SUPABASE_KEY=<check if valid>")
        return False


if __name__ == "__main__":
    result = asyncio.run(create_tables())
    exit(0 if result else 1)
