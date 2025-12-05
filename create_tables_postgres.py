"""Create Supabase tables using direct PostgreSQL connection.

Uses psycopg2 to execute SQL schema directly.
"""

import asyncio
from pathlib import Path
from src.utils.logger import logger


async def create_tables_via_postgres():
    """Create tables using PostgreSQL connection."""
    try:
        # Try to import psycopg2
        try:
            import psycopg2
        except ImportError:
            logger.error("psycopg2 not installed!")
            logger.info("Install with: pip install psycopg2-binary")
            return False

        # Supabase PostgreSQL connection string format:
        # postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

        logger.info("=" * 70)
        logger.info("SUPABASE POSTGRES CONNECTION")
        logger.info("=" * 70)
        logger.info("")
        logger.info("To create tables via PostgreSQL, you need the connection string.")
        logger.info("")
        logger.info("Get it from:")
        logger.info("https://supabase.com/dashboard/project/swaaegpotcnkphradxsx/settings/database")
        logger.info("")
        logger.info("Look for: 'Connection string' (URI format)")
        logger.info("")
        logger.info("Add to .env as:")
        logger.info("SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.swaaegpotcnkphradxsx.supabase.co:5432/postgres")
        logger.info("")
        logger.info("=" * 70)
        logger.info("")
        logger.info("ALTERNATIVE: Use Supabase SQL Editor (Recommended)")
        logger.info("=" * 70)
        logger.info("")
        logger.info("1. Go to: https://supabase.com/dashboard/project/swaaegpotcnkphradxsx/sql")
        logger.info("2. Click 'New Query'")
        logger.info("3. Copy contents from: src/database/schema.sql")
        logger.info("4. Paste and click 'RUN'")
        logger.info("")
        logger.info("This is the easiest and recommended method!")
        logger.info("")
        logger.info("=" * 70)

        return False

    except Exception as e:
        logger.error(f"Error: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(create_tables_via_postgres())
    exit(0 if result else 1)
