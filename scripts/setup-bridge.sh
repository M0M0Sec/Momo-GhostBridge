#!/bin/bash
#
# GhostBridge - Bridge Setup Script
# 
# This script sets up a transparent Layer 2 bridge between two interfaces.
# Designed for NanoPi R2S but works on any Linux with two Ethernet ports.
#
# Usage: ./setup-bridge.sh [--wan eth0] [--lan eth1] [--bridge br0] [--clone-mac]
#

set -e

# Default configuration
BRIDGE="br0"
WAN="eth0"
LAN="eth1"
CLONE_MAC=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
        --wan)
            WAN="$2"
            shift 2
            ;;
        --lan)
            LAN="$2"
            shift 2
            ;;
        --bridge)
            BRIDGE="$2"
            shift 2
            ;;
        --clone-mac)
            CLONE_MAC=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --wan IFACE      WAN interface (default: eth0)"
            echo "  --lan IFACE      LAN interface (default: eth1)"
            echo "  --bridge NAME    Bridge name (default: br0)"
            echo "  --clone-mac      Clone MAC from LAN to WAN"
            echo "  -v, --verbose    Verbose output"
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

# Verify interfaces exist
verify_interface() {
    if [ ! -e "/sys/class/net/$1" ]; then
        log_error "Interface $1 not found"
        exit 1
    fi
}

log_info "GhostBridge Setup"
log_info "=================="
log_info "Bridge: $BRIDGE"
log_info "WAN:    $WAN (to wall port)"
log_info "LAN:    $LAN (to target device)"
log_info "Clone MAC: $CLONE_MAC"
echo ""

# Step 1: Verify interfaces
log_info "Verifying interfaces..."
verify_interface "$WAN"
verify_interface "$LAN"

# Step 2: Wait for LAN interface to have carrier
log_info "Waiting for target device on LAN..."
ip link set "$LAN" up

TIMEOUT=30
COUNTER=0
while [ ! -f "/sys/class/net/$LAN/carrier" ] || [ "$(cat /sys/class/net/$LAN/carrier 2>/dev/null)" != "1" ]; do
    sleep 1
    COUNTER=$((COUNTER + 1))
    if [ $COUNTER -ge $TIMEOUT ]; then
        log_warn "No target device detected after ${TIMEOUT}s, continuing anyway"
        break
    fi
    if [ $VERBOSE = true ]; then
        echo -n "."
    fi
done
echo ""

# Step 3: Clone MAC address (optional)
if [ "$CLONE_MAC" = true ]; then
    log_info "Cloning MAC address..."
    
    # Wait a bit for ARP
    sleep 2
    
    # Try to get target MAC from ARP table
    TARGET_MAC=$(ip neigh show dev "$LAN" | head -1 | awk '{print $3}')
    
    if [ -n "$TARGET_MAC" ] && [ "$TARGET_MAC" != "FAILED" ]; then
        log_info "Detected target MAC: $TARGET_MAC"
        
        # Save original MAC
        ORIGINAL_MAC=$(cat /sys/class/net/$WAN/address)
        log_info "Original WAN MAC: $ORIGINAL_MAC"
        
        # Clone MAC to WAN
        ip link set "$WAN" down
        ip link set "$WAN" address "$TARGET_MAC"
        ip link set "$WAN" up
        
        log_info "Cloned MAC to WAN interface"
    else
        log_warn "Could not detect target MAC, skipping clone"
    fi
fi

# Step 4: Create bridge (if not exists)
log_info "Creating bridge $BRIDGE..."
if ip link show "$BRIDGE" &>/dev/null; then
    log_warn "Bridge $BRIDGE already exists"
else
    ip link add name "$BRIDGE" type bridge
fi

# Step 5: Disable STP (faster convergence, more stealthy)
log_info "Disabling STP..."
echo 0 > "/sys/class/net/$BRIDGE/bridge/stp_state"

# Step 6: Add interfaces to bridge
log_info "Adding interfaces to bridge..."
ip link set "$WAN" master "$BRIDGE" 2>/dev/null || log_warn "$WAN already in bridge"
ip link set "$LAN" master "$BRIDGE" 2>/dev/null || log_warn "$LAN already in bridge"

# Step 7: Enable promiscuous mode
log_info "Enabling promiscuous mode..."
ip link set "$WAN" promisc on
ip link set "$LAN" promisc on

# Step 8: Flush IP addresses (L2 only)
log_info "Flushing IP addresses..."
ip addr flush dev "$WAN" 2>/dev/null || true
ip addr flush dev "$LAN" 2>/dev/null || true
ip addr flush dev "$BRIDGE" 2>/dev/null || true

# Step 9: Bring everything up
log_info "Bringing interfaces up..."
ip link set "$WAN" up
ip link set "$LAN" up
ip link set "$BRIDGE" up

# Step 10: Verify setup
log_info "Verifying setup..."
echo ""
echo "Bridge Status:"
echo "=============="
bridge link show
echo ""
echo "Interface Status:"
echo "================="
ip -br link show "$BRIDGE" "$WAN" "$LAN"
echo ""

# Check connectivity
WAN_CARRIER=$(cat "/sys/class/net/$WAN/carrier" 2>/dev/null || echo "0")
LAN_CARRIER=$(cat "/sys/class/net/$LAN/carrier" 2>/dev/null || echo "0")

if [ "$WAN_CARRIER" = "1" ] && [ "$LAN_CARRIER" = "1" ]; then
    log_info "✓ Bridge is ACTIVE (both links up)"
elif [ "$WAN_CARRIER" = "1" ] || [ "$LAN_CARRIER" = "1" ]; then
    log_warn "Bridge is DEGRADED (one link down)"
    [ "$WAN_CARRIER" != "1" ] && log_warn "  - WAN link is down"
    [ "$LAN_CARRIER" != "1" ] && log_warn "  - LAN link is down"
else
    log_error "Bridge is DOWN (no links)"
fi

echo ""
log_info "Bridge setup complete!"
log_info ""
log_info "To tear down: ip link delete $BRIDGE"

