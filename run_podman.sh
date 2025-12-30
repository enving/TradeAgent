#!/bin/bash
# Quick Podman run script for TradeAgent

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🦭 TradeAgent Podman Launcher${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}   Please create .env from .env.example and add your API keys${NC}"
    exit 1
fi

# Check if Podman is running/installed
if ! podman info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Podman is not running or not installed${NC}"
    exit 1
fi

# Check if podman-compose is installed
if ! command -v podman-compose &> /dev/null; then
    echo -e "${RED}❌ Error: podman-compose is not installed${NC}"
    echo -e "${YELLOW}   Please install podman-compose${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Podman is ready${NC}"
echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Parse command line arguments
MODE=${1:-"once"}

case $MODE in
    "once")
        echo -e "${YELLOW}🚀 Running TradeAgent once (no scheduler)${NC}"
        podman-compose run --rm tradeagent
        ;;
    "schedule")
        echo -e "${YELLOW}📅 Starting TradeAgent with scheduler (daily at 9:35 AM ET)${NC}"
        podman-compose up -d
        echo ""
        echo -e "${GREEN}✅ TradeAgent scheduler started!${NC}"
        echo -e "${YELLOW}   Logs: podman-compose logs -f${NC}"
        echo -e "${YELLOW}   Stop: podman-compose down${NC}"
        ;;
    "build")
        echo -e "${YELLOW}🔨 Building Podman image${NC}"
        if podman-compose build; then
            echo -e "${GREEN}✅ Build complete!${NC}"
        else
            echo -e "${RED}❌ Build failed!${NC}"
            exit 1
        fi
        ;;
    "stop")
        echo -e "${YELLOW}🛑 Stopping TradeAgent${NC}"
        podman-compose down
        echo -e "${GREEN}✅ TradeAgent stopped${NC}"
        ;;
    "logs")
        echo -e "${YELLOW}📋 Showing logs (Ctrl+C to exit)${NC}"
        podman-compose logs -f
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $MODE${NC}"
        echo ""
        echo "Usage: $0 [once|schedule|build|stop|logs]"
        echo ""
        echo "Commands:"
        echo "  once     - Run trading bot once (default)"
        echo "  schedule - Start scheduler for daily execution at 9:35 AM ET"
        echo "  build    - Build Podman image"
        echo "  stop     - Stop scheduler"
        echo "  logs     - Show logs"
        exit 1
        ;;
esac
