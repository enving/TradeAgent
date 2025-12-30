# Event-Driven Trading Architecture

## Overview

TradeAgent now operates as a **hybrid event-driven system** that combines:
1. **Multi-frequency scheduled scans** (5x daily)
2. **Real-time market monitoring** (WebSocket price/volume alerts)
3. **Breaking news monitoring** (RSS feeds)

This architecture allows the bot to react immediately to market opportunities instead of waiting for the next scheduled scan.

---

## Trading Frequencies

### Entry Scans (5x Daily)
```
09:35 ET - Gap & Morning Momentum
10:30 ET - Post-Open Continuation
12:00 ET - Midday Breakouts
14:00 ET - Afternoon Setup
15:45 ET - Power Hour Momentum
```

### Exit Monitoring
```
Every 5 minutes during market hours (9:30-16:00 ET)
```

---

## Real-Time Event Triggers

### 1. Price Momentum Alerts
**Trigger:** >2% price movement in 5 minutes
**Action:** Immediate entry scan for ticker

### 2. Volume Spike Alerts
**Trigger:** Volume >3x 20-bar average
**Action:** Immediate entry scan for ticker

### 3. Breaking News Alerts
**Trigger:** High-impact news on watchlist ticker
**Keywords:** earnings, upgrade, downgrade, acquisition, FDA approval, etc.
**Action:** Immediate entry scan for ticker

---

## Monitored Tickers

**Real-time monitoring active for:**
- Mega Caps: AAPL, MSFT, NVDA, GOOGL, META, AMZN, TSLA
- High Momentum: AMD, PLTR, SNOW, CRWD, NET, DDOG, SQ
- Volatility Plays: SHOP, RBLX, U, DASH

---

## RSS News Sources

- Yahoo Finance
- Benzinga
- MarketWatch
- Seeking Alpha

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│         Event-Driven Trading Service                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐│
│  │  Scheduler  │  │  WebSocket  │  │ RSS Monitor││
│  │  (5x daily) │  │ (Real-time) │  │  (News)    ││
│  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘│
│         │                │                │       │
│         └────────────────┴────────────────┘       │
│                          │                        │
│                    ┌─────▼─────┐                  │
│                    │  Trading  │                  │
│                    │   Loop    │                  │
│                    └───────────┘                  │
└─────────────────────────────────────────────────────┘
```

**Flow:**
1. **Scheduled scans** run at fixed times (time-based)
2. **Real-time alerts** detect rapid price/volume changes (event-based)
3. **News monitor** detects breaking news (event-based)
4. All triggers → Execute trading loop for relevant ticker

---

## Usage

### Run Event-Driven Service

**Docker/Podman (Recommended):**
```bash
./run_podman.sh schedule
```

**Manual:**
```bash
python -m src.event_driven_service
```

### Configuration

Enable/disable real-time monitoring in `.env`:
```bash
ENABLE_LLM_FEATURES=true  # Enables WebSocket + RSS monitoring
```

### Monitoring Logs

```bash
# Docker
docker-compose logs -f

# Podman
podman-compose logs -f

# Local
tail -f logs/trading.log
```

---

## Benefits vs. Previous System

| Feature | Before | After |
|---------|--------|-------|
| **Entry Frequency** | 1x/day (9:35 AM) | 5x/day + event-driven |
| **Exit Monitoring** | None | Every 5 minutes |
| **News Reaction** | Next day | Immediate (<60s) |
| **Price Alerts** | None | Real-time (<5s) |
| **Volume Detection** | Daily scan | Real-time |

---

## API Rate Limits

**Alpaca Free Tier:**
- REST API: 200 requests/minute
- WebSocket: Unlimited (IEX feed)

**RSS Feeds:**
- No rate limits (public feeds)
- Polled every 60 seconds

**Estimated Daily Usage:**
- Scheduled scans: ~5 requests/scan × 5 scans = 25 requests
- Exit monitoring: ~5 requests × 78 checks = 390 requests
- Event-triggered scans: Variable (0-50)
- **Total: ~400-500 requests/day** ✓ Well within limits

---

## Future Enhancements

1. **WebHook Endpoint** - TradingView alerts integration
2. **Discord Bot** - Manual trade triggers via Discord
3. **Pre-Market Scanning** - 8:00-9:30 AM ET gap detection
4. **After-Hours Monitoring** - Extended hours trading

---

## Troubleshooting

**WebSocket not connecting?**
- Check Alpaca API keys in `.env`
- Verify `ENABLE_LLM_FEATURES=true`
- Free tier uses IEX feed (not SIP)

**RSS feeds not working?**
- Check internet connectivity
- Some feeds may be rate-limited
- Monitor logs for HTTP errors

**Too many scans?**
- Adjust `EXIT_MONITORING_INTERVAL` in `scheduler_service.py`
- Reduce monitored tickers in `event_driven_service.py`
