"""Tools for the Trading Orchestrator Agent."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import yfinance as yf
from openai import AsyncOpenAI

from sqlalchemy import text
from ...database.postgres_client import PostgresClient
from ...models.portfolio import Portfolio, Position
from ...models.trade import Signal
from ...utils.config import config
from ...utils.logger import logger


class OrchestratorTools:
    """Tools that the orchestrator agent uses to make decisions."""

    def __init__(self):
        """Initialize tools with flexible LLM provider support."""
        if not config.LLM_API_KEY:
            logger.warning(
                f"No LLM API key configured (provider: {config.LLM_PROVIDER}) - "
                "Orchestrator will have limited functionality"
            )
            self.llm_client = None
        else:
            logger.info(
                f"Initializing LLM client: provider={config.LLM_PROVIDER}, model={config.LLM_MODEL}"
            )
            self.llm_client = AsyncOpenAI(
                api_key=config.LLM_API_KEY,
                base_url=config.LLM_BASE_URL,
            )

    async def call_llm(self, prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        """Call LLM with a prompt and parse JSON response.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response

        Returns:
            Parsed JSON response as dictionary
        """
        if not self.llm_client:
            logger.error("LLM client not initialized - cannot make LLM calls")
            return {}

        try:
            response = await self.llm_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more consistent reasoning
            )

            content = response.choices[0].message.content

            # Extract JSON from response (handle cases where LLM adds text around JSON)
            if "{" in content and "}" in content:
                json_str = content[content.find("{") : content.rfind("}") + 1]
                result = json.loads(json_str)
            else:
                result = json.loads(content)

            return result

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return {}

    async def get_market_data_summary(self) -> Dict[str, Any]:
        """Get current market data summary (indices, volatility).

        Returns:
            Dictionary with market data
        """
        try:
            # Fetch major indices
            indices = {
                "SPY": "S&P 500",
                "QQQ": "Nasdaq 100",
                "DIA": "Dow Jones",
                "VIX": "Volatility Index",
            }

            market_data = {}

            for symbol, name in indices.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])
                    prev_price = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_price) / prev_price) * 100

                    market_data[symbol] = {
                        "name": name,
                        "price": current_price,
                        "change_pct": change_pct,
                    }

            # Calculate average market change
            avg_change = sum(
                d["change_pct"] for d in market_data.values() if d.get("change_pct")
            ) / len(market_data)

            market_data["overall_sentiment"] = (
                "BULLISH" if avg_change > 0.5 else "BEARISH" if avg_change < -0.5 else "NEUTRAL"
            )
            market_data["avg_change_pct"] = avg_change

            return market_data

        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return {"error": str(e)}

    async def get_recent_performance(self, days: int = 30) -> Dict[str, Any]:
        """Get recent trading performance.

        Args:
            days: Number of days to look back

        Returns:
            Performance metrics
        """
        try:
            client = await PostgresClient.get_instance()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Fetch recent trades
            stmt = text("""
                SELECT * FROM trades
                WHERE date >= :cutoff
            """)
            
            trades = []
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"cutoff": cutoff_date})
                trades = [dict(row._mapping) for row in result.fetchall()]

            if not trades:
                return {"total_trades": 0, "message": "No recent trades"}

            # Calculate metrics
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get("pnl") and float(t["pnl"]) > 0)
            losing_trades = sum(1 for t in trades if t.get("pnl") and float(t["pnl"]) < 0)

            total_pnl = sum(float(t.get("pnl", 0)) for t in trades if t.get("pnl"))
            win_rate = (winning_trades / total_trades) if total_trades > 0 else 0

            # Performance by strategy
            strategy_performance = {}
            for trade in trades:
                strategy = trade.get("strategy", "unknown")
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {"count": 0, "pnl": 0.0}

                strategy_performance[strategy]["count"] += 1
                if trade.get("pnl"):
                    strategy_performance[strategy]["pnl"] += float(trade["pnl"])

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0,
                "strategy_performance": strategy_performance,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"Error fetching recent performance: {e}")
            return {"error": str(e)}

    def format_signal_for_llm(self, signal: Signal) -> str:
        """Format a signal for LLM analysis.

        Args:
            signal: The trading signal

        Returns:
            Formatted string
        """
        return f"""
Ticker: {signal.ticker}
Action: {signal.action}
Entry Price: ${signal.entry_price}
Stop Loss: ${signal.stop_loss}
Take Profit: ${signal.take_profit}
Confidence: {signal.confidence}
Strategy: {signal.strategy}
Risk/Reward: {(signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss):.2f}
Technical Indicators:
  - RSI: {signal.rsi if hasattr(signal, "rsi") else "N/A"}
  - MACD: {signal.macd_histogram if hasattr(signal, "macd_histogram") else "N/A"}
  - Volume Ratio: {signal.volume_ratio if hasattr(signal, "volume_ratio") else "N/A"}
Metadata: {signal.metadata if hasattr(signal, "metadata") else {}}
""".strip()

    def format_portfolio_for_llm(self, portfolio: Portfolio, positions: List[Position]) -> str:
        """Format portfolio state for LLM analysis.

        Args:
            portfolio: Portfolio object
            positions: List of current positions

        Returns:
            Formatted string
        """
        positions_str = "\n".join(
            [
                f"  - {p.symbol}: {p.quantity} shares @ ${p.avg_entry_price} "
                f"(Current: ${p.current_price}, P&L: {p.unrealized_pnl_pct:.2%})"
                for p in positions
            ]
        )

        return f"""
Portfolio Value: ${portfolio.portfolio_value}
Cash: ${portfolio.cash}
Buying Power: ${portfolio.buying_power}
Number of Positions: {len(positions)}
Positions:
{positions_str if positions_str else "  (No positions)"}
""".strip()

    async def get_strategy_performance(self, days: int = 30) -> Dict[str, Dict[str, float]]:
        """Get performance breakdown by strategy.

        Args:
            days: Number of days to look back

        Returns:
            Strategy performance metrics
        """
        performance = await self.get_recent_performance(days)

        if "error" in performance or "strategy_performance" not in performance:
            return {}

        # return strategy metrics directly from performance dict calculated above
        # The original code fetched trades AGAIN for each strategy, which is inefficient.
        # We already calculated strategy_performance in get_recent_performance.
        # However, we need 'win_rate' and 'avg_pnl' which might not be in the brief summary.
        # Let's see: strategy_performance has 'count' and 'pnl'.
        # We need win rate. So we DO need to iterate trades again or better calculate it in get_recent_performance.
        
        # Let's rely on the strategy_performance dict constructed in get_recent_performance? 
        # No, it doesn't track wins per strategy.
        # Let's fix this efficiently by querying DB or improving get_recent_performance logic here.
        
        try:
            client = await PostgresClient.get_instance()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = text("""
                SELECT strategy, 
                       COUNT(*) as total_trades,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(pnl) as total_pnl
                FROM trades
                WHERE date >= :cutoff
                GROUP BY strategy
            """)

            strategy_metrics = {}
            async with client._connection() as conn:
                result = await conn.execute(stmt, {"cutoff": cutoff_date})
                rows = result.fetchall()
                
                for row in rows:
                    r = dict(row._mapping)
                    strategy = r["strategy"] or "unknown"
                    total = r["total_trades"]
                    wins = r["wins"] or 0
                    pnl = float(r["total_pnl"] or 0)
                    
                    strategy_metrics[strategy] = {
                        "total_trades": total,
                        "total_pnl": pnl,
                        "win_rate": wins / total if total > 0 else 0.0,
                        "avg_pnl": pnl / total if total > 0 else 0.0,
                    }
                    
            return strategy_metrics

        except Exception as e:
            logger.error(f"Error fetching detailed strategy performance: {e}")
            return {}

    async def log_orchestrator_decision(
        self,
        decision_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        reasoning: str,
    ) -> None:
        """Log orchestrator decisions to database for audit trail.

        Args:
            decision_type: Type of decision (e.g., 'market_regime', 'signal_quality')
            input_data: Input data used for decision
            output_data: Output/result of decision
            reasoning: LLM reasoning
        """
        try:
            await PostgresClient.log_orchestrator_decision(
                decision_type=decision_type,
                input_data=input_data,
                output_data=output_data,
                reasoning=reasoning,
            )
            logger.debug(f"Logged orchestrator decision: {decision_type}")

        except Exception as e:
            logger.warning(f"Failed to log orchestrator decision: {e}")
            # Don't fail if logging fails
