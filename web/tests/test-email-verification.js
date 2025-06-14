/**
 * Test script for Email Verification Flow functionality
 * Run this in the browser console while on the email verification pages
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

// Test suite for Email Verification Flow
const EmailVerificationTests = {
    async runAll() {
        console.group('🧪 Email Verification Flow Tests');
        
        // Check which page we're on
        const currentPath = window.location.pathname;
        
        if (currentPath === '/verify-email-sent' || 
            document.getElementById('verify-email-sent-view')?.style.display !== 'none') {
            await this.testEmailSentPage();
        } else if (currentPath === '/verify-email' || 
                   document.getElementById('verify-email-view')?.style.display !== 'none') {
            await this.testVerificationPage();
        } else {
            console.warn('Please navigate to an email verification page to run tests');
        }
        
        console.groupEnd();
    },
    
    async testEmailSentPage() {
        console.group('📧 Email Sent Page Tests');
        
        await this.testEmailSentElements();
        await this.testResendButton();
        await this.testRateLimiting();
        
        console.groupEnd();
    },
    
    async testEmailSentElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('userEmail') !== null,
            'User email display exists'
        );
        
        TestUtils.assert(
            document.getElementById('resendBtn') !== null,
            'Resend button exists'
        );
        
        TestUtils.assert(
            document.getElementById('resendMessage') !== null,
            'Resend message container exists'
        );
        
        TestUtils.assert(
            document.querySelector('.bi-envelope-check') !== null,
            'Email sent icon exists'
        );
        
        TestUtils.assert(
            document.querySelector('.alert-info') !== null,
            'Instructions panel exists'
        );
        
        // Test email display
        const emailDisplay = document.getElementById('userEmail');
        const storedEmail = sessionStorage.getItem('registeredEmail');
        
        TestUtils.assert(
            emailDisplay.textContent === (storedEmail || 'your email'),
            'Email is displayed correctly'
        );
        
        console.groupEnd();
    },
    
    async testResendButton() {
        console.group('🔄 Resend Button Test');
        
        const resendBtn = document.getElementById('resendBtn');
        const emailSentPage = window.currentEmailSentPage;
        
        if (!emailSentPage) {
            console.warn('Email sent page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test button initial state
        TestUtils.assert(
            !resendBtn.disabled,
            'Resend button is initially enabled'
        );
        
        // Test loading state
        emailSentPage.setLoading(true);
        await TestUtils.delay(100);
        
        const spinner = resendBtn.querySelector('.spinner-border');
        TestUtils.assert(
            !spinner.classList.contains('d-none'),
            'Spinner shows during loading'
        );
        
        TestUtils.assert(
            resendBtn.disabled,
            'Button is disabled during loading'
        );
        
        // Reset state
        emailSentPage.setLoading(false);
        await TestUtils.delay(100);
        
        // Test message display
        emailSentPage.showMessage('Test success message', 'success');
        await TestUtils.delay(100);
        
        const messageContainer = document.getElementById('resendMessage');
        TestUtils.assert(
            messageContainer.querySelector('.alert-success') !== null,
            'Success message displays correctly'
        );
        
        console.groupEnd();
    },
    
    async testRateLimiting() {
        console.group('⏱️ Rate Limiting Test');
        
        const emailSentPage = window.currentEmailSentPage;
        const resendBtn = document.getElementById('resendBtn');
        
        if (!emailSentPage) {
            console.warn('Email sent page not initialized');
            console.groupEnd();
            return;
        }
        
        // Simulate cooldown start
        emailSentPage.startCooldown();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            emailSentPage.resendCooldown === true,
            'Cooldown flag is set'
        );
        
        TestUtils.assert(
            resendBtn.disabled === true,
            'Button is disabled during cooldown'
        );
        
        TestUtils.assert(
            resendBtn.querySelector('.btn-text').textContent.includes('Resend available in'),
            'Countdown text is displayed'
        );
        
        console.groupEnd();
    },
    
    async testVerificationPage() {
        console.group('✅ Verification Page Tests');
        
        await this.testVerificationElements();
        await this.testVerificationStates();
        
        console.groupEnd();
    },
    
    async testVerificationElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('verifyingState') !== null,
            'Verifying state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('successState') !== null,
            'Success state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('errorState') !== null,
            'Error state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('errorMessage') !== null,
            'Error message element exists'
        );
        
        TestUtils.assert(
            document.getElementById('requestNewLink') !== null,
            'Request new link button exists'
        );
        
        console.groupEnd();
    },
    
    async testVerificationStates() {
        console.group('🔄 State Transitions Test');
        
        const verificationPage = window.currentEmailVerificationPage;
        
        if (!verificationPage) {
            console.warn('Verification page not initialized');
            console.groupEnd();
            return;
        }
        
        const verifyingState = document.getElementById('verifyingState');
        const successState = document.getElementById('successState');
        const errorState = document.getElementById('errorState');
        
        // Test initial state (should be verifying)
        TestUtils.assert(
            !verifyingState.classList.contains('d-none'),
            'Verifying state is visible initially'
        );
        
        TestUtils.assert(
            successState.classList.contains('d-none'),
            'Success state is hidden initially'
        );
        
        TestUtils.assert(
            errorState.classList.contains('d-none'),
            'Error state is hidden initially'
        );
        
        // Test success state
        verificationPage.showSuccess();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            verifyingState.classList.contains('d-none'),
            'Verifying state is hidden on success'
        );
        
        TestUtils.assert(
            !successState.classList.contains('d-none'),
            'Success state is visible on success'
        );
        
        TestUtils.assert(
            errorState.classList.contains('d-none'),
            'Error state remains hidden on success'
        );
        
        // Test error state
        verificationPage.showError('Test error message');
        await TestUtils.delay(100);
        
        TestUtils.assert(
            verifyingState.classList.contains('d-none'),
            'Verifying state is hidden on error'
        );
        
        TestUtils.assert(
            successState.classList.contains('d-none'),
            'Success state is hidden on error'
        );
        
        TestUtils.assert(
            !errorState.classList.contains('d-none'),
            'Error state is visible on error'
        );
        
        TestUtils.assert(
            document.getElementById('errorMessage').textContent === 'Test error message',
            'Error message is displayed correctly'
        );
        
        console.groupEnd();
    }
};

// Helper to navigate to test pages
const navigateToEmailVerificationPage = (page) => {
    if (window.router) {
        window.router.navigate(page);
    } else {
        console.log('Router not available. Navigate manually to:', page);
    }
};

// Run tests based on current page
const currentView = document.querySelector('.view:not([style*="display: none"])');
if (currentView && (currentView.id === 'verify-email-sent-view' || currentView.id === 'verify-email-view')) {
    console.log('🚀 Starting Email Verification Tests...');
    EmailVerificationTests.runAll().then(() => {
        console.log('✨ All tests completed!');
    });
} else {
    console.log('⚠️ Please navigate to an email verification page to run tests');
    console.log('Run one of:');
    console.log('- navigateToEmailVerificationPage("/verify-email-sent")');
    console.log('- navigateToEmailVerificationPage("/verify-email")');
}