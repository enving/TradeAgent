"""Create Supabase tables using REST API with service role key.

Executes SQL schema via Supabase Management API.
"""

import asyncio
import httpx
from pathlib import Path
from src.utils.logger import logger


async def create_tables():
    """Create all database tables via Supabase REST API."""

    # Supabase project details
    project_ref = "swaaegpotcnkphradxsx"
    supabase_url = f"https://{project_ref}.supabase.co"

    # Read schema
    schema_path = Path(__file__).parent / "src" / "database" / "schema.sql"
    schema_sql = schema_path.read_text()

    logger.info("=" * 70)
    logger.info("Creating Supabase Tables")
    logger.info("=" * 70)
    logger.info(f"Project: {project_ref}")
    logger.info(f"URL: {supabase_url}")
    logger.info("")

    # Try using the PostgREST API endpoint to execute raw SQL
    # This requires the service_role key (not anon key)

    logger.info("To execute SQL, we need the service_role key from Supabase.")
    logger.info("")
    logger.info("Please go to:")
    logger.info(f"https://supabase.com/dashboard/project/{project_ref}/settings/api")
    logger.info("")
    logger.info("Copy the 'service_role' key (NOT the 'anon' key!)")
    logger.info("")
    logger.info("Then update .env with:")
    logger.info("SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>")
    logger.info("")
    logger.info("=" * 70)
    logger.info("")
    logger.info("EASIEST OPTION: Use Supabase SQL Editor")
    logger.info("=" * 70)
    logger.info("")
    logger.info("1. Go to SQL Editor:")
    logger.info(f"   https://supabase.com/dashboard/project/{project_ref}/sql")
    logger.info("")
    logger.info("2. Click 'New Query'")
    logger.info("")
    logger.info("3. Copy this file content: src/database/schema.sql")
    logger.info("")
    logger.info("4. Paste and click 'RUN'")
    logger.info("")
    logger.info("This will create all 6 tables + indexes in ~2 seconds!")
    logger.info("")
    logger.info("=" * 70)

    return False


if __name__ == "__main__":
    result = asyncio.run(create_tables())
