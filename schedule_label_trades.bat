@echo off
REM Daily ML Trade Labeling (18:00 Berlin / 12:00 PM ET)
REM Labels trades from 7/14/30 days ago for ML training

cd /d "C:\Users\t.wilms\Documents\german_ai_cookbook\german_ai_cookbook\projects\TradeAgent"
.venv\Scripts\python.exe scripts\label_trades.py >> logs\labeling.log 2>&1
