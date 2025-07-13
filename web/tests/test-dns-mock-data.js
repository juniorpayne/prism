/**
 * Tests for DNS Mock Data Service
 */

// Simple test runner
const tests = {
    passed: 0,
    failed: 0,
    
    async run(name, testFn) {
        try {
            await testFn();
            console.log(`✓ ${name}`);
            this.passed++;
        } catch (error) {
            console.error(`✗ ${name}`);
            console.error(`  ${error.message}`);
            this.failed++;
        }
    },
    
    assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    },
    
    summary() {
        console.log(`\nTests: ${this.passed} passed, ${this.failed} failed`);
        return this.failed === 0;
    }
};

// Test suite
async function runTests() {
    console.log('DNS Mock Data Service Tests\n');
    
    // Initialize service
    const mockService = new DNSMockDataService();
    
    // Test 1: Get all zones
    await tests.run('should get all zones', async () => {
        const zones = await mockService.getAllZones();
        tests.assert(Array.isArray(zones), 'Zones should be an array');
        tests.assert(zones.length >= 2, 'Should have sample zones');
    });
    
    // Test 2: Get specific zone
    await tests.run('should get a specific zone', async () => {
        const zone = await mockService.getZone('example.com');
        tests.assert(zone.name === 'example.com', 'Zone name should match');
        tests.assert(zone.records.length > 0, 'Zone should have records');
    });
    
    // Test 3: Create new zone
    await tests.run('should create a new zone', async () => {
        const newZone = await mockService.createZone({
            name: 'test-new.com',
            email: 'admin@test-new.com'
        });
        tests.assert(newZone.name === 'test-new.com', 'New zone name should match');
        tests.assert(newZone.status === 'Active', 'New zone should be active');
    });
    
    // Test 4: Update zone
    await tests.run('should update a zone', async () => {
        const updated = await mockService.updateZone('test-new.com', {
            status: 'Inactive'
        });
        tests.assert(updated.status === 'Inactive', 'Zone status should be updated');
    });
    
    // Test 5: Add record
    await tests.run('should add a record to zone', async () => {
        const record = await mockService.addRecord('test-new.com', {
            name: 'www',
            type: 'A',
            value: '192.168.1.100'
        });
        tests.assert(record.name === 'www', 'Record name should match');
        tests.assert(record.id !== undefined, 'Record should have ID');
    });
    
    // Test 6: Delete zone
    await tests.run('should delete a zone', async () => {
        const result = await mockService.deleteZone('test-new.com');
        tests.assert(result.success === true, 'Delete should succeed');
        
        try {
            await mockService.getZone('test-new.com');
            tests.assert(false, 'Should not find deleted zone');
        } catch (e) {
            tests.assert(e.message.includes('not found'), 'Should throw not found error');
        }
    });
    
    // Test 7: Get statistics
    await tests.run('should get statistics', async () => {
        const stats = await mockService.getStats();
        tests.assert(typeof stats.totalZones === 'number', 'Should have totalZones');
        tests.assert(typeof stats.activeZones === 'number', 'Should have activeZones');
        tests.assert(typeof stats.totalRecords === 'number', 'Should have totalRecords');
    });
    
    // Test 8: Error handling
    await tests.run('should handle errors gracefully', async () => {
        try {
            await mockService.getZone('non-existent.com');
            tests.assert(false, 'Should throw error for non-existent zone');
        } catch (e) {
            tests.assert(e.message.includes('not found'), 'Should have proper error message');
        }
    });
    
    return tests.summary();
}

// Export for use in test runner
window.runDNSMockDataTests = runTests;