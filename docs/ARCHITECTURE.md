# 🏗️ GhostBridge Architecture

> **Version:** 0.6.0 | **Last Updated:** 2025-12-22

---

## 📋 Overview

GhostBridge is a transparent network implant designed for long-term persistence in Red Team operations. This document describes the technical architecture.

---

## 🎯 Design Goals

| Goal | Priority | Description |
|------|----------|-------------|
| **Stealth** | P0 | Invisible to network scans and monitoring |
| **Persistence** | P0 | Survives reboots, reconnects automatically |
| **Reliability** | P1 | 99.9%+ uptime, multiple fallback options |
| **Integration** | P1 | Seamless MoMo C2 integration |
| **Simplicity** | P2 | Easy deployment, minimal configuration |

---

## 🔧 System Architecture

### Component Overview

| Layer | Components |
|-------|------------|
| **User Space** | Beacon Service, Command Handler, Tunnel Manager, Stealth Module, MoMo Client |
| **Core** | Core Engine (orchestration) |
| **Kernel** | WireGuard Module, Linux Bridge, Netfilter |
| **Network** | wg0 (tunnel), br0 (bridge), eth0 (WAN), eth1 (LAN) |

### Data Flow

| Flow | Path |
|------|------|
| **Target Traffic** | Wall Port → eth0 → br0 → eth1 → Target Device |
| **C2 Traffic** | Core Engine → wg0 → Internet → C2 Server |
| **DNS Tunnel** | Core Engine → DNS Client → Port 53 → C2 Server |

---

## 🌉 Bridge Architecture

### Layer 2 Transparent Bridge

| Property | Value |
|----------|-------|
| Bridge Interface | `br0` |
| WAN Interface | `eth0` (to wall) |
| LAN Interface | `eth1` (to target) |
| IP Address | None (pure L2) |
| STP | Disabled |
| Promiscuous | Enabled |

### MAC Cloning Strategy

| Stage | Configuration |
|-------|---------------|
| **Before** | Wall ↔ Target PC (MAC: AA:BB:CC:DD:EE:FF) |
| **After** | Wall ↔ GhostBridge ↔ Target PC |
| **eth0 MAC** | AA:BB:CC:DD:EE:FF (cloned from target) |
| **eth1 MAC** | Original |
| **Result** | Network sees same MAC on wall port |

### Bridge Setup

```bash
# Create bridge
ip link add name br0 type bridge
ip link set br0 up
echo 0 > /sys/class/net/br0/bridge/stp_state

# Add interfaces
ip link set eth0 master br0
ip link set eth1 master br0

# Enable promiscuous mode
ip link set eth0 promisc on
ip link set eth1 promisc on

# Clone MAC from target
TARGET_MAC=$(cat /sys/class/net/eth1/address)
ip link set eth0 address $TARGET_MAC
```

---

## 🔐 Tunnel Architecture

### WireGuard Primary Tunnel

| Property | Value |
|----------|-------|
| Interface | `wg0` |
| Address | `10.66.66.x/24` |
| Port | 51820 (UDP) |
| Encryption | ChaCha20-Poly1305 |
| Keepalive | 25 seconds |

### DNS Tunnel Fallback (v0.6.0)

| Property | Value |
|----------|-------|
| Protocol | DNS over UDP/TCP |
| Record Types | TXT, NULL |
| Encodings | Base32, Base64, Hex |
| Compression | Zlib |
| Stealth | 0x20 bit randomization, jitter |

### Fallback Chain

| Priority | Method | Port | Timeout | Condition |
|----------|--------|------|---------|-----------|
| 1 | WireGuard UDP | 51820 | 30s | Primary |
| 2 | WireGuard TCP | 443 | 30s | UDP blocked |
| 3 | DNS Tunnel | 53 | - | VPN blocked |
| 4 | Auto-restore | - | 5min | Return to primary |

### DNS Tunnel Message Format

| Field | Size | Description |
|-------|------|-------------|
| Magic | 2 bytes | `0x4D4F` (MO) |
| Version | 1 byte | Protocol version |
| Session ID | 4 bytes | Session identifier |
| Sequence | 2 bytes | Packet sequence |
| Flags | 1 byte | Compression, chunk flags |
| CRC32 | 4 bytes | Checksum |
| Data | Variable | Encoded payload |

---

## 📡 Beacon Architecture

### Beacon Protocol

| Stage | Description |
|-------|-------------|
| **Timer** | 5 min interval ± 1 min jitter |
| **Collect** | Gather device status |
| **Send** | POST to C2 API |
| **Receive** | Get pending commands |
| **Execute** | Process commands locally |
| **Report** | Send command results |

### Beacon Payload

| Field | Type | Description |
|-------|------|-------------|
| device_id | string | Unique device ID |
| status | string | online/degraded/offline |
| uptime | int | Seconds since boot |
| tunnel_status | string | connected/fallback/disconnected |
| bridge_stats | object | Packets bridged |
| memory_usage | int | RAM usage in MB |
| cpu_usage | float | CPU percentage |

---

## 🛡️ Stealth Architecture

### Stealth Layers

| Layer | Features |
|-------|----------|
| **Network** | No IP on bridge, MAC cloning, no ARP replies, outbound-only |
| **Traffic** | Timing jitter, traffic blending, encrypted tunnel, DoH |
| **Host** | RAM-only logs, encrypted FS, minimal processes, fake identity |
| **Anti-Forensics** | Secure erase, no persistent logs, keys in RAM, self-destruct |

### Panic Sequence

| Step | Action |
|------|--------|
| 1 | Stop all services |
| 2 | Wipe RAM (keys, logs) |
| 3 | Secure erase config files |
| 4 | Overwrite with zeros |
| 5 | Halt or reboot system |

---

## 📁 Directory Structure

| Path | Purpose |
|------|---------|
| `/etc/ghostbridge/config.yml` | Main configuration |
| `/etc/ghostbridge/device.key` | Device identity key |
| `/etc/wireguard/wg0.conf` | WireGuard config |
| `/opt/ghostbridge/bin/` | Executables |
| `/opt/ghostbridge/lib/` | Python modules |
| `/var/ghostbridge/` | Runtime data (tmpfs) |

---

## 🔌 Hardware (NanoPi R2S)

### Port Configuration

| Port | Interface | Connection |
|------|-----------|------------|
| WAN (eth0) | RJ45 | Wall port / Switch |
| LAN (eth1) | RJ45 | Target device |
| USB-C | Power | 5V from target or wall |
| USB-A | Optional | WiFi dongle, storage |

### LED Indicators

| LED | Color | Meaning |
|-----|-------|---------|
| LED1 | Green | Power on |
| LED2 | Blue (solid) | Tunnel connected |
| LED2 | Blue (blink) | Connecting |
| LED2 | Off | Disconnected |

---

## 🌐 DNS Tunnel Details (v0.6.0)

### Encoding Comparison

| Encoder | Efficiency | DNS-Safe | Use Case |
|---------|------------|----------|----------|
| Base32 | 62.5% | A-Z, 2-7 | Subdomains (default) |
| Base64 | 75% | A-Za-z0-9+/ | TXT records |
| Hex | 50% | 0-9, A-F | Maximum compatibility |

### Query Format

| Component | Example |
|-----------|---------|
| Data | `JBSWY3DPEHPK3PXP` |
| Session | `.s1a2b3c4` |
| Sequence | `.q0001` |
| Domain | `.tunnel.example.com` |
| **Full** | `JBSWY3DPEHPK3PXP.s1a2b3c4.q0001.tunnel.example.com` |

### Rate Limiting

| Setting | Default | Description |
|---------|---------|-------------|
| Query interval | 500ms | Time between queries |
| Jitter | ±100ms | Timing randomization |
| Max queries/sec | 10 | Rate limit |
| Chunk size | 63 bytes | Max subdomain label |

---

## 🧪 Testing

### Test Categories

| Category | Tests | Coverage |
|----------|-------|----------|
| Unit | 120 | Core logic |
| Integration | 15 | Component interaction |
| DNS Tunnel | 26 | Encoding, protocol |
| Stealth | 10 | Anti-forensics |
| **Total** | 171 | 82% |

---

*GhostBridge Architecture v0.6.0*
