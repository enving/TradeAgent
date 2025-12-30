# TradeAgent Deployment Guide

## Raspberry Pi Auto-Update Setup

The Raspberry Pi automatically pulls updates from GitHub every 5 minutes and restarts the trading service when code changes are detected.

### Initial Setup (Run Once)

1. **Clone repository on Raspberry Pi:**
   ```bash
   ssh recovery@raspberrypi.local
   cd ~
   git clone https://github.com/YOUR_USERNAME/tradeagent.git
   cd tradeagent
   ```

2. **Setup Python environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your API keys
   ```

4. **Enable auto-update:**
   ```bash
   chmod +x scripts/setup_pi_auto_update.sh
   ./scripts/setup_pi_auto_update.sh
   ```

That's it! The Pi will now:
- Check for GitHub updates every 5 minutes
- Automatically pull new code
- Restart the trading service if files changed
- Update dependencies if `requirements.txt` changed

### Monitoring

**View auto-update logs:**
```bash
ssh recovery@raspberrypi.local
tail -f ~/tradeagent/logs/auto_update.log
```

**View trading logs:**
```bash
tail -f ~/tradeagent/logs/trading.log
```

**Check if service is running:**
```bash
pgrep -f "python.*event_driven_service" && echo "Running" || echo "Stopped"
```

### Manual Control

**Manually trigger update:**
```bash
cd ~/tradeagent
./scripts/pi_auto_update.sh
```

**Stop service:**
```bash
pkill -f "python.*event_driven_service"
```

**Start service manually:**
```bash
cd ~/tradeagent
source venv/bin/activate
nohup python -m src.event_driven_service > logs/service.log 2>&1 &
```

**Disable auto-update:**
```bash
crontab -l | grep -v 'pi_auto_update.sh' | crontab -
```

### Development Workflow

1. **Make changes on your development machine**
2. **Test locally:**
   ```bash
   source venv/bin/activate
   python -m src.event_driven_service
   ```
3. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
4. **Wait up to 5 minutes** - The Pi will automatically pull and restart

### Troubleshooting

**Auto-update not working?**
```bash
# Check cron is running
crontab -l

# Check cron logs
tail -f ~/tradeagent/logs/cron.log

# Manually test update script
cd ~/tradeagent
./scripts/pi_auto_update.sh
```

**Service crashes?**
```bash
# View service logs
tail -100 ~/tradeagent/logs/service.log

# View Python errors
tail -100 ~/tradeagent/logs/trading.log
```

**Git pull conflicts?**
```bash
# Reset local changes (CAUTION: This removes local modifications)
cd ~/tradeagent
cp .env .env.backup
git reset --hard origin/main
mv .env.backup .env
```

## Supabase Database Setup

### Missing Tables

If you see errors about missing tables (`orchestrator_decisions`, `news_articles`, `llm_analysis_log`), run:

1. Go to https://supabase.com/dashboard
2. Open your project
3. Click "SQL Editor"
4. Run `database/complete_schema.sql` OR
5. For just the orchestrator table: `database/create_orchestrator_table.sql`

### Connection Test

Test Supabase connection:
```bash
source venv/bin/activate
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
result = client.table('trades').select('*').limit(1).execute()
print('✅ Supabase connected successfully!')
"
```

## Security Notes

- **Never commit `.env` files** - They contain API keys
- **.env is excluded** from git sync and auto-update
- **Backup your .env** before major updates
- **Use service keys** for production, anon keys for development
