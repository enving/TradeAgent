@echo off
REM Morning Pre-Market Scan (7:00 AM Berlin)
REM Analyzes market and places orders for market open

cd /d "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"
.venv\Scripts\python.exe run_scheduled_trading.py pre-market >> logs\morning_scan.log 2>&1
