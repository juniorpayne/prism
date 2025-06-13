#!/usr/bin/env python3
"""
Authentication Demo Script
Demonstrates the user registration and JWT authentication flow
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx


class AuthDemo:
    def __init__(self, base_url="http://localhost:8081"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.access_token = None
        self.refresh_token = None

    async def close(self):
        await self.client.aclose()

    def print_section(self, title):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    def print_response(self, response):
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except Exception:
            print(f"Response: {response.text}")

    async def demo_registration(self):
        self.print_section("1. USER REGISTRATION")

        # Generate unique user data
        timestamp = int(datetime.now().timestamp())
        user_data = {
            "email": f"demo{timestamp}@example.com",
            "username": f"demouser{timestamp}",
            "password": "SecurePassword123!",
        }

        print(f"Registering user: {user_data['username']}")
        print(f"Email: {user_data['email']}")

        response = await self.client.post(f"{self.base_url}/api/auth/register", json=user_data)

        self.print_response(response)
        return user_data

    async def demo_login(self, username, password):
        self.print_section("2. JWT LOGIN")

        print(f"Logging in as: {username}")

        response = await self.client.post(
            f"{self.base_url}/api/auth/login", json={"username": username, "password": password}
        )

        self.print_response(response)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            print(f"\n✅ Successfully obtained JWT tokens!")
            print(f"Access token expires in: {data['expires_in']} seconds")

    async def demo_protected_endpoint(self):
        self.print_section("3. ACCESS PROTECTED ENDPOINT")

        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return

        print("Accessing /api/auth/me with JWT token...")

        response = await self.client.get(
            f"{self.base_url}/api/auth/me", headers={"Authorization": f"Bearer {self.access_token}"}
        )

        self.print_response(response)

    async def demo_refresh_token(self):
        self.print_section("4. REFRESH ACCESS TOKEN")

        if not self.refresh_token:
            print("❌ No refresh token available. Please login first.")
            return

        print("Refreshing access token...")

        response = await self.client.post(
            f"{self.base_url}/api/auth/refresh", json={"refresh_token": self.refresh_token}
        )

        self.print_response(response)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            print(f"\n✅ Successfully refreshed access token!")

    async def demo_logout(self):
        self.print_section("5. LOGOUT")

        if not self.access_token:
            print("❌ No access token available. Please login first.")
            return

        print("Logging out and revoking tokens...")

        response = await self.client.post(
            f"{self.base_url}/api/auth/logout",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

        self.print_response(response)

        # Try to use the token after logout
        print("\nTrying to access protected endpoint after logout...")
        response = await self.client.get(
            f"{self.base_url}/api/auth/me", headers={"Authorization": f"Bearer {self.access_token}"}
        )

        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Token properly revoked after logout!")

    async def run_demo(self):
        print("\n🚀 PRISM DNS AUTHENTICATION DEMO")
        print("================================\n")

        try:
            # Test API health
            response = await self.client.get(f"{self.base_url}/api/health")
            if response.status_code != 200:
                print("❌ API is not responding. Please ensure Docker services are running.")
                return

            print("✅ API is healthy and ready!\n")

            # Note about email verification
            print("ℹ️  NOTE: This demo simulates an already verified user.")
            print("    In production, email verification is required before login.\n")

            # For demo, we'll use a pre-existing verified user
            # In real scenario, you'd need to verify email first
            demo_user = {"username": "testuser", "password": "TestPassword123!"}

            # Try login with demo user
            await self.demo_login(demo_user["username"], demo_user["password"])

            if self.access_token:
                # Demo protected endpoint
                await self.demo_protected_endpoint()

                # Demo token refresh
                await self.demo_refresh_token()

                # Demo logout
                await self.demo_logout()
            else:
                print("\n⚠️  Demo user not found. Creating a new user...")

                # Register new user
                user_data = await self.demo_registration()

                print("\n⚠️  Email verification required!")
                print("    In production, check email for verification link.")
                print("    For demo purposes, check server logs for the verification token.")

        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            await self.close()


async def main():
    demo = AuthDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
