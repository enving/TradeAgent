@echo off
REM Market Hours Scan (16:00 Berlin / 10:00 AM ET)
REM Runs during market hours for immediate execution

cd /d "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"
.venv\Scripts\python.exe run_scheduled_trading.py market >> logs\market_scan.log 2>&1
