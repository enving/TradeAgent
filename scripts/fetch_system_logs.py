import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client


async def fetch_logs():
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment")
        return

    try:
        supabase: Client = create_client(url, key)

        response = (
            supabase.table("system_logs")
            .select("*")
            .order("timestamp", desc=True)
            .limit(50)
            .execute()
        )

        logs = response.data
        if logs:
            print(f"Found {len(logs)} log entries. Showing latest first:")
            print("-" * 80)
            for log in logs:
                ts = log.get("timestamp", "")
                lvl = log.get("level", "UNKNOWN")
                mod = log.get("module", "UNKNOWN")
                msg = log.get("message", "")
                print(f"[{ts}] [{lvl}] [{mod}] {msg}")

                trace = log.get("trace")
                if trace:
                    print(f"Trace: {trace}")
                print("-" * 40)
        else:
            print("No logs found.")
        return

    except Exception as e:
        print(f"Error fetching logs: {e}")


if __name__ == "__main__":
    asyncio.run(fetch_logs())
