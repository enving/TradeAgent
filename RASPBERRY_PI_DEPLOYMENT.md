# 🍓 Raspberry Pi Deployment Guide

Complete guide to deploy TradeAgent on Raspberry Pi for autonomous 24/7 trading.

---

## Prerequisites

- **Raspberry Pi 4** (4GB+ RAM recommended)
- **Raspberry Pi OS** (64-bit recommended)
- **SSH Access** enabled
- **Internet Connection**

---

## 🚀 Quick Deployment from Local Machine

### Step 1: Prepare Local Environment

```bash
# On your local machine (where you're developing):
cd /path/to/tradeagent

# Ensure all changes are committed
git add .
git commit -m "Latest updates with AI orchestrator"
git push origin main
```

### Step 2: SSH into Raspberry Pi

```bash
# From your local machine:
ssh recovery@<raspberry-pi-ip>
# Password: raspberry (from .env)

# Or use the automated script (if configured):
# Details in .env under #raspberry pi section
```

### Step 3: Clone/Update Repository on Pi

```bash
# On Raspberry Pi:
cd /home/recovery

# If first time:
git clone https://github.com/enving/TradeAgent.git
cd TradeAgent

# If updating:
cd TradeAgent
git pull origin main
```

### Step 4: Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys:
nano .env
```

**Required in .env:**
```bash
# Trading
ALPACA_API_KEY=pk_xxxxx
ALPACA_SECRET_KEY=xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx

# AI/LLM (IONOS - free for you!)
IONOS_API_KEY=your_ionos_key_here
IONOS_API_URL=https://openai.inference.de-txl.ionos.com/v1
IONOS_MODEL=openai/gpt-oss-120b
ENABLE_LLM_FEATURES=true

# News (optional but recommended)
FINNHUB_API_KEY=xxxxx
NEWS_API_KEY=xxxxx
```

### Step 5: Deploy with Podman (Recommended)

```bash
# Give execute permissions
chmod +x run_podman.sh

# Build container
./run_podman.sh build

# Test run once
./run_podman.sh once

# Check logs
./run_podman.sh logs

# If successful, start scheduler:
./run_podman.sh schedule
```

**The bot now runs autonomously at 9:35 AM ET every weekday! 🎉**

---

## 📊 Monitoring on Raspberry Pi

### View Logs (Real-time)

```bash
# Follow logs
./run_podman.sh logs

# Or directly:
tail -f logs/trading.log
```

### Check Status

```bash
# Activate venv
source venv/bin/activate

# Check current positions
python check_positions.py

# Check system status
python check_status.py
```

### View Orchestrator Decisions

```bash
# SSH into Raspberry Pi, then:
source venv/bin/activate

# Check latest orchestrator decisions (in Supabase)
# Or tail logs for orchestrator output:
grep "AI Orchestrator" logs/trading.log | tail -20
```

---

## 🔄 Updating the System

### Option 1: Quick Update (Git Pull)

```bash
# SSH into Raspberry Pi
ssh recovery@<pi-ip>

cd TradeAgent
git pull origin main

# Rebuild container
./run_podman.sh build

# Restart scheduler
./run_podman.sh stop
./run_podman.sh schedule
```

### Option 2: Manual File Transfer

```bash
# From your local machine:
scp -r src/ recovery@<pi-ip>:/home/recovery/TradeAgent/

# Then rebuild on Pi:
ssh recovery@<pi-ip>
cd TradeAgent
./run_podman.sh build
./run_podman.sh stop
./run_podman.sh schedule
```

---

## 🛠️ Troubleshooting

### Container Won't Start

```bash
# Check Podman status
podman ps -a

# View container logs
podman logs tradeagent-scheduler

# Remove stuck containers
podman rm -f tradeagent-scheduler
./run_podman.sh schedule
```

### Database Connection Issues

```bash
# Test Supabase connection:
source venv/bin/activate
python -c "import asyncio; from src.database.supabase_client import SupabaseClient; asyncio.run(SupabaseClient.get_instance())"

# Should print: "✓ Supabase client initialized"
```

### LLM Not Working

```bash
# Test IONOS connection:
source venv/bin/activate
python test_orchestrator.py

# Check logs for LLM provider:
grep "LLM_PROVIDER" logs/trading.log
# Should show: "provider=ionos"
```

### Trading Not Executing

```bash
# Check market hours:
python -c "import asyncio; from src.adapters.market_data_adapter import get_market_data_adapter; import datetime; asyncio.run((lambda: print('Market Open'))())"

# Check Alpaca connection:
python -c "import asyncio; from src.mcp_clients.alpaca_client import AlpacaMCPClient; asyncio.run(AlpacaMCPClient().get_account())"
```

---

## ⚡ Performance Optimization for Raspberry Pi

### Reduce Memory Usage

Edit `src/utils/config.py` to limit concurrent operations:

```python
# Add to config:
MAX_CONCURRENT_SCANS = 5  # Reduce from default 15
```

### Disable Optional Features

If Pi is struggling, disable optional features in `.env`:

```bash
ENABLE_NEWS_VERIFICATION=false  # Disable news verification
ENABLE_NEWS_SIGNALS=false       # Only use momentum strategy
```

### Use Swap Space (if needed)

```bash
# Increase swap for 4GB Pi:
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048

sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## 📈 Monitoring Performance

### System Resources

```bash
# Check CPU/Memory:
htop

# Check disk space:
df -h

# Check Podman stats:
podman stats tradeagent-scheduler
```

### Trading Performance

**View in Supabase:**
```sql
-- Daily performance
SELECT * FROM daily_performance ORDER BY date DESC LIMIT 7;

-- Win rate by strategy
SELECT strategy, COUNT(*) as trades,
       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
FROM trades
WHERE date > NOW() - INTERVAL '30 days'
GROUP BY strategy;

-- Orchestrator decisions
SELECT timestamp, decision_type, output_data
FROM orchestrator_decisions
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 🔐 Security Best Practices

### 1. Change Default Password

```bash
# On Raspberry Pi:
passwd recovery
# Enter new secure password
```

### 2. Set Up SSH Keys

```bash
# On your local machine:
ssh-keygen -t ed25519 -C "tradeagent-deploy"
ssh-copy-id recovery@<pi-ip>

# Now you can SSH without password!
```

### 3. Enable UFW Firewall

```bash
# On Raspberry Pi:
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### 4. Keep .env Secure

```bash
# On Raspberry Pi:
chmod 600 .env  # Only you can read
```

---

## 🔄 Automated Backup Strategy

### Backup Script

Create `backup_config.sh` on Pi:

```bash
#!/bin/bash
# Backup .env and logs weekly

BACKUP_DIR="/home/recovery/backups"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR
cp .env $BACKUP_DIR/.env.$DATE
cp -r logs/ $BACKUP_DIR/logs_$DATE/

# Keep only last 4 backups
ls -t $BACKUP_DIR/.env.* | tail -n +5 | xargs rm -f
ls -td $BACKUP_DIR/logs_*/ | tail -n +5 | xargs rm -rf
```

### Cron Job

```bash
# On Raspberry Pi:
crontab -e

# Add:
0 2 * * 0 /home/recovery/TradeAgent/backup_config.sh
# Runs every Sunday at 2 AM
```

---

## 📞 Remote Access

### Access from Anywhere

#### Option 1: Tailscale (Recommended)

```bash
# On Raspberry Pi:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Now access from anywhere using Tailscale IP!
ssh recovery@100.x.x.x
```

#### Option 2: Port Forwarding

Configure your router to forward port 22 to Raspberry Pi's local IP.

**⚠️ Warning:** Less secure, use SSH keys + Fail2Ban

---

## 🎯 Production Checklist

Before running real money (after paper trading success):

- [ ] Verified AI orchestrator is working (`test_orchestrator.py`)
- [ ] Tested for 2-3 weeks in paper trading
- [ ] Win rate > 55%
- [ ] Max drawdown < 10%
- [ ] Economic calendar integration verified
- [ ] All API keys secured
- [ ] Supabase backups enabled
- [ ] Monitoring alerts configured
- [ ] Emergency stop procedure documented

---

## 🆘 Emergency Stop

If you need to immediately stop trading:

```bash
# SSH into Raspberry Pi:
ssh recovery@<pi-ip>

# Stop the scheduler:
cd TradeAgent
./run_podman.sh stop

# OR kill all positions (if urgent):
source venv/bin/activate
python -c "import asyncio; from src.mcp_clients.alpaca_client import AlpacaMCPClient; asyncio.run(AlpacaMCPClient().close_all_positions())"
```

---

## 📚 Additional Resources

- **System Logs:** `/home/recovery/TradeAgent/logs/`
- **Container Logs:** `podman logs tradeagent-scheduler`
- **Supabase Dashboard:** https://supabase.com/dashboard
- **Alpaca Dashboard:** https://app.alpaca.markets/paper/dashboard/overview

---

## 🎉 You're All Set!

Your Raspberry Pi is now running an autonomous AI-powered trading bot!

**Next Steps:**
1. Monitor for 1 week
2. Review orchestrator decisions
3. Adjust parameters if needed
4. Scale up capital gradually

**Happy Trading! 🚀📈**
