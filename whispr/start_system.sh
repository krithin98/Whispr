#!/bin/bash

# SPX ATR Analytics System - Single Startup Script
# This script starts all components of the comprehensive analytics system

echo "=========================================="
echo "🚀 SPX ATR ANALYTICS SYSTEM STARTUP"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
BASE_DIR="/opt/spx-atr/whispr"
cd $BASE_DIR

# Check if data directory exists
if [ ! -d "data" ]; then
    echo -e "${YELLOW}Creating data directory...${NC}"
    mkdir -p data
fi

# Function to check if process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo -e "${GREEN}✅ $2 is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $2 is not running${NC}"
        return 1
    fi
}

# Function to start a background service
start_service() {
    local script=$1
    local name=$2
    local log=$3

    echo -e "${YELLOW}Starting $name...${NC}"
    nohup python3 $script > $log 2>&1 &
    sleep 2

    if check_process "$script" "$name"; then
        echo -e "${GREEN}$name started successfully${NC}"
    else
        echo -e "${RED}Failed to start $name${NC}"
        echo "Check log at: $log"
    fi
}

echo "Step 1: Checking Database"
echo "-------------------------"
if [ -f "data/whispr.db" ]; then
    echo -e "${GREEN}✅ Database exists${NC}"
    # Get row count
    TICK_COUNT=$(sqlite3 data/whispr.db "SELECT COUNT(*) FROM spx_price_ticks WHERE DATE(timestamp) = DATE('now');" 2>/dev/null)
    echo "   Price ticks today: $TICK_COUNT"
else
    echo -e "${RED}❌ Database not found${NC}"
    echo "Creating database..."
    sqlite3 data/whispr.db < backend/create_tables.sql
fi

echo ""
echo "Step 2: Checking Authentication"
echo "-------------------------------"
if [ -f "backend/.schwab_tokens.json" ]; then
    # Check token expiry
    EXPIRY=$(python3 -c "
import json
from datetime import datetime, timezone
with open('backend/.schwab_tokens.json') as f:
    data = json.load(f)
    exp = datetime.fromisoformat(data['expires_at'])
    now = datetime.now(timezone.utc)
    mins = (exp - now).total_seconds() / 60
    print(f'{mins:.1f}')
" 2>/dev/null)

    if [ ! -z "$EXPIRY" ]; then
        if (( $(echo "$EXPIRY > 0" | bc -l) )); then
            echo -e "${GREEN}✅ Auth tokens valid (expires in ${EXPIRY} minutes)${NC}"
        else
            echo -e "${RED}❌ Auth tokens expired${NC}"
        fi
    fi
else
    echo -e "${RED}❌ No auth tokens found${NC}"
    echo "Run: python3 backend/quick_auth.py"
fi

echo ""
echo "Step 3: Starting Core Services"
echo "------------------------------"

# Kill existing processes
echo "Stopping any existing services..."
pkill -f production_collector.py 2>/dev/null
pkill -f auth_monitor.py 2>/dev/null
pkill -f realtime_movement_monitor.py 2>/dev/null
sleep 2

# Start production collector
start_service "production_collector.py" "Production Collector" "logs/collector.log"

# Start auth monitor
start_service "backend/auth_monitor.py" "Auth Monitor" "logs/auth_monitor.log"

echo ""
echo "Step 4: Populating ATR Levels"
echo "-----------------------------"
python3 populate_atr_levels.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ ATR levels populated${NC}"
else
    echo -e "${RED}❌ Failed to populate ATR levels${NC}"
fi

echo ""
echo "Step 5: Starting Analytics Dashboard"
echo "------------------------------------"
echo -e "${YELLOW}Starting Comprehensive Analytics Dashboard...${NC}"

# Check if streamlit is already running
if pgrep -f "streamlit run" > /dev/null; then
    echo "Stopping existing Streamlit instances..."
    pkill -f "streamlit run"
    sleep 2
fi

# Start the dashboard
echo ""
echo -e "${GREEN}🎯 Starting dashboard on http://localhost:8501${NC}"
echo ""
echo "=========================================="
echo -e "${GREEN}✅ SYSTEM STARTUP COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Dashboard URL: http://localhost:8501"
echo ""
echo "System Components:"
echo "  • Production Collector: Gathering SPX data"
echo "  • Auth Monitor: Managing token refresh"
echo "  • Analytics Dashboard: Real-time visualization"
echo ""
echo "Logs:"
echo "  • Collector: logs/collector.log"
echo "  • Auth: logs/auth_monitor.log"
echo ""
echo "To stop all services: ./stop_system.sh"
echo ""

# Start Streamlit in foreground
streamlit run comprehensive_analytics_dashboard.py