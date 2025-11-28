#!/bin/bash

# ========================================
# Script de démarrage du robot
# ========================================

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Chemin du projet
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================"
echo "🤖 DÉMARRAGE DU SYSTÈME ROBOT"
echo "========================================"
echo ""

# Vérifier la configuration
if [ ! -f "config/config.yaml" ]; then
    echo -e "${RED}❌ Fichier config/config.yaml introuvable${NC}"
    if [ -f "config/config_example.yaml" ]; then
        echo -e "${YELLOW}💡 Copiez config_example.yaml vers config.yaml et configurez-le${NC}"
        echo -e "${YELLOW}   cp config/config_example.yaml config/config.yaml${NC}"
    fi
    exit 1
fi

# Charger la configuration (IP et ports)
RASPBERRY_IP=$(grep "raspberry_pi_ip:" config/config.yaml | awk '{print $2}' | tr -d '"')
CONTROL_PORT=$(grep "control_port:" config/config.yaml | awk '{print $2}')
PROXY_PORT=$(grep "camera_proxy_port:" config/config.yaml | awk '{print $2}')

# Créer les dossiers nécessaires
mkdir -p logs
mkdir -p static

# Vérifier les dépendances Python
echo -e "${BLUE}🔍 Vérification des dépendances...${NC}"
python3 -c "import yaml, flask, flask_socketio, gpiozero, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠  Dépendances manquantes, installation...${NC}"
    pip3 install -r requirements.txt
fi
echo -e "${GREEN}✓${NC} Dépendances OK"
echo ""

# Vérifier les certificats SSL
CERT_PATH=$(grep "cert_path:" config/config.yaml | awk '{print $2}' | tr -d '"')
KEY_PATH=$(grep "key_path:" config/config.yaml | awk '{print $2}' | tr -d '"')

if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}⚠  Certificats SSL manquants${NC}"
    echo "Génération des certificats..."
    mkdir -p $(dirname "$CERT_PATH")
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "$KEY_PATH" \
        -out "$CERT_PATH" \
        -days 365 \
        -subj "/CN=${RASPBERRY_IP}" \
        -addext "subjectAltName=IP:${RASPBERRY_IP}" 2>/dev/null
    echo -e "${GREEN}✓${NC} Certificats générés"
    echo ""
fi

# Variables pour les PIDs
PID_CONTROL=""
PID_PROXY=""

# Fonction de nettoyage
cleanup() {
    echo ""
    echo -e "${BLUE}🛑 Arrêt des serveurs...${NC}"
    
    if [ ! -z "$PID_CONTROL" ]; then
        kill $PID_CONTROL 2>/dev/null
        echo -e "${GREEN}✓${NC} Serveur de contrôle arrêté"
    fi
    
    if [ ! -z "$PID_PROXY" ]; then
        kill $PID_PROXY 2>/dev/null
        echo -e "${GREEN}✓${NC} Proxy caméra arrêté"
    fi
    
    # Sauvegarder les PIDs pour le script stop.sh
    rm -f logs/robot.pid
    
    exit 0
}

trap cleanup SIGINT SIGTERM

# Démarrer le serveur de contrôle
echo -e "${BLUE}1⃣  Démarrage du serveur de contrôle...${NC}"
cd ~/jean_test/car_control && python3 -m src.control_server &
PID_CONTROL=$!
sleep 3

if ! kill -0 $PID_CONTROL 2>/dev/null; then
    echo -e "${RED}❌ Échec du démarrage du serveur de contrôle${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Serveur de contrôle démarré (PID: $PID_CONTROL)"
echo ""

# Démarrer le proxy caméra
echo -e "${BLUE}2⃣  Démarrage du proxy caméra...${NC}"
python3 -m src.camera_proxy &
PID_PROXY=$!
sleep 2

if ! kill -0 $PID_PROXY 2>/dev/null; then
    echo -e "${YELLOW}⚠  Le proxy caméra n'a pas démarré${NC}"
    PID_PROXY=""
else
    echo -e "${GREEN}✓${NC} Proxy caméra démarré (PID: $PID_PROXY)"
fi
echo ""

# Sauvegarder les PIDs
echo "$PID_CONTROL $PID_PROXY" > logs/robot.pid

# Afficher le résumé
echo "========================================"
echo -e "${GREEN}✅ SYSTÈME OPÉRATIONNEL${NC}"
echo "========================================"
echo ""
echo "🎮 Interface de contrôle:"
echo "   https://${RASPBERRY_IP}:${CONTROL_PORT}"
echo ""

if [ ! -z "$PID_PROXY" ]; then
    echo "📹 Proxy caméra HTTPS:"
    echo "   https://${RASPBERRY_IP}:${PROXY_PORT}"
    echo ""
    echo -e "${BLUE}📱 Configuration IP Webcam:${NC}"
    echo "   1. Installez 'IP Webcam' sur Android"
    echo "   2. Lancez l'app et démarrez le serveur"
    echo "   3. Notez l'IP Android"
    echo "   4. Configurez dans l'interface robot"
else
    echo -e "${YELLOW}📹 Proxy caméra: Non disponible${NC}"
fi

echo ""
echo "📊 Logs: tail -f logs/robot.log"
echo ""
echo "========================================"
echo "Appuyez sur Ctrl+C pour arrêter"
echo "========================================"
echo ""

# Attendre les processus
if [ ! -z "$PID_PROXY" ]; then
    wait $PID_CONTROL $PID_PROXY
else
    wait $PID_CONTROL
fi
