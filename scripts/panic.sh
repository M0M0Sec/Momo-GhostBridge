#!/bin/bash
#
# GhostBridge Panic Script
#
# Emergency wipe and shutdown. Use when compromise is detected.
#
# Usage: ./panic.sh [--force]
#

set -e

# Colors
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${RED}[PANIC]${NC} $1"
}

# Check for force flag
FORCE=false
if [ "$1" = "--force" ]; then
    FORCE=true
fi

# Confirm unless forced
if [ "$FORCE" = false ]; then
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ⚠️  PANIC MODE  ⚠️                       ║${NC}"
    echo -e "${RED}║                                                          ║${NC}"
    echo -e "${RED}║  This will:                                              ║${NC}"
    echo -e "${RED}║  • Stop all GhostBridge services                        ║${NC}"
    echo -e "${RED}║  • Securely wipe all keys and configuration            ║${NC}"
    echo -e "${RED}║  • Delete all logs and data                             ║${NC}"
    echo -e "${RED}║  • Reboot the device                                    ║${NC}"
    echo -e "${RED}║                                                          ║${NC}"
    echo -e "${RED}║  THIS CANNOT BE UNDONE!                                  ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    read -p "Type 'PANIC' to confirm: " confirm
    if [ "$confirm" != "PANIC" ]; then
        echo "Aborted."
        exit 1
    fi
fi

log "Panic sequence initiated"

# 1. Stop services
log "Stopping services..."
systemctl stop ghostbridge-beacon 2>/dev/null || true
systemctl stop ghostbridge-tunnel 2>/dev/null || true
systemctl stop ghostbridge 2>/dev/null || true
systemctl stop wg-quick@wg0 2>/dev/null || true

# 2. Kill any remaining processes
log "Killing processes..."
pkill -9 -f ghostbridge 2>/dev/null || true
pkill -9 -f wireguard 2>/dev/null || true

# 3. Secure wipe keys
log "Wiping cryptographic keys..."
for keyfile in /etc/ghostbridge/*.key /etc/wireguard/*.key /etc/wireguard/*.conf; do
    if [ -f "$keyfile" ]; then
        # Overwrite with random data 3 times
        dd if=/dev/urandom of="$keyfile" bs=$(stat -c%s "$keyfile" 2>/dev/null || echo 4096) count=1 conv=notrunc 2>/dev/null || true
        dd if=/dev/zero of="$keyfile" bs=$(stat -c%s "$keyfile" 2>/dev/null || echo 4096) count=1 conv=notrunc 2>/dev/null || true
        dd if=/dev/urandom of="$keyfile" bs=$(stat -c%s "$keyfile" 2>/dev/null || echo 4096) count=1 conv=notrunc 2>/dev/null || true
        rm -f "$keyfile"
    fi
done

# 4. Wipe configuration
log "Wiping configuration..."
rm -rf /etc/ghostbridge 2>/dev/null || true
rm -rf /etc/wireguard 2>/dev/null || true

# 5. Wipe application
log "Wiping application..."
rm -rf /opt/ghostbridge 2>/dev/null || true

# 6. Wipe logs
log "Wiping logs..."
rm -rf /var/log/* 2>/dev/null || true
rm -rf /var/ghostbridge 2>/dev/null || true
rm -rf /tmp/* 2>/dev/null || true

# 7. Clear shell history
log "Clearing history..."
rm -f /root/.bash_history 2>/dev/null || true
rm -f /home/*/.bash_history 2>/dev/null || true
history -c 2>/dev/null || true

# 8. Sync and drop caches
log "Syncing filesystem..."
sync
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

# 9. Disable services
log "Disabling services..."
systemctl disable ghostbridge 2>/dev/null || true
systemctl disable ghostbridge-tunnel 2>/dev/null || true
systemctl disable ghostbridge-beacon 2>/dev/null || true

# 10. Remove service files
rm -f /etc/systemd/system/ghostbridge*.service 2>/dev/null || true
systemctl daemon-reload 2>/dev/null || true

log "Panic complete. Rebooting in 3 seconds..."
sleep 3

# Reboot
reboot -f

