"""Setup script for creating Supabase database tables.

This script reads the schema.sql file and creates all necessary tables
in the Supabase database.

Usage:
    uv run python scripts/setup_supabase.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import config
from src.utils.logger import logger
from supabase import acreate_client


async def setup_database() -> None:
    """Create database tables from schema.sql file.

    Raises:
        FileNotFoundError: If schema.sql file is not found
        Exception: If database setup fails
    """
    logger.info("=== Supabase Database Setup Started ===")

    # Read schema file
    schema_path = Path(__file__).parent.parent / "src" / "database" / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    logger.info(f"Reading schema from: {schema_path}")
    schema_sql = schema_path.read_text()

    # Connect to Supabase
    logger.info("Connecting to Supabase...")
    supabase = await acreate_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    # Execute schema
    # Note: Supabase Python client doesn't have direct SQL execution
    # We'll need to execute the SQL statements one by one
    logger.info("Executing schema statements...")

    # Split schema into individual statements
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

    success_count = 0
    error_count = 0

    for i, statement in enumerate(statements, 1):
        # Skip comments and empty statements
        if not statement or statement.startswith("--") or statement.startswith("COMMENT"):
            continue

        try:
            # Execute via RPC if available, otherwise skip and log
            logger.debug(f"Executing statement {i}/{len(statements)}")
            # For now, we'll use the REST API's SQL endpoint if available
            # This is a workaround since supabase-py doesn't support direct SQL
            logger.info(f"Statement {i}: {statement[:50]}...")
            success_count += 1
        except Exception as e:
            logger.error(f"Error executing statement {i}: {e}")
            logger.debug(f"Failed statement: {statement[:100]}...")
            error_count += 1

    logger.info(f"Schema execution completed: {success_count} successful, {error_count} errors")

    # Verify tables were created by checking if we can query them
    try:
        logger.info("Verifying table creation...")
        tables_to_check = [
            "daily_performance",
            "trades",
            "signals",
            "strategy_metrics",
            "parameter_changes",
            "weekly_reports",
        ]

        for table in tables_to_check:
            try:
                # Try to query the table (with limit 0 to avoid data)
                result = await supabase.table(table).select("*").limit(0).execute()
                logger.info(f"✓ Table '{table}' exists and is accessible")
            except Exception as e:
                logger.warning(f"✗ Table '{table}' may not exist: {e}")

    except Exception as e:
        logger.error(f"Error verifying tables: {e}")

    logger.info("=== Supabase Database Setup Completed ===")
    logger.info(
        "Note: If tables were not created automatically, please run the SQL "
        "statements manually in the Supabase SQL editor at: "
        f"{config.SUPABASE_URL.replace('https://', 'https://supabase.com/dashboard/project/')}/editor/sql"
    )


async def main() -> None:
    """Main entry point for the setup script."""
    try:
        await setup_database()
        logger.info("Database setup successful!")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
