# ⚔️ GhostBridge Operations Guide

> **Version:** 0.6.0 | **Classification:** Red Team Internal

---

## ⚠️ OPERATIONAL SECURITY WARNING

| ⚠️ OPSEC CRITICAL |
|-------------------|
| This device is designed for covert operations. |
| Follow ALL OPSEC guidelines to avoid detection. |
| **Failure to follow procedures may result in:** |
| • Device discovery and seizure |
| • Compromise of operation |
| • Legal consequences |
| • Attribution to your organization |
| **ALWAYS operate under proper authorization!** |

---

## 📋 Pre-Operation Checklist

### 1. Authorization
- [ ] Written authorization from client
- [ ] Scope of engagement defined
- [ ] Rules of engagement signed
- [ ] Emergency contacts established
- [ ] Legal team notified

### 2. Device Preparation
- [ ] Fresh SD card (new, not reused)
- [ ] Unique device ID configured
- [ ] WireGuard keys generated
- [ ] DNS tunnel domain configured (v0.6.0)
- [ ] C2 endpoint configured
- [ ] Beacon interval set
- [ ] Panic trigger configured

### 3. C2 Infrastructure
- [ ] VPS provisioned (clean)
- [ ] WireGuard server configured
- [ ] Domain purchased (burn domain)
- [ ] DNS tunnel nameserver ready (v0.6.0)
- [ ] DNS configured
- [ ] MoMo server running
- [ ] Monitoring active

### 4. Cover Story
- [ ] Cover identity prepared
- [ ] Fake credentials ready
- [ ] Exit strategy planned
- [ ] Backup devices available

---

## 🎯 Deployment Scenarios

### Scenario A: Printer Drop

**Target:** Network printer in common area

| Phase | Actions |
|-------|---------|
| **Reconnaissance** | Identify printer location, note cable routing, check power sources, time guard patrols |
| **Access** | Enter as IT support / cleaner / delivery, carry legitimate equipment, have cover story |
| **Installation** | Locate printer network cable, insert GhostBridge inline, power from printer USB, conceal |
| **Verification** | Check C2 connection via phone, verify bridge traffic, ensure printer still works |
| **Exfiltration** | Document entry/exit times, note witnesses, clear phone logs |

**Concealment Tips:**
- Place behind printer
- Use cable management clips
- Match cable colors
- Add fake label ("Network Booster")

---

### Scenario B: Conference Room

**Target:** AV equipment in meeting room

| Phase | Actions |
|-------|---------|
| **Reconnaissance** | Book meeting room if possible, identify network ports, note AV equipment |
| **Access** | Enter during off-hours or book legitimate meeting, bring laptop/equipment |
| **Installation** | Find TV/projector network cable, install inline to wall port, hide behind equipment |
| **Verification** | Confirm C2 connection, test AV still works, leave room normally |
| **Persistence** | Room often unused nights, low traffic area, difficult to spot |

**VLAN Bonus:**
- Meeting rooms often on executive VLAN
- May have less monitoring
- Access to sensitive traffic

---

### Scenario C: Under-Desk Installation

**Target:** Executive workstation

| Phase | Actions |
|-------|---------|
| **Reconnaissance** | Identify target executive, map office layout, note desk setup |
| **Access (HIGH RISK)** | Requires physical access, off-hours preferred, badge cloning helpful |
| **Installation** | Find docking station cable, install between wall and dock, clone MAC |
| **Concealment** | Use cable ties, match existing cables, add dust for aging, avoid visible lights |
| **Verification** | Quick C2 check, exit immediately, verify remotely later |

**High Value:**
- Executive network segment
- Often less restricted
- Sensitive communications

---

## 🔐 OPSEC Guidelines

### Before Deployment

| ✅ Do | ❌ Don't |
|-------|---------|
| Use burner phone for checks | Use personal phone |
| Wear gloves when handling | Leave fingerprints |
| Wipe device externally | Leave packaging |
| Use new cables | Reuse identifiable cables |
| Test in lab first | Deploy untested |

### During Deployment

| ✅ Do | ❌ Don't |
|-------|---------|
| Have cover story ready | Act suspicious |
| Move with purpose | Hesitate or look around |
| Dress appropriately | Stand out |
| Time visits properly | Rush or stay too long |
| Have exit plan | Get cornered |

### After Deployment

| ✅ Do | ❌ Don't |
|-------|---------|
| Verify C2 remotely | Return unnecessarily |
| Monitor beacon health | Ignore offline alerts |
| Log all activity | Leave gaps in records |
| Report to team lead | Operate solo |
| Have retrieval plan | Abandon device |

---

## 📡 Communication Security

### C2 Domain Selection

| ✅ Good | ❌ Bad |
|---------|--------|
| cdn-assets-prod.com | hacker-c2.com |
| cloud-sync-api.net | malware-server.xyz |
| update-service.io | totally-legit-domain.tk |
| static-content-delivery.com | ghostbridge-c2.org |

### Traffic Patterns

| ✅ Good | ❌ Bad |
|---------|--------|
| Random intervals (jitter) | Exact 5-minute beacons |
| Variable payload sizes | Fixed size packets |
| HTTPS on 443 | Unusual ports |
| Normal working hours | 3 AM activity spikes |
| Gradual ramp-up | Immediate full speed |

### Fallback Chain (v0.6.0)

| Priority | Method | Timeout | Action |
|----------|--------|---------|--------|
| 1 | WireGuard UDP | 30s | Primary tunnel |
| 2 | WireGuard TCP 443 | 30s | Firewall bypass |
| 3 | DNS Tunnel | - | VPN blocked (NEW) |
| 4 | Hibernate | 7 days | Beacon via DNS |
| 5 | Lost | - | Consider device burned |

**Note:** DNS tunneling (v0.6.0) provides covert C2 when all VPN options fail.

---

## 🚨 Emergency Procedures

### Device Discovery

| Timeframe | Actions |
|-----------|---------|
| **Immediate** (minutes) | Notify team lead, document timeline, assess exposure level |
| **Short-term** (hours) | Issue panic command, rotate C2 infrastructure, check other devices |
| **Long-term** (days) | Incident report, lessons learned, update procedures, client notification |

### C2 Compromise

| Phase | Actions |
|-------|---------|
| **Immediate** | Isolate C2 server, issue global panic to all devices, rotate all keys |
| **Assessment** | Determine exposure scope, identify affected devices, check for lateral movement |
| **Recovery** | Deploy new C2 infrastructure, re-provision surviving devices, enhanced monitoring |

### Personnel Compromise

| Phase | Actions |
|-------|---------|
| **Immediate** | Assume all devices known, panic all devices, lawyer contact, do NOT attempt recovery |
| **Assessment** | Determine what operator knew, identify at-risk infrastructure |
| **Recovery** | Full infrastructure rotation, new device provisioning, changed procedures |

---

## 📊 Monitoring & Alerting

### Beacon Health

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 Online | Normal operation | None |
| 🟡 Delayed | 1-3 missed beacons | Monitor |
| 🟠 Offline | 4-12 missed beacons | Investigate |
| 🔴 Lost | 24h+ no contact | Consider burned |

### Alert Triggers

| Alert | Condition | Response |
|-------|-----------|----------|
| Beacon Miss | 3 consecutive | Check network |
| Tunnel Change | Fallback activated | Investigate |
| DNS Fallback | VPN unreachable | Monitor (may be normal) |
| Panic Triggered | Manual or auto | Document |
| Anomaly Detected | Unusual traffic | Analyze |

### Dashboard Metrics

| Metric | Example |
|--------|---------|
| Device | ghost-001 |
| Status | 🟢 Online |
| Uptime | 14 days 3 hours |
| Last Beacon | 2 minutes ago |
| Tunnel | WireGuard UDP / DNS (fallback) |
| Bridge Traffic | 1.2 GB |
| Commands Executed | 47 |
| Network | 192.168.1.0/24 |

---

## 🔧 Maintenance Procedures

### Remote Commands

| Command | Description |
|---------|-------------|
| `gb status` | Check device status |
| `gb logs -n 100` | View last 100 log lines |
| `gb config set beacon.interval 600` | Update beacon interval |
| `gb tunnel reconnect` | Force tunnel reconnect |
| `gb tunnel fallback dns` | Force DNS tunnel mode |
| `gb stealth wipe-logs` | Clear local logs |
| `gb system reboot` | Reboot device |

### Scheduled Tasks

| Task | Frequency | Purpose |
|------|-----------|---------|
| Log rotation | Daily | Prevent disk fill |
| Key rotation | Monthly | Security hygiene |
| Config backup | Weekly | Recovery capability |
| Health check | Hourly | Early warning |

### Retrieval Checklist

| Phase | Actions |
|-------|---------|
| **Pre-Retrieval** | Confirm device active, plan access, prepare replacement, have cover story |
| **Retrieval** | Access location, remove device, restore original cabling, check for evidence |
| **Post-Retrieval** | Extract logs, secure wipe device, mark as retrieved, update inventory |

---

## 📝 Reporting

### Daily Report Template

```markdown
# GhostBridge Daily Report
Date: YYYY-MM-DD
Operator: [Name]

## Device Status
| Device | Status | Uptime | Tunnel | Notes |
|--------|--------|--------|--------|-------|
| ghost-001 | 🟢 | 14d | WireGuard | Normal |
| ghost-002 | 🟡 | 3d | DNS Tunnel | VPN blocked |

## Activity Summary
- Commands executed: 12
- Data collected: 150 MB
- Tunnel fallbacks: 1
- Alerts: 0

## Issues
- ghost-002 fell back to DNS tunnel (investigating)

## Tomorrow's Plan
- Monitor ghost-002 connectivity
- Execute network scan on ghost-001
```

---

## ⚖️ Legal Considerations

### Required Documentation
- [ ] Signed authorization letter
- [ ] Scope of work document
- [ ] Rules of engagement
- [ ] Emergency contact list
- [ ] Incident response plan

### Prohibited Actions
- ❌ Accessing systems outside scope
- ❌ Exfiltrating personal data
- ❌ Disrupting business operations
- ❌ Retaining data after engagement
- ❌ Sharing access with unauthorized parties

### Evidence Handling
- Maintain chain of custody
- Log all data access
- Encrypt all collected data
- Secure deletion after engagement
- Provide evidence only to authorized parties

---

*GhostBridge Operations Guide v0.6.0*
*Classification: Red Team Internal*
