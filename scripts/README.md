# Scripts Directory

Organized collection of utility, testing, and analysis scripts.

---

## 📂 Directory Structure

```
scripts/
├── utilities/     # Database setup, migrations, utilities
├── testing/       # Integration and component tests
├── analysis/      # Performance analysis and backtesting
├── label_trades.py    # Label trades for ML training
└── setup_supabase.py  # Initial Supabase setup
```

---

## 🔧 Utilities (scripts/utilities/)

Database setup, migrations, and maintenance scripts.

| Script | Purpose |
|--------|---------|
| `create_supabase_tables.py` | Create initial Supabase tables |
| `fix_rls_security.py` | Fix Row Level Security policies |
| `run_migration.py` | Run database migrations |
| `setup_database.py` | Complete database setup |
| `populate_historical_trades.py` | Populate historical trading data |

**Usage:**
```bash
# After setting up .env, run initial setup:
python scripts/utilities/setup_database.py
```

---

## 🧪 Testing (scripts/testing/)

Component and integration tests.

| Script | Purpose |
|--------|---------|
| `test_integration.py` | Full system integration test |
| `test_correlation_monitor.py` | Test portfolio correlation logic |
| `test_sentiment_tracker.py` | Test sentiment analysis |
| `test_market_adapter.py` | Test market data adapter |
| `test_alpha_vantage.py` | Test Alpha Vantage API client |
| `test_llm_comparison.py` | Compare LLM providers |

**Usage:**
```bash
# Run specific test:
python scripts/testing/test_integration.py

# Or use pytest for all tests:
pytest tests/
```

---

## 📊 Analysis (scripts/analysis/)

Performance analysis and strategy backtesting.

| Script | Purpose |
|--------|---------|
| `analyze_strategy_performance.py` | Analyze strategy performance metrics |
| `backtest_simple.py` | Simple backtesting framework |
| `performance_comparison.py` | Compare strategy performance |

**Usage:**
```bash
# Analyze performance:
python scripts/analysis/analyze_strategy_performance.py

# Run backtest:
python scripts/analysis/backtest_simple.py --start 2024-01-01 --end 2024-12-31
```

---

## 🚀 Root-Level Scripts (Frequently Used)

These remain in the project root for easy access:

| Script | Purpose |
|--------|---------|
| `test_orchestrator.py` | **Test AI Orchestrator** (NEW!) |
| `run_optimizer.py` | Run adaptive parameter optimization |
| `check_positions.py` | Quick portfolio status check |
| `check_status.py` | System status check |
| `run_trading_background.py` | Run trading in background |
| `run_scheduled_trading.py` | Scheduled trading execution |

**Usage:**
```bash
# Test orchestrator (after implementing it):
python test_orchestrator.py

# Optimize parameters:
python run_optimizer.py --strategy momentum --lookback 30

# Check current positions:
python check_positions.py
```

---

## 📝 Notes

- All scripts assume `.env` is configured
- Scripts use relative imports from `src/`
- For production, use Docker/Podman scripts instead
