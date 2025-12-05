@echo off
REM Pre-Open Scan (15:00 Berlin / 9:00 AM ET)
REM Final check before market opens at 9:30 AM ET

cd /d "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"
.venv\Scripts\python.exe run_scheduled_trading.py pre-market >> logs\preopen_scan.log 2>&1
