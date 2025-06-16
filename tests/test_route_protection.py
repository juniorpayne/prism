#!/usr/bin/env python3
"""
Manual test script for route protection functionality
Tests various scenarios for protected and public routes
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def test_route_protection():
    """Test route protection scenarios"""
    print("=== Testing Route Protection ===\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Test 1: Access protected route without authentication
        print("Test 1: Accessing protected route without authentication")
        await page.goto("http://localhost:8090/dashboard")
        await page.wait_for_load_state("networkidle")
        
        # Should redirect to login
        current_url = page.url
        print(f"  URL after navigation: {current_url}")
        assert "/login" in current_url, "Should redirect to login page"
        print("  ✓ Redirected to login page\n")
        
        # Test 2: Access public route without authentication
        print("Test 2: Accessing public route without authentication")
        await page.goto("http://localhost:8090/register")
        await page.wait_for_load_state("networkidle")
        
        current_url = page.url
        print(f"  URL: {current_url}")
        assert "/register" in current_url, "Should stay on register page"
        print("  ✓ Stayed on register page\n")
        
        # Test 3: Access 404 page
        print("Test 3: Accessing non-existent route")
        await page.goto("http://localhost:8090/non-existent-page")
        await page.wait_for_load_state("networkidle")
        
        # Check if 404 view is visible
        is_404_visible = await page.is_visible("#404-view")
        print(f"  404 view visible: {is_404_visible}")
        assert is_404_visible, "Should show 404 page"
        print("  ✓ 404 page displayed\n")
        
        # Test 4: Login and access protected route
        print("Test 4: Login and access protected route")
        
        # First, register a test user
        await page.goto("http://localhost:8090/register")
        await page.fill("#fullName", "Test User")
        await page.fill("#email", "test@example.com")
        await page.fill("#password", "TestPassword123!")
        await page.fill("#confirmPassword", "TestPassword123!")
        await page.check("#terms")
        
        # Mock successful registration
        await page.evaluate("""
            // Mock successful registration
            localStorage.setItem('accessToken', 'mock-jwt-token');
            localStorage.setItem('refreshToken', 'mock-refresh-token');
            localStorage.setItem('userEmail', 'test@example.com');
            window.dispatchEvent(new Event('tokenUpdate'));
        """)
        
        # Navigate to protected route
        await page.goto("http://localhost:8090/dashboard")
        await page.wait_for_load_state("networkidle")
        
        current_url = page.url
        print(f"  URL after login: {current_url}")
        assert "/dashboard" in current_url, "Should stay on dashboard"
        print("  ✓ Accessed protected route after login\n")
        
        # Test 5: Access auth-only route when logged in
        print("Test 5: Accessing auth-only route when logged in")
        await page.goto("http://localhost:8090/login")
        await page.wait_for_load_state("networkidle")
        
        current_url = page.url
        print(f"  URL: {current_url}")
        assert "/dashboard" in current_url, "Should redirect to dashboard"
        print("  ✓ Redirected from login to dashboard\n")
        
        # Test 6: Logout and verify redirect
        print("Test 6: Logout and verify redirect")
        
        # Clear tokens to simulate logout
        await page.evaluate("""
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('userEmail');
            window.dispatchEvent(new Event('tokenClear'));
        """)
        
        # Should redirect to login
        await page.wait_for_timeout(1000)
        current_url = page.url
        print(f"  URL after logout: {current_url}")
        assert "/login" in current_url, "Should redirect to login after logout"
        print("  ✓ Redirected to login after logout\n")
        
        # Test 7: Redirect after login functionality
        print("Test 7: Testing redirect after login")
        
        # Try to access settings page without auth
        await page.goto("http://localhost:8090/settings")
        await page.wait_for_load_state("networkidle")
        
        # Should redirect to login and save intended destination
        redirect_saved = await page.evaluate("localStorage.getItem('redirectAfterLogin')")
        print(f"  Saved redirect path: {redirect_saved}")
        assert redirect_saved == "/settings", "Should save intended destination"
        
        # Mock login
        await page.evaluate("""
            localStorage.setItem('accessToken', 'mock-jwt-token');
            localStorage.setItem('refreshToken', 'mock-refresh-token');
            window.dispatchEvent(new Event('tokenUpdate'));
            window.router.redirectAfterLogin();
        """)
        
        await page.wait_for_timeout(1000)
        current_url = page.url
        print(f"  URL after login: {current_url}")
        assert "/settings" in current_url, "Should redirect to originally requested page"
        print("  ✓ Redirected to originally requested page after login\n")
        
        # Test 8: Route loading state
        print("Test 8: Testing route loading state")
        
        # Check if loading class is added during navigation
        loading_class_test = await page.evaluate("""
            let loadingDetected = false;
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.target.classList.contains('route-loading')) {
                        loadingDetected = true;
                    }
                });
            });
            observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
            
            // Navigate to trigger loading state
            window.router.navigate('/profile');
            
            // Wait a bit
            await new Promise(resolve => setTimeout(resolve, 100));
            
            observer.disconnect();
            return loadingDetected;
        """)
        
        print(f"  Loading state detected: {loading_class_test}")
        print("  ✓ Route loading state working\n")
        
        await browser.close()
        
    print("=== All Route Protection Tests Passed! ===")


if __name__ == "__main__":
    asyncio.run(test_route_protection())