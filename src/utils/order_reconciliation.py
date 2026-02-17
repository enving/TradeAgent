"""Order Reconciliation Utility.

Syncs Alpaca orders with PostgreSQL trades to ensure all SELLs are logged.
Fixes issues where exits happen in Alpaca but aren't logged in PostgreSQL.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import text

from ..database.postgres_client import PostgresClient
from ..mcp_clients.alpaca_client import AlpacaMCPClient
from ..models.trade import Trade
from ..utils.logger import logger


async def reconcile_orders(lookback_hours: int = 24) -> dict[str, int]:
    """Reconcile Alpaca orders with PostgreSQL trades.

    Fetches recent orders from Alpaca and ensures all filled SELLs
    are logged in PostgreSQL. This catches exits that happened in Alpaca
    but weren't logged due to timing issues or errors.

    Args:
        lookback_hours: How far back to check for missing orders (default: 24h)

    Returns:
        Dictionary with reconciliation stats:
        {
            "checked": 50,      # Total orders checked
            "updated": 3,       # Existing trades updated with order IDs
            "missing": 0,       # Completely missing orders found
            "logged": 0,        # New trades logged
            "errors": 0         # Errors during processing
        }
    """
    logger.info(f"🔄 Starting order reconciliation (lookback: {lookback_hours}h)")

    stats = {
        "checked": 0,
        "updated": 0,
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

        # 2. Get existing trades from PostgreSQL
        db = await PostgresClient.get_instance()
        
        stmt = text("""
            SELECT id, alpaca_order_id, ticker, action, date, quantity, created_at
            FROM trades
            WHERE created_at >= :cutoff
        """)
        
        existing_trades = []
        async with db._connection() as conn:
            result = await conn.execute(stmt, {"cutoff": cutoff_time})
            existing_trades = [dict(row._mapping) for row in result.fetchall()]

        existing_order_ids = {
            str(trade["alpaca_order_id"])
            for trade in existing_trades
            if trade.get("alpaca_order_id")
        }

        # Build lookup for trades with null alpaca_order_id
        # Key: (ticker, action, date_hour, quantity)
        null_order_trades = {}
        for trade in existing_trades:
            if not trade.get("alpaca_order_id"):
                # Use hour-level precision for matching (avoid microsecond mismatches)
                # date column contains datetime
                # Handle possible datetime string vs object (SQLAlchemy returns object usually)
                trade_date = trade["date"]
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date.replace("Z", "+00:00"))
                elif isinstance(trade_date, datetime) and trade_date.tzinfo is None:
                    # Assume UTC if naive, or check DB
                    trade_date = trade_date.replace(tzinfo=timezone.utc)
                
                trade_hour = trade_date.replace(minute=0, second=0, microsecond=0)
                key = (
                    trade["ticker"],
                    trade["action"],
                    trade_hour.isoformat(),
                    str(trade["quantity"])
                )
                null_order_trades[key] = trade

        logger.info(
            f"Found {len(existing_order_ids)} trades with order IDs, "
            f"Found {len(null_order_trades)} trades with null order IDs"
        )

        # 3. Find missing orders and update null order IDs
        for order in recent_orders:
            stats["checked"] += 1

            # Skip if already logged
            if order["id"] in existing_order_ids:
                continue

            # Skip if not filled
            if order["status"] != "filled":
                continue

            # Check if this matches a trade with null alpaca_order_id
            order_date = datetime.fromisoformat(order["filled_at"].replace("Z", "+00:00"))
            order_hour = order_date.replace(minute=0, second=0, microsecond=0)
            action = "BUY" if order["side"] == "buy" else "SELL"

            match_key = (
                order["symbol"],
                action,
                order_hour.isoformat(),
                str(order["filled_qty"])
            )

            # If we find a matching trade with null order ID, UPDATE it
            if match_key in null_order_trades:
                existing_trade = null_order_trades[match_key]
                try:
                    logger.info(
                        f"🔄 Updating existing {action} trade with missing order ID: "
                        f"{order['symbol']} (Trade ID: {existing_trade['id']}, "
                        f"Order ID: {order['id']})"
                    )

                    # Update the trade with the alpaca_order_id
                    update_stmt = text("""
                        UPDATE trades
                        SET alpaca_order_id = :order_id
                        WHERE id = :trade_id
                    """)
                    
                    async with db._connection() as conn:
                        await conn.execute(update_stmt, {
                            "order_id": order["id"],
                            "trade_id": existing_trade["id"]
                        })

                    stats["updated"] += 1
                    logger.info(f"✅ Updated trade with order ID: {order['id']}")
                    continue

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"Failed to update trade {existing_trade['id']} with order ID: {e}",
                        exc_info=True,
                    )
                    continue

            # Found completely missing order!
            stats["missing"] += 1

            logger.warning(
                f"📊 Found missing {order['side'].upper()} order: "
                f"{order['symbol']} x{order['filled_qty']} @ ${order['filled_avg_price']} "
                f"(Order ID: {order['id']}, Filled: {order['filled_at']})"
            )

            # 4. Log missing order to PostgreSQL
            try:
                # Determine if this is a BUY or SELL
                action = "BUY" if order["side"] == "buy" else "SELL"

                # For SELLs, we need to find the original BUY to calculate PnL
                entry_price = None
                pnl = None
                pnl_pct = None

                if action == "SELL":
                    # Try to find matching BUY - Find most recent BUY for this ticker with no exit_price? 
                    # OR if we are reconciling passed trades, maybe just finding one that's open.
                    
                    buy_query = text("""
                        SELECT entry_price, quantity
                        FROM trades
                        WHERE ticker = :ticker
                          AND action = 'BUY'
                          AND exit_price IS NULL
                        ORDER BY date DESC
                        LIMIT 1
                    """)
                    
                    buy_trade = None
                    async with db._connection() as conn:
                        res = await conn.execute(buy_query, {"ticker": order["symbol"]})
                        row = res.fetchone()
                        if row:
                            buy_trade = dict(row._mapping)

                    if buy_trade:
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

                # Log to PostgreSQL
                await PostgresClient.log_trade(trade)
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
            f"{stats['updated']} updated, "
            f"{stats['missing']} missing, "
            f"{stats['logged']} logged, "
            f"{stats['errors']} errors"
        )

        return stats

    except Exception as e:
        logger.error(f"Order reconciliation failed: {e}", exc_info=True)
        raise
