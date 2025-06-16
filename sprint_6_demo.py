#!/usr/bin/env python3
"""
Sprint 6 Demo Runner - Interactive Demo Script
Helps guide through the sprint demo with automated actions
"""

import subprocess
import sys
import time
import webbrowser
from datetime import datetime


class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")


def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {text}{Colors.END}")


def print_action(text):
    print(f"{Colors.GREEN}  ✓ {text}{Colors.END}")


def print_talking_point(text):
    print(f"{Colors.YELLOW}  💬 {text}{Colors.END}")


def print_instruction(text):
    print(f"{Colors.BLUE}  ➜ {text}{Colors.END}")


def wait_for_enter(prompt="Press Enter to continue..."):
    input(f"\n{Colors.BOLD}{prompt}{Colors.END}")


def open_url(url):
    print_action(f"Opening {url}")
    webbrowser.open(url)
    time.sleep(2)


def run_command(cmd, description):
    print_action(f"Running: {description}")
    print(f"  {Colors.BLUE}$ {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{Colors.RED}  Error: {result.stderr}{Colors.END}")
    return result.returncode == 0


def main():
    print_header("SPRINT 6 DEMO")
    print("Multi-Tenant Web Interface - Authentication System")
    print(f"Demo Date: {datetime.now().strftime('%B %d, %Y')}")

    print_section("Demo Environment Setup")
    print_instruction("Starting Docker services...")

    if not run_command("docker compose up -d", "Starting application"):
        print(f"{Colors.RED}Failed to start services. Please check Docker.{Colors.END}")
        sys.exit(1)

    print_action("Waiting for services to be ready...")
    time.sleep(5)

    wait_for_enter("Services started. Press Enter to begin demo...")

    # Part 1: Authentication Flow
    print_header("PART 1: AUTHENTICATION FLOW")

    print_section("1.1 Registration Flow (SCRUM-61)")
    open_url("http://localhost:8090/#register")
    print_instruction("Demonstrate the registration form:")
    print_talking_point("Notice the real-time validation feedback")
    print_talking_point("Password strength indicator helps users create secure passwords")
    print_talking_point("All validation happens client-side for immediate feedback")
    wait_for_enter()

    print_section("1.2 Email Verification (SCRUM-62)")
    print_instruction("Show the email verification flow:")
    print_talking_point("Users receive clear instructions about next steps")
    print_talking_point("Rate limiting prevents abuse of email sending")
    print_talking_point("Graceful handling of expired/invalid tokens")
    wait_for_enter()

    print_section("1.3 Login Flow (SCRUM-60)")
    open_url("http://localhost:8090/#login")
    print_instruction("Demonstrate the login form:")
    print_talking_point("Clean, user-friendly interface")
    print_talking_point("Security-focused with proper error handling")
    print_talking_point("Smooth transitions and loading states")
    wait_for_enter()

    # Part 2: Router and Protected Routes
    print_header("PART 2: ROUTER & PROTECTED ROUTES")

    print_section("2.1 Client-Side Routing (SCRUM-58)")
    print_instruction("Test navigation without page refresh")
    print_instruction("Use browser back/forward buttons")
    print_instruction("Try accessing protected route while logged out")
    print_talking_point("SPA-like experience with proper URL management")
    print_talking_point("Browser navigation works as expected")
    print_talking_point("Protected routes automatically redirect unauthenticated users")
    wait_for_enter()

    # Part 3: Password Recovery
    print_header("PART 3: PASSWORD RECOVERY")

    print_section("3.1 Forgot Password (SCRUM-63)")
    open_url("http://localhost:8090/#forgot-password")
    print_instruction("Enter an email address")
    print_instruction("Show the success state")
    print_talking_point("Simple, focused interface")
    print_talking_point("Clear feedback about email being sent")
    print_talking_point("Rate limiting protects against abuse")
    wait_for_enter()

    print_section("3.2 Reset Password (SCRUM-64)")
    print_instruction("Show reset password page with token")
    print_talking_point("Secure token validation")
    print_talking_point("Same password strength requirements")
    print_talking_point("Clear success messaging")
    wait_for_enter()

    # Part 4: Session Management
    print_header("PART 4: SESSION MANAGEMENT")

    print_section("4.1 Activity Monitoring (SCRUM-65)")
    print_instruction("Login and show session timer in navbar")
    print_instruction("Perform activities to reset timer")
    print_talking_point("Real-time session monitoring")
    print_talking_point("All user interactions tracked")
    print_talking_point("Visual feedback with color-coded timer")
    wait_for_enter()

    print_section("4.2 Inactivity Warning")
    print_instruction("Simulate inactivity warning (or wait)")
    print_talking_point("User-friendly warning before logout")
    print_talking_point("Clear countdown timer")
    print_talking_point("Prevents accidental data loss")
    wait_for_enter()

    # Part 5: Remember Me
    print_header("PART 5: REMEMBER ME & PERSISTENT SESSIONS")

    print_section("5.1 Remember Me Login (SCRUM-66)")
    print_instruction("Login with 'Remember me' checked")
    print_instruction("Close and reopen browser")
    print_talking_point("Convenient for returning users")
    print_talking_point("Secure 30-day persistent sessions")
    print_talking_point("Visual indicator during auto-login")
    wait_for_enter()

    print_section("5.2 Cross-Tab Synchronization")
    print_instruction("Open multiple tabs")
    print_instruction("Login/logout in one tab")
    print_talking_point("Consistent experience across tabs")
    print_talking_point("Real-time synchronization")
    print_talking_point("Security-focused implementation")
    wait_for_enter()

    # Part 6: Technical Details
    print_header("PART 6: TECHNICAL HIGHLIGHTS")

    print_section("6.1 JWT Token Management (SCRUM-59)")
    print_instruction("Open browser developer tools")
    print_instruction("Show network requests with auth headers")
    print_talking_point("Transparent token management")
    print_talking_point("Automatic refresh before expiry")
    print_talking_point("Seamless API integration")
    wait_for_enter()

    # Summary
    print_header("DEMO SUMMARY")

    print_section("Sprint Achievements")
    print_action("9 User Stories Completed")
    print_action("100% Acceptance Criteria Met")
    print_action("Comprehensive Test Coverage")
    print_action("Zero Security Vulnerabilities")
    print_action("Fully Responsive Design")

    print_section("Key Features Delivered")
    print_action("Complete authentication system")
    print_action("Session management with warnings")
    print_action("Password recovery flow")
    print_action("Remember me functionality")
    print_action("Cross-tab synchronization")

    wait_for_enter("\nPress Enter for Q&A session...")

    print_header("Q&A SESSION")
    print_section("Common Questions")
    print("1. How are tokens stored securely?")
    print("2. What happens on token expiry?")
    print("3. Why 30-minute session timeout?")
    print("4. How does cross-tab sync work?")
    print("5. What's next for authentication?")

    wait_for_enter("\nPress Enter to wrap up demo...")

    print_header("THANK YOU!")
    print("Sprint 6 Demo Complete")
    print("\nWould you like to stop the services? (y/n): ", end="")

    if input().lower() == "y":
        run_command("docker compose down", "Stopping services")
        print_action("Services stopped")

    print(f"\n{Colors.GREEN}Demo completed successfully!{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user{Colors.END}")
        sys.exit(0)
