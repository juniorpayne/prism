#!/bin/bash

echo "🔍 Checking DKIM DNS Propagation for prism.thepaynes.ca"
echo "======================================================"
echo ""

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Checking DNS records..."
    
    # Check DKIM records
    DKIM1=$(dig CNAME f42iaximjxnnwaqnefccemwn5iprgg5y._domainkey.prism.thepaynes.ca +short)
    DKIM2=$(dig CNAME tcul75llc66ye4rezsf6mixgjltcuso4._domainkey.prism.thepaynes.ca +short)
    DKIM3=$(dig CNAME zbvfrvlrviqelwdklety4be3i4bzuykg._domainkey.prism.thepaynes.ca +short)
    
    if [[ -n "$DKIM1" && -n "$DKIM2" && -n "$DKIM3" ]]; then
        echo "✅ All DKIM records have propagated!"
        echo "  DKIM1: $DKIM1"
        echo "  DKIM2: $DKIM2"
        echo "  DKIM3: $DKIM3"
        echo ""
        echo "Checking AWS SES DKIM verification status..."
        aws ses get-identity-dkim-attributes --identities prism.thepaynes.ca --region us-east-1 | jq -r '.DkimAttributes."prism.thepaynes.ca".DkimVerificationStatus'
        break
    else
        echo "⏳ DKIM records not yet propagated. Waiting..."
        [[ -n "$DKIM1" ]] && echo "  ✓ DKIM1: $DKIM1" || echo "  ✗ DKIM1: Not found"
        [[ -n "$DKIM2" ]] && echo "  ✓ DKIM2: $DKIM2" || echo "  ✗ DKIM2: Not found"
        [[ -n "$DKIM3" ]] && echo "  ✓ DKIM3: $DKIM3" || echo "  ✗ DKIM3: Not found"
    fi
    
    echo ""
    sleep 60
done

echo ""
echo "🎉 DNS propagation complete! You can now send DKIM-signed emails."