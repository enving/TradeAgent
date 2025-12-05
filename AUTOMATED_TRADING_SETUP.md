# Automated Trading System - Setup Guide

**Status:** ✅ Ready to deploy
**Last Updated:** 2025-11-20

---

## 🎯 Overview

This system runs **fully automated** trading with:
- **3 daily scans** (spread throughout the day)
- **Pre-market order placement** (executes at market open)
- **Alpha Vantage quota optimization** (25 requests/day)
- **ML data collection** (automatic labeling)

---

## 📅 Daily Schedule (Berlin Time)

| Time  | Task | Description | Alpha Vantage Requests |
|-------|------|-------------|----------------------|
| **07:00** | Morning Pre-Market Scan | Analyzes momentum, places orders for market open | ~10-12 |
| **15:00** | Pre-Open Scan | Final check before US market opens (9:30 AM ET) | ~10-12 |
| **16:00** | Market Hours Scan | During US market hours (10:00 AM ET) | ~0-2 (only for exits) |
| **18:00** | ML Trade Labeling | Labels trades from 7/14/30 days ago | 0 |

**Total Alpha Vantage Requests:** ~20-24 per day (within 25/day limit)

---

## ⚙️ Installation

### Step 1: Run PowerShell Setup Script

1. **Open PowerShell as Administrator:**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)"

2. **Navigate to project folder:**
   ```powershell
   cd "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"
   ```

3. **Allow script execution (if needed):**
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

4. **Run setup script:**
   ```powershell
   .\setup_scheduled_tasks.ps1
   ```

5. **Verify tasks created:**
   - Open **Task Scheduler** (search in Windows)
   - Look for tasks starting with `TradeAgent_`

---

## 📊 How It Works

### Morning Pre-Market Scan (7:00 AM)
```
1. Alpha Vantage: Fetch 60 days historical data for 10 tickers (~2 min)
2. Calculate RSI, MACD, Volume indicators
3. Find momentum signals (if criteria met)
4. Place MARKET orders → Execute at 9:30 AM ET (15:30 Berlin)
5. Log ML features for self-learning
```

### Pre-Open Scan (15:00 / 3:00 PM)
```
1. Alpha Vantage: Refresh data for 10 tickers
2. Final momentum check before market opens
3. Place additional orders (if signals found)
4. Update existing positions
```

### Market Hours Scan (16:00 / 4:00 PM)
```
1. Market is OPEN - immediate execution
2. Check exit conditions (stop-loss, take-profit)
3. Close positions if needed
4. No Alpha Vantage calls (uses Alpaca quotes)
```

### ML Trade Labeling (18:00 / 6:00 PM)
```
1. Find unlabeled trades from 7/14/30 days ago
2. Get current price from Alpaca
3. Calculate return %
4. Label as: profitable (>5%), unprofitable (<-2%), neutral
5. Update database for ML training
```

---

## 📝 Logs

Logs are saved to: `C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent\logs\`

- `morning_scan.log` - Pre-market scans (7:00 AM)
- `preopen_scan.log` - Pre-open scans (15:00)
- `market_scan.log` - Market hours scans (16:00)
- `labeling.log` - ML trade labeling (18:00)

**View logs:**
```powershell
Get-Content logs\morning_scan.log -Tail 50
```

---

## 🔧 Manual Testing

### Test Pre-Market Scan (without scheduling)
```bash
python run_scheduled_trading.py pre-market
```

### Test Market Hours Scan
```bash
python run_scheduled_trading.py market
```

### Test ML Labeling
```bash
python scripts\label_trades.py
```

---

## 🛑 Disable/Enable Tasks

### Disable all tasks
```powershell
Get-ScheduledTask -TaskName "TradeAgent_*" | Disable-ScheduledTask
```

### Enable all tasks
```powershell
Get-ScheduledTask -TaskName "TradeAgent_*" | Enable-ScheduledTask
```

### Remove all tasks
```powershell
Unregister-ScheduledTask -TaskName "TradeAgent_*" -Confirm:$false
```

---

## 📈 Alpha Vantage Quota Management

**Free Tier:** 25 requests per day

**Strategy:**
- Morning scan: 10 tickers = 10 requests
- Pre-open scan: 10 tickers = 10 requests
- Exit checks: ~2-4 requests
- **Total: ~22-24 requests** (within limit)

**If quota exceeded:**
- Morning scan will fail
- System logs error
- Trading continues with defensive core only
- Quota resets at midnight UTC

**Monitor quota:**
```bash
python test_alpha_vantage.py
```

---

## 🚀 Expected Behavior

### First Run (Today)
1. Tasks created in Task Scheduler
2. No execution until scheduled time
3. Tomorrow morning at 7:00 AM: First scan

### Daily Operation
```
07:00 - Pre-market scan → Orders placed
15:00 - Pre-open scan → Additional orders
15:30 - US market opens → Orders execute
16:00 - Market scan → Check positions
18:00 - ML labeling → Update database
22:00 - US market closes
```

### What Gets Traded
- **Defensive Core (50%):** VTI, VGK, GLD (monthly rebalancing only)
- **Momentum (30%):** Top signals from watchlist (AAPL, MSFT, NVDA, etc.)
- **Max positions:** 5 total
- **Max position size:** 10% of portfolio

---

## 🔍 Monitoring

### Check scheduled tasks
```powershell
Get-ScheduledTask -TaskName "TradeAgent_*" | Select-Object TaskName, State, LastRunTime, NextRunTime
```

### Check if tasks ran successfully
```powershell
Get-ScheduledTask -TaskName "TradeAgent_MorningScan" | Get-ScheduledTaskInfo
```

### View portfolio status
```bash
python check_positions.py
```

---

## ⚠️ Important Notes

1. **Computer must be ON** at scheduled times (tasks won't run if PC is off)
2. **Internet connection required** (for Alpaca/Alpha Vantage API calls)
3. **Paper trading only** (no real money at risk)
4. **Alpha Vantage quota:** 25 requests/day (enough for 2 full scans)
5. **Pre-market orders:** Placed as MARKET orders (execute at open price)

---

## 🛡️ Safety Features

- ✅ **Risk limits:** Max 5 positions, 10% position size
- ✅ **Stop-loss:** -5% automatic exit
- ✅ **Take-profit:** +15% automatic exit
- ✅ **Circuit breaker:** Halts trading if daily loss > 5%
- ✅ **ML logging:** Error-safe (doesn't break trading)
- ✅ **Market hours check:** Only trades when appropriate

---

## 📞 Troubleshooting

### Task doesn't run
1. Check Task Scheduler → Task History
2. Verify task is **Enabled**
3. Check logs in `logs/` folder
4. Ensure PC was ON at scheduled time

### Alpha Vantage quota exceeded
```
Error: "standard API rate limit is 25 requests per day"
Solution: Wait until midnight UTC, quota resets
```

### No momentum signals found
```
Normal behavior - momentum signals are rare
Defensive core continues working
Check logs for details
```

### Pre-market orders not executing
```
Check Alpaca order history
Market orders execute at next market open
May take a few minutes after 9:30 AM ET
```

---

## 🎯 Next Steps

1. ✅ Run `setup_scheduled_tasks.ps1` (install tasks)
2. ✅ Verify tasks in Task Scheduler
3. ✅ Wait for first scheduled run (tomorrow 7:00 AM)
4. ✅ Monitor logs after each run
5. ✅ Review portfolio daily: `python check_positions.py`

---

**Questions?** Check logs in `logs/` folder or review error messages in Task Scheduler history.
