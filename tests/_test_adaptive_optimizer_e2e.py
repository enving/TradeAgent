import asyncio
import os
from dotenv import load_dotenv
from src.ml.adaptive_optimizer import get_optimizer
from src.database.supabase_client import SupabaseClient


async def test_optimizer_e2e():
    print("Starting Adaptive Optimizer E2E Test...")
    load_dotenv()

    optimizer = get_optimizer()

    # Run optimization for momentum
    print("Running optimization for momentum strategy...")
    try:
        best_params = await optimizer.optimize_momentum_parameters()
        print(f"✅ Optimization finished. Best params: {best_params}")

        # Check if it was logged to Supabase
        client = await SupabaseClient.get_instance()
        response = (
            await client.table("parameter_changes")
            .select("*")
            .order("changed_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            last_change = response.data[0]
            print(f"✅ Found log in Supabase: {last_change['reason']}")
            if last_change["strategy"] == "momentum":
                print("✅ Correct strategy logged")
            else:
                print(f"❌ Wrong strategy logged: {last_change['strategy']}")
        else:
            print("❌ No logs found in parameter_changes table")

    except Exception as e:
        print(f"❌ Error during optimization: {e}")


if __name__ == "__main__":
    asyncio.run(test_optimizer_e2e())
