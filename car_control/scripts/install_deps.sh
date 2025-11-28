#!/bin/bash

# ========================================
# Installation des dépendances
# ========================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "========================================"
echo "📦 INSTALLATION DES DÉPENDANCES"
echo "========================================"
echo ""

# Mise à jour du système
echo -e "${BLUE}1⃣  Mise à jour du système...${NC}"
sudo apt-get update

# Installation des paquets système
echo ""
echo -e "${BLUE}2⃣  Installation des paquets système...${NC}"
sudo apt-get install -y python3-pip python3-dev python3-yaml

# Installation des dépendances Python
echo ""
echo -e "${BLUE}3⃣  Installation des dépendances Python...${NC}"
pip3 install -r requirements.txt

# Vérification
echo ""
echo -e "${BLUE}4⃣  Vérification...${NC}"
python3 -c "import yaml, flask, flask_socketio, gpiozero, requests" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Toutes les dépendances sont installées${NC}"
else
    echo -e "${RED}❌ Erreur lors de l'installation${NC}"
    exit 1
fi

echo ""
echo "========================================"
echo -e "${GREEN}✅ INSTALLATION TERMINÉE${NC}"
echo "========================================"
echo ""
echo "Pour démarrer le robot:"
echo "  ./scripts/start.sh"
