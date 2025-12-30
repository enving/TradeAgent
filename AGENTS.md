# Agent Development Guide

This document contains important information for AI agents working on this project.

## SSH Access to Raspberry Pi

**Connection:**
```bash
ssh recovery@raspberrypi.local
```

**Credentials:**
- Username: `recovery`
- Password: `raspberry` (stored in `.env`)

**Project Directory:**
```bash
/home/recovery/tradeagent
```

## Environment Variables

Located in `.env` file (NOT committed to git):

### Alpaca Trading
- `ALPACA_API_KEY` - Alpaca trading API key
- `ALPACA_SECRET_KEY` - Alpaca secret key
- `ALPACA_BASE_URL` - Paper trading: `https://paper-api.alpaca.markets`

### Supabase Database
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase service/anon key

### LLM Providers
- `IONOS_API_KEY` - IONOS AI API key
- `OPENROUTER_API_KEY` - OpenRouter API key (fallback)

### News APIs
- `NEWSAPI_KEY` - NewsAPI.org key
- `ALPHAVANTAGE_API_KEY` - Alpha Vantage API key

### Raspberry Pi
- `user_name=recovery`
- `user_pw=raspberry`

## Critical Bugs Fixed

### 2025-12-30: STRATEGY_PARAMS Error

**Problem:** Exit checks were failing with `name 'STRATEGY_PARAMS' is not defined`

**Root Cause:** In `src/strategies/momentum_trading.py`, the `check_exit_conditions()` function referenced a global `STRATEGY_PARAMS` dict that no longer exists. Parameters are now managed by `StrategyParametersManager`.

**Fix Applied:**
```python
# OLD (broken):
if pnl_pct <= Decimal(str(-STRATEGY_PARAMS["stop_loss_pct"])):

# NEW (fixed):
params_manager = get_strategy_parameters()
params = await params_manager.get_parameters("momentum")
if pnl_pct <= Decimal(str(-params["stop_loss_pct"])):
```

**Files Changed:**
- `src/strategies/momentum_trading.py:check_exit_conditions()` - Added parameter loading
- `src/strategies/momentum_trading.py:update_strategy_parameters()` - Deprecated
- `src/strategies/momentum_trading.py:get_current_parameters()` - Deprecated

**Impact:** Stop-loss and take-profit orders now work correctly during market hours.

## Database Schema Issues

### Missing Tables

The following tables may need to be created manually in Supabase:

1. **orchestrator_decisions** - AI orchestrator decision log
   - Run: `database/create_orchestrator_table.sql`

2. **news_articles** - News article archive (usually auto-created)
3. **llm_analysis_log** - LLM sentiment analysis log (usually auto-created)

**Quick Fix:**
Run `database/complete_schema.sql` in Supabase SQL Editor to create all tables.

### Parameter Changes Table Issue

**Error:** `column parameter_changes.date does not exist`

**Cause:** Schema mismatch - table uses `changed_at` not `date`

**Fix:** Update queries to use correct column name:
```python
# Correct column names:
- changed_at (TIMESTAMPTZ)
- created_at (TIMESTAMPTZ)
```

## Deployment Process

### Current Setup (Auto-Update via Cron)

The Raspberry Pi automatically pulls updates every 5 minutes:

1. **Developer workflow:**
   ```bash
   # Make changes locally
   git add .
   git commit -m "fix: description"
   git push
   # Pi auto-updates within 5 minutes
   ```

2. **Auto-update script:** `scripts/pi_auto_update.sh`
   - Runs via cron every 5 minutes
   - Pulls latest from `main` branch
   - Restarts service if code changed
   - Updates dependencies if `requirements.txt` changed

3. **Setup on new Pi:**
   ```bash
   ssh recovery@raspberrypi.local
   cd ~/tradeagent
   ./scripts/setup_pi_auto_update.sh
   ```

### Manual Deployment (Fallback)

If auto-update fails, manually update:
```bash
ssh recovery@raspberrypi.local
cd ~/tradeagent
git pull
source venv/bin/activate
pip install -r requirements.txt
pkill -f "python.*event_driven_service"
nohup python -m src.event_driven_service > logs/service.log 2>&1 &
```

## Service Management

### Check Status
```bash
ssh recovery@raspberrypi.local "pgrep -f 'python.*event_driven_service' && echo 'Running' || echo 'Stopped'"
```

### View Logs
```bash
# Trading logs
ssh recovery@raspberrypi.local "tail -f ~/tradeagent/logs/trading.log"

# Auto-update logs
ssh recovery@raspberrypi.local "tail -f ~/tradeagent/logs/auto_update.log"

# Service output
ssh recovery@raspberrypi.local "tail -f ~/tradeagent/logs/service.log"
```

### Restart Service
```bash
ssh recovery@raspberrypi.local "cd ~/tradeagent && pkill -f python && source venv/bin/activate && nohup python -m src.event_driven_service > logs/service.log 2>&1 &"
```

## Testing Locally

### Run Full Service
```bash
source venv/bin/activate
python -m src.event_driven_service
```

### Run Specific Components
```bash
# Test momentum strategy
python -c "from src.strategies.momentum_trading import scan_for_signals; import asyncio; asyncio.run(scan_for_signals(alpaca_client))"

# Test Supabase connection
python -c "from supabase import create_client; import os; from dotenv import load_dotenv; load_dotenv(); client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY')); print(client.table('trades').select('*').limit(1).execute())"
```

## Common Issues

### 1. SSH Connection Fails
```bash
# Check Pi is reachable
ping raspberrypi.local

# Try IP address instead
ssh recovery@192.168.178.69
```

### 2. Service Not Running
```bash
# Check logs for errors
ssh recovery@raspberrypi.local "tail -100 ~/tradeagent/logs/trading.log"

# Restart manually
ssh recovery@raspberrypi.local "cd ~/tradeagent && ./scripts/pi_auto_update.sh"
```

### 3. Git Pull Fails
```bash
# Reset to remote (CAUTION: Loses local changes)
ssh recovery@raspberrypi.local "cd ~/tradeagent && cp .env .env.backup && git reset --hard origin/main && mv .env.backup .env"
```

### 4. Supabase Connection Errors
- Check SUPABASE_URL and SUPABASE_KEY in `.env`
- Verify tables exist in Supabase dashboard
- Run `database/complete_schema.sql` if tables missing

## Code Structure

### Key Files
- `src/event_driven_service.py` - Main service entry point
- `src/strategies/momentum_trading.py` - Momentum trading strategy
- `src/strategies/news_sentiment.py` - News-driven trading
- `src/orchestrator/ai_orchestrator.py` - AI decision orchestrator
- `src/risk/position_sizer.py` - Position sizing logic
- `src/config/strategy_params.py` - Strategy parameter manager

### Configuration
- `.env` - API keys and credentials (NOT in git)
- `config/config.yaml` - Trading parameters
- `database/*.sql` - Database schema files

## Best Practices

1. **Always test locally** before pushing to main
2. **Never commit .env** - Contains sensitive API keys
3. **Check logs after deployment** - Verify service started correctly
4. **Use descriptive commit messages** - Makes debugging easier
5. **Document parameter changes** - Update config files and docs

## Debugging Tips

1. **Check service status first:**
   ```bash
   ssh recovery@raspberrypi.local "pgrep -f python && echo 'Running'"
   ```

2. **Read logs from bottom up** - Latest errors are at the end
3. **Test database queries** - Many errors are Supabase schema issues
4. **Verify API keys** - Check rate limits and validity
5. **Monitor resource usage** - Pi has limited CPU/RAM

## Rate Limits

### APIs with Free Tier Limits
- **NewsAPI:** 100 requests/24h (currently rate-limited)
- **Alpha Vantage:** 25 requests/day (for technical data)
- **Yahoo Finance:** HTTP 429 errors indicate rate limiting

### Solutions
- Use local caching
- Reduce polling frequency
- Switch to paid tiers for production
- Use multiple API keys with rotation

## Git Workflow

```bash
# Feature development
git checkout -b fix/issue-description
# ... make changes ...
git add .
git commit -m "fix: description of fix"
git push origin fix/issue-description
# Create PR, review, merge to main
# Pi auto-updates from main within 5 min
```

## Architecture Notes

### Event-Driven Design
- Multi-frequency scheduler (5min exits, hourly scans)
- Real-time WebSocket feeds for market data
- RSS news monitoring
- Async/await throughout

### Strategy System
- Momentum: Technical breakouts (RSI, MACD, volume)
- News Sentiment: LLM analysis of news articles
- Defensive: Rebalancing with safe assets (GLD, VTI, VGK)

### Risk Management
- Kelly criterion position sizing
- Dynamic stop-loss/take-profit
- Maximum 5 concurrent positions
- Correlation-based filtering

## Useful Commands

```bash
# View all running Python processes on Pi
ssh recovery@raspberrypi.local "ps aux | grep python"

# Check disk space
ssh recovery@raspberrypi.local "df -h"

# View cron jobs
ssh recovery@raspberrypi.local "crontab -l"

# Tail multiple logs
ssh recovery@raspberrypi.local "tail -f ~/tradeagent/logs/*.log"
```

## Emergency Procedures

### Stop Trading Immediately
```bash
ssh recovery@raspberrypi.local "pkill -9 -f 'python.*event_driven_service'"
```

### Disable Auto-Update
```bash
ssh recovery@raspberrypi.local "crontab -r"
```

### Rollback to Previous Version
```bash
ssh recovery@raspberrypi.local "cd ~/tradeagent && git reset --hard HEAD~1"
```

---

**Last Updated:** 2025-12-30
**Maintainer:** AI Agent / Developer
