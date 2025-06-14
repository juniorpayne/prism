/**
 * Test script for Remember Me and Persistent Sessions functionality
 * Run this in the browser console when on the login page
 */

// Test utilities
const TestUtils = {
    assert: (condition, message) => {
        if (!condition) {
            console.error(`❌ FAILED: ${message}`);
            return false;
        }
        console.log(`✅ PASSED: ${message}`);
        return true;
    },
    
    delay: (ms) => new Promise(resolve => setTimeout(resolve, ms))
};

// Test suite for Remember Me functionality
const RememberMeTests = {
    async runAll() {
        console.group('🧪 Remember Me Tests');
        
        await this.testPersistentTokenManager();
        await this.testRememberMeCheckbox();
        await this.testPersistentSession();
        await this.testSessionSync();
        await this.testAutoLogin();
        await this.testLogoutClearsPersistence();
        
        console.groupEnd();
    },
    
    async testPersistentTokenManager() {
        console.group('🔑 Persistent Token Manager Test');
        
        // Check if PersistentTokenManager is available
        TestUtils.assert(
            window.PersistentTokenManager !== undefined,
            'PersistentTokenManager class exists'
        );
        
        // Test token manager initialization
        const tokenManager = window.api?.tokenManager;
        TestUtils.assert(
            tokenManager instanceof PersistentTokenManager,
            'API uses PersistentTokenManager'
        );
        
        // Test remember me methods
        TestUtils.assert(
            typeof tokenManager.isRemembered === 'function',
            'isRemembered method exists'
        );
        
        TestUtils.assert(
            typeof tokenManager.rememberUsername === 'function',
            'rememberUsername method exists'
        );
        
        TestUtils.assert(
            typeof tokenManager.getRememberedUsername === 'function',
            'getRememberedUsername method exists'
        );
        
        console.groupEnd();
    },
    
    async testRememberMeCheckbox() {
        console.group('☑️ Remember Me Checkbox Test');
        
        // Navigate to login page if not already there
        if (window.location.pathname !== '/login') {
            window.app?.router?.navigate('/login');
            await TestUtils.delay(500);
        }
        
        const rememberMe = document.getElementById('rememberMe');
        TestUtils.assert(
            rememberMe !== null,
            'Remember me checkbox exists'
        );
        
        // Test checkbox state persistence
        const initialState = rememberMe.checked;
        rememberMe.checked = true;
        rememberMe.dispatchEvent(new Event('change'));
        
        TestUtils.assert(
            rememberMe.checked === true,
            'Remember me checkbox can be checked'
        );
        
        // Reset state
        rememberMe.checked = initialState;
        
        console.groupEnd();
    },
    
    async testPersistentSession() {
        console.group('💾 Persistent Session Storage Test');
        
        const tokenManager = window.api?.tokenManager;
        if (!tokenManager) {
            console.warn('Token manager not available');
            console.groupEnd();
            return;
        }
        
        // Test persistent session storage
        const testRefreshToken = 'test.refresh.token';
        tokenManager.persistRefreshToken(testRefreshToken);
        
        const persistentData = tokenManager.getPersistentSession();
        TestUtils.assert(
            persistentData !== null,
            'Persistent session data can be stored'
        );
        
        TestUtils.assert(
            persistentData.refreshToken === testRefreshToken,
            'Refresh token is correctly stored'
        );
        
        TestUtils.assert(
            persistentData.createdAt !== undefined,
            'Created timestamp is stored'
        );
        
        TestUtils.assert(
            persistentData.expiresAt !== undefined,
            'Expiration timestamp is stored'
        );
        
        // Test expiration (30 days)
        const expectedExpiry = persistentData.createdAt + (30 * 24 * 60 * 60 * 1000);
        TestUtils.assert(
            Math.abs(persistentData.expiresAt - expectedExpiry) < 1000,
            'Expiration is set to 30 days'
        );
        
        // Cleanup
        tokenManager.clearPersistentSession();
        
        TestUtils.assert(
            tokenManager.getPersistentSession() === null,
            'Persistent session can be cleared'
        );
        
        console.groupEnd();
    },
    
    async testSessionSync() {
        console.group('🔄 Session Storage Sync Test');
        
        // Check if SessionStorageSync is available
        TestUtils.assert(
            window.SessionStorageSync !== undefined,
            'SessionStorageSync class exists'
        );
        
        const sessionSync = window.api?.sessionSync;
        TestUtils.assert(
            sessionSync instanceof SessionStorageSync,
            'Session sync is initialized'
        );
        
        // Test tab ID generation
        TestUtils.assert(
            sessionSync.tabId !== undefined,
            'Tab ID is generated'
        );
        
        TestUtils.assert(
            sessionSync.tabId.startsWith('tab_'),
            'Tab ID has correct format'
        );
        
        // Test broadcast functionality
        const testMessage = {
            type: 'test',
            data: { test: true }
        };
        
        sessionSync.broadcastSessionChange(testMessage.type, testMessage.data);
        await TestUtils.delay(50);
        
        const storedMessage = localStorage.getItem(sessionSync.syncKey);
        TestUtils.assert(
            storedMessage !== null,
            'Session change can be broadcast'
        );
        
        await TestUtils.delay(150); // Wait for cleanup
        
        TestUtils.assert(
            localStorage.getItem(sessionSync.syncKey) === null,
            'Broadcast message is cleaned up'
        );
        
        console.groupEnd();
    },
    
    async testAutoLogin() {
        console.group('🚀 Auto-Login Test');
        
        const tokenManager = window.api?.tokenManager;
        if (!tokenManager) {
            console.warn('Token manager not available');
            console.groupEnd();
            return;
        }
        
        // Test auto-login indicator methods
        TestUtils.assert(
            typeof tokenManager.showAutoLoginIndicator === 'function',
            'showAutoLoginIndicator method exists'
        );
        
        TestUtils.assert(
            typeof tokenManager.hideAutoLoginIndicator === 'function',
            'hideAutoLoginIndicator method exists'
        );
        
        // Test indicator display
        tokenManager.showAutoLoginIndicator();
        await TestUtils.delay(100);
        
        const indicator = document.getElementById('autoLoginIndicator');
        TestUtils.assert(
            indicator !== null,
            'Auto-login indicator is displayed'
        );
        
        TestUtils.assert(
            indicator.textContent.includes('Restoring your session'),
            'Indicator shows correct message'
        );
        
        // Test indicator removal
        tokenManager.hideAutoLoginIndicator();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            document.getElementById('autoLoginIndicator') === null,
            'Auto-login indicator is removed'
        );
        
        console.groupEnd();
    },
    
    async testLogoutClearsPersistence() {
        console.group('🚪 Logout Clears Persistence Test');
        
        const tokenManager = window.api?.tokenManager;
        if (!tokenManager) {
            console.warn('Token manager not available');
            console.groupEnd();
            return;
        }
        
        // Set up persistent session
        tokenManager.persistRefreshToken('test.token');
        localStorage.setItem(tokenManager.rememberMeKey, 'true');
        
        TestUtils.assert(
            tokenManager.getPersistentSession() !== null,
            'Persistent session is set up'
        );
        
        // Clear tokens (simulating logout)
        tokenManager.clearTokens();
        
        TestUtils.assert(
            tokenManager.getPersistentSession() === null,
            'Persistent session is cleared on logout'
        );
        
        TestUtils.assert(
            localStorage.getItem(tokenManager.rememberMeKey) === null,
            'Remember me flag is cleared on logout'
        );
        
        console.groupEnd();
    }
};

// Helper functions for manual testing
const RememberMeHelpers = {
    // Simulate a persistent session
    setupPersistentSession() {
        const tokenManager = window.api?.tokenManager;
        if (!tokenManager) {
            console.error('Token manager not available');
            return;
        }
        
        // Create fake tokens
        const fakeAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsInVzZXJuYW1lIjoidGVzdHVzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJpc19hY3RpdmUiOnRydWUsImlzX3ZlcmlmaWVkIjp0cnVlLCJleHAiOjk5OTk5OTk5OTl9.test';
        const fakeRefreshToken = 'fake.refresh.token';
        
        // Set tokens with remember me
        tokenManager.setTokens(fakeAccessToken, fakeRefreshToken, true);
        tokenManager.rememberUsername('testuser');
        
        console.log('✅ Persistent session set up. Refresh the page to test auto-login.');
    },
    
    // Clear all persistent data
    clearAllPersistence() {
        const tokenManager = window.api?.tokenManager;
        if (tokenManager) {
            tokenManager.clearTokens();
            tokenManager.clearRememberedUsername();
        }
        
        // Clear any other remember me data
        localStorage.removeItem('prism_persistent_session');
        localStorage.removeItem('prism_remember_me');
        localStorage.removeItem('prism_remembered_username');
        localStorage.removeItem('rememberedUsername');
        localStorage.removeItem('rememberMe');
        
        console.log('✅ All persistent data cleared');
    },
    
    // Check persistent session status
    checkSessionStatus() {
        const tokenManager = window.api?.tokenManager;
        if (!tokenManager) {
            console.error('Token manager not available');
            return;
        }
        
        const persistentSession = tokenManager.getPersistentSession();
        const isRemembered = tokenManager.isRemembered();
        const rememberedUsername = tokenManager.getRememberedUsername();
        
        console.log('📊 Persistent Session Status:');
        console.log('- Is Remembered:', isRemembered);
        console.log('- Remembered Username:', rememberedUsername);
        console.log('- Persistent Session:', persistentSession);
        
        if (persistentSession) {
            const remaining = persistentSession.expiresAt - Date.now();
            const days = Math.floor(remaining / (24 * 60 * 60 * 1000));
            console.log(`- Expires in: ${days} days`);
        }
    },
    
    // Simulate cross-tab login
    simulateCrossTabLogin() {
        const sessionSync = window.api?.sessionSync;
        if (!sessionSync) {
            console.error('Session sync not available');
            return;
        }
        
        // Broadcast login event
        sessionSync.broadcastSessionChange('login', {
            timestamp: Date.now()
        });
        
        console.log('✅ Cross-tab login event broadcast. Other tabs should reload.');
    },
    
    // Simulate cross-tab logout
    simulateCrossTabLogout() {
        const sessionSync = window.api?.sessionSync;
        if (!sessionSync) {
            console.error('Session sync not available');
            return;
        }
        
        // Broadcast logout event
        sessionSync.broadcastSessionChange('logout', {
            timestamp: Date.now()
        });
        
        console.log('✅ Cross-tab logout event broadcast. Other tabs should logout.');
    }
};

// Run tests
console.log('🚀 Starting Remember Me Tests...');
RememberMeTests.runAll().then(() => {
    console.log('✨ All tests completed!');
    console.log('');
    console.log('📚 Manual Testing Helpers:');
    console.log('- RememberMeHelpers.setupPersistentSession() - Set up a test persistent session');
    console.log('- RememberMeHelpers.clearAllPersistence() - Clear all persistent data');
    console.log('- RememberMeHelpers.checkSessionStatus() - Check current session status');
    console.log('- RememberMeHelpers.simulateCrossTabLogin() - Simulate login in another tab');
    console.log('- RememberMeHelpers.simulateCrossTabLogout() - Simulate logout in another tab');
});