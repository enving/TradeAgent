# TradeAgent Docker Container
# Autonomous trading bot that runs daily at market open

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env.example .env

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check (check if bot is responsive)
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s \
    CMD python -c "import sys; sys.exit(0)"

# Run the trading bot
CMD ["python", "-m", "src.main"]
