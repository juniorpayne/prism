#!/usr/bin/env python3
"""
Sprint 8 Demo Script
Automated demo setup and walkthrough for Sprint 8 features
"""

import subprocess
import sys
import time
import webbrowser
from datetime import datetime


class Colors:
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.GREEN}▶ {text}{Colors.END}")


def print_step(number, text):
    print(f"  {Colors.YELLOW}{number}.{Colors.END} {text}")


def wait_for_input(prompt="Press Enter to continue..."):
    input(f"\n{Colors.BOLD}{prompt}{Colors.END}")


def run_command(cmd, description):
    print(f"\n{Colors.YELLOW}Running: {description}{Colors.END}")
    print(f"{Colors.BLUE}$ {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{Colors.RED}Error: {result.stderr}{Colors.END}")
        return False
    return True


def main():
    print_header("SPRINT 8 DEMO")
    print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    print("Account Management and Authentication Enforcement")

    # Pre-demo setup
    print_section("Pre-Demo Setup")
    print_step(1, "Starting Docker containers...")
    if not run_command("docker compose up -d", "Starting all services"):
        print(f"{Colors.RED}Failed to start Docker containers!{Colors.END}")
        sys.exit(1)

    print_step(2, "Waiting for services to be ready...")
    time.sleep(5)

    print_step(3, "Checking service health...")
    run_command("docker compose ps", "Checking container status")

    print_step(4, "Creating demo accounts...")
    if run_command("python3 create_demo_account.py", "Setting up demo accounts"):
        print(f"{Colors.GREEN}Demo accounts created successfully!{Colors.END}")
    else:
        print(
            f"{Colors.YELLOW}Warning: Could not create demo accounts. You may need to register manually.{Colors.END}"
        )

    print_step(5, "Opening application in browser...")
    webbrowser.open("http://localhost:8090")

    wait_for_input()

    # Demo sections
    sections = [
        (
            "Authentication and Registration",
            [
                "Navigate to the Register page",
                "Show real-time password strength indicator",
                "Create a new account with all validations",
                "Show email verification page",
                "Navigate to Login page",
                "Demonstrate Remember Me checkbox",
                "Login with the test account",
            ],
        ),
        (
            "Protected Routes and Navigation",
            [
                "Open incognito window and try /dashboard",
                "Show redirect to login",
                "Login and show redirect back to dashboard",
                "Show user menu with avatar and email",
                "Show session timer in navbar",
            ],
        ),
        (
            "Dashboard and Host Management",
            [
                "Show dashboard statistics cards",
                "Navigate to Hosts page",
                "Demonstrate search functionality",
                "Show sorting options",
                "Click on a host for details modal",
            ],
        ),
        (
            "User Profile Management",
            [
                "Navigate to My Profile",
                "Show profile information display",
                "Click Edit Profile",
                "Update full name and bio",
                "Show character counter in action",
                "Save and show success message",
            ],
        ),
        (
            "Account Settings",
            [
                "Navigate to Settings",
                "Show collapsible sidebar (resize window)",
                "Go through each settings section",
                "Show General settings options",
                "Show Security settings with sessions",
                "Show Notification preferences",
                "Show Account management section",
            ],
        ),
        (
            "Password Change Flow",
            [
                "Click Change Password from Security",
                "Show current password field",
                "Enter new password and watch strength indicator",
                "Show password requirements updating",
                "Submit form (mock success)",
                "Show auto-logout warning",
            ],
        ),
        (
            "Activity Logging",
            [
                "Navigate to Activity Log",
                "Show default date range (last 30 days)",
                "Filter by event type",
                "Change date range",
                "Show pagination controls",
                "Click through pages",
            ],
        ),
        (
            "Account Deletion Flow",
            [
                "Go to Settings > Account",
                "Click Delete My Account",
                "Show Step 1: Warning and consequences",
                "Check the understanding checkbox",
                "Show Step 2: Password and username verification",
                "Show Step 3: Final confirmation",
                "Explain success flow (don't execute)",
            ],
        ),
        (
            "Session Management",
            [
                "Show session timer counting down",
                "Explain session warning at 5 minutes",
                "Click Logout",
                "Show redirect to login",
                "Try to access protected route",
            ],
        ),
    ]

    for section_name, steps in sections:
        print_section(section_name)
        for i, step in enumerate(steps, 1):
            print_step(i, step)
        wait_for_input(f"Ready to demo {section_name}?")
        print(f"{Colors.GREEN}✓ {section_name} demonstrated{Colors.END}")

    # Technical highlights
    print_header("TECHNICAL HIGHLIGHTS")

    print_section("Security Features")
    features = [
        "JWT-based authentication with refresh tokens",
        "Protected routes with authentication guards",
        "Session timeout management (30 minutes)",
        "Password strength validation (zxcvbn-based)",
        "Multi-factor confirmation for account deletion",
        "XSS protection in all inputs",
        "CSRF protection ready",
    ]
    for feature in features:
        print(f"  • {feature}")

    print_section("User Experience Features")
    features = [
        "Responsive design (Bootstrap 5)",
        "Real-time form validation",
        "Loading states and spinners",
        "Toast notifications",
        "Smooth page transitions",
        "Character counting",
        "Password visibility toggles",
        "Remember Me functionality",
    ]
    for feature in features:
        print(f"  • {feature}")

    # Q&A
    print_header("Q&A SESSION")
    print("Prepared to discuss:")
    print("  • Next sprint priorities")
    print("  • UX/UI feedback")
    print("  • Security requirements")
    print("  • Integration needs")
    print("  • Performance optimization")

    wait_for_input("Demo complete! Press Enter to show container logs...")

    # Show logs
    print_section("Container Logs (last 50 lines)")
    run_command("docker compose logs --tail=50", "Showing recent logs")

    print_header("DEMO COMPLETE")
    print(f"{Colors.GREEN}Thank you for attending the Sprint 8 demo!{Colors.END}")
    print("\nDon't forget to:")
    print("  • Gather feedback")
    print("  • Note improvement requests")
    print("  • Document any bugs found")
    print("  • Update the backlog")


if __name__ == "__main__":
    main()
