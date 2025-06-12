# Emergency Procedures Training Guide

## Training Overview

**Duration**: 90 minutes  
**Format**: Scenario-based training with simulations  
**Participants**: All on-call engineers and team leads

## Learning Objectives

After this training, participants will be able to:
1. Quickly assess incident severity
2. Execute emergency response procedures
3. Communicate effectively during incidents
4. Perform rollbacks and recovery operations
5. Complete post-incident reviews

## Pre-Training Setup

### Required Access
- [ ] PagerDuty account
- [ ] AWS console access
- [ ] Production SSH keys
- [ ] Slack workspace
- [ ] Monitoring dashboards
- [ ] Runbook access

### Test Environment
```bash
# Verify access to test environment
ssh ubuntu@test-instance.example.com
cd ~/prism-deployment
docker-compose ps
```

## Module 1: Incident Detection & Assessment (20 min)

### 1.1 Alert Sources

**Automated Alerts**
- Prometheus/AlertManager
- CloudWatch alarms
- Synthetic monitoring
- Error tracking (Sentry)

**Manual Reports**
- Customer complaints
- Internal testing
- Performance degradation
- Security notifications

### 1.2 Severity Assessment

**Quick Assessment Questions:**
1. Is the service completely down?
2. How many users are affected?
3. Is there data loss risk?
4. Is this a security incident?

**Severity Matrix:**
```
┌─────────────┬──────────────┬────────────┐
│   Impact    │    Scope     │  Severity  │
├─────────────┼──────────────┼────────────┤
│   Total     │     All      │     P1     │
│   Total     │    Partial   │     P2     │
│  Degraded   │     All      │     P2     │
│  Degraded   │    Partial   │     P3     │
│   Minor     │     Any      │     P4     │
└─────────────┴──────────────┴────────────┘
```

### 1.3 Initial Response Drill

**Scenario**: API returns 503 errors

```bash
# 1. Acknowledge alert
pd-cli incident ack <incident-id>

# 2. Join incident channel
# Slack: #incident-2024-01-15

# 3. Initial assessment
curl -f https://prism.thepaynes.ca/api/health
docker-compose ps
docker-compose logs --tail=100 prism-server

# 4. Communicate status
"Investigating API 503 errors. Initial check shows service is running but not responding. Checking logs."
```

## Module 2: Emergency Procedures (30 min)

### 2.1 Service Restart Procedure

**When to use**: Service unresponsive but infrastructure healthy

```bash
#!/bin/bash
# emergency-restart.sh

echo "🚨 Emergency Restart Initiated"
echo "Time: $(date)"
echo "Engineer: $USER"

# 1. Capture current state
docker-compose ps > /tmp/pre-restart-state.txt
docker-compose logs --tail=1000 > /tmp/pre-restart-logs.txt

# 2. Graceful restart attempt
echo "Attempting graceful restart..."
docker-compose restart prism-server

# 3. Wait and check
sleep 30
if curl -f http://localhost:8081/api/health; then
    echo "✅ Service recovered"
    exit 0
fi

# 4. Hard restart if needed
echo "Performing hard restart..."
docker-compose down
docker-compose up -d

# 5. Verify
sleep 30
if curl -f http://localhost:8081/api/health; then
    echo "✅ Service recovered after hard restart"
else
    echo "❌ Service still down - escalate!"
    exit 1
fi
```

### 2.2 Database Recovery

**When to use**: Database connection issues or corruption

```sql
-- Check connections
SELECT count(*) FROM pg_stat_activity;

-- Kill long-running queries
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'active' 
  AND query_start < now() - interval '5 minutes'
  AND query NOT LIKE '%pg_stat_activity%';

-- Emergency vacuum
VACUUM FULL;
ANALYZE;

-- Check for locks
SELECT * FROM pg_locks WHERE granted = false;
```

### 2.3 Emergency Rollback

**When to use**: Bad deployment causing issues

```bash
#!/bin/bash
# rollback.sh

# 1. List recent deployments
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"

# 2. Rollback to previous version
PREVIOUS_VERSION=${1:-"v1.2.3"}
echo "Rolling back to $PREVIOUS_VERSION"

# 3. Update docker-compose
sed -i "s/:latest/:$PREVIOUS_VERSION/g" docker-compose.yml

# 4. Deploy previous version
docker-compose pull
docker-compose up -d

# 5. Verify
./scripts/health-check.sh
```

### 2.4 Emergency DNS Failover

**When to use**: PowerDNS failure

```bash
# 1. Verify DNS is down
dig @localhost -p 53 test.managed.prism.local

# 2. Switch to backup DNS
./scripts/dns-failover.sh

# 3. Update route53 (if applicable)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch file://dns-failover.json

# 4. Notify DNS changes
"DNS has been failed over to backup servers. TTL is 300s, full propagation in 5 minutes."
```

## Module 3: Communication Protocols (20 min)

### 3.1 Incident Communication Template

**Initial Alert**
```
🚨 INCIDENT ALERT - [P1/P2/P3]
Service: Prism DNS API
Impact: [Description of impact]
Start: [Time]
Lead: @[your-name]
Channel: #incident-[date]

Current Status: Investigating
Next Update: In 15 minutes
```

**Status Updates**
```
📊 UPDATE - [Time]
Status: [Investigating/Identified/Implementing/Monitoring]
Finding: [What we found]
Action: [What we're doing]
Impact: [Current user impact]
ETA: [Expected resolution time]
Next Update: [Time]
```

**Resolution**
```
✅ RESOLVED - [Time]
Duration: [Total time]
Root Cause: [Brief description]
Resolution: [What fixed it]
Impact: [# users, duration]
Follow-up: Post-mortem scheduled for [date/time]
```

### 3.2 Stakeholder Matrix

| Severity | Internal | External | Customer |
|----------|----------|----------|----------|
| P1 | Immediate | 30 min | 30 min |
| P2 | 30 min | 1 hour | 1 hour |
| P3 | 1 hour | Next day | If asked |
| P4 | Daily summary | No | No |

### 3.3 Communication Channels

**Internal**
- Slack: #incidents (automated)
- Slack: #incident-YYYY-MM-DD (war room)
- Email: incidents@company.com
- Phone: On-call phone tree

**External**
- Status page: status.prism-dns.com
- Twitter: @PrismDNSStatus
- Email: customers@prism-dns.com

## Module 4: Hands-On Scenarios (30 min)

### Scenario 1: Complete Outage

**Simulation Setup**
```bash
# Instructor breaks service
docker-compose stop prism-server postgres
```

**Expected Actions:**
1. Acknowledge alert (2 min)
2. Assess impact (3 min)
3. Communicate status (2 min)
4. Diagnose issue (5 min)
5. Implement fix (5 min)
6. Verify resolution (3 min)
7. Send resolution notice (2 min)

### Scenario 2: Performance Degradation

**Simulation Setup**
```bash
# Instructor creates high load
for i in {1..10000}; do
  curl -X POST http://localhost:8081/api/hosts \
    -d '{"hostname":"load-'$i'"}' &
done
```

**Expected Actions:**
1. Identify performance issue
2. Check resource usage
3. Implement rate limiting
4. Scale services if needed
5. Monitor recovery

### Scenario 3: Security Incident

**Simulation Setup**
```bash
# Suspicious activity in logs
echo "Failed password for root from 185.220.101.45" >> /var/log/auth.log
```

**Expected Actions:**
1. Isolate system
2. Preserve evidence
3. Block suspicious IPs
4. Rotate credentials
5. Notify security team

## Module 5: Post-Incident Review (10 min)

### 5.1 Timeline Construction

```markdown
## Incident Timeline

- **14:32** - First alert triggered (Prometheus)
- **14:33** - On-call engineer acknowledged
- **14:35** - Initial investigation started
- **14:38** - Issue identified (DB connection pool exhausted)
- **14:42** - Fix implemented (restart + config change)
- **14:45** - Service restored
- **14:50** - All-clear given
```

### 5.2 Five Whys Analysis

```
Problem: API returned 503 errors

Why? → Database connections were exhausted
Why? → Connection pool was too small
Why? → Traffic increased beyond expected levels
Why? → Marketing campaign launched without notice
Why? → No process for capacity planning communication

Root Cause: Lack of communication process between teams
```

### 5.3 Action Items Template

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| Increase connection pool size | DevOps | Tomorrow | High |
| Create capacity planning process | Tech Lead | Next Sprint | High |
| Add predictive alerts | SRE | Next Week | Medium |
| Update runbook | On-call | This Week | Medium |

## Training Exercises

### Exercise 1: Alert Response Speed Drill

**Setup**: Random alerts during training
**Goal**: < 5 minute acknowledgment
**Measurement**: Time to first action

### Exercise 2: Communication Practice

**Setup**: Role-play incident with observers
**Goal**: Clear, timely updates
**Measurement**: Communication checklist

### Exercise 3: Rollback Practice

**Setup**: Deploy "bad" version
**Goal**: Successfully rollback
**Measurement**: Time to recovery

## Certification Checklist

Before going on-call, engineers must:

- [ ] Complete this emergency training
- [ ] Shadow experienced on-call (1 week)
- [ ] Successfully handle test incident
- [ ] Know all runbook locations
- [ ] Have all necessary access
- [ ] Understand escalation process
- [ ] Practice communication templates
- [ ] Complete post-incident review

## Additional Resources

### Emergency Contacts

```yaml
escalation:
  L1_oncall: "+1-555-ONCALL1"
  L2_backup: "+1-555-ONCALL2"
  L3_manager: "+1-555-MANAGER"
  L4_director: "+1-555-DIRECTOR"

vendors:
  aws_support: "https://console.aws.amazon.com/support"
  cloudflare: "+1-555-CLOUDFL"
  datadog: "+1-555-DATADOG"

internal:
  security: "security@company.com"
  legal: "legal@company.com"
  pr: "pr@company.com"
```

### Quick Reference Card

```bash
# Service Health
curl https://prism.thepaynes.ca/api/health
docker-compose ps
docker-compose logs --tail=100

# Quick Restart
docker-compose restart prism-server

# Resource Check
docker stats --no-stream
df -h
free -m

# Network Check
netstat -tulpn | grep LISTEN
ss -s

# Database Check
docker exec postgres pg_isready
```

### Post-Training Survey

1. How confident are you in handling P1 incidents? (1-10)
2. What additional scenarios should we cover?
3. Which procedures need more clarification?
4. How can we improve this training?

## Continuous Improvement

### Monthly Drills
- First Monday: Communication drill
- Second Monday: Rollback drill
- Third Monday: Full scenario
- Fourth Monday: New scenario

### Metrics to Track
- Time to acknowledge
- Time to resolution
- Communication quality
- Procedure compliance
- Post-incident completion

---

*Remember: In an emergency, stay calm, follow the runbook, and communicate clearly. You've got this!*