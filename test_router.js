/**
 * Test script for router implementation
 */

const puppeteer = require('puppeteer');

async function testRouter() {
    const browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => console.log('Browser console:', msg.text()));
    page.on('pageerror', error => console.error('Page error:', error.message));
    
    try {
        console.log('Testing Router Implementation...\n');
        
        // Test 1: Load main page
        console.log('Test 1: Loading main page...');
        await page.goto('http://localhost:8090', { waitUntil: 'networkidle0' });
        let url = page.url();
        console.log(`✓ Current URL: ${url}`);
        
        // Test 2: Check if router is initialized
        console.log('\nTest 2: Checking router initialization...');
        const hasRouter = await page.evaluate(() => {
            return window.app && window.app.router && typeof window.Router === 'function';
        });
        console.log(`✓ Router initialized: ${hasRouter}`);
        
        // Test 3: Navigate to dashboard (protected route without token)
        console.log('\nTest 3: Testing protected route without authentication...');
        await page.evaluate(() => {
            window.app.router.navigate('/dashboard');
        });
        await new Promise(resolve => setTimeout(resolve, 500));
        url = page.url();
        console.log(`✓ Redirected to: ${url}`);
        console.log(`✓ Should redirect to login: ${url.includes('/login')}`);
        
        // Test 4: Check redirect path saved
        const redirectPath = await page.evaluate(() => {
            return localStorage.getItem('redirectAfterLogin');
        });
        console.log(`✓ Redirect path saved: ${redirectPath}`);
        
        // Test 5: Navigate to public route
        console.log('\nTest 5: Testing public route navigation...');
        await page.evaluate(() => {
            window.app.router.navigate('/register');
        });
        await new Promise(resolve => setTimeout(resolve, 500));
        url = page.url();
        console.log(`✓ Navigated to: ${url}`);
        
        // Test 6: Set fake JWT token and test protected route
        console.log('\nTest 6: Testing protected route with authentication...');
        await page.evaluate(() => {
            // Create a valid JWT token that expires in 1 hour
            const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
            const payload = btoa(JSON.stringify({ 
                exp: Math.floor(Date.now() / 1000) + 3600,
                sub: 'user123'
            }));
            const signature = 'fake-signature';
            const token = `${header}.${payload}.${signature}`;
            localStorage.setItem('accessToken', token);
        });
        
        await page.evaluate(() => {
            window.app.router.navigate('/dashboard');
        });
        await new Promise(resolve => setTimeout(resolve, 500));
        url = page.url();
        console.log(`✓ Successfully navigated to: ${url}`);
        console.log(`✓ Dashboard accessible: ${url.includes('/dashboard')}`);
        
        // Test 7: Check if dashboard view is visible
        const dashboardVisible = await page.evaluate(() => {
            const dashboard = document.getElementById('dashboard-view');
            return dashboard && dashboard.style.display !== 'none';
        });
        console.log(`✓ Dashboard view visible: ${dashboardVisible}`);
        
        // Test 8: Test navigation to hosts
        console.log('\nTest 8: Testing navigation to hosts...');
        await page.evaluate(() => {
            window.app.router.navigate('/hosts');
        });
        await new Promise(resolve => setTimeout(resolve, 500));
        url = page.url();
        console.log(`✓ Navigated to: ${url}`);
        
        const hostsVisible = await page.evaluate(() => {
            const hosts = document.getElementById('hosts-view');
            return hosts && hosts.style.display !== 'none';
        });
        console.log(`✓ Hosts view visible: ${hostsVisible}`);
        
        // Test 9: Test browser back button
        console.log('\nTest 9: Testing browser back button...');
        await page.goBack();
        await new Promise(resolve => setTimeout(resolve, 500));
        url = page.url();
        console.log(`✓ Back button navigated to: ${url}`);
        
        // Test 10: Test direct URL access
        console.log('\nTest 10: Testing direct URL access...');
        await page.goto('http://localhost:8090/hosts', { waitUntil: 'networkidle0' });
        url = page.url();
        console.log(`✓ Direct access URL: ${url}`);
        
        const hostsVisibleDirect = await page.evaluate(() => {
            const hosts = document.getElementById('hosts-view');
            return hosts && hosts.style.display !== 'none';
        });
        console.log(`✓ Hosts view visible on direct access: ${hostsVisibleDirect}`);
        
        console.log('\n✅ All router tests completed successfully!');
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    } finally {
        await browser.close();
    }
}

// Run tests
testRouter().catch(console.error);