#!/bin/bash
# Setup automated daily execution without Docker

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🤖 TradeAgent Automated Setup${NC}"
echo ""

# Create logs directory
mkdir -p /home/tristan/Repos/TradeAgent/logs
echo -e "${GREEN}✅ Logs directory created${NC}"

# Create start script
cat > /home/tristan/Repos/TradeAgent/start_bot.sh << 'EOF'
#!/bin/bash
cd /home/tristan/Repos/TradeAgent
source venv_linux/bin/activate
echo "=== TradeAgent Started at $(date) ===" >> logs/bot.log
python3 -m src.main >> logs/bot.log 2>&1
echo "=== TradeAgent Finished at $(date) ===" >> logs/bot.log
EOF

chmod +x /home/tristan/Repos/TradeAgent/start_bot.sh
echo -e "${GREEN}✅ Start script created${NC}"

# Setup cron job
(crontab -l 2>/dev/null | grep -v "TradeAgent"; echo "# TradeAgent - Daily trading bot (9:35 AM ET)"; echo "35 14 * * 1-5 /home/tristan/Repos/TradeAgent/start_bot.sh") | crontab -

echo -e "${GREEN}✅ Cron job installed!${NC}"
echo ""
echo -e "${YELLOW}Schedule: Monday-Friday at 9:35 AM ET (14:35 UTC)${NC}"
echo ""
echo "Installed cron job:"
crontab -l | grep -A1 "TradeAgent"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:      tail -f logs/bot.log"
echo "  Run manually:   ./start_bot.sh"
echo "  View crontab:   crontab -l"
echo "  Edit crontab:   crontab -e"
echo "  Test now:       ./start_bot.sh"
echo ""
echo -e "${GREEN}Setup complete! Bot will run automatically.${NC}"
