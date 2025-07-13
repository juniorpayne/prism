# \!/usr/bin/env python3
import boto3

ses = boto3.client("ses", region_name="us-east-1")

try:
    response = ses.send_email(
        Source="noreply@prism.thepaynes.ca",
        Destination={"ToAddresses": ["junior@thepaynes.ca"]},
        Message={
            "Subject": {"Data": "Prism DNS - SES Test Email"},
            "Body": {
                "Text": {
                    "Data": "This is a test email from Prism DNS.\n\nIf you received this, AWS SES is configured correctly\!"
                },
                "Html": {
                    "Data": "<h1>Prism DNS Test</h1><p>This is a test email from <strong>Prism DNS</strong>.</p><p>If you received this, AWS SES is configured correctly\!</p>"
                },
            },
        },
        ConfigurationSetName="prism-dns-production",
    )
    print("Test email sent successfully\!")
    print(f"Message ID: {response['MessageId']}")
except Exception as e:
    print(f"Failed to send email: {e}")
