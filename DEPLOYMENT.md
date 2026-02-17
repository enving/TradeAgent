# TradeAgent Deployment Guide

## Local Deployment (Docker & PostgreSQL)

The system is designed to run locally using Docker for the database and Python for the application.

### Prerequisites

- Docker Desktop (or Engine)
- Python 3.9+
- pip (Python package installer)

### 1. Database Setup

Start the PostgreSQL database using Docker Compose:

```bash
docker-compose up -d postgres
```

This starts a PostgreSQL instance on port 5432 with the following credentials (defined in `docker-compose.yml`):
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `trade_agent`

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and ensure the database URL matches your Docker setup:

```ini
POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/trade_agent
```

Add your Alpaca API keys:

```ini
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_PAPER=true
```

### 3. Application Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Initialize the database schema:

```bash
python3 scripts/setup_db.py
```

### 4. Running the Application

Check system health:

```bash
python3 scripts/agent_health_check.py
```

Run the main trading loop:

```bash
python3 -m src.main
```

## Monitoring

- **Database Logs**: `docker-compose logs -f postgres`
- **Application Logs**: Check the `logs/` directory.

## Troubleshooting

**Database Connection Failed?**
- Ensure Docker container is running: `docker ps`
- Check port 5432 availability.

**Missing Tables?**
- Run `python3 scripts/setup_db.py` to recreate the schema.
