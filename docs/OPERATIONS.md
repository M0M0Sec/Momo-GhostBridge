# ⚔️ GhostBridge Operations Guide

> **Version:** 0.1.0 | **Classification:** Red Team Internal

---

## ⚠️ OPERATIONAL SECURITY WARNING

```
┌─────────────────────────────────────────────────────────────────┐
│                    ⚠️  OPSEC CRITICAL  ⚠️                        │
│                                                                  │
│  This device is designed for covert operations.                 │
│  Follow ALL OPSEC guidelines to avoid detection.                │
│                                                                  │
│  Failure to follow procedures may result in:                    │
│  • Device discovery and seizure                                 │
│  • Compromise of operation                                      │
│  • Legal consequences                                           │
│  • Attribution to your organization                             │
│                                                                  │
│  ALWAYS operate under proper authorization!                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

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
- [ ] C2 endpoint configured
- [ ] Beacon interval set
- [ ] Panic trigger configured

### 3. C2 Infrastructure
- [ ] VPS provisioned (clean)
- [ ] WireGuard server configured
- [ ] Domain purchased (burn domain)
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

**Approach:**
```
1. Reconnaissance
   - Identify printer location
   - Note cable routing
   - Check power sources
   - Time guard patrols

2. Access
   - Enter as IT support / cleaner / delivery
   - Carry legitimate-looking equipment
   - Have cover story ready

3. Installation
   - Locate printer network cable
   - Trace to wall port
   - Insert GhostBridge inline
   - Power from printer USB
   - Conceal device

4. Verification
   - Check C2 connection (via phone)
   - Verify bridge traffic
   - Ensure printer still works
   - Exit normally

5. Exfiltration
   - Document entry/exit times
   - Note any witnesses
   - Clear phone logs
```

**Concealment Tips:**
- Place behind printer
- Use cable management clips
- Match cable colors
- Add fake label ("Network Booster")

---

### Scenario B: Conference Room

**Target:** AV equipment in meeting room

**Approach:**
```
1. Reconnaissance
   - Book meeting room (if possible)
   - Identify network ports
   - Note AV equipment
   - Check under tables

2. Access
   - Enter during off-hours
   - Or book legitimate meeting
   - Bring laptop/equipment

3. Installation
   - Find TV/projector network cable
   - Install inline to wall port
   - Power from AV equipment
   - Hide behind equipment

4. Verification
   - Confirm C2 connection
   - Test AV still works
   - Leave room normal

5. Persistence
   - Room often unused nights
   - Low traffic area
   - Difficult to spot
```

**VLAN Bonus:**
- Meeting rooms often on executive VLAN
- May have less monitoring
- Access to sensitive traffic

---

### Scenario C: Under-Desk Installation

**Target:** Executive workstation

**Approach:**
```
1. Reconnaissance
   - Identify target executive
   - Map office layout
   - Note desk setup
   - Check cable routing

2. Access (HIGH RISK)
   - Requires physical access
   - Off-hours preferred
   - May need social engineering
   - Badge cloning helpful

3. Installation
   - Find docking station cable
   - Install between wall and dock
   - Clone docking station MAC
   - Hide under desk

4. Concealment
   - Use cable ties
   - Match existing cables
   - Add dust for aging
   - Avoid visible lights

5. Verification
   - Quick C2 check
   - Exit immediately
   - Verify remotely later
```

**High Value:**
- Executive network segment
- Often less restricted
- Sensitive communications
- High-value targets

---

## 🔐 OPSEC Guidelines

### Before Deployment

| Do | Don't |
|-----|-------|
| Use burner phone for checks | Use personal phone |
| Wear gloves when handling | Leave fingerprints |
| Wipe device externally | Leave packaging |
| Use new cables | Reuse identifiable cables |
| Test in lab first | Deploy untested |

### During Deployment

| Do | Don't |
|-----|-------|
| Have cover story ready | Act suspicious |
| Move with purpose | Hesitate or look around |
| Dress appropriately | Stand out |
| Time visits properly | Rush or stay too long |
| Have exit plan | Get cornered |

### After Deployment

| Do | Don't |
|-----|-------|
| Verify C2 remotely | Return unnecessarily |
| Monitor beacon health | Ignore offline alerts |
| Log all activity | Leave gaps in records |
| Report to team lead | Operate solo |
| Have retrieval plan | Abandon device |

---

## 📡 Communication Security

### C2 Domain Selection
```
Good:                           Bad:
cdn-assets-prod.com            hacker-c2.com
cloud-sync-api.net             malware-server.xyz
update-service.io              totally-legit-domain.tk
static-content-delivery.com    ghostbridge-c2.org
```

### Traffic Patterns
```
Good:                           Bad:
• Random intervals (jitter)    • Exact 5-minute beacons
• Variable payload sizes       • Fixed size packets
• HTTPS on 443                 • Unusual ports
• Normal working hours         • 3 AM activity spikes
• Gradual ramp-up              • Immediate full speed
```

### Fallback Procedures
```
1. Primary tunnel fails
   → Wait 5 minutes
   → Try TCP 443

2. TCP fails
   → Try WebSocket wrapper
   → Use Cloudflare Tunnel

3. All tunnels fail
   → Enter hibernate mode
   → Beacon daily via DNS
   → Wait for network restore

4. No connection 7 days
   → Consider device burned
   → Do NOT attempt retrieval
   → Remote wipe if possible
```

---

## 🚨 Emergency Procedures

### Device Discovery

```
IF device is discovered:

1. IMMEDIATE (within minutes)
   □ Notify team lead
   □ Document timeline
   □ Assess exposure level

2. SHORT-TERM (within hours)
   □ Issue panic command
   □ Rotate C2 infrastructure
   □ Check other devices
   □ Review logs for attribution

3. LONG-TERM (within days)
   □ Incident report
   □ Lessons learned
   □ Update procedures
   □ Client notification (if required)
```

### C2 Compromise

```
IF C2 server is compromised:

1. IMMEDIATE
   □ Isolate C2 server
   □ Issue global panic to all devices
   □ Rotate all keys

2. ASSESSMENT
   □ Determine exposure scope
   □ Identify affected devices
   □ Check for lateral movement

3. RECOVERY
   □ Deploy new C2 infrastructure
   □ Re-provision surviving devices
   □ Enhanced monitoring
```

### Personnel Compromise

```
IF operator is detained:

1. IMMEDIATE (team responsibility)
   □ Assume all devices known
   □ Panic all devices
   □ Lawyer contact
   □ Do NOT attempt recovery

2. ASSESSMENT
   □ Determine what operator knew
   □ Identify at-risk infrastructure
   □ Check for device locations

3. RECOVERY
   □ Full infrastructure rotation
   □ New device provisioning
   □ Changed procedures
```

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
| Panic Triggered | Manual or auto | Document |
| Anomaly Detected | Unusual traffic | Analyze |

### Dashboard Metrics

```
Device: ghost-001
Status: 🟢 Online
Uptime: 14 days 3 hours
Last Beacon: 2 minutes ago
Tunnel: WireGuard UDP
Bridge Traffic: 1.2 GB
Commands Executed: 47
Network: 192.168.1.0/24
Gateway: 192.168.1.1
Clients Seen: 23
```

---

## 🔧 Maintenance Procedures

### Remote Maintenance

```bash
# Check status
gb status

# View logs (last 100 lines)
gb logs -n 100

# Update beacon interval
gb config set beacon.interval 600

# Force tunnel reconnect
gb tunnel reconnect

# Clear local logs
gb stealth wipe-logs

# Reboot device
gb system reboot
```

### Scheduled Tasks

| Task | Frequency | Purpose |
|------|-----------|---------|
| Log rotation | Daily | Prevent disk fill |
| Key rotation | Monthly | Security hygiene |
| Config backup | Weekly | Recovery capability |
| Health check | Hourly | Early warning |

### Retrieval Procedures

```
RETRIEVAL CHECKLIST:

1. Pre-Retrieval
   □ Confirm device still active
   □ Plan access method
   □ Prepare replacement (if needed)
   □ Have cover story

2. Retrieval
   □ Access location
   □ Remove device
   □ Restore original cabling
   □ Check for evidence left behind

3. Post-Retrieval
   □ Extract device logs
   □ Secure wipe device
   □ Mark device as retrieved
   □ Update inventory
```

---

## 📝 Reporting

### Daily Report Template

```markdown
# GhostBridge Daily Report
Date: YYYY-MM-DD
Operator: [Name]

## Device Status
| Device | Status | Uptime | Notes |
|--------|--------|--------|-------|
| ghost-001 | 🟢 | 14d | Normal |
| ghost-002 | 🟡 | 3d | Delayed beacons |

## Activity Summary
- Commands executed: 12
- Data collected: 150 MB
- Alerts: 0

## Issues
- None

## Tomorrow's Plan
- Monitor ghost-002
- Execute network scan on ghost-001
```

### Incident Report Template

```markdown
# GhostBridge Incident Report
Date: YYYY-MM-DD
Severity: [Critical/High/Medium/Low]

## Summary
Brief description of incident.

## Timeline
- HH:MM - Event 1
- HH:MM - Event 2

## Impact
What was affected?

## Response
What actions were taken?

## Root Cause
Why did this happen?

## Lessons Learned
What can we improve?

## Action Items
- [ ] Task 1
- [ ] Task 2
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

*GhostBridge Operations Guide v0.1.0*
*Classification: Red Team Internal*

