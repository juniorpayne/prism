# Sprint Demo: TCP Client Authentication & User Isolation

## Demo Overview
This demo showcases the complete TCP client authentication system implemented in SCRUM-135 epic, demonstrating:
1. API token generation for TCP clients
2. Client configuration with authentication
3. User-specific host isolation
4. Admin capabilities for viewing all hosts

## Pre-Demo Setup

### 1. Create Demo Users
```bash
# In the web UI, create two demo users:
# - User 1: alice@example.com (regular user)
# - User 2: bob@example.com (regular user)
# - Admin: admin@example.com (admin user)
```

### 2. Generate API Tokens
```bash
# Log in as each user and generate tokens via web UI
# Navigate to Profile > API Tokens > Generate New Token
# Save the tokens for demo:
# - Alice's token: [will be generated]
# - Bob's token: [will be generated]
```

## Demo Script

### Part 1: Show the Problem (No Authentication)
```bash
# Show old client config without authentication
cat prism-client-old.yaml
```

**Talking Points:**
- Previously, all TCP clients registered anonymously
- No way to know which user owns which host
- No access control or user isolation

### Part 2: New Client Configuration

#### Alice's Client Configuration
```bash
# Show Alice's client configuration
cat demo/alice-prism-client.yaml
```

```yaml
service:
  name: prism-client-alice
  description: "Alice's Prism Host Client"
  pid_file: /tmp/prism-client-alice.pid

server:
  host: localhost
  port: 8080
  timeout: 10
  auth_token: "alice-token-here"  # REQUIRED - New field!

heartbeat:
  interval: 5

network:
  hostname: alice-laptop.example.com

logging:
  level: INFO
  file: /tmp/prism-client-alice.log
```

#### Bob's Client Configuration
```bash
# Show Bob's client configuration
cat demo/bob-prism-client.yaml
```

```yaml
service:
  name: prism-client-bob
  description: "Bob's Prism Host Client"
  pid_file: /tmp/prism-client-bob.pid

server:
  host: localhost
  port: 8080
  timeout: 10
  auth_token: "bob-token-here"  # REQUIRED - New field!

heartbeat:
  interval: 5

network:
  hostname: bob-server.example.com

logging:
  level: INFO
  file: /tmp/prism-client-bob.log
```

### Part 3: Run the Clients

```bash
# Terminal 1 - Run Alice's client
cd /home/junior/managedDns
python prism_client.py -c demo/alice-prism-client.yaml start

# Terminal 2 - Run Bob's client  
python prism_client.py -c demo/bob-prism-client.yaml start

# Show the logs to see authentication
tail -f /tmp/prism-client-alice.log
# Look for: "Client configured with API token authentication"
```

### Part 4: User Isolation in Web UI

1. **Log in as Alice**
   - Navigate to Dashboard
   - Show only Alice's host (alice-laptop.example.com) is visible
   - Show host count: 1
   - Try to access Bob's host ID directly - get 404

2. **Log in as Bob**
   - Navigate to Dashboard
   - Show only Bob's host (bob-server.example.com) is visible
   - Show host count: 1
   - Cannot see Alice's hosts

3. **Log in as Admin**
   - Navigate to Dashboard
   - Initially see only admin's hosts (if any)
   - Toggle "Show all users' hosts" 
   - Now see all hosts with Owner column
   - Show system statistics

### Part 5: API Demonstration

```bash
# Get Alice's JWT token
ALICE_TOKEN="Bearer [alice-jwt-token]"

# Alice can only see her hosts
curl -H "Authorization: $ALICE_TOKEN" http://localhost:8000/api/v1/hosts
# Returns: Only alice-laptop.example.com

# Admin can see all hosts
ADMIN_TOKEN="Bearer [admin-jwt-token]"
curl -H "Authorization: $ADMIN_TOKEN" http://localhost:8000/api/v1/hosts?all=true
# Returns: All hosts with owner information

# Show statistics endpoint
curl -H "Authorization: $ALICE_TOKEN" http://localhost:8000/api/v1/hosts/stats/summary
# Returns: Alice's stats only

curl -H "Authorization: $ADMIN_TOKEN" http://localhost:8000/api/v1/hosts/stats/summary
# Returns: Admin stats + system_stats
```

### Part 6: Security Features

1. **Token Revocation**
   - Show token management UI
   - Revoke one of Alice's tokens
   - Try to use revoked token - fails immediately

2. **Failed Authentication**
   ```bash
   # Show what happens with invalid token
   cat demo/invalid-client.yaml  # Has invalid token
   python prism_client.py -c demo/invalid-client.yaml start
   # Client fails to start with clear error
   ```

3. **Missing Token**
   ```bash
   # Show what happens without token
   cat demo/no-auth-client.yaml  # Missing auth_token
   python prism_client.py -c demo/no-auth-client.yaml start
   # Error: "Missing required field: server.auth_token"
   ```

## Key Benefits to Highlight

1. **User Ownership**: Every host is now associated with a user
2. **Access Control**: Users can only see/manage their own hosts
3. **Security**: Tokens can be revoked immediately if compromised
4. **Audit Trail**: All token usage is tracked (IP, timestamp)
5. **Admin Oversight**: Admins can view all hosts when needed
6. **Simple Implementation**: Just add auth_token to existing config

## Demo Cleanup

```bash
# Stop the demo clients
python prism_client.py -c demo/alice-prism-client.yaml stop
python prism_client.py -c demo/bob-prism-client.yaml stop

# Clean up PID files
rm /tmp/prism-client-*.pid
```

## Questions to Anticipate

1. **Q: What happens to existing clients without tokens?**
   A: They won't work - this is a breaking change. All clients must be updated with tokens.

2. **Q: Can we migrate existing anonymous hosts?**
   A: Yes, but that would be a separate task. For now, start fresh with authenticated clients.

3. **Q: How secure are the tokens?**
   A: Tokens are bcrypt hashed in the database, transmitted over TCP (should use TLS in production).

4. **Q: Can one user have multiple tokens?**
   A: Yes, users can generate multiple tokens for different clients/locations.

5. **Q: What about rate limiting?**
   A: Token creation is rate-limited (10 per hour). Token validation has caching to reduce DB load.