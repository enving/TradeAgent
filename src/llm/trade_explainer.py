"""Trade explanation generator using OpenRouter LLM API.

Uses OpenRouter to access Claude (or other models) for generating
natural language explanations of trading decisions.
"""

from openai import AsyncOpenAI

from ..models.portfolio import Portfolio
from ..models.trade import Trade
from ..utils.config import config
from ..utils.logger import logger


class TradeExplainer:
    """Generates natural language explanations for trades using LLM.

    Uses OpenRouter API (OpenAI-compatible) to access Claude or other models.
    Only used for explanations - NEVER for trading decisions.
    """

    def __init__(self):
        """Initialize OpenRouter client."""
        if not config.OPENROUTER_API_KEY:
            logger.warning("OpenRouter API key not configured")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=config.OPENROUTER_API_KEY,
                base_url=config.OPENROUTER_BASE_URL,
            )
            logger.info(f"TradeExplainer initialized with model: {config.OPENROUTER_MODEL}")

    async def explain_trade(
        self, trade: Trade, portfolio: Portfolio | None = None
    ) -> str | None:
        """Generate natural language explanation for a trade.

        IMPORTANT: This is for human-readable explanations only.
        The trade decision was already made deterministically.

        Args:
            trade: The executed trade to explain
            portfolio: Optional portfolio context

        Returns:
            Natural language explanation, or None if LLM is disabled/failed

        Example:
            "Bought 10 shares of AAPL at $268.50 due to strong bullish momentum
            (RSI: 62.5, MACD histogram positive at 1.25). Entry aligns with
            momentum strategy targeting 15% upside with 5% stop-loss protection."
        """
        if not config.ENABLE_LLM_FEATURES:
            logger.debug("LLM features disabled, using fallback explanation")
            return self._get_fallback_explanation(trade)

        if not self.client:
            logger.warning("OpenRouter client not initialized")
            return None

        try:
            # Build context for the LLM
            prompt = self._build_trade_prompt(trade, portfolio)

            # Call OpenRouter API
            response = await self.client.chat.completions.create(
                model=config.OPENROUTER_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a professional financial analyst. "
                            "Explain trading decisions clearly and concisely. "
                            "Focus on the technical reasoning and risk management. "
                            "Keep explanations to 2-3 sentences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=250,
                temperature=0.7,
            )

            explanation = response.choices[0].message.content.strip()

            logger.debug(
                f"Generated explanation for {trade.action} {trade.ticker} "
                f"(tokens: ~{response.usage.total_tokens})"
            )

            return explanation

        except Exception as e:
            logger.error(f"Failed to generate trade explanation: {e}")
            # Fallback to simple explanation
            return self._get_fallback_explanation(trade)

    def _build_trade_prompt(self, trade: Trade, portfolio: Portfolio | None) -> str:
        """Build the prompt for trade explanation.

        Args:
            trade: Trade to explain
            portfolio: Optional portfolio context

        Returns:
            Formatted prompt for the LLM
        """
        # Basic trade info
        prompt_parts = [
            f"Explain this {trade.strategy} strategy trade:",
            f"",
            f"Action: {trade.action} {trade.quantity} shares of {trade.ticker}",
            f"Entry Price: ${trade.entry_price}",
        ]

        # Add technical indicators if available
        if trade.rsi:
            prompt_parts.append(f"RSI: {trade.rsi}")
        if trade.macd_histogram:
            prompt_parts.append(f"MACD Histogram: {trade.macd_histogram}")
        if trade.volume_ratio:
            prompt_parts.append(f"Volume Ratio: {trade.volume_ratio}x average")

        # Add risk management for momentum trades (if available)
        if (
            trade.strategy == "momentum"
            and hasattr(trade, "stop_loss")
            and hasattr(trade, "take_profit")
            and trade.stop_loss
            and trade.take_profit
        ):
            risk_pct = (trade.entry_price - trade.stop_loss) / trade.entry_price * 100
            reward_pct = (trade.take_profit - trade.entry_price) / trade.entry_price * 100
            prompt_parts.append(f"Stop-Loss: ${trade.stop_loss} (-{risk_pct:.1f}%)")
            prompt_parts.append(f"Take-Profit: ${trade.take_profit} (+{reward_pct:.1f}%)")

        # Add portfolio context if available
        if portfolio:
            prompt_parts.append(f"")
            prompt_parts.append(f"Portfolio Context:")
            prompt_parts.append(f"Portfolio Value: ${portfolio.portfolio_value:,.2f}")
            prompt_parts.append(f"Available Cash: ${portfolio.cash:,.2f}")

        return "\n".join(prompt_parts)

    def _get_fallback_explanation(self, trade: Trade) -> str:
        """Generate simple fallback explanation if LLM fails.

        Args:
            trade: Trade to explain

        Returns:
            Basic explanation string
        """
        if trade.strategy == "defensive":
            return (
                f"Defensive core rebalancing: {trade.action} {trade.quantity} "
                f"{trade.ticker} at ${trade.entry_price} to maintain target allocation."
            )
        elif trade.strategy == "momentum":
            indicators = []
            if trade.rsi:
                indicators.append(f"RSI {trade.rsi}")
            if trade.macd_histogram and trade.macd_histogram > 0:
                indicators.append("positive MACD")
            if trade.volume_ratio and trade.volume_ratio > 1:
                indicators.append(f"{trade.volume_ratio}x volume")

            indicators_str = ", ".join(indicators) if indicators else "technical signals"

            return (
                f"Momentum trade: {trade.action} {trade.quantity} {trade.ticker} "
                f"at ${trade.entry_price} based on {indicators_str}."
            )
        else:
            return (
                f"Automated trade: {trade.action} {trade.quantity} {trade.ticker} "
                f"at ${trade.entry_price}."
            )


# Global instance
_explainer = None


async def get_trade_explainer() -> TradeExplainer:
    """Get or create the global TradeExplainer instance.

    Returns:
        TradeExplainer instance
    """
    global _explainer
    if _explainer is None:
        _explainer = TradeExplainer()
    return _explainer
