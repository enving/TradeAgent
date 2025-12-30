#!/bin/bash
# Setup script for Raspberry Pi - Run this ONCE on the Pi to enable auto-updates
# Usage: ssh recovery@raspberrypi.local 'bash -s' < scripts/setup_pi_auto_update.sh

set -e

echo "=========================================="
echo "Setting up Auto-Update on Raspberry Pi"
echo "=========================================="

REPO_DIR="/home/recovery/tradeagent"
CRON_SCHEDULE="*/5 * * * *"  # Every 5 minutes

cd "$REPO_DIR"

# Make auto-update script executable
chmod +x scripts/pi_auto_update.sh

# Create logs directory
mkdir -p logs

# Setup cron job
(crontab -l 2>/dev/null | grep -v "pi_auto_update.sh"; echo "$CRON_SCHEDULE cd $REPO_DIR && ./scripts/pi_auto_update.sh >> logs/cron.log 2>&1") | crontab -

echo ""
echo "✅ Auto-update configured!"
echo ""
echo "Configuration:"
echo "  - Checks for updates every 5 minutes"
echo "  - Logs to: $REPO_DIR/logs/auto_update.log"
echo "  - Cron logs: $REPO_DIR/logs/cron.log"
echo ""
echo "To view logs:"
echo "  tail -f $REPO_DIR/logs/auto_update.log"
echo ""
echo "To manually trigger update:"
echo "  cd $REPO_DIR && ./scripts/pi_auto_update.sh"
echo ""
echo "To disable auto-update:"
echo "  crontab -l | grep -v 'pi_auto_update.sh' | crontab -"
echo ""
