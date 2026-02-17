"""Initialize PostgreSQL database schema.

Reads src/database/schema.sql and executes it against the configured PostgreSQL database.
"""

import asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.utils.config import config
from src.utils.logger import logger

async def setup_database():
    """Create tables using schema.sql."""
    try:
        logger.info(f"Connecting to database: {config.POSTGRES_URL}")
        
        # Create engine
        engine = create_async_engine(
            config.POSTGRES_URL,
            echo=True,
        )
        
        # Read schema file
        schema_path = Path("src/database/schema.sql")
        if not schema_path.exists():
            logger.error(f"Schema file not found: {schema_path}")
            return False
            
        logger.info(f"Reading schema from {schema_path}")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
            
        # Execute schema
        # Split by statements because asyncpg/SQLAlchemy doesn't support multiple statements in one execute call
        statements = schema_sql.split(";")
        
        async with engine.begin() as conn:
            logger.info(f"Executing {len(statements)} statements...")
            for statement in statements:
                if statement.strip():
                    await conn.execute(text(statement))
            logger.info("Schema execution completed successfully.")
            
        # Verify tables created
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {tables}")
            
        return True

    except Exception as e:
        logger.error(f"Failed to setup database: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(setup_database())
    if success:
        logger.info("✅ Database setup complete")
        exit(0)
    else:
        logger.error("❌ Database setup failed")
        exit(1)
