#!/bin/bash
# AWS SES Production Setup Script
# Sets up domain verification, DKIM, SPF, and monitoring for production email delivery

set -e

# Configuration
DOMAIN="${SES_DOMAIN:-prism.thepaynes.ca}"
REGION="${AWS_REGION:-us-east-1}"
CONFIG_SET="${SES_CONFIG_SET:-prism-dns-production}"
FROM_EMAIL="${SES_FROM_EMAIL:-noreply@$DOMAIN}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 AWS SES Production Setup${NC}"
echo "======================================"
echo "Domain: $DOMAIN"
echo "Region: $REGION"
echo "Configuration Set: $CONFIG_SET"
echo "From Email: $FROM_EMAIL"
echo ""

# Function to check AWS CLI
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
        exit 1
    fi
    
    # Check credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure'.${NC}"
        exit 1
    fi
}

# Function to verify domain
verify_domain() {
    echo -e "\n${YELLOW}📧 Verifying domain: $DOMAIN${NC}"
    
    # Check if already verified
    VERIFICATION_STATUS=$(aws ses get-identity-verification-attributes \
        --identities $DOMAIN \
        --region $REGION \
        --query "VerificationAttributes.\"$DOMAIN\".VerificationStatus" \
        --output text 2>/dev/null || echo "NotFound")
    
    if [ "$VERIFICATION_STATUS" == "Success" ]; then
        echo -e "${GREEN}✅ Domain already verified${NC}"
        return 0
    fi
    
    # Initiate verification
    VERIFY_OUTPUT=$(aws ses verify-domain-identity --domain $DOMAIN --region $REGION)
    VERIFY_TOKEN=$(echo $VERIFY_OUTPUT | jq -r '.VerificationToken')
    
    echo -e "${YELLOW}📝 Add this TXT record to your DNS:${NC}"
    echo -e "${GREEN}_amazonses.$DOMAIN  TXT  \"$VERIFY_TOKEN\"${NC}"
    echo ""
    
    # Save to file for reference
    echo "_amazonses.$DOMAIN  TXT  \"$VERIFY_TOKEN\"" > ses_dns_records.txt
}

# Function to enable DKIM
enable_dkim() {
    echo -e "\n${YELLOW}🔐 Enabling DKIM signing${NC}"
    
    # Enable DKIM
    aws ses put-identity-dkim-signing-attributes \
        --identity $DOMAIN \
        --dkim-signing-attributes "SigningEnabled=true" \
        --region $REGION &>/dev/null || true
    
    # Get DKIM tokens
    DKIM_TOKENS=$(aws ses get-identity-dkim-attributes \
        --identities $DOMAIN \
        --region $REGION \
        --query "DkimAttributes.\"$DOMAIN\".DkimTokens[]" \
        --output text)
    
    if [ -z "$DKIM_TOKENS" ]; then
        echo -e "${RED}❌ Failed to get DKIM tokens${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}📝 Add these CNAME records to your DNS:${NC}"
    i=1
    for token in $DKIM_TOKENS; do
        echo -e "${GREEN}dkim${i}._domainkey.$DOMAIN  CNAME  dkim${i}.amazonses.com${NC}"
        echo "dkim${i}._domainkey.$DOMAIN  CNAME  dkim${i}.amazonses.com" >> ses_dns_records.txt
        ((i++))
    done
    echo ""
}

# Function to set custom MAIL FROM domain
set_mail_from() {
    echo -e "\n${YELLOW}📮 Setting custom MAIL FROM domain${NC}"
    
    aws ses put-identity-mail-from-domain-attributes \
        --identity $DOMAIN \
        --mail-from-domain "mail.$DOMAIN" \
        --behavior-on-mx-failure UseDefaultValue \
        --region $REGION &>/dev/null || true
    
    echo -e "${YELLOW}📝 Add these records for custom MAIL FROM:${NC}"
    echo -e "${GREEN}mail.$DOMAIN  MX  10 feedback-smtp.$REGION.amazonses.com${NC}"
    echo -e "${GREEN}mail.$DOMAIN  TXT  \"v=spf1 include:amazonses.com ~all\"${NC}"
    
    # Add to file
    echo "" >> ses_dns_records.txt
    echo "mail.$DOMAIN  MX  10 feedback-smtp.$REGION.amazonses.com" >> ses_dns_records.txt
    echo "mail.$DOMAIN  TXT  \"v=spf1 include:amazonses.com ~all\"" >> ses_dns_records.txt
    echo ""
}

# Function to create configuration set
create_configuration_set() {
    echo -e "\n${YELLOW}⚙️  Creating configuration set: $CONFIG_SET${NC}"
    
    # Check if exists
    if aws ses describe-configuration-set \
        --configuration-set-name $CONFIG_SET \
        --region $REGION &>/dev/null; then
        echo -e "${GREEN}✅ Configuration set already exists${NC}"
    else
        # Create configuration set
        aws ses put-configuration-set \
            --configuration-set "Name=$CONFIG_SET" \
            --region $REGION
        echo -e "${GREEN}✅ Configuration set created${NC}"
    fi
    
    # Enable reputation tracking
    aws ses put-configuration-set-reputation-options \
        --configuration-set-name $CONFIG_SET \
        --reputation-tracking-enabled \
        --region $REGION &>/dev/null || true
}

# Function to create SNS topic for events
create_sns_topic() {
    echo -e "\n${YELLOW}📢 Creating SNS topic for bounce/complaint notifications${NC}"
    
    TOPIC_NAME="ses-${CONFIG_SET}-events"
    
    # Create topic
    TOPIC_ARN=$(aws sns create-topic \
        --name $TOPIC_NAME \
        --region $REGION \
        --query 'TopicArn' \
        --output text)
    
    echo -e "${GREEN}✅ SNS topic created: $TOPIC_ARN${NC}"
    
    # Subscribe webhook endpoint (if deployed)
    if [ ! -z "$WEBHOOK_URL" ]; then
        aws sns subscribe \
            --topic-arn $TOPIC_ARN \
            --protocol https \
            --notification-endpoint "$WEBHOOK_URL/api/webhooks/ses/notifications" \
            --region $REGION
        echo -e "${GREEN}✅ Webhook subscribed to SNS topic${NC}"
    fi
    
    echo $TOPIC_ARN
}

# Function to configure event destinations
configure_event_destinations() {
    echo -e "\n${YELLOW}📊 Configuring event destinations${NC}"
    
    # Create SNS topic first
    TOPIC_ARN=$(create_sns_topic)
    
    # Configure SNS destination for bounces and complaints
    aws ses put-configuration-set-event-destination \
        --configuration-set-name $CONFIG_SET \
        --event-destination \
            "Name=sns-events,Enabled=true,SNSDestination={TopicARN=$TOPIC_ARN},MatchingEventTypes=[bounce,complaint]" \
        --region $REGION &>/dev/null || echo "SNS destination may already exist"
    
    # Configure CloudWatch destination for metrics
    aws ses put-configuration-set-event-destination \
        --configuration-set-name $CONFIG_SET \
        --event-destination \
            "Name=cloudwatch-metrics,Enabled=true,CloudWatchDestination={DimensionConfigurations=[{DimensionName=MessageTag,DimensionValueSource=messageTag,DefaultDimensionValue=none}]},MatchingEventTypes=[send,bounce,complaint,delivery,reject,open,click]" \
        --region $REGION &>/dev/null || echo "CloudWatch destination may already exist"
    
    echo -e "${GREEN}✅ Event destinations configured${NC}"
}

# Function to display SPF and DMARC records
display_spf_dmarc() {
    echo -e "\n${YELLOW}📝 Additional DNS records (SPF and DMARC):${NC}"
    echo -e "${GREEN}$DOMAIN  TXT  \"v=spf1 include:amazonses.com ~all\"${NC}"
    echo -e "${GREEN}_dmarc.$DOMAIN  TXT  \"v=DMARC1; p=quarantine; rua=mailto:dmarc@$DOMAIN; ruf=mailto:dmarc@$DOMAIN; fo=1\"${NC}"
    
    # Add to file
    echo "" >> ses_dns_records.txt
    echo "$DOMAIN  TXT  \"v=spf1 include:amazonses.com ~all\"" >> ses_dns_records.txt
    echo "_dmarc.$DOMAIN  TXT  \"v=DMARC1; p=quarantine; rua=mailto:dmarc@$DOMAIN; ruf=mailto:dmarc@$DOMAIN; fo=1\"" >> ses_dns_records.txt
}

# Function to check verification status
check_verification_status() {
    echo -e "\n${YELLOW}✅ Checking domain verification status${NC}"
    
    aws ses get-identity-verification-attributes \
        --identities $DOMAIN \
        --region $REGION \
        --output table
    
    # Check DKIM status
    echo -e "\n${YELLOW}🔐 DKIM verification status:${NC}"
    aws ses get-identity-dkim-attributes \
        --identities $DOMAIN \
        --region $REGION \
        --query "DkimAttributes.\"$DOMAIN\"" \
        --output table
}

# Function to test email sending
test_email_send() {
    echo -e "\n${YELLOW}📧 Testing email send (sandbox mode)${NC}"
    
    if [ -z "$TEST_EMAIL" ]; then
        echo -e "${YELLOW}⚠️  Set TEST_EMAIL environment variable to test sending${NC}"
        return
    fi
    
    # Create test message
    cat > test-email.json <<EOF
{
    "Source": "$FROM_EMAIL",
    "Destination": {
        "ToAddresses": ["$TEST_EMAIL"]
    },
    "Message": {
        "Subject": {
            "Data": "Prism DNS - SES Test Email",
            "Charset": "UTF-8"
        },
        "Body": {
            "Text": {
                "Data": "This is a test email from Prism DNS to verify SES configuration.",
                "Charset": "UTF-8"
            },
            "Html": {
                "Data": "<h1>Prism DNS</h1><p>This is a test email to verify SES configuration.</p>",
                "Charset": "UTF-8"
            }
        }
    },
    "ConfigurationSetName": "$CONFIG_SET"
}
EOF
    
    # Send test email
    if aws ses send-email \
        --cli-input-json file://test-email.json \
        --region $REGION &>/dev/null; then
        echo -e "${GREEN}✅ Test email sent successfully to $TEST_EMAIL${NC}"
    else
        echo -e "${RED}❌ Failed to send test email. You may need to verify $TEST_EMAIL in SES sandbox.${NC}"
    fi
    
    rm -f test-email.json
}

# Function to display next steps
display_next_steps() {
    echo -e "\n${GREEN}📋 Next Steps:${NC}"
    echo "======================================"
    echo "1. Add all DNS records from 'ses_dns_records.txt' to your DNS provider"
    echo "2. Wait for DNS propagation (can take up to 72 hours)"
    echo "3. Run this script again to check verification status"
    echo "4. Request production access (exit sandbox) at:"
    echo "   https://console.aws.amazon.com/ses/home?region=$REGION#/account"
    echo "5. Update the webhook URL and run again to subscribe to SNS"
    echo "6. Test email delivery with: TEST_EMAIL=your@email.com ./setup-ses-production.sh"
    echo ""
    echo -e "${YELLOW}📄 DNS records saved to: ses_dns_records.txt${NC}"
    echo -e "${YELLOW}🔍 Check DNS propagation: dig TXT _amazonses.$DOMAIN${NC}"
}

# Main execution
main() {
    check_aws_cli
    
    case "${1:-all}" in
        verify)
            check_verification_status
            ;;
        test)
            test_email_send
            ;;
        all)
            verify_domain
            enable_dkim
            set_mail_from
            create_configuration_set
            configure_event_destinations
            display_spf_dmarc
            echo ""
            check_verification_status
            display_next_steps
            ;;
        *)
            echo "Usage: $0 [all|verify|test]"
            echo "  all    - Complete setup (default)"
            echo "  verify - Check verification status only"
            echo "  test   - Send test email (requires TEST_EMAIL env var)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"