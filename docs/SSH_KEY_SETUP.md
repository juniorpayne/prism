# SSH Key Setup for GitHub Actions

This guide explains how to properly set up the EC2_SSH_KEY secret in GitHub for deployment.

## Prerequisites

- Access to your EC2 instance's private SSH key (usually a .pem file)
- GitHub repository admin access to set secrets

## Step 1: Prepare Your SSH Key

First, ensure your SSH key is in the correct format:

```bash
# If you have a .pem file from AWS
cat your-key.pem
```

The key should look like one of these formats:

### RSA Format (older)
```
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
[multiple lines of base64 encoded data]
...
-----END RSA PRIVATE KEY-----
```

### OpenSSH Format (newer)
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAAAdzc2gtcn...
[multiple lines of base64 encoded data]
...
-----END OPENSSH PRIVATE KEY-----
```

## Step 2: Verify Key Format

Before adding to GitHub, verify your key works:

```bash
# Test if the key is valid
ssh-keygen -y -f your-key.pem > /dev/null && echo "Key is valid" || echo "Key is invalid"

# Test connection to EC2
ssh -i your-key.pem ubuntu@35.170.180.10 "echo 'Connection successful'"
```

## Step 3: Copy the Key Content

Copy the ENTIRE contents of your key file, including:
- The `-----BEGIN` line
- All the encoded content
- The `-----END` line

```bash
# Copy to clipboard on macOS
cat your-key.pem | pbcopy

# Copy to clipboard on Linux (with xclip)
cat your-key.pem | xclip -selection clipboard

# Or just display and manually copy
cat your-key.pem
```

## Step 4: Add to GitHub Secrets

1. Go to your GitHub repository
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `EC2_SSH_KEY`
5. Value: Paste the ENTIRE key content
6. Click **Add secret**

## Important Notes

### DO NOT:
- Add quotes around the key
- Modify line endings
- Add extra spaces or characters
- Use a public key (.pub file)
- Share this key publicly

### DO:
- Include the BEGIN and END lines
- Preserve all line breaks
- Keep the exact formatting
- Test the key locally first

## Troubleshooting

### "error in libcrypto"
This usually means:
1. The key format is corrupted
2. Line endings were changed (CRLF vs LF)
3. The key was truncated
4. Extra characters were added

### "Permission denied (publickey)"
This usually means:
1. Wrong key for the EC2 instance
2. Wrong username (should be `ubuntu` for Ubuntu AMIs)
3. Key permissions are incorrect (should be 600)

### Testing Your Secret

You can test if the secret is properly set by running the deploy workflow and checking the "Setup SSH Authentication" step output.

## Alternative: Using GitHub's CLI

```bash
# Using GitHub CLI to set the secret
gh secret set EC2_SSH_KEY < your-key.pem
```

## Security Best Practices

1. **Rotate Keys Regularly**: Change SSH keys periodically
2. **Limit Key Access**: Only use this key for deployment
3. **Use Key Pairs**: Generate deployment-specific keys
4. **Monitor Usage**: Check GitHub Actions logs for unauthorized use

## Example Setup Script

```bash
#!/bin/bash
# setup-deploy-key.sh

# Check if key file exists
if [ ! -f "$1" ]; then
    echo "Usage: $0 <path-to-key.pem>"
    exit 1
fi

KEY_FILE="$1"

# Validate key
if ssh-keygen -y -f "$KEY_FILE" > /dev/null 2>&1; then
    echo "✅ Key is valid"
else
    echo "❌ Key is invalid"
    exit 1
fi

# Test connection
echo "Testing connection to EC2..."
if ssh -i "$KEY_FILE" -o ConnectTimeout=5 ubuntu@35.170.180.10 "echo 'Success'" 2>/dev/null; then
    echo "✅ Connection successful"
else
    echo "❌ Connection failed"
    exit 1
fi

echo ""
echo "Key is valid and working. Copy the following content to GitHub Secrets:"
echo "Secret name: EC2_SSH_KEY"
echo "Secret value:"
echo "---"
cat "$KEY_FILE"
echo "---"
```

Save this script and run:
```bash
chmod +x setup-deploy-key.sh
./setup-deploy-key.sh your-key.pem
```