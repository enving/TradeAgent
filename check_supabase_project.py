"""Check which Supabase project is correct."""

import asyncio
import os
import httpx
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()


async def check_project():
    """Check both project refs."""

    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # Decode JWT to see project ref
    import base64
    import json

    try:
        # JWT format: header.payload.signature
        parts = service_role_key.split('.')
        payload = parts[1]

        # Add padding if needed
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)

        decoded = base64.urlsafe_b64decode(payload)
        jwt_data = json.loads(decoded)

        logger.info("=" * 70)
        logger.info("JWT Token Analysis")
        logger.info("=" * 70)
        logger.info(f"Project Ref (from JWT): {jwt_data.get('ref')}")
        logger.info(f"Role: {jwt_data.get('role')}")
        logger.info(f"Issuer: {jwt_data.get('iss')}")
        logger.info("")

        correct_ref = jwt_data.get('ref')
        correct_url = f"https://{correct_ref}.supabase.co"

        logger.info("=" * 70)
        logger.info("CORRECT CONFIGURATION")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Update .env with:")
        logger.info(f"SUPABASE_URL={correct_url}")
        logger.info("")
        logger.info("The service_role key matches this project!")
        logger.info("")
        logger.info("=" * 70)

        return correct_ref

    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        return None


if __name__ == "__main__":
    result = asyncio.run(check_project())
