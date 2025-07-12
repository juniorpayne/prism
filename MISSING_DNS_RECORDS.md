# Missing DNS Records for prism.thepaynes.ca

## Current Status

### ✅ Already Configured:
- Domain verification TXT record
- SPF record for prism.thepaynes.ca
- DMARC record
- Custom MAIL FROM MX record
- Custom MAIL FROM TXT record

### ❌ Missing DKIM Records:
You need to add these 3 CNAME records to enable DKIM signing:

```
zbvfrvlrviqelwdklety4be3i4bzuykg._domainkey.prism.thepaynes.ca  CNAME  zbvfrvlrviqelwdklety4be3i4bzuykg.dkim.amazonses.com
f42iaximjxnnwaqnefccemwn5iprgg5y._domainkey.prism.thepaynes.ca  CNAME  f42iaximjxnnwaqnefccemwn5iprgg5y.dkim.amazonses.com
tcul75llc66ye4rezsf6mixgjltcuso4._domainkey.prism.thepaynes.ca  CNAME  tcul75llc66ye4rezsf6mixgjltcuso4.dkim.amazonses.com
```

## How to Add in Your DNS Provider:

For each record:
- **Type**: CNAME (not TXT!)
- **Name**: The part before `.prism.thepaynes.ca` (e.g., `zbvfrvlrviqelwdklety4be3i4bzuykg._domainkey`)
- **Value**: The full `.dkim.amazonses.com` address

## Verification

Once added, you can verify with:
```bash
# Check each DKIM record
dig CNAME zbvfrvlrviqelwdklety4be3i4bzuykg._domainkey.prism.thepaynes.ca +short
dig CNAME f42iaximjxnnwaqnefccemwn5iprgg5y._domainkey.prism.thepaynes.ca +short
dig CNAME tcul75llc66ye4rezsf6mixgjltcuso4._domainkey.prism.thepaynes.ca +short

# Check DKIM status in AWS
aws ses get-identity-dkim-attributes --identities prism.thepaynes.ca --region us-east-1
```

DKIM verification status should change from "Pending" to "Success" within a few minutes after DNS propagation.