"""Trading Orchestrator Agent - The central AI brain of the trading system.

This agent coordinates all trading strategies, analyzes market conditions,
prioritizes signals, and explains decisions using LLM-powered reasoning.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ...models.portfolio import Portfolio, Position
from ...models.trade import Signal
from ...utils.logger import logger
from .prompts import (
    MARKET_REGIME_ANALYSIS_PROMPT,
    MULTI_SIGNAL_PRIORITIZATION_PROMPT,
    SIGNAL_QUALITY_SCORING_PROMPT,
    STRATEGY_WEIGHT_ADJUSTMENT_PROMPT,
    TRADE_DECISION_EXPLANATION_PROMPT,
)
from .tools import OrchestratorTools


class MarketRegime:
    """Market regime classification."""

    BULL_TRENDING = "BULL_TRENDING"
    BEAR_TRENDING = "BEAR_TRENDING"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    CRISIS = "CRISIS"


class TradingOrchestrator:
    """Central AI agent that coordinates all trading strategies.

    This agent uses LLM-powered reasoning to:
    - Analyze current market regime
    - Score and prioritize trading signals
    - Explain trade decisions
    - Adjust strategy weights dynamically
    """

    def __init__(self):
        """Initialize the orchestrator."""
        self.tools = OrchestratorTools()
        self.current_regime: Optional[str] = None
        self.regime_confidence: float = 0.0
        self.strategy_weights: Dict[str, float] = {
            "momentum": 0.40,
            "news_sentiment": 0.20,
            "defensive": 0.40,
        }

    async def analyze_market_regime(
        self, portfolio: Portfolio, positions: List[Position]
    ) -> Tuple[str, float, str]:
        """Analyze current market conditions and classify the regime.

        Args:
            portfolio: Current portfolio state
            positions: Current open positions

        Returns:
            Tuple of (regime, confidence, reasoning)
        """
        logger.info("Analyzing market regime...")

        try:
            # Gather market data
            market_data = await self.tools.get_market_data_summary()
            recent_performance = await self.tools.get_recent_performance(days=30)
            portfolio_state = self.tools.format_portfolio_for_llm(portfolio, positions)

            # Build prompt
            prompt = MARKET_REGIME_ANALYSIS_PROMPT.format(
                market_data=market_data,
                recent_performance=recent_performance,
                portfolio_state=portfolio_state,
            )

            # Get LLM analysis
            result = await self.tools.call_llm(prompt, max_tokens=600)

            if not result:
                logger.warning("Failed to analyze market regime - using default")
                return MarketRegime.RANGING, 0.5, "LLM analysis failed, defaulting to RANGING"

            regime = result.get("regime", MarketRegime.RANGING)
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "No reasoning provided")

            # Update strategy weights based on regime
            if "recommended_strategy_weights" in result:
                self.strategy_weights = result["recommended_strategy_weights"]
                logger.info(f"Updated strategy weights: {self.strategy_weights}")

            # Cache regime
            self.current_regime = regime
            self.regime_confidence = confidence

            # Log decision
            await self.tools.log_orchestrator_decision(
                decision_type="market_regime_analysis",
                input_data={
                    "market_data": market_data,
                    "portfolio_value": float(portfolio.portfolio_value),
                    "position_count": len(positions),
                },
                output_data={
                    "regime": regime,
                    "confidence": confidence,
                    "strategy_weights": self.strategy_weights,
                },
                reasoning=reasoning,
            )

            logger.info(f"Market Regime: {regime} (confidence: {confidence:.2f})")
            logger.info(f"Reasoning: {reasoning}")

            return regime, confidence, reasoning

        except Exception as e:
            logger.error(f"Error analyzing market regime: {e}", exc_info=True)
            return MarketRegime.RANGING, 0.5, f"Error: {str(e)}"

    async def score_signal_quality(
        self, signal: Signal, portfolio: Portfolio, positions: List[Position]
    ) -> Tuple[float, str, str]:
        """Score the quality of a trading signal using LLM analysis.

        Args:
            signal: The trading signal to evaluate
            portfolio: Current portfolio state
            positions: Current open positions

        Returns:
            Tuple of (quality_score, recommendation, reasoning)
        """
        logger.debug(f"Scoring signal quality for {signal.ticker}...")

        try:
            # Gather context
            signal_details = self.tools.format_signal_for_llm(signal)
            market_context = await self.tools.get_market_data_summary()
            historical_performance = await self.tools.get_recent_performance(days=30)
            portfolio_state = self.tools.format_portfolio_for_llm(portfolio, positions)

            # Build prompt
            prompt = SIGNAL_QUALITY_SCORING_PROMPT.format(
                signal_details=signal_details,
                market_context=market_context,
                historical_performance=historical_performance,
                portfolio_state=portfolio_state,
            )

            # Get LLM evaluation
            result = await self.tools.call_llm(prompt, max_tokens=500)

            if not result:
                logger.warning(f"Failed to score signal for {signal.ticker} - using default")
                return 0.5, "HOLD", "LLM analysis failed"

            quality_score = float(result.get("quality_score", 0.5))
            recommendation = result.get("recommendation", "HOLD")
            reasoning = result.get("reasoning", "No reasoning provided")

            # Log decision
            await self.tools.log_orchestrator_decision(
                decision_type="signal_quality_scoring",
                input_data={
                    "ticker": signal.ticker,
                    "strategy": signal.strategy,
                    "confidence": float(signal.confidence),
                },
                output_data={
                    "quality_score": quality_score,
                    "recommendation": recommendation,
                    "concerns": result.get("concerns", []),
                    "strengths": result.get("strengths", []),
                },
                reasoning=reasoning,
            )

            logger.debug(
                f"{signal.ticker}: Quality={quality_score:.2f}, "
                f"Recommendation={recommendation}"
            )

            return quality_score, recommendation, reasoning

        except Exception as e:
            logger.error(f"Error scoring signal quality for {signal.ticker}: {e}")
            return 0.5, "HOLD", f"Error: {str(e)}"

    async def prioritize_signals(
        self,
        signals: List[Signal],
        portfolio: Portfolio,
        positions: List[Position],
    ) -> List[Tuple[Signal, float, str]]:
        """Prioritize and rank trading signals using LLM analysis.

        Args:
            signals: List of trading signals to prioritize
            portfolio: Current portfolio state
            positions: Current open positions

        Returns:
            List of tuples (signal, priority_score, reasoning) sorted by priority
        """
        logger.info(f"Prioritizing {len(signals)} signals...")

        if not signals:
            return []

        try:
            # Format signals for LLM
            signals_formatted = "\n\n".join(
                [f"Signal {i+1}:\n{self.tools.format_signal_for_llm(s)}" for i, s in enumerate(signals)]
            )

            portfolio_state = self.tools.format_portfolio_for_llm(portfolio, positions)

            # Build prompt
            prompt = MULTI_SIGNAL_PRIORITIZATION_PROMPT.format(
                signals=signals_formatted,
                portfolio=portfolio_state,
                regime=self.current_regime or "UNKNOWN",
                risk_budget="MEDIUM",  # TODO: Calculate from portfolio metrics
                cash=portfolio.cash,
            )

            # Get LLM ranking
            result = await self.tools.call_llm(prompt, max_tokens=800)

            if not result or "ranked_signals" not in result:
                logger.warning("Failed to prioritize signals - using default ordering")
                # Fallback: use original signal confidence
                return [(s, float(s.confidence), "Default ranking by signal confidence") for s in signals]

            # Match LLM rankings back to original signals
            ranked = []
            ranked_tickers = {item["ticker"]: item for item in result["ranked_signals"]}

            for signal in signals:
                if signal.ticker in ranked_tickers:
                    item = ranked_tickers[signal.ticker]
                    priority_score = float(item.get("priority_score", 0.5))
                    reasoning = item.get("reasoning", "No reasoning provided")
                else:
                    priority_score = float(signal.confidence) * 0.5  # Lower priority if not in LLM ranking
                    reasoning = "Not ranked by LLM, using default"

                ranked.append((signal, priority_score, reasoning))

            # Sort by priority score
            ranked.sort(key=lambda x: x[1], reverse=True)

            # Log decision
            await self.tools.log_orchestrator_decision(
                decision_type="signal_prioritization",
                input_data={
                    "signal_count": len(signals),
                    "tickers": [s.ticker for s in signals],
                },
                output_data={
                    "ranked_tickers": [s.ticker for s, _, _ in ranked],
                    "priority_scores": [score for _, score, _ in ranked],
                    "overall_recommendation": result.get("overall_recommendation", ""),
                },
                reasoning=result.get("reasoning", ""),
            )

            logger.info(f"Signal prioritization complete. Top 3: {[s.ticker for s, _, _ in ranked[:3]]}")

            return ranked

        except Exception as e:
            logger.error(f"Error prioritizing signals: {e}", exc_info=True)
            # Fallback to original signal confidence
            return [(s, float(s.confidence), f"Error during prioritization: {str(e)}") for s in signals]

    async def explain_decision(
        self, signal: Signal, approved: bool, factors: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation for a trade decision.

        Args:
            signal: The trading signal
            approved: Whether the signal was approved
            factors: Dictionary of factors that contributed to decision

        Returns:
            Explanation string
        """
        logger.debug(f"Generating explanation for {signal.ticker} decision...")

        try:
            # Format signal
            signal_str = self.tools.format_signal_for_llm(signal)

            # Build prompt
            prompt = TRADE_DECISION_EXPLANATION_PROMPT.format(
                signal=signal_str,
                decision="APPROVED" if approved else "REJECTED",
                factors=factors,
            )

            # Get LLM explanation
            result = await self.tools.call_llm(prompt, max_tokens=400)

            if not result:
                return f"Decision: {'APPROVED' if approved else 'REJECTED'}. No detailed explanation available."

            # Format explanation
            summary = result.get("summary", "No summary")
            reasoning = result.get("reasoning", "No reasoning")
            technical = ", ".join(result.get("technical_factors", []))
            risk = ", ".join(result.get("risk_factors", []))

            explanation = f"""
{summary}

{reasoning}

Technical Factors: {technical if technical else 'None'}
Risk Factors: {risk if risk else 'None'}
Market Context: {result.get('market_context', 'N/A')}
Expected Outcome: {result.get('expected_outcome', 'N/A')}
""".strip()

            # Log explanation
            await self.tools.log_orchestrator_decision(
                decision_type="trade_decision_explanation",
                input_data={
                    "ticker": signal.ticker,
                    "approved": approved,
                },
                output_data=result,
                reasoning=reasoning,
            )

            return explanation

        except Exception as e:
            logger.error(f"Error generating decision explanation: {e}")
            return f"Decision: {'APPROVED' if approved else 'REJECTED'}. Error generating explanation: {str(e)}"

    async def adjust_strategy_weights(self) -> Dict[str, float]:
        """Dynamically adjust allocation weights between strategies based on performance.

        Returns:
            New strategy weights
        """
        logger.info("Adjusting strategy weights based on performance...")

        try:
            # Get strategy performance
            strategy_performance = await self.tools.get_strategy_performance(days=30)

            if not strategy_performance:
                logger.warning("No performance data available - keeping current weights")
                return self.strategy_weights

            # Build prompt
            prompt = STRATEGY_WEIGHT_ADJUSTMENT_PROMPT.format(
                strategy_performance=strategy_performance,
                regime=self.current_regime or "UNKNOWN",
                current_weights=self.strategy_weights,
            )

            # Get LLM recommendation
            result = await self.tools.call_llm(prompt, max_tokens=400)

            if not result or "new_weights" not in result:
                logger.warning("Failed to adjust weights - keeping current")
                return self.strategy_weights

            new_weights = result["new_weights"]
            reasoning = result.get("reasoning", "No reasoning provided")

            # Validate weights sum to ~1.0
            total = sum(new_weights.values())
            if abs(total - 1.0) > 0.1:
                logger.warning(f"Weights don't sum to 1.0 (sum={total}), normalizing...")
                new_weights = {k: v / total for k, v in new_weights.items()}

            # Update weights
            old_weights = self.strategy_weights.copy()
            self.strategy_weights = new_weights

            # Log decision
            await self.tools.log_orchestrator_decision(
                decision_type="strategy_weight_adjustment",
                input_data={
                    "old_weights": old_weights,
                    "performance": strategy_performance,
                },
                output_data={
                    "new_weights": new_weights,
                    "expected_improvement": result.get("expected_improvement", ""),
                },
                reasoning=reasoning,
            )

            logger.info(f"Strategy weights updated: {new_weights}")
            logger.info(f"Reasoning: {reasoning}")

            return new_weights

        except Exception as e:
            logger.error(f"Error adjusting strategy weights: {e}", exc_info=True)
            return self.strategy_weights

    def get_current_regime(self) -> Tuple[Optional[str], float]:
        """Get the current market regime classification.

        Returns:
            Tuple of (regime, confidence)
        """
        return self.current_regime, self.regime_confidence

    def get_strategy_weights(self) -> Dict[str, float]:
        """Get current strategy allocation weights.

        Returns:
            Dictionary of strategy weights
        """
        return self.strategy_weights.copy()
