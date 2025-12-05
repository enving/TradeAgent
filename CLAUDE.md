### 🔄 Project Awareness & Context
- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn't listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for unit tests.
- **TradeAgent is a 100% deterministic paper trading system** - No LLM involvement in trading decisions (LLM features are optional and separate from core trading logic).

### 📦 Key Integrations & Features

#### Core Trading Infrastructure
- **Alpaca Paper Trading API** - All trades executed via `src/mcp_clients/alpaca_client.py` (200 calls/min)
- **Supabase Database** - All trades, signals, ML training data with Row Level Security (RLS) enabled
- **Market Data Adapter** - Market hours, trading calendar, portfolio analytics in `src/adapters/market_data_adapter.py`
- **yfinance** - Primary market data source (unlimited, free) for momentum scanning

#### AI/LLM Features (✅ ENABLED)
- **🤖 OpenRouter LLM** - Claude 3.5 Sonnet for news sentiment analysis
- **📰 News Aggregation** - Multi-source news from Yahoo Finance, Finnhub, NewsAPI
- **🧠 Sentiment Analysis** - LLM-powered sentiment scoring for trading signals
- **📊 News-Driven Strategy** - Generates BUY signals from high-conviction news + technical confirmation
- **💬 Trade Explanation** - LLM explains reasoning behind every trade decision

#### Data Sources (✅ ALL CONFIGURED)
- **NewsAPI** - 1000 requests/day for general financial news
- **Finnhub** - Company-specific news and earnings data
- **yfinance** - Real-time quotes, historical data, company news (unlimited)
- **Alpha Vantage** - Technical indicators (RSI, MACD) - 5 calls/min, 500/day

#### Advanced Features
- **ML Data Collection** - Automated feature collection for every trade (technicals + sentiment + news)
- **Backtesting Engine** - Historical simulation framework in `src/backtest/`
- **Performance Analytics** - Sharpe ratio, max drawdown, Calmar ratio tracking

### 🔑 Environment Variables

**Required (Core Trading):**
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` - Paper trading API (✅ configured)
- `SUPABASE_URL`, `SUPABASE_KEY` - Database connection (✅ configured)

**AI/LLM Features (✅ ALL CONFIGURED):**
- `OPENROUTER_API_KEY` - Claude 3.5 Sonnet for sentiment analysis (✅ active)
- `NEWS_API_KEY` - NewsAPI for financial news (✅ active)
- `FINNHUB_API_KEY` - Company news and earnings (✅ active)
- `ALPHAVANTAGE_API_KEY` - Technical indicators backup (✅ configured)
- `ENABLE_LLM_FEATURES=true` - Master switch for all AI features (✅ enabled)
- `ENABLE_NEWS_VERIFICATION=true` - Verify momentum signals with news (✅ enabled)
- `ENABLE_NEWS_SIGNALS=true` - Generate signals from news (✅ enabled)

### 🤖 Running the Trading Bot
- **Single execution:** `python -m src.main` (runs once, logs to console)
- **Background mode:** `python run_trading_background.py` (runs once, logs to file)
- **Scheduled execution:** Use `run_scheduled_trading.py` or OS-level schedulers (cron/Task Scheduler)
- **Check status:** `python check_positions.py` (quick portfolio summary)
- **Test integrations:** `python test_alpha_vantage.py`, `python test_market_adapter.py`

### ⚡ Rate Limiting & API Considerations
- **Alpaca Free Tier:** 200 calls/min (implemented sliding window rate limiter in `src/mcp_clients/alpaca_client.py`)
- **Alpha Vantage Free Tier:** 5 calls/min, 500 calls/day (12-second delay between calls in `src/clients/alpha_vantage_client.py`)
- **Momentum Scanning:** Takes ~2 minutes for 10-ticker watchlist due to Alpha Vantage rate limits
- **Trade-off:** Using Alpha Vantage for free market data vs paid Alpaca subscription for real-time data
- **Future Upgrade:** When trading with real money, upgrade to paid Alpaca for faster data access

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a "Discovered During Work" section.

### 🗄️ Database Schema
Supabase tables (see `src/database/schema.sql` and `database/migrations/` for full schema):

#### Core Trading Tables:
- **trades** - All executed trades (entries & exits, supports 'news_sentiment' strategy)
- **signals** - Generated trading signals before execution (includes `metadata` JSONB field)
- **daily_performance** - Daily aggregated performance metrics
- **strategy_metrics** - Per-strategy performance tracking
- **weekly_reports** - Weekly performance summaries
- **parameter_changes** - Audit trail of strategy parameter adjustments

#### 🆕 News & LLM Logging Tables (Added: 2025-12-03):
- **news_articles** - Archive of ALL fetched news articles
  - Sources: Yahoo Finance, Finnhub, NewsAPI
  - Deduplication by URL (UNIQUE constraint)
  - Fields: ticker, title, summary, source, url, published_at, fetched_at
- **llm_analysis_log** - Complete log of EVERY LLM sentiment analysis
  - Captures ALL analyses (BUY, SELL, HOLD) - not just signals
  - Fields: action, sentiment_score, confidence, impact, reasoning
  - Tracks signal flow: signal_generated, signal_approved, technical_filter_reason
  - Links to signals table if signal was created
  - **Purpose:** Understand why LLM recommended actions & why signals were rejected

#### ML Training Data:
- **ml_training_data** - Automated ML feature collection for every trade
  - **Automatic feature collection** runs on every trade via `src/core/feature_collector.py`
  - **Features captured:** RSI, MACD, volume ratios, strategy triggers, portfolio state, market context
  - **Future ML training:** After 3-6 months of data, train models to predict trade outcomes
  - **Labeling script:** `scripts/label_trades.py` labels outcomes after 7/14/30 days

**Security:** All tables have Row Level Security (RLS) enabled. Only service role can read/write.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.