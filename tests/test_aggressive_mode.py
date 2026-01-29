import asyncio
from decimal import Decimal
from src.risk.position_sizer import PositionSizer
from src.models.trade import Signal
from src.models.portfolio import Portfolio
from src.utils.config import config


async def test_aggressive_sizing():
    print(f"Testing PositionSizer (Aggressive Mode = {config.AGGRESSIVE_MODE})")

    sizer = PositionSizer()

    # Mock signal
    signal = Signal(
        ticker="AAPL",
        action="BUY",
        entry_price=Decimal("150.0"),
        stop_loss=Decimal("142.5"),  # 5% stop
        take_profit=Decimal("168.0"),  # 12% target
        confidence=Decimal("0.8"),
        strategy="momentum",
    )

    # Mock portfolio
    portfolio = Portfolio(
        portfolio_value=Decimal("100000.0"),
        cash=Decimal("50000.0"),
        buying_power=Decimal("100000.0"),
        equity=Decimal("50000.0"),
        last_equity=Decimal("50000.0"),
    )

    pos_value, reasoning = sizer.calculate_position_size(signal, portfolio)
    print(f"Result: ${pos_value:,.2f} ({pos_value / portfolio.portfolio_value:.1%} of portfolio)")
    print(f"Reasoning: {reasoning}")


if __name__ == "__main__":
    asyncio.run(test_aggressive_sizing())
