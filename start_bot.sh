#!/bin/bash
# TradeAgent Background Runner
# Runs the trading bot and logs output

cd /home/tristan/Repos/TradeAgent

# Activate virtual environment
source venv_linux/bin/activate

# Run the bot
echo "=== TradeAgent Started at $(date) ===" >> logs/bot.log
python3 -m src.main >> logs/bot.log 2>&1
echo "=== TradeAgent Finished at $(date) ===" >> logs/bot.log
