#!/bin/bash

# Stop all SPX ATR Analytics System components

echo "=========================================="
echo "🛑 STOPPING SPX ATR ANALYTICS SYSTEM"
echo "=========================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping all services...${NC}"

# Stop services
services=(
    "streamlit run"
    "production_collector.py"
    "auth_monitor.py"
    "realtime_movement_monitor.py"
    "monitor_spx_flow.py"
)

for service in "${services[@]}"; do
    if pgrep -f "$service" > /dev/null; then
        echo -e "Stopping: $service"
        pkill -f "$service"
    fi
done

sleep 2

# Verify all stopped
all_stopped=true
for service in "${services[@]}"; do
    if pgrep -f "$service" > /dev/null; then
        echo -e "${RED}⚠️  $service still running${NC}"
        all_stopped=false
    fi
done

if $all_stopped; then
    echo ""
    echo -e "${GREEN}✅ All services stopped successfully${NC}"
else
    echo ""
    echo -e "${YELLOW}Some services may still be running${NC}"
    echo "Use 'ps aux | grep python' to check"
fi

echo ""
echo "=========================================="
echo "System shutdown complete"
echo "=========================================="