#!/bin/bash
# Quick Docker run script for TradeAgent

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 TradeAgent Docker Launcher${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}   Please create .env from .env.example and add your API keys${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo -e "${YELLOW}   Please start Docker Desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Parse command line arguments
MODE=${1:-"once"}

case $MODE in
    "once")
        echo -e "${YELLOW}🚀 Running TradeAgent once (no scheduler)${NC}"
        docker compose run --rm tradeagent
        ;;
    "schedule")
        echo -e "${YELLOW}📅 Starting TradeAgent with scheduler (daily at 9:35 AM ET)${NC}"
        docker compose up -d
        echo ""
        echo -e "${GREEN}✅ TradeAgent scheduler started!${NC}"
        echo -e "${YELLOW}   Logs: docker compose logs -f${NC}"
        echo -e "${YELLOW}   Stop: docker compose down${NC}"
        ;;
    "build")
        echo -e "${YELLOW}🔨 Building Docker image${NC}"
        docker compose build
        echo -e "${GREEN}✅ Build complete!${NC}"
        ;;
    "stop")
        echo -e "${YELLOW}🛑 Stopping TradeAgent${NC}"
        docker compose down
        echo -e "${GREEN}✅ TradeAgent stopped${NC}"
        ;;
    "logs")
        echo -e "${YELLOW}📋 Showing logs (Ctrl+C to exit)${NC}"
        docker compose logs -f
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $MODE${NC}"
        echo ""
        echo "Usage: $0 [once|schedule|build|stop|logs]"
        echo ""
        echo "Commands:"
        echo "  once     - Run trading bot once (default)"
        echo "  schedule - Start scheduler for daily execution at 9:35 AM ET"
        echo "  build    - Build Docker image"
        echo "  stop     - Stop scheduler"
        echo "  logs     - Show logs"
        exit 1
        ;;
esac
