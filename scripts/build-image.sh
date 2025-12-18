#!/bin/bash
#
# GhostBridge Image Builder
#
# Creates a deployable SD card image for NanoPi R2S.
#
# Prerequisites:
#   - Docker or Armbian build tools
#   - Base Armbian image for NanoPi R2S
#
# Usage: ./build-image.sh [OPTIONS]
#
# Options:
#   -o, --output    Output image file (default: ghostbridge.img)
#   -b, --base      Base Armbian image to modify
#   -c, --config    Config file to embed
#   -k, --keys      Directory containing WireGuard keys
#

set -e

# Defaults
OUTPUT="ghostbridge-$(date +%Y%m%d).img"
BASE_IMAGE=""
CONFIG_FILE=""
KEYS_DIR=""
WORK_DIR="/tmp/ghostbridge-build"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    echo "GhostBridge Image Builder"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -o, --output    Output image file"
    echo "  -b, --base      Base Armbian image"
    echo "  -c, --config    Config file to embed"
    echo "  -k, --keys      WireGuard keys directory"
    echo "  -h, --help      Show this help"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -b|--base)
            BASE_IMAGE="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -k|--keys)
            KEYS_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validation
if [ -z "$BASE_IMAGE" ]; then
    log_error "Base image required (-b)"
    usage
fi

if [ ! -f "$BASE_IMAGE" ]; then
    log_error "Base image not found: $BASE_IMAGE"
    exit 1
fi

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo)"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             GhostBridge Image Builder                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create work directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Step 1: Copy base image
log_info "Copying base image..."
cp "$BASE_IMAGE" "$OUTPUT"

# Step 2: Mount image
log_info "Mounting image..."
LOOP_DEV=$(losetup -f --show -P "$OUTPUT")
ROOTFS="$WORK_DIR/rootfs"

mkdir -p "$ROOTFS"
mount "${LOOP_DEV}p1" "$ROOTFS" 2>/dev/null || mount "${LOOP_DEV}p2" "$ROOTFS"

log_info "Mounted at $ROOTFS"

# Step 3: Copy GhostBridge files
log_info "Installing GhostBridge..."

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Copy source
mkdir -p "$ROOTFS/opt/ghostbridge"
cp -r "$PROJECT_DIR/src" "$ROOTFS/opt/ghostbridge/"
cp -r "$PROJECT_DIR/scripts" "$ROOTFS/opt/ghostbridge/"
cp -r "$PROJECT_DIR/services" "$ROOTFS/opt/ghostbridge/"
cp "$PROJECT_DIR/pyproject.toml" "$ROOTFS/opt/ghostbridge/"
cp "$PROJECT_DIR/requirements.txt" "$ROOTFS/opt/ghostbridge/"

# Step 4: Create config directory
log_info "Setting up configuration..."

mkdir -p "$ROOTFS/etc/ghostbridge"
chmod 700 "$ROOTFS/etc/ghostbridge"

if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$ROOTFS/etc/ghostbridge/config.yml"
    chmod 600 "$ROOTFS/etc/ghostbridge/config.yml"
fi

if [ -n "$KEYS_DIR" ] && [ -d "$KEYS_DIR" ]; then
    cp "$KEYS_DIR"/* "$ROOTFS/etc/ghostbridge/"
    chmod 600 "$ROOTFS/etc/ghostbridge"/*.key 2>/dev/null || true
fi

# Step 5: Install systemd services
log_info "Installing services..."

cp "$PROJECT_DIR/services/"*.service "$ROOTFS/etc/systemd/system/"
cp "$PROJECT_DIR/services/"*.timer "$ROOTFS/etc/systemd/system/" 2>/dev/null || true

# Enable services (via symlinks)
mkdir -p "$ROOTFS/etc/systemd/system/multi-user.target.wants"
ln -sf ../ghostbridge.service "$ROOTFS/etc/systemd/system/multi-user.target.wants/"
ln -sf ../ghostbridge-tunnel.service "$ROOTFS/etc/systemd/system/multi-user.target.wants/"
ln -sf ../ghostbridge-beacon.service "$ROOTFS/etc/systemd/system/multi-user.target.wants/"

# Step 6: Create first-boot script
log_info "Creating first-boot script..."

cat > "$ROOTFS/opt/ghostbridge/first-boot.sh" << 'EOF'
#!/bin/bash
# GhostBridge First Boot Setup

# Wait for network
sleep 10

# Install Python dependencies
python3 -m pip install --quiet -e /opt/ghostbridge

# Generate keys if not present
if [ ! -f /etc/ghostbridge/wg_private.key ]; then
    wg genkey | tee /etc/ghostbridge/wg_private.key | wg pubkey > /etc/ghostbridge/wg_public.key
    chmod 600 /etc/ghostbridge/wg_private.key
fi

# Generate device ID if not present
if [ ! -f /etc/ghostbridge/device_id ]; then
    echo "ghost-$(date +%s | tail -c 6)" > /etc/ghostbridge/device_id
fi

# Disable this script
systemctl disable ghostbridge-firstboot
rm /etc/systemd/system/ghostbridge-firstboot.service

# Restart services
systemctl restart ghostbridge ghostbridge-tunnel ghostbridge-beacon
EOF

chmod +x "$ROOTFS/opt/ghostbridge/first-boot.sh"

cat > "$ROOTFS/etc/systemd/system/ghostbridge-firstboot.service" << EOF
[Unit]
Description=GhostBridge First Boot Setup
After=network-online.target
Wants=network-online.target
ConditionPathExists=/opt/ghostbridge/first-boot.sh

[Service]
Type=oneshot
ExecStart=/opt/ghostbridge/first-boot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

ln -sf ../ghostbridge-firstboot.service "$ROOTFS/etc/systemd/system/multi-user.target.wants/"

# Step 7: System hardening
log_info "Applying hardening..."

# Disable shell history
echo "unset HISTFILE" >> "$ROOTFS/etc/profile.d/no-history.sh"

# Set hostname
echo "netswitch" > "$ROOTFS/etc/hostname"

# Disable unnecessary services
for svc in bluetooth cups avahi-daemon ModemManager snapd; do
    rm -f "$ROOTFS/etc/systemd/system/multi-user.target.wants/$svc.service" 2>/dev/null || true
    rm -f "$ROOTFS/etc/systemd/system/sockets.target.wants/$svc.socket" 2>/dev/null || true
done

# Step 8: Cleanup
log_info "Cleaning up..."

# Clear logs
rm -rf "$ROOTFS/var/log/"* 2>/dev/null || true
rm -rf "$ROOTFS/var/cache/apt/"* 2>/dev/null || true
rm -rf "$ROOTFS/tmp/"* 2>/dev/null || true

# Clear bash history
rm -f "$ROOTFS/root/.bash_history" 2>/dev/null || true

# Step 9: Unmount
log_info "Unmounting..."

sync
umount "$ROOTFS"
losetup -d "$LOOP_DEV"

# Step 10: Compress (optional)
log_info "Compressing image..."
gzip -k "$OUTPUT" 2>/dev/null || true

# Done
mv "$OUTPUT" "$(dirname "$BASE_IMAGE")/"
mv "$OUTPUT.gz" "$(dirname "$BASE_IMAGE")/" 2>/dev/null || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║             Image Build Complete!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Output: $(dirname "$BASE_IMAGE")/$OUTPUT"
echo ""
echo -e "${YELLOW}To flash:${NC}"
echo "  dd if=$OUTPUT of=/dev/sdX bs=4M status=progress"
echo ""
log_info "Done!"

