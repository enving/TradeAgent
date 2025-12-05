"""Adaptive Strategy Parameter Optimizer.

Automatically optimizes strategy parameters based on recent performance.
Uses a grid search approach to test parameter combinations and selects
the best performing parameters based on Sharpe ratio.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple, Any
import itertools

from ..database.supabase_client import SupabaseClient
from ..utils.logger import logger


class AdaptiveOptimizer:
    """Optimizes strategy parameters based on rolling performance window."""

    def __init__(self, lookback_days: int = 30):
        """Initialize optimizer.

        Args:
            lookback_days: Number of days to analyze for optimization
        """
        self.lookback_days = lookback_days

    async def optimize_momentum_parameters(self) -> Dict[str, Any]:
        """Optimize momentum strategy parameters.

        Tests different combinations of:
        - RSI range (40-80 variations)
        - MACD histogram threshold
        - Volume ratio threshold

        Returns:
            Optimal parameters based on Sharpe ratio
        """
        logger.info(f"Starting momentum parameter optimization (lookback: {self.lookback_days} days)")

        # Define parameter grid to test
        param_grid = {
            "rsi_lower": [40, 45, 50],
            "rsi_upper": [70, 75, 80],
            "macd_threshold": [-0.1, 0.0, 0.1],
            "volume_ratio": [1.0, 1.1, 1.2],
        }

        # Generate all combinations
        param_combinations = list(
            itertools.product(
                param_grid["rsi_lower"],
                param_grid["rsi_upper"],
                param_grid["macd_threshold"],
                param_grid["volume_ratio"],
            )
        )

        logger.info(f"Testing {len(param_combinations)} parameter combinations")

        # Get historical trades
        trades = await self._fetch_recent_trades("momentum", self.lookback_days)

        if len(trades) < 10:
            logger.warning(
                f"Not enough trades for optimization ({len(trades)} < 10). Using default parameters."
            )
            return self._get_default_momentum_params()

        # Test each combination
        best_params = None
        best_sharpe = float("-inf")
        results = []

        for rsi_low, rsi_high, macd_thresh, vol_ratio in param_combinations:
            # Skip invalid combinations
            if rsi_low >= rsi_high:
                continue

            # Simulate trades with these parameters
            filtered_trades = self._filter_trades_by_params(
                trades,
                {
                    "rsi_lower": rsi_low,
                    "rsi_upper": rsi_high,
                    "macd_threshold": macd_thresh,
                    "volume_ratio": vol_ratio,
                },
            )

            if len(filtered_trades) < 5:
                continue  # Not enough trades with these params

            # Calculate performance metrics
            sharpe_ratio = self._calculate_sharpe_ratio(filtered_trades)
            win_rate = self._calculate_win_rate(filtered_trades)
            avg_return = self._calculate_avg_return(filtered_trades)

            results.append(
                {
                    "params": {
                        "rsi_lower": rsi_low,
                        "rsi_upper": rsi_high,
                        "macd_threshold": macd_thresh,
                        "volume_ratio": vol_ratio,
                    },
                    "sharpe_ratio": sharpe_ratio,
                    "win_rate": win_rate,
                    "avg_return": avg_return,
                    "trade_count": len(filtered_trades),
                }
            )

            # Track best
            if sharpe_ratio > best_sharpe:
                best_sharpe = sharpe_ratio
                best_params = {
                    "rsi_lower": rsi_low,
                    "rsi_upper": rsi_high,
                    "macd_threshold": macd_thresh,
                    "volume_ratio": vol_ratio,
                }

        if best_params is None:
            logger.warning("No valid parameter combinations found. Using defaults.")
            return self._get_default_momentum_params()

        # Log results
        logger.info(f"Optimization complete! Best Sharpe ratio: {best_sharpe:.3f}")
        logger.info(f"Optimal parameters: {best_params}")

        # Log top 3 combinations
        top_3 = sorted(results, key=lambda x: x["sharpe_ratio"], reverse=True)[:3]
        logger.info("Top 3 parameter combinations:")
        for i, result in enumerate(top_3, 1):
            logger.info(
                f"  {i}. Sharpe: {result['sharpe_ratio']:.3f}, "
                f"Win Rate: {result['win_rate']:.1%}, "
                f"Avg Return: {result['avg_return']:.2%}, "
                f"Trades: {result['trade_count']}, "
                f"Params: {result['params']}"
            )

        # Log parameter change to database
        await self._log_parameter_change(
            strategy="momentum",
            old_params=self._get_default_momentum_params(),
            new_params=best_params,
            reason=f"Adaptive optimization (Sharpe: {best_sharpe:.3f})",
        )

        return best_params

    async def _fetch_recent_trades(
        self, strategy: str, lookback_days: int
    ) -> List[Dict[str, Any]]:
        """Fetch recent trades for analysis.

        Args:
            strategy: Strategy name
            lookback_days: Number of days to look back

        Returns:
            List of trade records
        """
        client = await SupabaseClient.get_instance()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        response = (
            await client.table("trades")
            .select("*")
            .eq("strategy", strategy)
            .gte("date", cutoff_date.isoformat())
            .order("date", desc=True)
            .execute()
        )

        return response.data if response.data else []

    def _filter_trades_by_params(
        self, trades: List[Dict[str, Any]], params: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Filter trades that would have passed with given parameters.

        Args:
            trades: List of historical trades
            params: Parameter set to test

        Returns:
            Filtered list of trades
        """
        filtered = []
        for trade in trades:
            # Check if trade would have passed filters
            rsi = trade.get("rsi")
            macd = trade.get("macd_histogram")
            vol_ratio = trade.get("volume_ratio")

            # Skip if missing data
            if rsi is None or macd is None or vol_ratio is None:
                continue

            # Apply filters
            if (
                params["rsi_lower"] <= float(rsi) <= params["rsi_upper"]
                and float(macd) > params["macd_threshold"]
                and float(vol_ratio) > params["volume_ratio"]
            ):
                filtered.append(trade)

        return filtered

    def _calculate_sharpe_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate Sharpe ratio from trades.

        Args:
            trades: List of closed trades

        Returns:
            Sharpe ratio (annualized)
        """
        if not trades:
            return 0.0

        # Get returns
        returns = []
        for trade in trades:
            pnl_pct = trade.get("pnl_pct")
            if pnl_pct is not None:
                returns.append(float(pnl_pct))

        if len(returns) < 2:
            return 0.0

        # Calculate mean and std
        import statistics

        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        # Sharpe ratio (assuming ~252 trading days per year)
        # Annualized: mean * sqrt(252) / std
        sharpe = (mean_return * (252**0.5)) / std_return
        return sharpe

    def _calculate_win_rate(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate from trades.

        Args:
            trades: List of closed trades

        Returns:
            Win rate (0.0 to 1.0)
        """
        if not trades:
            return 0.0

        wins = sum(1 for t in trades if t.get("pnl_pct") and float(t["pnl_pct"]) > 0)
        return wins / len(trades)

    def _calculate_avg_return(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average return from trades.

        Args:
            trades: List of closed trades

        Returns:
            Average return (fraction)
        """
        if not trades:
            return 0.0

        returns = [float(t["pnl_pct"]) for t in trades if t.get("pnl_pct") is not None]
        if not returns:
            return 0.0

        return sum(returns) / len(returns)

    def _get_default_momentum_params(self) -> Dict[str, float]:
        """Get default momentum strategy parameters.

        Returns:
            Default parameters
        """
        return {
            "rsi_lower": 45,
            "rsi_upper": 75,
            "macd_threshold": 0.0,
            "volume_ratio": 1.1,
        }

    async def _log_parameter_change(
        self,
        strategy: str,
        old_params: Dict[str, Any],
        new_params: Dict[str, Any],
        reason: str,
    ) -> None:
        """Log parameter change to database.

        Args:
            strategy: Strategy name
            old_params: Previous parameters
            new_params: New parameters
            reason: Reason for change
        """
        try:
            client = await SupabaseClient.get_instance()

            await client.table("parameter_changes").insert(
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "reason": f"[{strategy}] {reason}",
                    "old_params": old_params,
                    "new_params": new_params,
                }
            ).execute()

            logger.info(f"Parameter change logged for {strategy}")

        except Exception as e:
            logger.error(f"Failed to log parameter change: {e}")


# Global singleton
_optimizer = None


def get_optimizer() -> AdaptiveOptimizer:
    """Get or create the AdaptiveOptimizer singleton.

    Returns:
        AdaptiveOptimizer instance
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = AdaptiveOptimizer()
    return _optimizer
