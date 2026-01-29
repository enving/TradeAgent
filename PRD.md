# Product Requirements Document (PRD) - TradeAgent

## Project Overview
**Project Name**: TradeAgent
**Version**: 1.1.0
**Last Updated**: 2026-01-17
**Owner**: Tristan Häfele
**LinkedIn**: https://de.linkedin.com/in/tristan-wilms-812b8011b

## Purpose & Vision
TradeAgent is a production-ready hybrid AI trading system that combines deterministic technical analysis with LLM-powered sentiment analysis. It aims to provide an autonomous, risk-managed trading solution that learns and adapts over time.

## Goals
### Primary Goals
- [x] Implement deterministic Momentum Strategy (RSI, MACD, Volume)
- [x] Integrate LLM-powered News Sentiment Analysis (Claude 3.5 Sonnet / IONOS)
- [x] Develop Adaptive Parameter Optimization (Grid Search)
- [x] Establish a robust Risk Management framework (Kelly Criterion, Correlation Monitor)
- [x] Deploy autonomously on Raspberry Pi with auto-update capability

### Success Metrics
- **Sharpe Ratio**: Positive risk-adjusted returns over a 30-day rolling window.
- **Uptime**: 99% during market hours.
- **Execution Accuracy**: Correct execution of stop-loss and take-profit orders.

## Target Users
**Primary Users**: Algorithmic traders and developers interested in hybrid AI trading.
**Secondary Users**: Researchers looking into sentiment-based market trends.

## Features & Requirements

### Core Features (MVP)
| Feature ID | Feature Name | Priority | Status | Description |
|------------|--------------|----------|--------|-------------|
| FEAT-001   | Momentum Strat| High     | Completed| Technical breakouts based on RSI, MACD, and Volume. |
| FEAT-002   | Sentiment Anal| High     | Completed| LLM analysis of news articles for trading signals. |
| FEAT-003   | Risk Manager | High     | Completed| Kelly sizing, stop-loss/take-profit, correlation filters. |
| FEAT-004   | Pi Deployment | High     | Completed| Automated deployment and service management on RPi. |

### Advanced Features
| Feature ID | Feature Name | Priority | Status | Description |
|------------|--------------|----------|--------|-------------|
| FEAT-005   | Adaptive Opt | Medium   | Completed| Weekly parameter optimization based on Sharpe ratio. |
| FEAT-006   | Remote Logs  | Medium   | Completed| System logging to Supabase for remote monitoring. |
| FEAT-007   | Circuit Break| High     | Completed| Daily loss limits and macro event detection. |
| FEAT-008   | Aggressive Mode| Medium   | Completed| High-growth mode (0.8 Kelly, 25% max pos) targeting 1% daily. |

## Technical Requirements

### Architecture
Event-driven system with multi-frequency scheduling, real-time WebSocket feeds, and persistent logging to Supabase.

### Tech Stack
- **Backend**: Python 3.12+ (Asyncio, Paramiko)
- **Database**: Supabase (PostgreSQL)
- **LLM**: IONOS (gpt-oss-120b) / OpenRouter (Claude 3.5 Sonnet)
- **Infrastructure**: Raspberry Pi 4/5, Docker/Podman

### Dependencies
```
alpaca-trade-api
supabase
paramiko
python-dotenv
yfinance
pandas
numpy
```

## User Stories
### Story 1: Autonomous Trading
**As a** trader
**I want** the system to scan, analyze, and trade without manual intervention
**So that** I can capture market opportunities 24/7.

## Implementation Phases
### Phase 1: Core System (v1.0)
- Momentum strategy and Alpaca integration.
- Basic risk management.

### Phase 2: AI & Optimization (v1.1)
- Sentiment analysis integration.
- Adaptive optimizer and remote monitoring.

---

**Document History**:
- v1.0.0 (2026-01-01): Initial release.
- v1.1.0 (2026-01-17): Updated with adaptive optimizer and remote monitoring features.
