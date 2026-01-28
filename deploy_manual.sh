#!/bin/bash
# Manuelles Deployment Script für TradeAgent auf Raspberry Pi

# Konfiguration
PI_USER="recovery"
PI_HOST="raspberrypi.local" # Oder IP-Adresse verwenden

echo "🚀 Starte manuelles Deployment auf $PI_HOST..."

# 1. SSH Verbindung prüfen
if ! ping -c 1 $PI_HOST &> /dev/null; then
    echo "⚠️  Host $PI_HOST nicht erreichbar. Bitte IP-Adresse prüfen."
    read -p "Gib die IP-Adresse des Pi ein (oder Enter für Abbruch): " NEW_IP
    if [ -z "$NEW_IP" ]; then
        echo "❌ Abbruch."
        exit 1
    fi
    PI_HOST=$NEW_IP
fi

# 2. Update durchführen
echo "🔄 Führe Update durch..."
ssh $PI_USER@$PI_HOST << EOF
    cd ~/TradeAgent
    echo "⬇️  Pulling latest changes..."
    git pull origin main
    
    echo "🔨 Rebuilding container..."
    ./run_podman.sh build
    
    echo "🛑 Stopping old container..."
    ./run_podman.sh stop
    
    echo "📅 Starting scheduled service..."
    ./run_podman.sh schedule
EOF

echo "✅ Fertig! Logs überprüfen mit:"
echo "ssh $PI_USER@$PI_HOST 'tail -f ~/TradeAgent/logs/trading.log'"
