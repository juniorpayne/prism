#!/usr/bin/env node

/**
 * Simple test runner for token management UI
 * This validates that all required components are in place
 */

const fs = require('fs');
const path = require('path');

let testsPassed = 0;
let testsFailed = 0;

function test(description, fn) {
    try {
        fn();
        console.log('✓', description);
        testsPassed++;
    } catch (error) {
        console.log('✗', description);
        console.log('  ', error.message);
        testsFailed++;
    }
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message || 'Assertion failed');
    }
}

// Test files exist
test('index.html contains API tokens section', () => {
    const content = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    assert(content.includes('settingsApiTokens'), 'Missing API tokens settings section');
    assert(content.includes('API Tokens'), 'Missing API Tokens header');
    assert(content.includes('generate-token-btn'), 'Missing generate token button');
    assert(content.includes('tokens-table'), 'Missing tokens table');
});

test('Token management JavaScript exists', () => {
    const filePath = path.join(__dirname, 'js', 'token-management.js');
    assert(fs.existsSync(filePath), 'token-management.js file missing');
    
    const content = fs.readFileSync(filePath, 'utf8');
    assert(content.includes('loadTokens'), 'loadTokens function missing');
    assert(content.includes('generateToken'), 'generateToken function missing');
    assert(content.includes('revokeToken'), 'revokeToken function missing');
    assert(content.includes('copyTokenToClipboard'), 'copyTokenToClipboard function missing');
});

test('Utils has required functions', () => {
    const content = fs.readFileSync(path.join(__dirname, 'js', 'utils.js'), 'utf8');
    assert(content.includes('formatBytes'), 'formatBytes function missing');
    assert(content.includes('showNotification'), 'showNotification function missing');
    assert(content.includes('showConfirmDialog'), 'showConfirmDialog function missing');
    assert(content.includes('formatTimestamp'), 'formatTimestamp function missing');
});

test('Token generation modal exists', () => {
    const content = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    assert(content.includes('tokenModal'), 'Token modal missing');
    assert(content.includes('token-name'), 'Token name input missing');
    assert(content.includes('token-expiry'), 'Token expiry select missing');
    assert(content.includes('token-form'), 'Token form missing');
});

test('Token display modal exists', () => {
    const content = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    assert(content.includes('tokenDisplayModal'), 'Token display modal missing');
    assert(content.includes('token-value'), 'Token value input missing');
    assert(content.includes('copy-token-btn'), 'Copy token button missing');
});

test('Settings integration', () => {
    const content = fs.readFileSync(path.join(__dirname, 'js', 'settings.js'), 'utf8');
    assert(content.includes('api-tokens'), 'API tokens section not integrated in settings');
    assert(content.includes('tokenManagement.loadTokens'), 'Token loading not integrated');
});

test('Test file exists', () => {
    const filePath = path.join(__dirname, 'tests', 'test-token-management-ui.html');
    assert(fs.existsSync(filePath), 'Test file missing');
    
    const content = fs.readFileSync(filePath, 'utf8');
    assert(content.includes('Token Management UI'), 'Test title missing');
    assert(content.includes('mocha'), 'Mocha testing framework missing');
    assert(content.includes('chai'), 'Chai assertion library missing');
});

// Summary
console.log('\n========================================');
console.log(`Tests passed: ${testsPassed}`);
console.log(`Tests failed: ${testsFailed}`);
console.log('========================================');

if (testsFailed > 0) {
    console.log('\n❌ Some tests failed. Please fix the issues above.');
    process.exit(1);
} else {
    console.log('\n✅ All tests passed! Token management UI is properly implemented.');
    process.exit(0);
}