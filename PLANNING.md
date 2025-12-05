# TradeAgent - Planning & Architecture

**Last Updated:** 2025-11-18

## Project Overview

TradeAgent is a **100% deterministic paper trading system** with zero LLM involvement in trading decisions. It combines a defensive core strategy (buy & hold ETFs) with momentum trading signals based on technical indicators.

### Key Principles
- **Deterministic Logic Only** - All trading decisions are mathematical and rule-based
- **Paper Trading** - Uses Alpaca Paper Trading API for safe testing
- **Dual Strategy** - Defensive core (50%) + Momentum trading (50%)
- **Risk Management** - Hard-coded position limits and stop-losses
- **Full Observability** - All trades logged to Supabase database

## Architecture

### Tech Stack
- **Language:** Python 3.11+
- **Async Framework:** asyncio with async/await throughout
- **Trading API:** Alpaca Paper Trading (alpaca-py SDK v0.9.0+)
- **Database:** Supabase PostgreSQL
- **Data Validation:** Pydantic v2
- **Technical Indicators:** ta library v0.11.0+
- **Testing:** Pytest with pytest-asyncio

### Project Structure

```
TradeAgent/
├── src/
│   ├── main.py                    # Main trading loop orchestration
│   ├── core/
│   │   ├── performance_analyzer.py # Daily/weekly performance analysis
│   │   └── risk_manager.py         # Position sizing & risk filters
│   ├── database/
│   │   └── supabase_client.py      # Database operations
│   ├── mcp_clients/
│   │   └── alpaca_client.py        # Alpaca SDK wrapper
│   ├── models/
│   │   ├── portfolio.py            # Portfolio & Position models
│   │   └── trade.py                # Signal & Trade models
│   ├── strategies/
│   │   ├── defensive_core.py       # Buy & hold ETF rebalancing
│   │   └── momentum_trading.py     # Technical indicator signals
│   └── utils/
│       ├── config.py               # Environment configuration
│       ├── logger.py               # Logging setup
│       └── rate_limiter.py         # API rate limiting
├── tests/                          # Pytest unit tests
├── check_positions.py              # Quick portfolio status utility
├── .env                            # Environment variables (NEVER commit)
├── .mcp.json                       # MCP server config (NEVER commit)
└── pyproject.toml                  # Dependencies & project config
```

## Trading Strategies

### 1. Defensive Core (50% of Portfolio)
**Purpose:** Stable foundation with broad market exposure

**Allocation:**
- VTI: 25% - US Total Market ETF
- VGK: 15% - European Market ETF
- GLD: 10% - Gold ETF

**Rebalancing Triggers:**
1. First day of each month
2. Portfolio drift > 5% from target allocations

**Logic:**
- Calculate target value per ETF
- Calculate current value from positions
- Generate BUY/SELL signals to reach targets
- Only rebalance if difference > $100

### 2. Momentum Trading (50% of Portfolio)
**Purpose:** Capture short-term trends with technical breakouts

**Entry Signals:**
- RSI (14-day) between 30-70 (not oversold/overbought)
- MACD histogram positive (bullish momentum)
- Volume > 1.5x average (strong interest)
- Confidence scoring based on signal strength

**Exit Conditions:**
1. Stop-loss hit (automatic via Alpaca bracket order)
2. Take-profit hit (automatic via Alpaca bracket order)
3. RSI > 70 (overbought, manual exit)
4. Holding period > 30 days (prevent bag-holding)

**Risk Limits:**
- Maximum 5 concurrent momentum positions
- 10% max position size per trade
- 2:1 minimum risk/reward ratio required

## Risk Management

### Hard-Coded Limits
```python
MAX_POSITIONS = 5                      # Concurrent momentum positions
MAX_POSITION_SIZE_PCT = 10%           # Per position
MAX_DAILY_RISK_PCT = 2%               # Per trade
DAILY_LOSS_LIMIT_PCT = 3%             # Circuit breaker
```

### Position Sizing Logic
**Defensive Core:**
```python
shares = abs(target_value - current_value) / entry_price
```

**Momentum Trading:**
```python
max_position_value = portfolio_value * 0.10
shares = max_position_value / entry_price
```

### Circuit Breaker
If daily P&L drops below -3%, all trading halts for the day.

## Database Schema

### Supabase Tables
1. **trades** - All executed trades (entries & exits)
2. **signals** - Generated trading signals
3. **performance_metrics** - Daily performance snapshots
4. **portfolio_snapshots** - Daily portfolio state
5. **risk_events** - Risk violations & circuit breaker triggers
6. **strategy_performance** - Per-strategy performance tracking

## Daily Trading Loop

**Execution Time:** Once per trading day (can be scheduled via cron)

**Workflow:**
1. Fetch portfolio state from Alpaca
2. Check defensive core rebalancing triggers
3. Execute rebalancing orders if needed
4. Scan for momentum entry signals
5. Apply risk filters to signals
6. Execute approved momentum entries
7. Check exit conditions for open positions
8. Close positions that meet exit criteria
9. Analyze daily performance
10. Generate weekly report (if Sunday)

## Environment Configuration

### Required Environment Variables (.env)
```env
# Alpaca Paper Trading
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Supabase Database
SUPABASE_URL=https://your_project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Environment
ENVIRONMENT=development  # or production
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

### MCP Server Configuration (.mcp.json)
```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_REF"
    }
  }
}
```

## Testing Strategy

### Unit Tests
- Target: 90%+ pass rate
- Framework: pytest with pytest-asyncio
- Mock external APIs (Alpaca, Supabase)
- Test coverage: Core logic, risk management, position sizing

### Integration Tests
- Real Alpaca Paper Trading API (free tier)
- Real Supabase database (development instance)
- Verify end-to-end workflow

### Current Test Status
- Unit Tests: 110/125 passing (88%)
- Integration Tests: 3/3 passing (100%)

## Known Limitations

1. **Alpaca Free Tier** - Cannot fetch recent SIP market data (blocks historical bar fetching)
2. **Momentum Scanning** - Limited without paid Alpaca subscription for recent data
3. **Market Hours** - System executes during market hours only (Alpaca paper trading follows real market hours)
4. **Fractional Shares** - Rounded to 2 decimal places (Alpaca limitation)

## Deployment

### Local Execution
```bash
# Activate virtual environment
source venv_linux/bin/activate  # Linux/Mac
.venv\Scripts\activate          # Windows

# Run trading loop
python -m src.main
```

### Scheduled Execution (Future)
- Set up cron job for daily execution
- Monitor logs for errors
- Set up email/SMS alerts for circuit breaker events

## Code Style & Conventions

### General Rules
- **PEP8** compliant
- **Type hints** on all functions
- **Docstrings** (Google style) on all functions
- **Black** formatting
- **Decimal** for all money/price calculations (never float)
- **Async/await** throughout

### File Size Limit
- Maximum 500 lines per file
- Refactor into modules if approaching limit

### Import Style
```python
# Standard library
import asyncio
from datetime import datetime

# Third-party
from pydantic import BaseModel

# Local (relative imports within package)
from ..models.trade import Signal
from .risk_manager import calculate_position_size
```

### Docstring Template
```python
def calculate_position_size(signal: Signal, portfolio: Portfolio) -> Decimal:
    """Calculate safe position size based on portfolio value.

    For defensive core: Uses target_value to calculate exact shares needed.
    For momentum: Uses 10% max position size limit.

    Args:
        signal: Trading signal with entry price
        portfolio: Current portfolio state

    Returns:
        Number of shares to buy (rounded down)

    Example:
        Portfolio value: $10,000
        Max position size: 10% = $1,000
        Entry price: $100/share
        Position size: 10 shares
    """
```

## Security

### Never Commit
- `.env` - API keys and secrets
- `.mcp.json` - MCP server configuration
- `logs/` - Log files may contain sensitive data
- `*.log` - Same as above

### Always Commit
- `.env.example` - Template with placeholder values
- `.gitignore` - Updated security rules

## Future Enhancements (Not Implemented)

1. **Advanced Risk Management**
   - Portfolio correlation analysis
   - VaR (Value at Risk) calculations
   - Drawdown monitoring

2. **Additional Strategies**
   - Mean reversion
   - Pairs trading
   - Sector rotation

3. **Alerting & Monitoring**
   - Email notifications for trades
   - SMS alerts for circuit breaker
   - Telegram bot integration

4. **Backtesting Framework**
   - Historical data simulation
   - Strategy parameter optimization
   - Walk-forward analysis

5. **Performance Dashboard**
   - Web UI for portfolio visualization
   - Real-time P&L charts
   - Strategy comparison metrics

## Contact & Support

- **GitHub Issues:** Report bugs and feature requests
- **Documentation:** README.md and inline docstrings
- **Logs:** Check `logs/` directory for detailed execution logs
