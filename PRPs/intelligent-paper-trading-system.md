name: "Intelligent Paper Trading System - Deterministic First with Strategic LLM Integration"
description: |

## Purpose
Build a production-ready, deterministic-first trading bot that executes daily trades via Alpaca Paper Trading API (via MCP), with minimal LLM usage (only for non-deterministic edge cases). The system prioritizes mathematical analysis and clear rules over AI decision-making, achieving 15-20% annual returns through proven strategies.

## Core Principles
1. **Deterministic First**: 80%+ decisions without LLM - use pure math and boolean logic
2. **Context is King**: All documentation, examples, and patterns included for one-pass implementation
3. **Validation Loops**: Executable tests at every step with self-correction capability
4. **Progressive Success**: Start with defensive core, validate, then add momentum trading
5. **Global rules**: Follow all rules in CLAUDE.md (max 500 lines per file, use venv_linux, pytest for all features)

---

## Goal
Build an autonomous trading system that:
- Executes daily trades via Alpaca MCP (Paper Trading) with clear entry/exit rules
- Implements a 2-layer strategy: Defensive Core (50% portfolio) + Momentum Trading (30% portfolio)
- Logs all trades and performance metrics to Supabase for analysis
- Runs deterministically with <5% LLM usage for edge cases only
- Achieves realistic 15-20% annual returns through backtested strategies

## Why
- **Business Value**: Automate wealth building through proven trading strategies without emotional bias
- **Learning Platform**: Paper trading allows risk-free testing and strategy optimization
- **Data-Driven**: All decisions logged to Supabase enable continuous performance analysis
- **Scalability**: Start with paper trading, graduate to live trading after proven performance

## What
A Python-based trading system with:
- **Daily execution loop** (9:00 AM EST) that analyzes positions and executes trades
- **Defensive Core Strategy**: Buy & hold ETFs (VTI, VGK, GLD) with monthly rebalancing
- **Momentum Trading Strategy**: Technical breakout trading (RSI, MACD, trend following)
- **Risk Management**: Hard-coded position limits, stop-loss, take-profit rules
- **Performance Tracking**: All trades, signals, and metrics stored in Supabase
- **MCP Integration**: Alpaca MCP for trading, potential for future MCP server deployment

### Success Criteria
- [ ] Daily trading loop runs without errors for 7 consecutive days
- [ ] All trades logged to Supabase with full technical context (RSI, MACD, etc.)
- [ ] Defensive Core rebalancing works (VTI/VGK/GLD allocations correct)
- [ ] Momentum strategy executes >=1 trade/week when signals present
- [ ] Risk limits enforced (max 10% per position, max 5 concurrent positions)
- [ ] Paper trading account remains profitable (>0% return over 2 weeks)
- [ ] Daily performance analysis runs automatically and logs metrics
- [ ] Strategy parameters adjust automatically based on performance (verify in parameter_changes table)
- [ ] Weekly report generated every Sunday
- [ ] Rate limiting implemented for all APIs (no 429 errors in logs)
- [ ] All unit tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `ruff check src/ --fix`
- [ ] No type errors: `mypy src/`

---

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Core Technical Documentation

- url: https://docs.alpaca.markets/docs/about-paper-trading
  why: Alpaca Paper Trading overview and limitations
  critical: Paper trading uses live market data but simulated execution

- url: https://docs.alpaca.markets/reference/
  why: Alpaca API reference for orders, positions, account management
  critical: Use alpaca-docker MCP instead of direct API calls

- url: https://supabase.com/docs/reference/python/initializing
  why: Supabase Python async client setup and best practices
  critical: Use acreate_client() for async, single instance pattern (Singleton)

- url: https://supabase.com/docs/reference/python/insert
  why: Inserting trade logs and performance metrics
  section: Batch inserts for multiple signals

- url: https://pypi.org/project/ta-lib/
  why: TA-Lib is industry standard for technical indicators (RSI, MACD)
  critical: "Requires system-level install: apt-get install ta-lib (Linux) or conda install -c conda-forge ta-lib"

- url: https://pandas-ta.readthedocs.io/
  why: Alternative to TA-Lib - pure Python, easier install, pandas integration
  critical: "Use pandas_ta if TA-Lib installation fails - it's more beginner-friendly"

- url: https://www.quantifiedstrategies.com/python-momentum-trading-strategy/
  why: Proven momentum strategy implementation patterns
  section: Backtesting results, entry/exit criteria

- url: https://docs.python.org/3/library/asyncio.html
  why: Async/await patterns for concurrent API calls
  critical: "Use asyncio.gather() for parallel MCP calls"

# MCP SERVER DOCUMENTATION

- mcp: alpaca-docker
  why: Primary interface for all Alpaca trading operations
  critical: "Use MCP tools instead of direct HTTP requests to Alpaca API"
  available_tools: |
    - get_account: Retrieve account balance and buying power
    - get_positions: List all open positions
    - submit_order: Place market/limit orders
    - get_latest_quote: Real-time quote data
    - close_position: Close a specific position
    - get_bars: Historical OHLCV data

- mcp: context7
  why: Access to additional API documentation at runtime
  usage: "Query for specific API patterns when needed"

# CODE EXAMPLES FROM CODEBASE

- file: examples/building-blocks/3-tools.py
  why: Pattern for LLM tool calling with external APIs
  pattern: |
    1. Define tool schema (function signature + description)
    2. Execute function locally
    3. Return result to LLM
  critical: "We do the OPPOSITE - tools call MCP, not LLM deciding"

- file: examples/workflows/2-workflow-patterns/1-prompt-chaining.py
  why: Multi-step validation pattern with gate checks
  pattern: |
    1. Extract + validate (gate check)
    2. Process details
    3. Generate confirmation
  critical: "Use for signal validation: screen → analyze → confirm"

- file: examples/building-blocks/4-validation.py
  why: Pydantic schema validation pattern
  pattern: |
    - Define BaseModel with Field descriptions
    - Use client.beta.chat.completions.parse()
    - Auto-retry on validation failure
  critical: "Use Pydantic for all data models (Trade, Signal, Portfolio)"

- file: examples/building-blocks/6-recovery.py
  why: Error handling and retry logic patterns
  pattern: |
    - Try/except with specific exceptions
    - Exponential backoff for retries
    - Fallback responses
  critical: "Alpaca MCP may timeout - implement retry logic"

# LIBRARY DOCUMENTATION

- library: pandas
  version: ">=2.0.0"
  why: DataFrame operations for OHLCV data and indicator calculations

- library: pydantic
  version: ">=2.0.0"
  why: Data validation for trades, signals, portfolio state

- library: python-dotenv
  version: "*"
  why: Load environment variables (required by CLAUDE.md)

- library: supabase
  version: ">=2.2.0"
  why: Async database client for trade logging
  critical: "Use acreate_client() not create_client()"

- library: pandas_ta
  version: "*"
  why: Technical indicators (RSI, MACD, SMA) - easier than TA-Lib
  alternative: "ta-lib (faster but harder to install)"
```

### Current Codebase Tree

```bash
TradeAgent/
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md
│   │   └── execute-prp.md
│   └── settings.local.json
├── PRPs/
│   └── templates/
│       └── prp_base.md
├── examples/
│   ├── building-blocks/
│   │   ├── 1-intelligence.py    # Basic LLM calls
│   │   ├── 2-memory.py          # Context persistence
│   │   ├── 3-tools.py           # External API integration ⭐
│   │   ├── 4-validation.py      # Pydantic schema validation ⭐
│   │   ├── 5-control.py         # Deterministic routing
│   │   ├── 6-recovery.py        # Error handling ⭐
│   │   └── 7-feedback.py        # Human-in-loop
│   └── workflows/
│       ├── 1-introduction/
│       └── 2-workflow-patterns/
│           ├── 1-prompt-chaining.py  # Multi-step validation ⭐
│           ├── 2-routing.py
│           ├── 3-parallizaton.py
│           └── 4-orchestrator.py
├── validation/
├── CLAUDE.md                    # Project rules ⭐
├── INITIAL.md                   # Feature specification
└── README.md

# ⭐ = Critical files to reference for patterns
```

### Desired Codebase Tree with Files to Add

```bash
TradeAgent/
├── .env.example                 # API keys template (NEW)
├── .env                         # Actual keys - gitignored (NEW)
├── requirements.txt             # Python dependencies (NEW)
├── pyproject.toml              # Modern Python project config (NEW)
│
├── src/
│   ├── __init__.py             # (NEW)
│   ├── main.py                 # Daily trading loop entry point (NEW)
│   │                           # Responsibility: Orchestrate daily execution
│   │
│   ├── core/
│   │   ├── __init__.py         # (NEW)
│   │   ├── indicators.py       # RSI, MACD, SMA calculations (NEW)
│   │   │                       # Responsibility: Pure math, no LLM
│   │   ├── risk_manager.py     # Position sizing, stop-loss logic (NEW)
│   │   │                       # Responsibility: Enforce hard limits
│   │   └── portfolio.py        # Rebalancing calculations (NEW)
│   │                           # Responsibility: Defensive core strategy
│   │
│   ├── strategies/
│   │   ├── __init__.py         # (NEW)
│   │   ├── defensive_core.py   # ETF buy & hold + rebalancing (NEW)
│   │   │                       # Responsibility: VTI/VGK/GLD management
│   │   └── momentum_trading.py # Technical breakout strategy (NEW)
│   │                           # Responsibility: RSI/MACD/trend signals
│   │
│   ├── mcp_clients/
│   │   ├── __init__.py         # (NEW)
│   │   ├── alpaca_client.py    # Wrapper for alpaca-docker MCP (NEW)
│   │   │                       # Responsibility: All trading operations
│   │   └── data_client.py      # Market data fetching (NEW)
│   │                           # Responsibility: OHLCV bars, quotes
│   │
│   ├── models/
│   │   ├── __init__.py         # (NEW)
│   │   ├── portfolio.py        # Portfolio, Position Pydantic models (NEW)
│   │   ├── trade.py            # Trade, Signal, Order models (NEW)
│   │   └── performance.py      # Metrics, returns models (NEW)
│   │
│   ├── database/
│   │   ├── __init__.py         # (NEW)
│   │   ├── supabase_client.py  # Async Supabase operations (NEW)
│   │   │                       # Responsibility: Log trades, signals, metrics
│   │   └── schema.sql          # Supabase table definitions (NEW)
│   │
│   └── utils/
│       ├── __init__.py         # (NEW)
│       ├── logger.py           # Structured logging setup (NEW)
│       └── config.py           # Load/validate env vars (NEW)
│
├── tests/
│   ├── __init__.py             # (NEW)
│   ├── test_indicators.py      # Unit tests for RSI, MACD (NEW)
│   ├── test_risk_manager.py    # Position sizing tests (NEW)
│   ├── test_strategies.py      # Strategy logic tests (NEW)
│   ├── test_mcp_clients.py     # MCP integration tests (NEW)
│   └── fixtures/
│       └── sample_bars.json    # Mock market data (NEW)
│
├── scripts/
│   ├── setup_supabase.py       # Create Supabase tables (NEW)
│   └── backtest.py             # Historical analysis (FUTURE)
│
└── venv_linux/                 # Virtual environment (REQUIRED by CLAUDE.md)
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: TA-Lib Installation Challenges
# TA-Lib requires system-level dependencies before pip install
# SOLUTION: Use pandas_ta instead (pure Python, no system deps)
import pandas_ta as ta
# df.ta.rsi(length=14) instead of talib.RSI(df['close'], timeperiod=14)

# CRITICAL: Supabase Async Pattern
# ❌ WRONG: client = create_client(url, key)
# ✅ CORRECT: client = await acreate_client(url, key)
# Must use async/await throughout for Supabase operations

# CRITICAL: Alpaca MCP vs Direct API
# ❌ WRONG: requests.post('https://paper-api.alpaca.markets/v2/orders', ...)
# ✅ CORRECT: Use alpaca-docker MCP tools (get_account, submit_order, etc.)
# Reason: MCP handles auth, retry logic, rate limiting automatically

# CRITICAL: Pydantic v2 Changes
# Field() syntax changed in v2
# ✅ Use: Field(description="...", ge=0, le=100)
# ❌ Old v1: Field(..., description="...")

# CRITICAL: DataFrame Column Access
# When calculating indicators, ensure no NaN values
df['rsi'] = ta.rsi(df['close'], length=14)
df = df.dropna()  # Remove NaN rows from indicator warmup period

# CRITICAL: MACD Returns Tuple
macd = ta.macd(df['close'])  # Returns DataFrame with 3 columns
df['MACD'] = macd['MACD_12_26_9']
df['MACDh'] = macd['MACDh_12_26_9']  # Histogram
df['MACDs'] = macd['MACDs_12_26_9']  # Signal line

# CRITICAL: Market Hours
# Alpaca Paper Trading follows NYSE hours: 9:30 AM - 4:00 PM EST
# Pre-market: 4:00 AM - 9:30 AM EST
# After-hours: 4:00 PM - 8:00 PM EST
# Use timezone-aware datetime: from datetime import timezone

# CRITICAL: Position Sizing
# Alpaca uses fractional shares for stocks (not ETFs in all cases)
# Always check account.buying_power before submitting orders
# Use notional (dollar amount) instead of qty when possible

# CRITICAL: Stop-Loss Implementation
# Alpaca supports bracket orders (entry + stop-loss + take-profit in one)
# ✅ Use bracket orders instead of separate orders
# Pattern: submit_order(..., order_class='bracket', stop_loss={'stop_price': X}, take_profit={'limit_price': Y})

# CRITICAL: Rate Limits - ALL SERVICES
# Alpaca Paper API: 200 requests/minute
# TwelveData Free Tier: 8 requests/minute, 800 requests/day
# Alpha Vantage Free Tier: 25 requests/day (5 per minute)
# Chart-img.com: Check API key tier limits
# Supabase: 500 requests/second (generous, unlikely to hit)
#
# STRATEGY: Use Alpaca MCP for most data (included in trading requests)
# Only use TwelveData/AlphaVantage for extended historical data if needed
# Implement exponential backoff on 429 errors for ALL services
# Use batch operations when possible (get_positions gets all at once)
# Cache historical data locally to avoid repeated API calls

# CRITICAL: Virtual Environment (CLAUDE.md requirement)
# ALL Python commands must use venv_linux
# ✅ uv run python src/main.py
# ❌ python src/main.py
```

---

## Implementation Blueprint

### Phase 1: Foundation (Week 1)
**Goal**: Basic infrastructure working end-to-end

### Data Models and Structure

Create the core data models to ensure type safety and consistency throughout the system.

```python
# src/models/portfolio.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

class Position(BaseModel):
    """Represents a single portfolio position"""
    symbol: str = Field(description="Stock/ETF ticker symbol")
    quantity: Decimal = Field(description="Number of shares held", ge=0)
    avg_entry_price: Decimal = Field(description="Average entry price per share", gt=0)
    current_price: Decimal = Field(description="Current market price", gt=0)
    market_value: Decimal = Field(description="Current position value")
    unrealized_pnl: Decimal = Field(description="Unrealized profit/loss")
    unrealized_pnl_pct: Decimal = Field(description="Unrealized P&L percentage")

class Portfolio(BaseModel):
    """Represents complete portfolio state"""
    cash: Decimal = Field(description="Available cash", ge=0)
    portfolio_value: Decimal = Field(description="Total portfolio value", gt=0)
    buying_power: Decimal = Field(description="Available buying power", ge=0)
    positions: list[Position] = Field(default_factory=list)

# src/models/trade.py
from typing import Literal

class Signal(BaseModel):
    """Trading signal generated by strategy"""
    ticker: str
    action: Literal['BUY', 'SELL', 'HOLD']
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    confidence: Decimal = Field(ge=0, le=1, description="Signal strength 0-1")
    strategy: Literal['defensive', 'momentum']
    # Technical context
    rsi: Decimal | None = Field(default=None, ge=0, le=100)
    macd_histogram: Decimal | None = None
    volume_ratio: Decimal | None = Field(default=None, ge=0)

class Trade(BaseModel):
    """Executed trade record for database"""
    id: str | None = None
    date: datetime
    ticker: str
    action: Literal['BUY', 'SELL']
    quantity: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    exit_price: Decimal | None = None
    exit_reason: Literal['stop_loss', 'take_profit', 'technical_exit', 'rebalance'] | None = None
    pnl: Decimal | None = None
    pnl_pct: Decimal | None = None
    strategy: Literal['defensive', 'momentum']
    # Technical snapshot
    rsi: Decimal | None = None
    macd_histogram: Decimal | None = None
    volume_ratio: Decimal | None = None
    alpaca_order_id: str | None = None
```

### List of Tasks (In Order)

```yaml
Task 1: Environment Setup
CREATE .env.example:
  - Template for: ALPACA_API_KEY, ALPACA_SECRET_KEY, SUPABASE_URL, SUPABASE_KEY
  - Include comments explaining each variable

CREATE requirements.txt:
  - Core: pandas>=2.0.0, pydantic>=2.0.0, python-dotenv
  - Trading: pandas_ta, alpaca-py (fallback if MCP unavailable)
  - Database: supabase>=2.2.0
  - Dev: pytest, ruff, mypy, black

CREATE pyproject.toml:
  - Configure ruff (line-length=100, target Python 3.11+)
  - Configure mypy (strict mode)
  - Configure pytest (asyncio mode)

VALIDATION:
  - uv sync (install dependencies)
  - uv run python -c "import pandas_ta; import supabase; print('OK')"

---

Task 2: Configuration & Logging
CREATE src/utils/config.py:
  - PATTERN: Use python-dotenv load_dotenv() (CLAUDE.md requirement)
  - Load and validate all environment variables
  - Raise clear errors if missing required vars
  - Export typed config object (not raw strings)

PSEUDOCODE:
from dotenv import load_dotenv
import os

load_dotenv()  # CLAUDE.md requirement

class Config:
    ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY") or raise ValueError(...)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL") or raise ValueError(...)
    # ... validate all required vars

    @classmethod
    def validate(cls):
        """Ensure all required vars are set"""
        # Check each field is not None

config = Config()
config.validate()

CREATE src/utils/logger.py:
  - PATTERN: Follow Python logging best practices
  - Structured logging with timestamps
  - Different levels: DEBUG for technical details, INFO for trades
  - Log to console + file (logs/trading.log)

VALIDATION:
  - uv run python -c "from src.utils.config import config; print(config.ALPACA_API_KEY[:5])"
  - uv run python -c "from src.utils.logger import logger; logger.info('Test')"

---

Task 3: Pydantic Models
CREATE src/models/portfolio.py:
  - MIRROR pattern from: examples/workflows/2-workflow-patterns/1-prompt-chaining.py (EventDetails)
  - Portfolio, Position models with Field descriptions
  - Use Decimal for all money/price fields (not float)

CREATE src/models/trade.py:
  - Signal, Trade models
  - Literal types for action/strategy fields
  - Optional fields for exit data (None until closed)

CREATE src/models/performance.py:
  - DailyPerformance, StrategyMetrics models

VALIDATION:
  - CREATE tests/test_models.py
  - Test valid portfolio creation
  - Test invalid data raises ValidationError
  - RUN: uv run pytest tests/test_models.py -v

---

Task 4: Supabase Setup
CREATE src/database/schema.sql:
  - Tables: daily_performance, trades, signals, strategy_metrics
  - PATTERN: Follow schema from INITIAL.md lines 293-366
  - Add indexes: CREATE INDEX idx_trades_ticker ON trades(ticker)
  - Add timestamps: created_at TIMESTAMP DEFAULT NOW()

CREATE scripts/setup_supabase.py:
  - Connect to Supabase
  - Execute schema.sql
  - Verify tables created

CREATE src/database/supabase_client.py:
  - PATTERN: Singleton pattern for client instance
  - Use acreate_client() for async (CRITICAL gotcha)
  - Methods: log_trade(), log_signal(), log_performance()
  - Use batch inserts for multiple records

PSEUDOCODE:
from supabase import acreate_client
from src.utils.config import config

class SupabaseClient:
    _instance = None  # Singleton

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = await acreate_client(
                config.SUPABASE_URL,
                config.SUPABASE_KEY
            )
        return cls._instance

    async def log_trade(self, trade: Trade):
        client = await self.get_instance()
        await client.table('trades').insert(trade.model_dump())

VALIDATION:
  - RUN: uv run python scripts/setup_supabase.py
  - Verify tables in Supabase dashboard
  - Test insert: uv run pytest tests/test_supabase_client.py -v

---

Task 5: Technical Indicators (Pure Math - No LLM)
CREATE src/core/indicators.py:
  - PATTERN: Pure functions, no state, no LLM
  - Use pandas_ta library (easier than TA-Lib)
  - Functions: calculate_rsi(), calculate_macd(), calculate_sma(), calculate_ema()

PSEUDOCODE:
import pandas as pd
import pandas_ta as ta

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate RSI - Relative Strength Index

    Args:
        df: DataFrame with 'close' column
        period: Lookback period (default 14)

    Returns:
        Series with RSI values (0-100)
    """
    # CRITICAL: pandas_ta syntax
    rsi = ta.rsi(df['close'], length=period)
    return rsi

def calculate_macd(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD - Moving Average Convergence Divergence

    Returns:
        (macd_line, signal_line, histogram)
    """
    # CRITICAL: Returns DataFrame with 3 columns
    macd = ta.macd(df['close'])
    return (
        macd['MACD_12_26_9'],
        macd['MACDs_12_26_9'],  # Signal
        macd['MACDh_12_26_9']   # Histogram
    )

def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Current volume / average volume"""
    avg_volume = df['volume'].rolling(window=period).mean()
    return df['volume'] / avg_volume

VALIDATION:
  - CREATE tests/test_indicators.py
  - Use fixtures/sample_bars.json for test data
  - Test RSI in range 0-100
  - Test MACD returns 3 series
  - Test NaN handling (dropna)
  - RUN: uv run pytest tests/test_indicators.py -v

---

Task 6: Alpaca MCP Client Wrapper
CREATE src/mcp_clients/alpaca_client.py:
  - Wrapper around alpaca-docker MCP tools
  - PATTERN: Async methods wrapping MCP calls
  - Methods: get_account(), get_positions(), submit_market_order(), close_position()
  - Error handling with retry logic (CRITICAL: 429 rate limits)

PSEUDOCODE:
from src.models.portfolio import Portfolio, Position
from src.models.trade import Trade

class AlpacaMCPClient:
    """Wrapper for alpaca-docker MCP server"""

    async def get_account(self) -> Portfolio:
        """Get current account state"""
        # CRITICAL: Use MCP tool, not HTTP request
        # mcp_result = await alpaca_mcp.call_tool("get_account")
        # Parse into Portfolio model
        # PATTERN: Pydantic validation ensures correct types
        pass

    async def get_positions(self) -> list[Position]:
        """Get all open positions"""
        pass

    async def submit_market_order(
        self,
        symbol: str,
        qty: Decimal,
        side: Literal['buy', 'sell'],
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None
    ) -> str:
        """Submit market order with optional bracket"""
        # CRITICAL: Use bracket orders if stop_loss/take_profit provided
        # order_class = 'bracket' if stop_loss else 'market'
        # Return order_id
        pass

    async def close_position(self, symbol: str) -> bool:
        """Close entire position"""
        pass

CREATE src/mcp_clients/data_client.py:
  - Get historical bars (OHLCV data)
  - Get latest quotes
  - CRITICAL: Implement rate limiting for all external APIs

PSEUDOCODE for rate limiting:
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    """Generic rate limiter for API calls"""
    def __init__(self, max_calls: int, period_seconds: int):
        self.max_calls = max_calls
        self.period = timedelta(seconds=period_seconds)
        self.calls = []

    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        now = datetime.now()

        # Remove calls outside the time window
        self.calls = [t for t in self.calls if now - t < self.period]

        if len(self.calls) >= self.max_calls:
            # Wait until oldest call expires
            sleep_time = (self.calls[0] + self.period - now).total_seconds()
            await asyncio.sleep(sleep_time)
            self.calls = self.calls[1:]  # Remove expired

        self.calls.append(now)

# Rate limiters for each service
ALPACA_LIMITER = RateLimiter(max_calls=200, period_seconds=60)  # 200/min
TWELVEDATA_LIMITER = RateLimiter(max_calls=8, period_seconds=60)  # 8/min
ALPHAVANTAGE_LIMITER = RateLimiter(max_calls=5, period_seconds=60)  # 5/min

class DataClient:
    """Handles market data fetching with rate limiting"""

    async def get_bars_alpaca(self, symbol: str, days: int = 30):
        """Primary method - use Alpaca MCP (most generous rate limit)"""
        await ALPACA_LIMITER.acquire()
        # Call alpaca MCP get_bars
        pass

    async def get_bars_twelvedata(self, symbol: str, days: int = 30):
        """Fallback if Alpaca unavailable - STRICT rate limits"""
        await TWELVEDATA_LIMITER.acquire()
        # Call TwelveData API
        # CRITICAL: Cache results locally to avoid repeated calls
        pass

VALIDATION:
  - CREATE tests/test_mcp_clients.py with mocks
  - Test get_account returns Portfolio
  - Test submit_order with bracket params
  - RUN: uv run pytest tests/test_mcp_clients.py -v

---

Task 7: Risk Manager (Pure Logic - No LLM)
CREATE src/core/risk_manager.py:
  - PATTERN: Pure functions with hard-coded limits
  - Functions: filter_signals_by_risk(), calculate_position_size(), check_daily_loss_limit()

PSEUDOCODE:
from src.models.trade import Signal
from src.models.portfolio import Portfolio

MAX_POSITIONS = 5
MAX_POSITION_SIZE_PCT = 0.10  # 10% of portfolio
MAX_DAILY_RISK_PCT = 0.02     # 2% per trade
DAILY_LOSS_LIMIT_PCT = 0.03   # Circuit breaker at -3%

def filter_signals_by_risk(
    signals: list[Signal],
    portfolio: Portfolio,
    current_positions: list[Position]
) -> list[Signal]:
    """Apply risk filters and sort by confidence"""
    # 1. Check position limit
    if len(current_positions) >= MAX_POSITIONS:
        return []

    # 2. Sort by confidence (highest first)
    signals.sort(key=lambda s: s.confidence, reverse=True)

    # 3. Take top N within position limit
    available_slots = MAX_POSITIONS - len(current_positions)
    return signals[:available_slots]

def calculate_position_size(
    signal: Signal,
    portfolio: Portfolio
) -> Decimal:
    """Calculate safe position size"""
    # Max position value: 10% of portfolio
    max_position_value = portfolio.portfolio_value * Decimal(MAX_POSITION_SIZE_PCT)

    # Calculate shares (rounded down)
    shares = max_position_value / signal.entry_price
    return shares.quantize(Decimal('0.01'))

VALIDATION:
  - CREATE tests/test_risk_manager.py
  - Test max position limit enforced
  - Test position sizing calculation
  - RUN: uv run pytest tests/test_risk_manager.py -v

---

Task 8: Defensive Core Strategy
CREATE src/strategies/defensive_core.py:
  - PATTERN: Deterministic rebalancing logic, no LLM
  - Functions: should_rebalance(), calculate_rebalancing_orders()

PSEUDOCODE:
from datetime import date
from src.models.trade import Signal

TARGET_ALLOCATIONS = {
    'VTI': Decimal('0.25'),  # 25% US Total Market
    'VGK': Decimal('0.15'),  # 15% Europe
    'GLD': Decimal('0.10'),  # 10% Gold
}

def should_rebalance(today: date, positions: list[Position], portfolio: Portfolio) -> bool:
    """Check if rebalancing needed"""
    # Trigger 1: First trading day of month
    if today.day == 1:
        return True

    # Trigger 2: Portfolio drift > 5%
    for symbol, target_pct in TARGET_ALLOCATIONS.items():
        position = next((p for p in positions if p.symbol == symbol), None)

        if position is None:
            current_pct = Decimal('0')
        else:
            current_pct = position.market_value / portfolio.portfolio_value

        drift = abs(current_pct - target_pct)
        if drift > Decimal('0.05'):  # 5% drift
            return True

    return False

def calculate_rebalancing_orders(
    positions: list[Position],
    portfolio: Portfolio
) -> list[Signal]:
    """Calculate buy/sell orders to reach target allocations"""
    signals = []

    for symbol, target_pct in TARGET_ALLOCATIONS.items():
        target_value = portfolio.portfolio_value * target_pct

        position = next((p for p in positions if p.symbol == symbol), None)
        current_value = position.market_value if position else Decimal('0')

        diff = target_value - current_value

        if abs(diff) > Decimal('100'):  # Only if >$100 difference
            action = 'BUY' if diff > 0 else 'SELL'
            signals.append(Signal(
                ticker=symbol,
                action=action,
                entry_price=position.current_price if position else Decimal('0'),  # Will get latest quote
                confidence=Decimal('1.0'),  # Deterministic
                strategy='defensive'
            ))

    return signals

VALIDATION:
  - CREATE tests/test_strategies.py
  - Test rebalancing on month start
  - Test drift detection
  - Test order calculation
  - RUN: uv run pytest tests/test_strategies.py -v

---

Task 9: Momentum Trading Strategy
CREATE src/strategies/momentum_trading.py:
  - PATTERN: Technical analysis only, no LLM
  - Functions: scan_for_signals(), check_exit_conditions()

PSEUDOCODE:
from src.core.indicators import calculate_rsi, calculate_macd, calculate_sma, calculate_volume_ratio

WATCHLIST = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AMZN', 'AMD', 'NFLX', 'AVGO']

async def scan_for_signals(alpaca_client: AlpacaMCPClient) -> list[Signal]:
    """Scan watchlist for momentum entry signals"""
    signals = []

    for ticker in WATCHLIST:
        # Get 30 days of bars
        bars = await alpaca_client.get_bars(ticker, days=30)
        df = pd.DataFrame(bars)

        # Calculate indicators
        df['rsi'] = calculate_rsi(df)
        df['macd'], df['signal'], df['histogram'] = calculate_macd(df)
        df['sma20'] = calculate_sma(df, period=20)
        df['volume_ratio'] = calculate_volume_ratio(df)

        df = df.dropna()  # Remove NaN from warmup

        latest = df.iloc[-1]

        # Entry Criteria (ALL must be True)
        entry_conditions = [
            50 < latest['rsi'] < 70,           # Bullish, not overbought
            latest['histogram'] > 0,            # Positive momentum
            latest['close'] > latest['sma20'], # Uptrend
            latest['volume_ratio'] > 1.0       # Above average volume
        ]

        if all(entry_conditions):
            # Calculate stop-loss and take-profit
            entry_price = Decimal(str(latest['close']))
            stop_loss = entry_price * Decimal('0.95')   # -5%
            take_profit = entry_price * Decimal('1.15') # +15%

            # Confidence = average of normalized indicators
            confidence = (
                (latest['rsi'] - 50) / 20 +  # Normalize RSI 50-70 to 0-1
                min(latest['histogram'] / 2, 1.0) +
                min(latest['volume_ratio'] - 1, 1.0)
            ) / 3

            signals.append(Signal(
                ticker=ticker,
                action='BUY',
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=Decimal(str(confidence)),
                strategy='momentum',
                rsi=Decimal(str(latest['rsi'])),
                macd_histogram=Decimal(str(latest['histogram'])),
                volume_ratio=Decimal(str(latest['volume_ratio']))
            ))

    return signals

async def check_exit_conditions(position: Position, alpaca_client: AlpacaMCPClient) -> tuple[bool, str | None]:
    """Check if momentum position should exit"""
    # Get current price
    quote = await alpaca_client.get_latest_quote(position.symbol)
    current_price = quote['price']

    # Check stop-loss
    pnl_pct = (current_price - position.avg_entry_price) / position.avg_entry_price
    if pnl_pct <= -0.05:
        return (True, 'stop_loss')

    # Check take-profit
    if pnl_pct >= 0.15:
        return (True, 'take_profit')

    # Check technical exit
    bars = await alpaca_client.get_bars(position.symbol, days=30)
    df = pd.DataFrame(bars)
    df['rsi'] = calculate_rsi(df)
    df['histogram'] = calculate_macd(df)[2]
    df = df.dropna()
    latest = df.iloc[-1]

    if latest['rsi'] > 75 or latest['histogram'] < 0:
        return (True, 'technical_exit')

    return (False, None)

VALIDATION:
  - Test signal generation with sample data
  - Test exit conditions
  - RUN: uv run pytest tests/test_strategies.py -v

---

Task 10: Main Trading Loop
CREATE src/main.py:
  - PATTERN: Orchestrate all components
  - Entry point for daily execution

PSEUDOCODE:
import asyncio
from datetime import datetime, timezone
from src.utils.config import config
from src.utils.logger import logger
from src.mcp_clients.alpaca_client import AlpacaMCPClient
from src.database.supabase_client import SupabaseClient
from src.strategies.defensive_core import should_rebalance, calculate_rebalancing_orders
from src.strategies.momentum_trading import scan_for_signals, check_exit_conditions
from src.core.risk_manager import filter_signals_by_risk, calculate_position_size

async def daily_trading_loop():
    """Main trading loop - 100% deterministic, no LLM"""
    logger.info("=== Daily Trading Loop Started ===")

    # Initialize clients
    alpaca = AlpacaMCPClient()
    supabase = await SupabaseClient.get_instance()

    # 1. Get portfolio state
    portfolio = await alpaca.get_account()
    positions = await alpaca.get_positions()
    logger.info(f"Portfolio Value: ${portfolio.portfolio_value}")

    # 2. Defensive Core: Check rebalancing
    today = datetime.now(timezone.utc).date()
    if should_rebalance(today, positions, portfolio):
        logger.info("Rebalancing triggered")
        rebalance_signals = calculate_rebalancing_orders(positions, portfolio)

        for signal in rebalance_signals:
            # Execute rebalancing orders
            qty = calculate_position_size(signal, portfolio)
            order_id = await alpaca.submit_market_order(
                symbol=signal.ticker,
                qty=qty,
                side=signal.action.lower()
            )
            # Log trade
            await supabase.log_trade(Trade(
                date=datetime.now(timezone.utc),
                ticker=signal.ticker,
                action=signal.action,
                quantity=qty,
                entry_price=signal.entry_price,
                strategy='defensive',
                alpaca_order_id=order_id
            ))

    # 3. Momentum Trading: Scan for signals
    momentum_signals = await scan_for_signals(alpaca)
    logger.info(f"Found {len(momentum_signals)} momentum signals")

    # 4. Apply risk filters
    filtered_signals = filter_signals_by_risk(momentum_signals, portfolio, positions)

    # 5. Execute momentum entries
    for signal in filtered_signals:
        qty = calculate_position_size(signal, portfolio)
        order_id = await alpaca.submit_market_order(
            symbol=signal.ticker,
            qty=qty,
            side='buy',
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        await supabase.log_trade(Trade(
            date=datetime.now(timezone.utc),
            ticker=signal.ticker,
            action='BUY',
            quantity=qty,
            entry_price=signal.entry_price,
            strategy='momentum',
            rsi=signal.rsi,
            macd_histogram=signal.macd_histogram,
            alpaca_order_id=order_id
        ))

    # 6. Check exit conditions for momentum positions
    for position in positions:
        if position.symbol not in ['VTI', 'VGK', 'GLD']:  # Skip defensive core
            should_exit, reason = await check_exit_conditions(position, alpaca)

            if should_exit:
                logger.info(f"Exiting {position.symbol}: {reason}")
                await alpaca.close_position(position.symbol)
                # Log exit
                await supabase.log_trade(Trade(
                    date=datetime.now(timezone.utc),
                    ticker=position.symbol,
                    action='SELL',
                    quantity=position.quantity,
                    entry_price=position.avg_entry_price,
                    exit_price=position.current_price,
                    exit_reason=reason,
                    pnl=position.unrealized_pnl,
                    pnl_pct=position.unrealized_pnl_pct,
                    strategy='momentum'
                ))

    # 7. Daily Performance Analysis (end of day)
    await analyze_daily_performance()

    logger.info("=== Daily Trading Loop Completed ===")

if __name__ == "__main__":
    asyncio.run(daily_trading_loop())

VALIDATION:
  - RUN: uv run python src/main.py
  - Check logs/trading.log for execution flow
  - Verify trades in Supabase dashboard
  - Verify positions in Alpaca dashboard

---

Task 11: Daily Performance Analysis & Continuous Optimization
CREATE src/core/performance_analyzer.py:
  - PATTERN: Deterministic performance analysis, no LLM
  - Functions: analyze_daily_performance(), adjust_parameters_if_needed(), generate_weekly_report()
  - Responsibility: Learn from past trades and adjust strategy parameters

PSEUDOCODE:
from datetime import datetime, timedelta
from src.database.supabase_client import SupabaseClient
from src.utils.logger import logger

# Global strategy parameters (will be adjusted)
STRATEGY_PARAMS = {
    'momentum': {
        'rsi_min': 50,
        'rsi_max': 70,
        'stop_loss_pct': 0.05,
        'take_profit_pct': 0.15,
        'min_volume_ratio': 1.0
    },
    'defensive': {
        'rebalance_drift_threshold': 0.05
    }
}

async def analyze_daily_performance():
    """
    Runs at end of day (after market close 4 PM EST)
    Analyzes today's trades and updates metrics
    100% deterministic - no LLM
    """
    logger.info("=== Daily Performance Analysis Started ===")

    supabase = await SupabaseClient.get_instance()
    today = datetime.now().date()

    # 1. Fetch today's trades
    response = await supabase.table('trades').select('*').eq('date', today).execute()
    trades = response.data

    if not trades:
        logger.info("No trades today")
        return

    # 2. Calculate daily metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) < 0]

    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

    total_pnl = sum(t.get('pnl', 0) for t in trades)
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    logger.info(f"Daily Stats: {total_trades} trades, Win Rate: {win_rate:.2%}, P&L: ${total_pnl:.2f}")

    # 3. Store daily performance
    await supabase.table('daily_performance').insert({
        'date': today,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'daily_pnl': total_pnl,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }).execute()

    # 4. Per-strategy breakdown
    for strategy in ['defensive', 'momentum']:
        strategy_trades = [t for t in trades if t['strategy'] == strategy]
        if strategy_trades:
            strategy_pnl = sum(t.get('pnl', 0) for t in strategy_trades)
            strategy_win_rate = len([t for t in strategy_trades if t.get('pnl', 0) > 0]) / len(strategy_trades)

            await supabase.table('strategy_metrics').insert({
                'strategy': strategy,
                'date': today,
                'total_trades': len(strategy_trades),
                'win_rate': strategy_win_rate,
                'total_pnl': strategy_pnl
            }).execute()

            logger.info(f"{strategy.upper()} Strategy: {len(strategy_trades)} trades, Win Rate: {strategy_win_rate:.2%}, P&L: ${strategy_pnl:.2f}")

    # 5. Check if parameter adjustment needed (deterministic rules)
    await adjust_parameters_if_needed()

    logger.info("=== Daily Performance Analysis Completed ===")


async def adjust_parameters_if_needed():
    """
    Deterministic parameter adjustment based on performance
    Checks last 5 days of performance and adjusts if needed
    """
    supabase = await SupabaseClient.get_instance()

    # Get last 5 days of momentum strategy performance
    five_days_ago = datetime.now().date() - timedelta(days=5)
    response = await supabase.table('strategy_metrics')\
        .select('*')\
        .eq('strategy', 'momentum')\
        .gte('date', five_days_ago)\
        .execute()

    recent_performance = response.data

    if len(recent_performance) < 5:
        logger.info("Not enough data for parameter adjustment (need 5 days)")
        return

    # Calculate 5-day average win rate
    avg_win_rate = sum(p['win_rate'] for p in recent_performance) / len(recent_performance)

    # Rule 1: If win rate < 55% for 5 consecutive days, tighten entry criteria
    if avg_win_rate < 0.55:
        logger.warning(f"Low win rate detected: {avg_win_rate:.2%}. Tightening entry criteria.")
        STRATEGY_PARAMS['momentum']['rsi_min'] = 55  # More conservative
        STRATEGY_PARAMS['momentum']['rsi_max'] = 65
        STRATEGY_PARAMS['momentum']['min_volume_ratio'] = 1.2  # Require stronger volume

        # Log parameter change
        await supabase.table('parameter_changes').insert({
            'date': datetime.now(),
            'reason': f'Low win rate: {avg_win_rate:.2%}',
            'old_params': {'rsi_min': 50, 'rsi_max': 70, 'min_volume_ratio': 1.0},
            'new_params': STRATEGY_PARAMS['momentum']
        }).execute()

    # Rule 2: If average loss / average win > 0.5, widen stop-loss
    total_wins = sum(p.get('total_wins', 0) for p in recent_performance)
    total_losses = sum(p.get('total_losses', 0) for p in recent_performance)

    if total_wins > 0 and total_losses > 0:
        avg_win_amount = sum(p.get('avg_win', 0) for p in recent_performance) / len(recent_performance)
        avg_loss_amount = sum(p.get('avg_loss', 0) for p in recent_performance) / len(recent_performance)

        risk_reward_ratio = abs(avg_loss_amount / avg_win_amount) if avg_win_amount > 0 else 0

        if risk_reward_ratio > 0.5:
            logger.warning(f"Risk/Reward worsening: {risk_reward_ratio:.2f}. Widening stop-loss.")
            STRATEGY_PARAMS['momentum']['stop_loss_pct'] = 0.07  # -7% instead of -5%

            await supabase.table('parameter_changes').insert({
                'date': datetime.now(),
                'reason': f'Risk/Reward ratio: {risk_reward_ratio:.2f}',
                'old_params': {'stop_loss_pct': 0.05},
                'new_params': {'stop_loss_pct': 0.07}
            }).execute()

    # Rule 3: If win rate > 65% for 5 days, loosen entry criteria (capture more opportunities)
    if avg_win_rate > 0.65:
        logger.info(f"High win rate detected: {avg_win_rate:.2%}. Loosening entry criteria to capture more trades.")
        STRATEGY_PARAMS['momentum']['rsi_min'] = 45
        STRATEGY_PARAMS['momentum']['rsi_max'] = 75

        await supabase.table('parameter_changes').insert({
            'date': datetime.now(),
            'reason': f'High win rate: {avg_win_rate:.2%}',
            'old_params': {'rsi_min': 50, 'rsi_max': 70},
            'new_params': {'rsi_min': 45, 'rsi_max': 75}
        }).execute()


async def generate_weekly_report():
    """
    Runs every Sunday - comprehensive weekly analysis
    Compares performance vs SPY benchmark
    Identifies best/worst performers
    """
    supabase = await SupabaseClient.get_instance()

    # Get last 7 days
    week_ago = datetime.now().date() - timedelta(days=7)

    # Fetch all trades from last week
    response = await supabase.table('trades').select('*').gte('date', week_ago).execute()
    weekly_trades = response.data

    if not weekly_trades:
        logger.info("No trades this week")
        return

    # Calculate weekly metrics
    total_pnl = sum(t.get('pnl', 0) for t in weekly_trades)
    total_trades = len(weekly_trades)
    winning_trades = [t for t in weekly_trades if t.get('pnl', 0) > 0]
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

    # Best and worst performers
    sorted_trades = sorted(weekly_trades, key=lambda t: t.get('pnl_pct', 0), reverse=True)
    best_performers = sorted_trades[:3]
    worst_performers = sorted_trades[-3:]

    # Portfolio return
    # (Would need to fetch portfolio value from 7 days ago and compare)

    logger.info(f"===== WEEKLY REPORT =====")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Win Rate: {win_rate:.2%}")
    logger.info(f"Total P&L: ${total_pnl:.2f}")
    logger.info(f"Best Performers: {[t['ticker'] + f' ({t.get("pnl_pct", 0):.2%})' for t in best_performers]}")
    logger.info(f"Worst Performers: {[t['ticker'] + f' ({t.get("pnl_pct", 0):.2%})' for t in worst_performers]}")
    logger.info(f"========================")

    # Store weekly summary
    await supabase.table('weekly_reports').insert({
        'week_ending': datetime.now().date(),
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'best_performers': [t['ticker'] for t in best_performers],
        'worst_performers': [t['ticker'] for t in worst_performers]
    }).execute()

INTEGRATION INTO MAIN:
  - Call analyze_daily_performance() at end of daily_trading_loop()
  - Schedule generate_weekly_report() to run Sundays (use cron or check day of week)

CREATE src/database/schema.sql additions:
  - Add table: parameter_changes (date, reason, old_params, new_params)
  - Add table: weekly_reports (week_ending, total_trades, win_rate, total_pnl, best_performers, worst_performers)
  - Update daily_performance table with avg_win, avg_loss, profit_factor columns

VALIDATION:
  - CREATE tests/test_performance_analyzer.py
  - Test daily metrics calculation
  - Test parameter adjustment logic (mock 5 days of bad performance)
  - Test weekly report generation
  - RUN: uv run pytest tests/test_performance_analyzer.py -v

---

Task 12: Integration Tests
CREATE tests/test_integration.py:
  - Test full daily loop with mocked MCP
  - Test defensive rebalancing end-to-end
  - Test momentum signal → order flow
  - Test exit conditions → close position

VALIDATION:
  - RUN: uv run pytest tests/test_integration.py -v
  - ALL TESTS MUST PASS

---

Task 12: Linting & Type Checking
RUN validation commands:
  - uv run ruff check src/ --fix
  - uv run mypy src/
  - uv run pytest tests/ -v

FIX any errors found:
  - Read error messages carefully
  - Fix root cause, don't suppress warnings
  - Re-run until clean

VALIDATION:
  - All 3 commands return 0 exit code
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run FIRST - fix errors before proceeding
uv run ruff check src/ --fix      # Auto-fix PEP8 violations
uv run mypy src/                   # Type checking
uv run black src/                  # Code formatting

# Expected: No errors
# If errors: READ error message, understand root cause, fix, re-run
```

### Level 2: Unit Tests
```bash
# Run tests for each module
uv run pytest tests/test_models.py -v
uv run pytest tests/test_indicators.py -v
uv run pytest tests/test_risk_manager.py -v
uv run pytest tests/test_strategies.py -v
uv run pytest tests/test_mcp_clients.py -v

# Expected: All tests pass
# If failing: Read pytest output, fix code (NOT tests), re-run
```

### Level 3: Integration Test
```bash
# Test full daily loop
uv run pytest tests/test_integration.py -v

# Expected: Complete workflow passes
# If failing: Check logs/trading.log for details, fix, re-run
```

### Level 4: Manual Execution
```bash
# Run actual trading loop (paper trading - no real money)
uv run python src/main.py

# Expected output:
# - "Daily Trading Loop Started"
# - Portfolio value logged
# - Rebalancing status
# - Momentum signals found
# - Orders executed (or "No signals")
# - "Daily Trading Loop Completed"

# Verify in external systems:
# 1. Supabase: Check trades table has new rows
# 2. Alpaca Dashboard: Check positions match expected
```

---

## Final Validation Checklist

- [ ] All tests pass: `uv run pytest tests/ -v` (0 failures)
- [ ] No linting errors: `uv run ruff check src/` (0 errors)
- [ ] No type errors: `uv run mypy src/` (0 errors)
- [ ] Manual test successful: `uv run python src/main.py` completes without crash
- [ ] Defensive rebalancing works: VTI/VGK/GLD positions created
- [ ] Momentum signals generated: At least 1 signal in logs (if market conditions allow)
- [ ] Risk limits enforced: Max 5 positions, max 10% per position verified in logs
- [ ] Supabase logging works: Trades visible in database
- [ ] Alpaca integration works: Orders appear in Alpaca paper trading dashboard
- [ ] Error handling works: Graceful failures on API errors (test by disconnecting network briefly)
- [ ] Logs are clear: Can understand execution flow from logs/trading.log

---

## Anti-Patterns to Avoid

- ❌ Don't use LLMs for calculations - use pure math (pandas_ta for indicators)
- ❌ Don't use float for money - use Decimal for precision
- ❌ Don't make direct HTTP requests to Alpaca - use MCP tools
- ❌ Don't use sync Supabase client - use acreate_client() async
- ❌ Don't skip Pydantic validation - always validate data models
- ❌ Don't ignore rate limits - implement retry logic with backoff
- ❌ Don't create files >500 lines - split into modules (CLAUDE.md rule)
- ❌ Don't forget venv_linux - all Python commands use uv run (CLAUDE.md rule)
- ❌ Don't skip tests - every function needs pytest tests (CLAUDE.md rule)
- ❌ Don't hardcode API keys - use .env with python-dotenv (CLAUDE.md rule)

---

## Success Metrics (Week 1)

**Must Have:**
- ✅ Daily loop runs 7 consecutive days without crashes
- ✅ All trades logged to Supabase with technical context
- ✅ Defensive core rebalances correctly (verify VTI/VGK/GLD allocations)
- ✅ Momentum strategy executes >=1 trade/week
- ✅ Risk limits enforced (max 10% per position verified)
- ✅ Paper trading account balance >$0 (not losing all money)

**Nice to Have:**
- Win rate >55% for momentum trades
- Sharpe ratio >1.0
- Max drawdown <12%

**Anti-Goals (DO NOT):**
- ❌ Use LLMs for deterministic calculations
- ❌ Build multi-agent systems (keep it simple)
- ❌ Trade crypto (focus on equities only)
- ❌ Implement options strategies (Phase 1 is stocks/ETFs only)
- ❌ Build custom MCP servers (use existing alpaca-docker MCP)
- ❌ Use expensive APIs (Danelfin) - respect free tier limits

---

## PRP Quality Score

**Confidence Level: 9/10**

**Strengths:**
✅ Complete context: Alpaca MCP patterns, Supabase async, pandas_ta examples
✅ Executable validation: Every task has pytest tests + ruff/mypy checks
✅ References existing patterns: Building blocks for validation, workflows for chaining
✅ Clear implementation path: 12 sequential tasks with pseudocode
✅ Error handling documented: Rate limits, retry logic, bracket orders
✅ Follows CLAUDE.md: venv_linux, 500 line limit, pytest requirements
✅ Deterministic focus: 80%+ logic without LLM, pure math for indicators

**Weaknesses:**
⚠️ MCP integration not tested: Assumes alpaca-docker MCP works as expected
⚠️ No backtest validation: Week 1 focuses on infrastructure, not performance optimization

**Mitigation:**
- Start with defensive core (simpler, less risky)
- Add comprehensive logging to debug MCP issues
- Manual verification in Alpaca dashboard after each run

This PRP provides all necessary context for one-pass implementation success. The AI agent can execute this end-to-end with self-validation and iterative refinement using the validation loops.

---

## Continuous Optimization Strategy

### How It Works (100% Deterministic - No ML)

The system learns and improves through **rule-based parameter adjustment** based on performance metrics.

#### Daily Cycle (Automated):

1. **Morning (9:00 AM EST)**: Execute trades using current strategy parameters
2. **End of Day (4:30 PM EST)**: Run `analyze_daily_performance()`
   - Calculate daily metrics: win rate, P&L, profit factor
   - Store in Supabase for historical tracking
   - Check if parameter adjustment needed (every 5 days)

#### Parameter Adjustment Rules (Deterministic):

**Rule 1: Low Win Rate (< 55% for 5 days)**
```python
# Action: Make entry criteria MORE conservative
rsi_min: 50 → 55  # Only enter on stronger signals
rsi_max: 70 → 65  # Avoid overbought conditions
min_volume_ratio: 1.0 → 1.2  # Require stronger volume confirmation
```

**Rule 2: Poor Risk/Reward (Avg Loss / Avg Win > 0.5)**
```python
# Action: Widen stop-loss to give trades more room
stop_loss_pct: 5% → 7%  # Less likely to get stopped out prematurely
```

**Rule 3: High Win Rate (> 65% for 5 days)**
```python
# Action: Loosen entry criteria to capture MORE opportunities
rsi_min: 50 → 45  # Accept slightly weaker signals
rsi_max: 70 → 75  # Allow more overbought entries
```

#### Weekly Analysis (Every Sunday):

- `generate_weekly_report()` runs automatically
- Identifies best/worst performing tickers
- Compares portfolio return vs SPY benchmark (future enhancement)
- Logs weekly summary to Supabase

#### Example Optimization Scenario:

**Days 1-5**: Win rate = 45%, losing money
- System detects: `avg_win_rate < 0.55`
- **Automatic adjustment**: Tightens entry criteria (RSI 55-65 instead of 50-70)
- Logs change to `parameter_changes` table with reason

**Days 6-10**: Win rate improves to 62% with tighter criteria
- System continues monitoring
- No adjustment needed (within target range 55-65%)

**Days 11-15**: Win rate = 68%, missing opportunities
- System detects: `avg_win_rate > 0.65`
- **Automatic adjustment**: Loosens entry criteria to capture more trades
- Balances between quality and quantity of signals

### Key Differences from Traditional ML:

✅ **Deterministic**: Same performance → same adjustment (reproducible)
✅ **Explainable**: Every parameter change logged with reason
✅ **Fast**: No training time, immediate adjustments
✅ **Robust**: Can't overfit, no model drift
✅ **Debuggable**: Check `parameter_changes` table to see full history

### Rate Limiting Implementation:

All external API calls go through `RateLimiter` class:

- **Alpaca**: 200 req/min (primary data source)
- **TwelveData**: 8 req/min, 800/day (fallback, cached)
- **Alpha Vantage**: 5 req/min, 25/day (rarely used)
- **Supabase**: 500 req/sec (generous, no issues expected)

**Strategy**:
1. Use Alpaca MCP for all real-time data (bars, quotes)
2. Only fall back to TwelveData for extended historical data
3. Cache historical data locally to avoid repeated API calls
4. Implement exponential backoff on 429 errors

**Implementation**:
```python
# Before every API call:
await ALPACA_LIMITER.acquire()  # Blocks if rate limit hit
result = await alpaca_mcp.get_bars(...)
```

This ensures we NEVER hit rate limits, even during high-activity periods (market open, volatility spikes).

---

## Summary

This PRP implements a **self-optimizing trading system** that:

1. **Executes deterministically** (80%+ logic without LLM)
2. **Learns from performance** (rule-based parameter adjustment)
3. **Respects API limits** (rate limiting for all services)
4. **Tracks everything** (all trades, signals, metrics in Supabase)
5. **Adjusts automatically** (continuous improvement without human intervention)

The system gets **smarter over time** through data-driven parameter tuning, while remaining fully explainable and debuggable. Every decision and adjustment is logged for transparency and analysis.
