# Prism Client Authentication Migration Guide

## Overview
Starting with version 1.1.0, Prism clients **require** API token authentication. All TCP clients must have a valid API token to register hosts. This ensures proper user isolation and security.

## Why Authentication is Required
- **User Isolation**: Hosts are associated with your user account
- **Security**: Prevents unauthorized host registration
- **Audit Trail**: Track which clients are registering hosts
- **Access Control**: Manage which clients can register hosts on your behalf

## Migration Steps

### Step 1: Generate an API Token
1. Log in to the Prism web interface
2. Navigate to Settings → API Tokens
3. Click "Generate New Token"
4. Give your token a descriptive name (e.g., "Home Server", "Office Network")
5. Choose an expiration period or leave it as "Never expire"
6. **Important**: Save the generated token immediately - you won't be able to see it again!

### Step 2: Update Your Client Configuration

#### Option A: Configuration File (Recommended)
Edit your `prism-client.yaml` file and add the **required** `auth_token` field:

```yaml
# Server connection settings
server:
  host: prism.example.com
  port: 8080
  timeout: 10
  auth_token: "your-generated-token-here"  # REQUIRED
```

**Important**: The client will not start without a valid auth_token in the configuration.

#### Option B: Command Line Override
You can override the configuration file token via command line:

```bash
./prism_client.py --config prism-client.yaml --auth-token "your-generated-token-here"
```

**Note**: Command line tokens override configuration file tokens.

### Step 3: Restart Your Client
After adding the token, restart your Prism client:

```bash
# If running as a service
./prism_client.py --stop --config prism-client.yaml
./prism_client.py --daemon --config prism-client.yaml

# If running in foreground
# Stop with Ctrl+C and restart
./prism_client.py --config prism-client.yaml
```

### Step 4: Verify Authentication
Check your client logs to confirm authentication is working:

```bash
grep "API token authentication" prism-client.log
# Should see: "Client configured with API token authentication"
```

In the web interface, newly registered hosts will appear under your account.

## Breaking Changes
- **Token Required**: All clients must have a valid auth_token
- **No Anonymous Registration**: Clients without tokens will fail to start
- **Immediate Migration Required**: Update all clients before upgrading

## Security Best Practices
1. **One Token Per Client**: Generate separate tokens for each client location
2. **Use Descriptive Names**: Name tokens by location or purpose
3. **Set Expiration**: Consider using expiring tokens for better security
4. **Secure Storage**: Treat tokens like passwords - store them securely
5. **Regular Rotation**: Periodically rotate tokens, especially for critical systems

## Troubleshooting

### Client Won't Start
- **Error**: "Missing required field: server.auth_token"
  - **Fix**: Add the auth_token field to your configuration file

- **Error**: "auth_token must be a string"
  - **Fix**: Ensure token is quoted in YAML: `auth_token: "token-here"`

- **Error**: "auth_token cannot be empty"
  - **Fix**: Provide a valid token, not an empty string

- **Error**: "auth_token appears to be invalid (too short)"
  - **Fix**: Verify you copied the complete token (should be at least 10 characters)

- **Error**: "auth_token cannot contain spaces"
  - **Fix**: Remove any spaces from the token value

### Authentication Not Working
1. Check client logs for authentication messages
2. Verify token is active in web interface (Settings → API Tokens)
3. Ensure token hasn't expired
4. Try using `--auth-token` command line option to test

### Client Connection Errors
- Verify the server has been updated to support token authentication
- Check that the token is valid and not revoked
- Ensure network connectivity to the server

## Token Management

### Revoking Tokens
If a token is compromised:
1. Go to Settings → API Tokens
2. Click "Revoke" next to the compromised token
3. Generate a new token
4. Update client configuration
5. Restart client

### Monitoring Token Usage
The web interface shows:
- Last used timestamp for each token
- Which tokens are active/revoked
- Token expiration dates

## Example Configurations

### Home Network Client
```yaml
server:
  host: prism.mycompany.com
  port: 8080
  timeout: 10
  auth_token: "home-token-abcd1234efgh5678ijkl9012mnop3456"

heartbeat:
  interval: 60  # Check in every minute
```

### Office Network Client
```yaml
server:
  host: prism.mycompany.com
  port: 8080
  timeout: 10
  auth_token: "office-token-qrst1234uvwx5678yzab9012cdef3456"

heartbeat:
  interval: 300  # Check in every 5 minutes
```

## FAQ

**Q: Will my existing clients stop working?**
A: Yes, all clients must be updated with valid auth tokens before upgrading to version 1.1.0.

**Q: Can I use the same token for multiple clients?**
A: Yes, but it's not recommended. Use separate tokens for better security and tracking.

**Q: What happens if my token expires?**
A: The client will fail to register hosts. You must generate a new token and update your configuration.

**Q: What happens if I don't add a token?**
A: The client will fail to start with an error: "Missing required field: server.auth_token"

**Q: How do I know which hosts belong to which token?**
A: Currently, hosts are associated with users, not specific tokens. Token-level tracking may be added in future versions.

## Support
For additional help:
- Check the [main documentation](README.md)
- Review client logs for detailed error messages
- Contact your system administrator