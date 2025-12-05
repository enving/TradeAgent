"""Check current portfolio status from Supabase."""

import asyncio
from src.database.supabase_client import SupabaseClient

async def main():
    import json
    from decimal import Decimal
    
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Decimal):
                return float(o)
            return super().default(o)

    data = {}
    supabase = await SupabaseClient.get_instance()
    
    try:
        # Portfolio (using daily_performance as proxy for latest status)
        response = await supabase.table("daily_performance").select("*").order("date", desc=True).limit(1).execute()
        if response.data:
            data["portfolio"] = response.data[0]
        else:
            data["portfolio"] = None
            
        # Trades
        response = await supabase.table("trades").select("*").order("date", desc=True).limit(5).execute()
        data["trades"] = response.data
        
        print("JSON_START")
        print(json.dumps(data, cls=DecimalEncoder, indent=2))
        print("JSON_END")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
