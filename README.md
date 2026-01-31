# 🤖 TradeAgent - AI-Powered Algorithmic Trading System

[![TradeAgent CI](https://github.com/enving/TradeAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/enving/TradeAgent/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🤖 For AI Agents

**Bootstrap Instructions:**
If you are an AI agent (Claude, GPT, etc.) working on this repository, start here:

1.  **Read Context:** `cat AGENTS.md`
2.  **Verify Environment:** `python3 scripts/agent_health_check.py`
3.  **Run Tests:** `pytest` (Unit) or `python3 scripts/testing/test_integration.py` (Integration)

---

**TradeAgent** is a production-ready hybrid AI trading system that combines deterministic technical analysis with LLM-powered sentiment analysis. Built for Alpaca's paper trading API, it features adaptive parameter optimization, portfolio correlation monitoring, and comprehensive risk management.

## ✨ Key Features

### 🧠 **Intelligent Strategies**
- **Momentum Trading**: RSI, MACD, volume-based signals with dynamic thresholds
- **News Sentiment Analysis**: Claude 3.5 Sonnet analyzes 90+ articles per ticker
- **Sentiment Trend Tracker**: Detects sentiment momentum shifts and inflection points
- **Defensive Core**: Monthly rebalancing of VTI/VGK/GLD allocation

### 📊 **Adaptive & Self-Learning**
- **Adaptive Parameter Optimizer**: Grid search optimization based on rolling 30-day performance
- **ML Training Pipeline**: Collects labeled data for future ensemble models
- **Performance Analytics**: Daily & weekly reports with Sharpe ratio tracking

### 🛡️ **Risk Management**
- **Portfolio Correlation Monitor**: Blocks over-concentrated positions (max 40% per sector)
- **Dynamic Position Sizing**: Kelly Criterion with half-Kelly safety (3-15% per position)
- **Circuit Breakers**: -3% daily loss limit, automatic trading halt
- **Stop-Loss & Take-Profit**: Bracket orders on all momentum entries

### 🗄️ **Data Infrastructure**
- **Multi-Source News**: Yahoo Finance, Finnhub, Alpha Vantage, NewsAPI
- **Persistent Logging**: All trades, signals, and LLM analyses stored in Supabase
- **Complete Audit Trail**: Track parameter changes, performance metrics, reasoning

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Alpaca Paper Trading Account** ([Sign up](https://alpaca.markets/))
- **Supabase Account** ([Sign up](https://supabase.com/))
- **OpenRouter API Key** ([Sign up](https://openrouter.ai/)) (optional, for LLM features)

### Installation

1. **Clone the repository**
\`\`\`bash
git clone https://github.com/enving/TradeAgent.git
cd TradeAgent
\`\`\`

2. **Create virtual environment**
\`\`\`bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
\`\`\`

3. **Install dependencies**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

4. **Configure environment variables**
\`\`\`bash
cp .env.example .env
# Edit .env with your API keys
\`\`\`

Required variables:
\`\`\`env
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
\`\`\`

Optional (for LLM features):
\`\`\`env
OPENROUTER_API_KEY=your_openrouter_key
NEWS_API_KEY=your_newsapi_key
FINNHUB_API_KEY=your_finnhub_key
ENABLE_LLM_FEATURES=true
\`\`\`

5. **Set up Supabase database**

Run these SQL migrations in your Supabase SQL Editor (in order):
1. `database/migrations/create_ml_training_data.sql`
2. `database/migrations/add_news_and_llm_logging_v2.sql`
3. `database/migrations/add_parameter_changes.sql`

6. **Test the installation**
\`\`\`bash
python3 test_integration.py
\`\`\`

---

## 🐳 Docker Deployment (Recommended for Production)

**Run the bot autonomously with automated scheduling!**

### Quick Start

\`\`\`bash
# 1. Build Docker image
./run_docker.sh build

# 2. Test run once
./run_docker.sh once

# 3. Start daily scheduler (runs at 9:35 AM ET on weekdays)
./run_docker.sh schedule

# 4. Monitor logs
./run_docker.sh logs

# 5. Stop scheduler
./run_docker.sh stop
\`\`\`

### 🦭 Podman Support (Rootless)

If you prefer Podman (no root privileges required), use `run_podman.sh`:

```bash
# 1. Build and run once
./run_podman.sh build
./run_podman.sh once

# 2. Start scheduler
./run_podman.sh schedule
```
\`\`

### What You Get

- ✅ **Autonomous operation** - Runs daily at 9:35 AM ET automatically
- ✅ **Isolated environment** - No dependency conflicts
- ✅ **Auto-restart** - Recovers from failures automatically
- ✅ **Cross-platform** - Works on Linux, macOS, Windows
- ✅ **Easy updates** - \`git pull && ./run_docker.sh build\`

### Alternative Deployment Options

For native Linux deployment or cron-based scheduling, see detailed guide:
- **[deployment/README.md](deployment/README.md)** - Full deployment guide with SystemD and Cron options

---

## 📖 Usage

### Run Daily Trading Loop

\`\`\`bash
python3 -m src.main
\`\`\`

The bot will:
1. Check market hours
2. Scan for momentum signals (15 tickers)
3. Analyze news sentiment (if LLM enabled)
4. Apply risk filters (correlation, sector limits)
5. Execute trades with bracket orders
6. Monitor exit conditions for open positions
7. Log performance metrics to Supabase

### Pre-Market Orders

\`\`\`bash
python3 -c "import asyncio; from src.main import daily_trading_loop; asyncio.run(daily_trading_loop(allow_premarket=True))"
\`\`\`

### Optimize Strategy Parameters

After collecting 30+ trades:
\`\`\`bash
# Run adaptive optimizer
python3 run_optimizer.py --strategy momentum --lookback 30

# View current parameters
python3 run_optimizer.py --show
\`\`\`

### Test Components

\`\`\`bash
# Test correlation monitor
python3 test_correlation_monitor.py

# Test sentiment tracker
python3 test_sentiment_tracker.py
```

### Strategy Simulation
Test strategy behavior against historical and synthetic market scenarios:

```bash
# Run scenario simulation (Flash Crash, Market Gap, etc.)
python3 scripts/analysis/scenario_simulator.py

# Simulate historical sentiment based trading
python3 scripts/analysis/real_case_simulation.py
```

---

## 🏗️ Architecture

\`\`\`
TradeAgent/
├── src/
│   ├── strategies/         # Trading strategies
│   ├── risk/               # Risk management
│   ├── ml/                 # Machine learning
│   ├── llm/                # LLM integration
│   ├── core/               # Core logic
│   ├── adapters/           # External APIs
│   ├── models/             # Data models
│   └── database/           # Supabase client
├── database/migrations/    # SQL migrations
└── tests/                  # Tests
\`\`\`

---

## 📊 Trading Strategies

### 1. Momentum Strategy
**Entry:** RSI 45-75, MACD > 0, Volume > 1.1x avg  
**Exit:** Stop -3%, Target +8%, RSI > 80

### 2. News Sentiment (Optional)
**Entry:** Sentiment > 0.6, High impact, OR inflection detected  
Claude 3.5 Sonnet analyzes 90+ articles/ticker

### 3. Defensive Core
**Allocation:** 50% VTI, 30% VGK, 20% GLD  
**Rebalance:** Monthly, first trading day

---

## 🔬 Advanced Features

### Adaptive Parameter Optimization
Tests 27+ parameter combinations on 30-day performance, selects optimal Sharpe ratio.

### Sentiment Trend Tracker
Detects sentiment momentum via linear regression, blocks volatile signals.

### Portfolio Correlation Monitor
Prevents over-concentration: max 0.7 correlation, 40% sector limit.

---

## 🧪 Testing

\`\`\`bash
# Integration test
python3 test_integration.py

# Component tests
python3 test_correlation_monitor.py
python3 test_sentiment_tracker.py
\`\`\`

---

## ⚠️ Disclaimer

**Educational purposes only. Not financial advice.**

- Paper trading only
- No profitability guarantees
- Trading involves risk of loss
- Use at your own risk

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

**Built with ❤️ by algorithmic traders, for algorithmic traders.**
