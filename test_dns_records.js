// Test script to verify DNS records functionality
const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        
        // Log console messages
        page.on('console', msg => console.log('Browser console:', msg.text()));
        page.on('pageerror', error => console.log('Page error:', error.message));
        
        // Navigate to the app
        console.log('Navigating to app...');
        await page.goto('http://localhost:8090', { waitUntil: 'networkidle2' });
        
        // Wait for app to load
        await page.waitForTimeout(2000);
        
        // Navigate to DNS Zones
        console.log('Clicking DNS Zones...');
        await page.evaluate(() => {
            const link = document.querySelector('a[href="#dns-zones"]');
            if (link) link.click();
        });
        
        await page.waitForTimeout(1000);
        
        // Check if zones loaded
        const zonesLoaded = await page.evaluate(() => {
            const tbody = document.querySelector('#zones-tbody');
            return tbody && tbody.children.length > 0;
        });
        
        console.log('Zones loaded:', zonesLoaded);
        
        if (zonesLoaded) {
            // Click on first zone
            console.log('Opening first zone...');
            await page.evaluate(() => {
                const firstZoneLink = document.querySelector('#zones-tbody a');
                if (firstZoneLink) firstZoneLink.click();
            });
            
            await page.waitForTimeout(1000);
            
            // Click Records tab
            console.log('Clicking Records tab...');
            await page.evaluate(() => {
                const recordsTab = document.querySelector('#records-tab');
                if (recordsTab) recordsTab.click();
            });
            
            await page.waitForTimeout(1000);
            
            // Check if records loaded
            const recordsLoaded = await page.evaluate(() => {
                const recordsContainer = document.querySelector('.records-container');
                const tbody = document.querySelector('#records-tbody');
                return recordsContainer && tbody;
            });
            
            console.log('Records tab loaded:', recordsLoaded);
            
            // Get record count
            const recordCount = await page.evaluate(() => {
                const tbody = document.querySelector('#records-tbody');
                return tbody ? tbody.children.length : 0;
            });
            
            console.log('Number of records:', recordCount);
        }
        
    } catch (error) {
        console.error('Test error:', error);
    } finally {
        await browser.close();
    }
})();