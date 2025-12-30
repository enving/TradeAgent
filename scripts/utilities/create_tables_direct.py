"""Create Supabase tables directly using service_role key."""

import asyncio
import os
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()


async def create_all_tables():
    """Create all database tables using service_role key."""

    try:
        # Get credentials
        supabase_url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        logger.info("=" * 70)
        logger.info("Creating Supabase Tables (Direct)")
        logger.info("=" * 70)
        logger.info(f"URL: {supabase_url}")
        logger.info(f"Using service_role key: {service_role_key[:20]}...")
        logger.info("")

        # Create client with service_role key
        supabase = create_client(supabase_url, service_role_key)

        logger.info("Connected to Supabase!")
        logger.info("")

        # Read schema SQL
        schema_path = Path(__file__).parent / "src" / "database" / "schema.sql"
        schema_sql = schema_path.read_text()

        logger.info("Read schema file successfully")
        logger.info("")

        # The Python SDK doesn't support direct SQL execution
        # We need to use the SQL Editor in the dashboard OR PostgreSQL connection

        logger.info("=" * 70)
        logger.info("SQL Execution Method")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Supabase Python SDK doesn't support direct SQL execution.")
        logger.info("")
        logger.info("FASTEST METHOD: Copy/Paste in SQL Editor (30 seconds)")
        logger.info("")
        logger.info("1. Go to SQL Editor:")
        logger.info(f"   https://supabase.com/dashboard/project/fwdwdbcirkojdhzvpnsz/sql")
        logger.info("")
        logger.info("2. Click 'New Query'")
        logger.info("")
        logger.info("3. Copy ALL content from: src/database/schema.sql")
        logger.info("")
        logger.info("4. Paste and click 'RUN'")
        logger.info("")
        logger.info("=" * 70)
        logger.info("")
        logger.info("After creating tables, run:")
        logger.info("  .venv/Scripts/python.exe test_integration.py")
        logger.info("")
        logger.info("=" * 70)

        return True

    except Exception as e:
        logger.error(f"Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(create_all_tables())
    exit(0 if result else 1)
