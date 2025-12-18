#!/bin/bash
#
# GhostBridge - Bridge Teardown Script
#
# Tears down the bridge and restores original configuration.
#
# Usage: ./teardown-bridge.sh [--bridge br0] [--wan eth0] [--lan eth1]
#

set -e

# Default configuration
BRIDGE="br0"
WAN="eth0"
LAN="eth1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --bridge)
            BRIDGE="$2"
            shift 2
            ;;
        --wan)
            WAN="$2"
            shift 2
            ;;
        --lan)
            LAN="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --bridge NAME    Bridge name (default: br0)"
            echo "  --wan IFACE      WAN interface (default: eth0)"
            echo "  --lan IFACE      LAN interface (default: eth1)"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo)"
    exit 1
fi

log_info "GhostBridge Teardown"
log_info "===================="
echo ""

# Step 1: Remove interfaces from bridge
log_info "Removing interfaces from bridge..."
ip link set "$WAN" nomaster 2>/dev/null || log_warn "$WAN not in bridge"
ip link set "$LAN" nomaster 2>/dev/null || log_warn "$LAN not in bridge"

# Step 2: Disable promiscuous mode
log_info "Disabling promiscuous mode..."
ip link set "$WAN" promisc off 2>/dev/null || true
ip link set "$LAN" promisc off 2>/dev/null || true

# Step 3: Delete bridge
log_info "Deleting bridge..."
if ip link show "$BRIDGE" &>/dev/null; then
    ip link set "$BRIDGE" down 2>/dev/null || true
    ip link delete "$BRIDGE" type bridge
    log_info "Bridge $BRIDGE deleted"
else
    log_warn "Bridge $BRIDGE does not exist"
fi

# Step 4: Bring interfaces back up
log_info "Bringing interfaces up..."
ip link set "$WAN" up 2>/dev/null || true
ip link set "$LAN" up 2>/dev/null || true

echo ""
log_info "Teardown complete!"
log_info ""
log_info "Note: Original MAC addresses are NOT restored automatically."
log_info "      Reboot to restore original MAC addresses."

