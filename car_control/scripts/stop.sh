#!/bin/bash

# ========================================
# Script d'arrêt du robot
# ========================================

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🛑 Arrêt du système robot..."

if [ -f "logs/robot.pid" ]; then
    PIDS=$(cat logs/robot.pid)
    
    for PID in $PIDS; do
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null
            echo -e "${GREEN}✓${NC} Processus $PID arrêté"
        fi
    done
    
    rm -f logs/robot.pid
    echo -e "${GREEN}✅ Système arrêté${NC}"
else
    echo -e "${RED}❌ Aucun processus en cours trouvé${NC}"
    echo "Tentative d'arrêt forcé..."
    pkill -f "src.control_server"
    pkill -f "src.camera_proxy"
fi
