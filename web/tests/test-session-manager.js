/**
 * Test script for Session Manager functionality
 * Run this in the browser console when logged in
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

// Test suite for Session Manager
const SessionManagerTests = {
    async runAll() {
        console.group('🧪 Session Manager Tests');
        
        await this.testInitialization();
        await this.testActivityMonitoring();
        await this.testSessionTimer();
        await this.testWarningModal();
        await this.testCrossTabSync();
        await this.testAutoLogout();
        
        console.groupEnd();
    },
    
    async testInitialization() {
        console.group('🚀 Initialization Test');
        
        const app = window.app;
        TestUtils.assert(
            app !== undefined,
            'App instance exists'
        );
        
        TestUtils.assert(
            app.sessionManager !== null,
            'Session manager instance exists'
        );
        
        // Check if authenticated
        const isAuth = window.api?.tokenManager?.isAuthenticated();
        
        if (isAuth) {
            TestUtils.assert(
                app.sessionManager.isRunning === true,
                'Session manager is running when authenticated'
            );
            
            const timerContainer = document.getElementById('sessionTimerContainer');
            TestUtils.assert(
                timerContainer && !timerContainer.classList.contains('d-none'),
                'Session timer is visible when authenticated'
            );
        } else {
            console.warn('User not authenticated - some tests will be skipped');
        }
        
        console.groupEnd();
    },
    
    async testActivityMonitoring() {
        console.group('🖱️ Activity Monitoring Test');
        
        const sessionManager = window.app?.sessionManager;
        if (!sessionManager || !sessionManager.isRunning) {
            console.warn('Session manager not running');
            console.groupEnd();
            return;
        }
        
        // Record initial activity time
        const initialActivity = sessionManager.lastActivity;
        
        // Wait a bit
        await TestUtils.delay(100);
        
        // Simulate mouse click
        document.dispatchEvent(new MouseEvent('mousedown'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            sessionManager.lastActivity > initialActivity,
            'Mouse activity updates last activity time'
        );
        
        // Test keyboard activity
        const keyboardActivity = sessionManager.lastActivity;
        await TestUtils.delay(100);
        
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            sessionManager.lastActivity > keyboardActivity,
            'Keyboard activity updates last activity time'
        );
        
        // Test scroll activity
        const scrollActivity = sessionManager.lastActivity;
        await TestUtils.delay(100);
        
        document.dispatchEvent(new Event('scroll'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            sessionManager.lastActivity > scrollActivity,
            'Scroll activity updates last activity time'
        );
        
        console.groupEnd();
    },
    
    async testSessionTimer() {
        console.group('⏰ Session Timer Test');
        
        const sessionManager = window.app?.sessionManager;
        const timerEl = document.getElementById('sessionTimer');
        
        if (!sessionManager || !sessionManager.isRunning || !timerEl) {
            console.warn('Session manager or timer element not available');
            console.groupEnd();
            return;
        }
        
        // Update activity to reset timer
        sessionManager.updateActivity();
        
        // Force timer update
        sessionManager.checkInactivity();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            timerEl.textContent.includes('Session:'),
            'Timer displays session text'
        );
        
        TestUtils.assert(
            /\d+:\d{2}/.test(timerEl.textContent),
            'Timer displays time in MM:SS format'
        );
        
        // Check timer color based on remaining time
        const timeRemaining = sessionManager.getTimeUntilExpiry();
        const minutes = Math.floor(timeRemaining / 60000);
        
        if (minutes < 5) {
            TestUtils.assert(
                timerEl.classList.contains('text-danger'),
                'Timer shows danger color when < 5 minutes'
            );
        } else if (minutes < 10) {
            TestUtils.assert(
                timerEl.classList.contains('text-warning'),
                'Timer shows warning color when < 10 minutes'
            );
        } else {
            TestUtils.assert(
                timerEl.classList.contains('text-muted'),
                'Timer shows muted color when > 10 minutes'
            );
        }
        
        console.groupEnd();
    },
    
    async testWarningModal() {
        console.group('⚠️ Warning Modal Test');
        
        const sessionManager = window.app?.sessionManager;
        if (!sessionManager || !sessionManager.isRunning) {
            console.warn('Session manager not running');
            console.groupEnd();
            return;
        }
        
        // Show warning modal
        sessionManager.showWarning(5 * 60 * 1000); // 5 minutes
        await TestUtils.delay(500);
        
        const modal = document.getElementById('sessionWarningModal');
        TestUtils.assert(
            modal !== null,
            'Warning modal is created'
        );
        
        TestUtils.assert(
            modal.style.display === 'block',
            'Warning modal is visible'
        );
        
        const countdown = document.getElementById('sessionCountdown');
        TestUtils.assert(
            countdown !== null,
            'Countdown element exists'
        );
        
        TestUtils.assert(
            /\d+:\d{2}/.test(countdown.textContent),
            'Countdown shows time format'
        );
        
        const continueBtn = document.getElementById('continueSessionBtn');
        TestUtils.assert(
            continueBtn !== null,
            'Continue session button exists'
        );
        
        const logoutBtn = document.getElementById('logoutNowBtn');
        TestUtils.assert(
            logoutBtn !== null,
            'Logout now button exists'
        );
        
        // Test continue session
        continueBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            document.getElementById('sessionWarningModal') === null,
            'Modal is removed after clicking continue'
        );
        
        TestUtils.assert(
            sessionManager.warningShown === false,
            'Warning shown flag is reset'
        );
        
        console.groupEnd();
    },
    
    async testCrossTabSync() {
        console.group('🔄 Cross-Tab Sync Test');
        
        const sessionManager = window.app?.sessionManager;
        if (!sessionManager || !sessionManager.isRunning || !sessionManager.config.crossTabSync) {
            console.warn('Session manager not running or cross-tab sync disabled');
            console.groupEnd();
            return;
        }
        
        // Test storage update
        const initialActivity = sessionManager.lastActivity;
        const newActivity = Date.now() + 10000; // Future time
        
        // Simulate activity from another tab
        localStorage.setItem(sessionManager.storageKey, newActivity.toString());
        
        // Trigger storage event manually (since we're in same tab)
        const event = new StorageEvent('storage', {
            key: sessionManager.storageKey,
            newValue: newActivity.toString(),
            oldValue: initialActivity.toString()
        });
        
        sessionManager.handleStorageChange(event);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            sessionManager.lastActivity === newActivity,
            'Activity syncs from other tab storage'
        );
        
        console.groupEnd();
    },
    
    async testAutoLogout() {
        console.group('🚪 Auto-Logout Test');
        
        const sessionManager = window.app?.sessionManager;
        if (!sessionManager || !sessionManager.isRunning) {
            console.warn('Session manager not running');
            console.groupEnd();
            return;
        }
        
        // Test auto-logout notification
        sessionManager.showAutoLogoutNotification();
        await TestUtils.delay(100);
        
        const notification = document.getElementById('autoLogoutNotification');
        TestUtils.assert(
            notification !== null,
            'Auto-logout notification is shown'
        );
        
        TestUtils.assert(
            notification.textContent.includes('logged out'),
            'Notification shows logout message'
        );
        
        // Test cleanup
        const originalIsRunning = sessionManager.isRunning;
        sessionManager.cleanup();
        
        TestUtils.assert(
            sessionManager.isRunning === false,
            'Session manager stops after cleanup'
        );
        
        TestUtils.assert(
            sessionManager.activityTimer === null,
            'Activity timer is cleared'
        );
        
        TestUtils.assert(
            sessionManager.warningTimer === null,
            'Warning timer is cleared'
        );
        
        // Restore if it was running
        if (originalIsRunning) {
            sessionManager.init();
        }
        
        console.groupEnd();
    }
};

// Helper functions for testing
const SessionTestHelpers = {
    // Simulate inactivity by setting last activity to past
    simulateInactivity(minutes) {
        const sessionManager = window.app?.sessionManager;
        if (sessionManager) {
            sessionManager.lastActivity = Date.now() - (minutes * 60 * 1000);
            sessionManager.checkInactivity();
        }
    },
    
    // Force show warning modal
    forceShowWarning() {
        const sessionManager = window.app?.sessionManager;
        if (sessionManager) {
            sessionManager.showWarning(5 * 60 * 1000); // 5 minutes
        }
    },
    
    // Get session info
    getSessionInfo() {
        const sessionManager = window.app?.sessionManager;
        if (!sessionManager) {
            return 'Session manager not available';
        }
        
        const timeRemaining = sessionManager.getTimeUntilExpiry();
        const minutes = Math.floor(timeRemaining / 60000);
        const seconds = Math.floor((timeRemaining % 60000) / 1000);
        
        return {
            isRunning: sessionManager.isRunning,
            isAuthenticated: window.api?.tokenManager?.isAuthenticated() || false,
            lastActivity: new Date(sessionManager.lastActivity).toLocaleTimeString(),
            timeRemaining: `${minutes}:${seconds.toString().padStart(2, '0')}`,
            warningShown: sessionManager.warningShown,
            config: sessionManager.config
        };
    }
};

// Run tests if authenticated
if (window.api?.tokenManager?.isAuthenticated()) {
    console.log('🚀 Starting Session Manager Tests...');
    SessionManagerTests.runAll().then(() => {
        console.log('✨ All tests completed!');
        console.log('📊 Session Info:', SessionTestHelpers.getSessionInfo());
    });
} else {
    console.log('⚠️ Please login to run session manager tests');
    console.log('Available test helpers:');
    console.log('- SessionTestHelpers.simulateInactivity(minutes)');
    console.log('- SessionTestHelpers.forceShowWarning()');
    console.log('- SessionTestHelpers.getSessionInfo()');
}