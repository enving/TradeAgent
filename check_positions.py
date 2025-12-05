"""Quick check of current portfolio positions."""

import asyncio
from src.mcp_clients.alpaca_client import AlpacaMCPClient


async def check_positions():
    """Check current positions."""
    client = AlpacaMCPClient()

    portfolio = await client.get_account()
    positions = await client.get_positions()

    print("=" * 60)
    print("CURRENT PORTFOLIO")
    print("=" * 60)
    print(f"Portfolio Value: ${portfolio.portfolio_value:,.2f}")
    print(f"Cash: ${portfolio.cash:,.2f}")
    print(f"Buying Power: ${portfolio.buying_power:,.2f}")
    print()
    print(f"Positions ({len(positions)}):")
    print("-" * 60)

    for pos in positions:
        value = float(pos.quantity) * float(pos.current_price)
        pnl_pct = float(pos.unrealized_pnl_pct) * 100
        pnl_sign = "+" if float(pos.unrealized_pnl) >= 0 else ""

        print(f"{pos.symbol:6} | {pos.quantity:8} shares @ ${pos.current_price:7.2f}")
        print(f"       | Value: ${value:,.2f} | P&L: {pnl_sign}${pos.unrealized_pnl:.2f} ({pnl_pct:+.2f}%)")
        print()

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_positions())
