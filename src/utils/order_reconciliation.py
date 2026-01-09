"""Order Reconciliation Utility.

Syncs Alpaca orders with Supabase trades to ensure all SELLs are logged.
Fixes issues where exits happen in Alpaca but aren't logged in Supabase.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from ..database.supabase_client import SupabaseClient
from ..mcp_clients.alpaca_client import AlpacaMCPClient
from ..models.trade import Trade
from ..utils.logger import logger


async def reconcile_orders(lookback_hours: int = 24) -> dict[str, int]:
    """Reconcile Alpaca orders with Supabase trades.

    Fetches recent orders from Alpaca and ensures all filled SELLs
    are logged in Supabase. This catches exits that happened in Alpaca
    but weren't logged due to timing issues or errors.

    Args:
        lookback_hours: How far back to check for missing orders (default: 24h)

    Returns:
        Dictionary with reconciliation stats:
        {
            "checked": 50,      # Total orders checked
            "missing": 3,       # Missing SELLs found
            "logged": 3,        # Successfully logged
            "errors": 0         # Errors during logging
        }
    """
    logger.info(f"🔄 Starting order reconciliation (lookback: {lookback_hours}h)")

    stats = {
        "checked": 0,
        "missing": 0,
        "logged": 0,
        "errors": 0,
    }

    try:
        # 1. Get recent orders from Alpaca
        alpaca = AlpacaMCPClient()
        alpaca_orders = await alpaca.get_recent_orders(limit=100)

        # Filter to lookback window
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        recent_orders = [
            order for order in alpaca_orders
            if order["filled_at"] and
            datetime.fromisoformat(order["filled_at"].replace("Z", "+00:00")) > cutoff_time
        ]

        logger.info(f"Found {len(recent_orders)} orders in last {lookback_hours}h")

        # 2. Get existing trades from Supabase
        client = await SupabaseClient.get_instance()
        response = (
            await client.table("trades")
            .select("alpaca_order_id, ticker, action, created_at")
            .gte("created_at", cutoff_time.isoformat())
            .execute()
        )

        existing_order_ids = {
            str(trade["alpaca_order_id"])
            for trade in (response.data or [])
            if trade.get("alpaca_order_id")
        }

        logger.info(f"Found {len(existing_order_ids)} trades in Supabase")

        # 3. Find missing orders (especially SELLs)
        for order in recent_orders:
            stats["checked"] += 1

            # Skip if already logged
            if order["id"] in existing_order_ids:
                continue

            # Skip if not filled
            if order["status"] != "filled":
                continue

            # Found missing order!
            stats["missing"] += 1

            logger.warning(
                f"📊 Found missing {order['side'].upper()} order: "
                f"{order['symbol']} x{order['filled_qty']} @ ${order['filled_avg_price']} "
                f"(Order ID: {order['id']}, Filled: {order['filled_at']})"
            )

            # 4. Log missing order to Supabase
            try:
                # Determine if this is a BUY or SELL
                action = "BUY" if order["side"] == "buy" else "SELL"

                # For SELLs, we need to find the original BUY to calculate PnL
                entry_price = None
                pnl = None
                pnl_pct = None

                if action == "SELL":
                    # Try to find matching BUY
                    buy_response = (
                        await client.table("trades")
                        .select("entry_price, quantity")
                        .eq("ticker", order["symbol"])
                        .eq("action", "BUY")
                        .is_("exit_price", "null")
                        .order("date", desc=True)
                        .limit(1)
                        .execute()
                    )

                    if buy_response.data and len(buy_response.data) > 0:
                        buy_trade = buy_response.data[0]
                        entry_price = Decimal(str(buy_trade["entry_price"]))
                        exit_price = Decimal(str(order["filled_avg_price"]))
                        quantity = Decimal(str(order["filled_qty"]))

                        # Calculate PnL
                        pnl = (exit_price - entry_price) * quantity
                        pnl_pct = (exit_price - entry_price) / entry_price

                        logger.info(
                            f"  Matched with BUY @ ${entry_price:.2f}, "
                            f"PnL: ${pnl:.2f} ({pnl_pct:.2%})"
                        )
                    else:
                        logger.warning(
                            f"  Could not find matching BUY for {order['symbol']} - "
                            f"logging SELL without PnL"
                        )
                        entry_price = Decimal(str(order["filled_avg_price"]))  # Use exit as entry

                # Create trade object
                trade = Trade(
                    date=datetime.fromisoformat(order["filled_at"].replace("Z", "+00:00")),
                    ticker=order["symbol"],
                    action=action,
                    quantity=Decimal(str(order["filled_qty"])),
                    entry_price=entry_price or Decimal(str(order["filled_avg_price"])),
                    exit_price=Decimal(str(order["filled_avg_price"])) if action == "SELL" else None,
                    exit_reason="technical_exit" if action == "SELL" else None,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    strategy="momentum",  # Assume momentum (could be improved)
                    alpaca_order_id=order["id"],
                )

                # Log to Supabase
                await SupabaseClient.log_trade(trade)
                stats["logged"] += 1

                logger.info(f"✅ Logged missing {action}: {order['symbol']}")

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"Failed to log missing order {order['id']} ({order['symbol']}): {e}",
                    exc_info=True,
                )

        # 5. Summary
        logger.info(
            f"🔄 Reconciliation complete: "
            f"{stats['checked']} checked, "
            f"{stats['missing']} missing, "
            f"{stats['logged']} logged, "
            f"{stats['errors']} errors"
        )

        return stats

    except Exception as e:
        logger.error(f"Order reconciliation failed: {e}", exc_info=True)
        raise
