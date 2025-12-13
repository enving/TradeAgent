#!/bin/bash
# Install TradeAgent as SystemD service with timer

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🤖 TradeAgent SystemD Installer${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (sudo)${NC}"
    exit 1
fi

# Check if service files exist
if [ ! -f "deployment/tradeagent.service" ]; then
    echo -e "${RED}❌ Service file not found${NC}"
    exit 1
fi

if [ ! -f "deployment/tradeagent.timer" ]; then
    echo -e "${RED}❌ Timer file not found${NC}"
    exit 1
fi

# Create logs directory
echo -e "${YELLOW}📁 Creating logs directory${NC}"
mkdir -p /home/tristan/Repos/TradeAgent/logs
chown tristan:tristan /home/tristan/Repos/TradeAgent/logs

# Copy service and timer files
echo -e "${YELLOW}📋 Installing service files${NC}"
cp deployment/tradeagent.service /etc/systemd/system/
cp deployment/tradeagent.timer /etc/systemd/system/

# Reload systemd
echo -e "${YELLOW}🔄 Reloading systemd${NC}"
systemctl daemon-reload

# Enable timer
echo -e "${YELLOW}✅ Enabling timer${NC}"
systemctl enable tradeagent.timer

# Start timer
echo -e "${YELLOW}▶️  Starting timer${NC}"
systemctl start tradeagent.timer

# Show status
echo ""
echo -e "${GREEN}✅ TradeAgent SystemD service installed!${NC}"
echo ""
echo -e "${YELLOW}Status:${NC}"
systemctl status tradeagent.timer --no-pager
echo ""
echo -e "${YELLOW}Next scheduled run:${NC}"
systemctl list-timers tradeagent.timer --no-pager
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:    sudo journalctl -u tradeagent -f"
echo "  Stop timer:   sudo systemctl stop tradeagent.timer"
echo "  Disable:      sudo systemctl disable tradeagent.timer"
echo "  Run now:      sudo systemctl start tradeagent.service"
