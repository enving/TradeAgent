# TradeAgent Deployment Guide

Autonomous trading bot deployment options.

---

## 🐳 Option 1: Docker (Recommended)

**Best for:** Cross-platform deployment, easy updates, isolated environment

### Quick Start

```bash
# 1. Build and run once
./run_docker.sh build
./run_docker.sh once

# 2. Start with daily scheduler (9:35 AM ET)
./run_docker.sh schedule

# 3. View logs
./run_docker.sh logs

# 4. Stop scheduler
./run_docker.sh stop
```

### Docker Compose Commands

```bash
# Start scheduler (runs daily at 9:35 AM ET)
docker compose up -d

# View logs
docker compose logs -f

# Stop scheduler
docker compose down

# Rebuild after code changes
docker compose build
```

### Docker Advantages
- ✅ Cross-platform (Linux, macOS, Windows)
- ✅ Isolated environment (no conflicts)
- ✅ Easy updates (rebuild image)
- ✅ Resource limits (CPU, memory)
- ✅ Automatic restarts on failure

---

## 🐧 Option 2: SystemD (Linux Native)

**Best for:** Linux servers, system-level integration, native performance

### Installation

```bash
# 1. Install service and timer
cd /home/tristan/Repos/TradeAgent
sudo ./deployment/install_systemd.sh

# 2. Verify installation
sudo systemctl status tradeagent.timer
```

### SystemD Commands

```bash
# View timer status
sudo systemctl status tradeagent.timer

# View next scheduled run
systemctl list-timers tradeagent.timer

# View logs
sudo journalctl -u tradeagent -f

# Run immediately
sudo systemctl start tradeagent.service

# Stop timer
sudo systemctl stop tradeagent.timer

# Disable timer
sudo systemctl disable tradeagent.timer
```

### SystemD Advantages
- ✅ Native Linux integration
- ✅ System-level logging (journalctl)
- ✅ Automatic start on boot
- ✅ Better performance (no containerization overhead)
- ✅ Integrates with system monitoring

---

## 📅 Option 3: Cron (Simple)

**Best for:** Quick setup, minimal dependencies

### Installation

```bash
# 1. Open crontab
crontab -e

# 2. Add this line (runs at 9:35 AM ET on weekdays)
35 9 * * 1-5 cd /home/tristan/Repos/TradeAgent && /home/tristan/Repos/TradeAgent/venv_linux/bin/python -m src.main >> /home/tristan/Repos/TradeAgent/logs/cron.log 2>&1
```

### Cron Commands

```bash
# View crontab
crontab -l

# View logs
tail -f /home/tristan/Repos/TradeAgent/logs/cron.log

# Remove cron job
crontab -e  # Delete the line
```

### Cron Advantages
- ✅ Simplest setup
- ✅ No additional dependencies
- ✅ Works everywhere
- ❌ No automatic restarts
- ❌ Basic logging only

---

## ⚡ Comparison

| Feature | Docker | SystemD | Cron |
|---------|--------|---------|------|
| **Ease of Setup** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Cross-Platform** | ✅ Yes | ❌ Linux only | ✅ Yes |
| **Auto Restart** | ✅ Yes | ✅ Yes | ❌ No |
| **Resource Limits** | ✅ Yes | ✅ Yes | ❌ No |
| **Logging** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Updates** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **Performance** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation:**
- **Development:** Docker (easy testing, isolated)
- **Production Linux:** SystemD (native, reliable)
- **Quick Testing:** Cron (fastest setup)

---

## 🔧 Troubleshooting

### Docker Issues

**Problem:** Container exits immediately
```bash
# Check logs
docker compose logs tradeagent

# Run interactively
docker compose run --rm tradeagent bash
```

**Problem:** Permission denied
```bash
# Fix permissions
sudo chown -R $USER:$USER .
```

### SystemD Issues

**Problem:** Service fails to start
```bash
# Check status
sudo systemctl status tradeagent.service

# View detailed logs
sudo journalctl -u tradeagent -n 100 --no-pager
```

**Problem:** Timer not running
```bash
# Verify timer is enabled
systemctl is-enabled tradeagent.timer

# Check next run time
systemctl list-timers tradeagent.timer
```

### General Issues

**Problem:** Missing API keys
```bash
# Check .env file exists
cat .env

# Verify all required keys are set
grep -E "ALPACA|SUPABASE|OPENROUTER" .env
```

**Problem:** Python dependencies
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or rebuild Docker image
docker compose build --no-cache
```

---

## 📊 Monitoring

### Docker Monitoring

```bash
# Container stats
docker stats tradeagent-bot

# Health check
docker inspect tradeagent-bot | grep Health

# Follow logs
docker compose logs -f --tail=100
```

### SystemD Monitoring

```bash
# Service status
sudo systemctl status tradeagent

# Recent logs
sudo journalctl -u tradeagent -n 50

# Follow logs live
sudo journalctl -u tradeagent -f
```

### Cron Monitoring

```bash
# View cron log
tail -f logs/cron.log

# Check if cron is running
ps aux | grep cron
```

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] Set all environment variables in `.env`
- [ ] Test bot manually: `python -m src.main`
- [ ] Verify Supabase connection
- [ ] Verify Alpaca API works (paper trading)
- [ ] Check logs directory is writable
- [ ] Set correct timezone (ET for market hours)
- [ ] Configure resource limits (memory, CPU)
- [ ] Setup monitoring/alerts
- [ ] Test scheduler (run once before enabling daily)
- [ ] Backup `.env` file securely

---

## 📝 Updating Code

### Docker

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild image
docker compose build

# 3. Restart containers
docker compose down && docker compose up -d
```

### SystemD

```bash
# 1. Pull latest code
git pull origin main

# 2. Restart service (if running)
sudo systemctl restart tradeagent.timer

# No rebuild needed!
```

### Cron

```bash
# 1. Pull latest code
git pull origin main

# No restart needed - runs at next scheduled time
```

---

## 🔐 Security Notes

- **Never commit `.env`** → Contains API keys
- **Use paper trading first** → Test with fake money
- **Limit API permissions** → Read-only for market data
- **Monitor resource usage** → Prevent runaway processes
- **Backup database** → Export Supabase data regularly
- **Review logs daily** → Check for errors/anomalies

---

**Last Updated:** 2025-12-05
