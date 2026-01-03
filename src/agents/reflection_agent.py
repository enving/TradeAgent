"""Reflection Agent - self-improvement module.

Analyzes past trading performance to identify patterns of success and failure.
Implements the "Self-Reflection" loop found in advanced agentic systems.
"""

from datetime import datetime, timezone
from typing import Dict, Any
import json

from ..database.supabase_client import SupabaseClient
from ..utils.logger import logger


class ReflectionAgent:
    """Agent that learns from past trades."""

    def __init__(self):
        self.supabase = SupabaseClient.get_instance()

    async def run_daily_reflection(self) -> Dict[str, Any]:
        """Run daily reflection on recently closed trades."""
        logger.info("🧠 Reflection Agent: Starting daily analysis...")

        try:
            client = await self.supabase
            response = (
                client.table("trades").select("*").order("date", desc=True).limit(20).execute()
            )
            trades_data = response.data

            closed_trades = [
                t for t in trades_data if t.get("action") == "SELL" and t.get("pnl") is not None
            ]

            if not closed_trades:
                logger.info("Reflection Agent: No closed trades to analyze today.")
                return {"status": "no_trades"}

            total_pnl = sum(float(t["pnl"]) for t in closed_trades)
            win_count = len([t for t in closed_trades if float(t["pnl"]) > 0])
            win_rate = win_count / len(closed_trades) if closed_trades else 0

            logger.info(
                f"Reflection Stats: {len(closed_trades)} trades, PnL: ${total_pnl:.2f}, Win Rate: {win_rate:.1%}"
            )

            lessons = []
            if total_pnl < 0:
                lessons.append(
                    "Daily PnL negative: Consider tightening stop-losses during volatility."
                )
            if win_rate < 0.5:
                lessons.append("Win rate below 50%: Review entry criteria for Momentum strategy.")

            reflection_result = {
                "date": datetime.now(timezone.utc).isoformat(),
                "trades_analyzed": len(closed_trades),
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "lessons": lessons,
            }

            logger.info(f"Reflection Result: {json.dumps(reflection_result, indent=2)}")

            return reflection_result

        except Exception as e:
            logger.error(f"Reflection Agent failed: {e}")
            return {"status": "error", "error": str(e)}
