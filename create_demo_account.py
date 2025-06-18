#!/usr/bin/env python3
"""
Create demo account for Sprint 8 demo
"""

import json
import sys
import time

import requests

# Configuration
API_BASE_URL = "http://localhost:8081/api"
DEMO_ACCOUNTS = [
    {
        "email": "demo@example.com",
        "username": "demouser",
        "password": "DemoPass123!",
        "full_name": "Demo User",
    },
    {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "AdminPass123!",
        "full_name": "Admin User",
    },
]


def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        return response.status_code == 200
    except Exception:
        return False


def create_account(account_data):
    """Create a demo account"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=account_data,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 201:
            print(f"✓ Created account: {account_data['email']}")
            return True
        elif response.status_code == 409:
            print(f"! Account already exists: {account_data['email']}")
            return True
        else:
            print(f"✗ Failed to create {account_data['email']}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error creating account: {e}")
        return False


def login_test(email, password):
    """Test login with account"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Login successful for {email}")
            print(f"  Access token: {data.get('access_token', '')[:20]}...")
            return True
        else:
            print(f"✗ Login failed for {email}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error testing login: {e}")
        return False


def main():
    print("=== Creating Demo Accounts for Sprint 8 ===\n")

    # Check API health
    print("Checking API health...")
    retries = 5
    while retries > 0:
        if check_api_health():
            print("✓ API is running\n")
            break
        else:
            print(f"API not ready, retrying in 2 seconds... ({retries} retries left)")
            time.sleep(2)
            retries -= 1
    else:
        print("✗ API is not running. Please start Docker containers first.")
        print("Run: docker compose up -d")
        sys.exit(1)

    # Create demo accounts
    print("Creating demo accounts...")
    success_count = 0
    for account in DEMO_ACCOUNTS:
        if create_account(account):
            success_count += 1

    print(f"\n{success_count}/{len(DEMO_ACCOUNTS)} accounts ready")

    # Test login
    print("\nTesting login...")
    for account in DEMO_ACCOUNTS:
        login_test(account["email"], account["password"])

    # Print credentials
    print("\n=== Demo Credentials ===")
    print("\nPrimary Demo Account:")
    print(f"  Email: {DEMO_ACCOUNTS[0]['email']}")
    print(f"  Username: {DEMO_ACCOUNTS[0]['username']}")
    print(f"  Password: {DEMO_ACCOUNTS[0]['password']}")

    print("\nSecondary Demo Account:")
    print(f"  Email: {DEMO_ACCOUNTS[1]['email']}")
    print(f"  Username: {DEMO_ACCOUNTS[1]['username']}")
    print(f"  Password: {DEMO_ACCOUNTS[1]['password']}")

    print("\n✓ Demo setup complete!")
    print("\nYou can now login at: http://localhost:8090")


if __name__ == "__main__":
    main()
