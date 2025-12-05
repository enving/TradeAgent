"""Run adaptive strategy parameter optimization.

This script analyzes recent trading performance and optimizes
strategy parameters to maximize Sharpe ratio.

Usage:
    python3 run_optimizer.py [--lookback 30] [--strategy momentum]
"""

import asyncio
import argparse

from src.ml.adaptive_optimizer import get_optimizer
from src.config.strategy_params import get_strategy_parameters
from src.utils.logger import logger


async def run_optimization(strategy: str, lookback_days: int):
    """Run optimization for a strategy.

    Args:
        strategy: Strategy to optimize ('momentum', 'news_sentiment', etc.)
        lookback_days: Days of data to analyze
    """
    logger.info("=" * 60)
    logger.info(f"ADAPTIVE PARAMETER OPTIMIZATION")
    logger.info(f"Strategy: {strategy}")
    logger.info(f"Lookback: {lookback_days} days")
    logger.info("=" * 60)

    optimizer = get_optimizer()

    if strategy == "momentum":
        # Run momentum optimization
        optimal_params = await optimizer.optimize_momentum_parameters()

        # Update strategy parameters
        params_manager = get_strategy_parameters()
        await params_manager.update_parameters(
            strategy="momentum",
            new_params=optimal_params,
            reason=f"Adaptive optimization ({lookback_days}d lookback)",
        )

        logger.info("\n✅ Optimization complete!")
        logger.info(f"New parameters: {optimal_params}")
        logger.info("\nThese parameters will be used in the next trading loop.")

    else:
        logger.warning(f"Optimization not yet implemented for strategy: {strategy}")
        logger.info("Currently supported: momentum")


async def show_current_parameters():
    """Display current parameters for all strategies."""
    logger.info("\n" + "=" * 60)
    logger.info("CURRENT STRATEGY PARAMETERS")
    logger.info("=" * 60)

    params_manager = get_strategy_parameters()

    for strategy in ["momentum", "news_sentiment", "defensive"]:
        params = await params_manager.get_parameters(strategy)
        logger.info(f"\n{strategy.upper()}:")
        for key, value in params.items():
            logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run adaptive parameter optimization")
    parser.add_argument(
        "--strategy",
        type=str,
        default="momentum",
        help="Strategy to optimize (default: momentum)",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=30,
        help="Days of data to analyze (default: 30)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show current parameters without optimizing",
    )

    args = parser.parse_args()

    if args.show:
        asyncio.run(show_current_parameters())
    else:
        asyncio.run(run_optimization(args.strategy, args.lookback))
