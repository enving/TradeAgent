#!/bin/bash
# Auto-update script for Raspberry Pi
# This script pulls latest changes from GitHub and restarts the service if needed
# Place this on the Pi and run it via cron every 5 minutes

set -e

REPO_DIR="/home/recovery/tradeagent"
LOG_FILE="/home/recovery/tradeagent/logs/auto_update.log"
BRANCH="main"

cd "$REPO_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Auto-update check started ==="

# Fetch latest changes
git fetch origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "✓ Already up to date (commit: ${LOCAL:0:7})"
    exit 0
fi

log "📥 Updates found! Pulling changes..."
log "   Local:  ${LOCAL:0:7}"
log "   Remote: ${REMOTE:0:7}"

# Backup .env before pull
cp .env .env.backup 2>/dev/null || log "No .env to backup"

# Pull changes
if git pull origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE"; then
    log "✅ Git pull successful"
else
    log "❌ Git pull failed"
    exit 1
fi

# Restore .env
mv .env.backup .env 2>/dev/null || log "No .env backup to restore"

# Update dependencies if requirements.txt changed
if git diff --name-only "$LOCAL" "$REMOTE" | grep -q "requirements.txt"; then
    log "📦 Requirements changed, updating dependencies..."
    source venv/bin/activate
    pip install -q -r requirements.txt 2>&1 | tee -a "$LOG_FILE"
    log "✅ Dependencies updated"
fi

# Check if service is running
if pgrep -f "python.*event_driven_service" > /dev/null; then
    log "🔄 Restarting service..."
    pkill -f "python.*event_driven_service" || true
    sleep 3
fi

# Start service
log "🚀 Starting service..."
source venv/bin/activate
nohup python -m src.event_driven_service > logs/service.log 2>&1 &
NEW_PID=$!

log "✅ Service started (PID: $NEW_PID)"
log "=== Auto-update completed successfully ==="
