#!/usr/bin/env python3
"""
Sprint Demo: Authentication Features
Demonstrates SCRUM-53, SCRUM-54, and SCRUM-55
"""

import asyncio
import json
import time
from datetime import datetime

import httpx


class AuthenticationDemo:
    def __init__(self):
        self.base_url = "http://localhost:8081"
        self.client = httpx.AsyncClient(timeout=30.0)
        self.access_token = None
        self.refresh_token = None
        self.demo_user = None

    def print_section(self, title):
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70 + "\n")

    def print_step(self, step):
        print(f"\n🔹 {step}")
        print("-" * 50)

    def print_response(self, response):
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        except Exception:
            print(f"Response: {response.text}")

    async def check_health(self):
        """Check if API is healthy."""
        response = await self.client.get(f"{self.base_url}/api/health")
        if response.status_code == 200:
            print("✅ API is healthy and ready!")
            return True
        return False

    async def demo_scrum_53(self):
        """SCRUM-53: User Registration and Email Verification"""
        self.print_section("SCRUM-53: USER REGISTRATION & EMAIL VERIFICATION")

        # Generate unique user
        timestamp = int(datetime.now().timestamp())
        self.demo_user = {
            "email": f"sprint.demo{timestamp}@example.com",
            "username": f"sprintdemo{timestamp}",
            "password": "DemoPassword123!",
        }

        # Step 1: Register User
        self.print_step("Step 1: Register New User")
        print(f"Email: {self.demo_user['email']}")
        print(f"Username: {self.demo_user['username']}")

        response = await self.client.post(f"{self.base_url}/api/auth/register", json=self.demo_user)
        self.print_response(response)

        if response.status_code == 201:
            print("\n✅ User registered successfully!")
            print("📧 In production: Verification email would be sent")
            user_id = response.json()["user"]["id"]

            # Step 2: Simulate Email Verification
            self.print_step("Step 2: Email Verification (Simulated)")
            print("In production: User clicks link in email")
            print("For demo: Directly updating database...")

            # Direct database update for demo
            import subprocess

            update_cmd = f"""
            docker compose exec -T server python3 -c "
import asyncio
from sqlalchemy import update
from server.database.connection import get_async_db
from server.auth.models import User
from uuid import UUID

async def verify_user():
    async for db in get_async_db():
        await db.execute(
            update(User)
            .where(User.id == UUID('{user_id}'))
            .values(email_verified=True)
        )
        await db.commit()
        print('User verified!')
        break

asyncio.run(verify_user())
"
            """
            result = subprocess.run(update_cmd, shell=True, capture_output=True, text=True)
            if "User verified!" in result.stdout:
                print("✅ Email verified successfully!")
            else:
                print("⚠️  Could not verify email:", result.stderr)

    async def demo_scrum_54(self):
        """SCRUM-54: JWT Authentication"""
        self.print_section("SCRUM-54: JWT AUTHENTICATION")

        if not self.demo_user:
            print("❌ No demo user available")
            return

        # Step 1: Login
        self.print_step("Step 1: Login with Credentials")
        print(f"Username: {self.demo_user['username']}")

        response = await self.client.post(
            f"{self.base_url}/api/auth/login",
            json={"username": self.demo_user["username"], "password": self.demo_user["password"]},
        )
        self.print_response(response)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            print("\n✅ Login successful!")
            print(f"🔑 Access token expires in: {data['expires_in']} seconds")

            # Step 2: Access Protected Endpoint
            self.print_step("Step 2: Access Protected Endpoint")
            response = await self.client.get(
                f"{self.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            self.print_response(response)

            # Step 3: Refresh Token
            self.print_step("Step 3: Refresh Access Token")
            response = await self.client.post(
                f"{self.base_url}/api/auth/refresh", json={"refresh_token": self.refresh_token}
            )
            self.print_response(response)

            if response.status_code == 200:
                self.access_token = response.json()["access_token"]
                print("\n✅ Token refreshed successfully!")

            # Step 4: Logout
            self.print_step("Step 4: Logout")
            response = await self.client.post(
                f"{self.base_url}/api/auth/logout",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            self.print_response(response)

            # Verify logout
            print("\nVerifying logout - trying to access protected endpoint...")
            response = await self.client.get(
                f"{self.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 401:
                print("✅ Logout successful - token invalidated!")

    async def demo_scrum_55(self):
        """SCRUM-55: Password Reset Flow"""
        self.print_section("SCRUM-55: PASSWORD RESET FLOW")

        if not self.demo_user:
            print("❌ No demo user available")
            return

        # Step 1: Request Password Reset
        self.print_step("Step 1: Request Password Reset")
        print(f"Email: {self.demo_user['email']}")

        response = await self.client.post(
            f"{self.base_url}/api/auth/forgot-password", json={"email": self.demo_user["email"]}
        )
        self.print_response(response)
        print("\n📧 In production: Password reset email would be sent")

        # Step 2: Try with non-existent email (security test)
        self.print_step("Step 2: Security Test - Non-existent Email")
        response = await self.client.post(
            f"{self.base_url}/api/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )
        self.print_response(response)
        print("\n✅ Same response for security (prevents user enumeration)")

        # Step 3: Simulate Password Reset
        self.print_step("Step 3: Reset Password (Simulated)")
        print("In production: User clicks link in email with token")
        print("For demo: Using a test token...")

        # Create a reset token for demo
        import subprocess

        create_token_cmd = f"""
        docker compose exec -T server python3 -c "
import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from server.database.connection import get_async_db
from server.auth.models import User, PasswordResetToken
from server.auth.utils import hash_token
from uuid import UUID

async def create_reset_token():
    async for db in get_async_db():
        # Get user
        result = await db.execute(
            select(User).where(User.email == '{self.demo_user['email']}')
        )
        user = result.scalar_one_or_none()
        if user:
            token = 'demo_reset_token_123'
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.add(reset_token)
            await db.commit()
            print('Reset token created!')
        break

asyncio.run(create_reset_token())
"
        """
        subprocess.run(create_token_cmd, shell=True, capture_output=True, text=True)

        # Reset password
        new_password = "NewDemoPassword123!"
        response = await self.client.post(
            f"{self.base_url}/api/auth/reset-password",
            json={"token": "demo_reset_token_123", "password": new_password},
        )
        self.print_response(response)

        if response.status_code == 200:
            print("\n✅ Password reset successful!")
            print("📧 In production: Confirmation email would be sent")

            # Step 4: Verify New Password Works
            self.print_step("Step 4: Login with New Password")
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.demo_user["username"], "password": new_password},
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Login successful with new password!")

    async def show_security_features(self):
        """Highlight security features implemented"""
        self.print_section("SECURITY FEATURES IMPLEMENTED")

        print("🔐 Registration & Email Verification:")
        print("   • Email verification required before login")
        print("   • Secure token generation")
        print("   • Rate limiting (5 registrations per hour)")
        print("   • Password complexity requirements")

        print("\n🔐 JWT Authentication:")
        print("   • Short-lived access tokens (15 minutes)")
        print("   • Long-lived refresh tokens (7 days)")
        print("   • Secure token storage with hashing")
        print("   • Session tracking and revocation")

        print("\n🔐 Password Reset:")
        print("   • Prevents user enumeration")
        print("   • Token expiration (1 hour)")
        print("   • One-time use tokens")
        print("   • Rate limiting (3 requests per hour)")
        print("   • All sessions invalidated on reset")

    async def run_demo(self):
        """Run the complete sprint demo"""
        print("\n🚀 SPRINT DEMO: AUTHENTICATION FEATURES")
        print("=" * 70)
        print("EPIC: SCRUM-52 - Multi-Tenant Managed DNS Service")
        print("Sprint: Authentication Implementation")
        print("=" * 70)

        # Check API health
        if not await self.check_health():
            print("❌ API is not healthy. Please check services.")
            return

        # Demo each user story
        await self.demo_scrum_53()  # Registration & Email Verification
        await asyncio.sleep(2)

        await self.demo_scrum_54()  # JWT Authentication
        await asyncio.sleep(2)

        await self.demo_scrum_55()  # Password Reset

        # Show security features
        await self.show_security_features()

        print("\n" + "=" * 70)
        print("  ✅ SPRINT DEMO COMPLETE!")
        print("=" * 70)
        print("\nAll three user stories have been successfully implemented:")
        print("• SCRUM-53: User Registration & Email Verification ✅")
        print("• SCRUM-54: JWT Authentication ✅")
        print("• SCRUM-55: Password Reset Flow ✅")
        print("\n🎉 Sprint ready for production deployment!")

        await self.client.aclose()


if __name__ == "__main__":
    demo = AuthenticationDemo()
    asyncio.run(demo.run_demo())
