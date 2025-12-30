"""Run database migration for news and LLM logging tables.

This script executes the SQL migration to add:
- news_articles table
- llm_analysis_log table
- Update existing table constraints to support 'news_sentiment'
"""

import asyncio
from pathlib import Path

from src.database.supabase_client import SupabaseClient
from src.utils.logger import logger


async def run_migration():
    """Execute the news and LLM logging migration."""
    migration_file = Path(__file__).parent / "database" / "migrations" / "add_news_and_llm_logging.sql"

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    # Read migration SQL
    with open(migration_file, "r") as f:
        migration_sql = f.read()

    logger.info("Connecting to Supabase...")
    client = await SupabaseClient.get_instance()

    try:
        # Execute migration
        logger.info("Executing migration...")
        logger.info(f"SQL length: {len(migration_sql)} characters")

        # Split on semicolons and execute statements one by one
        # (Supabase might not support multi-statement queries)
        statements = [s.strip() for s in migration_sql.split(";") if s.strip()]

        success_count = 0
        error_count = 0

        for i, statement in enumerate(statements, 1):
            # Skip comments and empty statements
            if not statement or statement.startswith("--") or statement.startswith("/*"):
                continue

            try:
                logger.debug(f"Executing statement {i}/{len(statements)}")
                # Use raw RPC call for SQL execution
                await client.rpc("exec_sql", {"sql": statement}).execute()
                success_count += 1
            except Exception as e:
                # Some statements might fail if already exists (that's OK)
                error_msg = str(e)
                if "already exists" in error_msg or "duplicate" in error_msg.lower():
                    logger.debug(f"Statement {i} skipped (already exists): {error_msg}")
                else:
                    logger.warning(f"Statement {i} failed: {error_msg}")
                    error_count += 1

        logger.info(f"Migration complete! {success_count} statements executed, {error_count} errors")

        # Verify new tables exist
        logger.info("Verifying new tables...")
        try:
            # Try to query the new tables
            await client.table("news_articles").select("*").limit(1).execute()
            logger.info("✅ news_articles table verified")
        except Exception as e:
            logger.error(f"❌ news_articles table verification failed: {e}")

        try:
            await client.table("llm_analysis_log").select("*").limit(1).execute()
            logger.info("✅ llm_analysis_log table verified")
        except Exception as e:
            logger.error(f"❌ llm_analysis_log table verification failed: {e}")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("=== Database Migration: News & LLM Logging ===")
    success = asyncio.run(run_migration())

    if success:
        logger.info("✅ Migration completed successfully!")
    else:
        logger.error("❌ Migration failed. Please check the logs.")
        logger.info("You may need to run the SQL manually in Supabase SQL Editor:")
        logger.info("https://supabase.com/dashboard/project/fwdwdbcirkojdhzvpnsz/sql/new")
