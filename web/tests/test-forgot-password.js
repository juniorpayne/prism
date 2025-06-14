/**
 * Test script for Forgot Password functionality
 * Run this in the browser console while on the forgot password page
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

// Test suite for Forgot Password
const ForgotPasswordTests = {
    async runAll() {
        console.group('🧪 Forgot Password Tests');
        
        await this.testPageElements();
        await this.testFormValidation();
        await this.testSuccessState();
        await this.testRateLimiting();
        
        console.groupEnd();
    },
    
    async testPageElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('forgotPasswordForm') !== null,
            'Forgot password form exists'
        );
        
        TestUtils.assert(
            document.getElementById('forgotEmail') !== null,
            'Email input exists'
        );
        
        TestUtils.assert(
            document.getElementById('forgotPasswordBtn') !== null,
            'Submit button exists'
        );
        
        TestUtils.assert(
            document.getElementById('forgotPasswordSuccess') !== null,
            'Success view exists'
        );
        
        TestUtils.assert(
            document.getElementById('rateLimitWarning') !== null,
            'Rate limit warning container exists'
        );
        
        TestUtils.assert(
            document.querySelector('.bi-key') !== null,
            'Key icon exists'
        );
        
        console.groupEnd();
    },
    
    async testFormValidation() {
        console.group('✅ Form Validation Test');
        
        const forgotPage = window.currentForgotPasswordPage;
        const emailInput = document.getElementById('forgotEmail');
        const form = document.getElementById('forgotPasswordForm');
        
        if (!forgotPage) {
            console.warn('Forgot password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test empty email
        emailInput.value = '';
        emailInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            !emailInput.classList.contains('is-valid') && 
            !emailInput.classList.contains('is-invalid'),
            'Empty email shows no validation'
        );
        
        // Test invalid email
        emailInput.value = 'invalid-email';
        emailInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            emailInput.classList.contains('is-invalid'),
            'Invalid email shows error state'
        );
        
        // Test valid email
        emailInput.value = 'test@example.com';
        emailInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            emailInput.classList.contains('is-valid'),
            'Valid email shows success state'
        );
        
        console.groupEnd();
    },
    
    async testSuccessState() {
        console.group('🎉 Success State Test');
        
        const forgotPage = window.currentForgotPasswordPage;
        
        if (!forgotPage) {
            console.warn('Forgot password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Show success state
        forgotPage.showSuccess('test@example.com');
        await TestUtils.delay(100);
        
        const form = document.getElementById('forgotPasswordForm');
        const successView = document.getElementById('forgotPasswordSuccess');
        const sentToEmail = document.getElementById('sentToEmail');
        
        TestUtils.assert(
            form.classList.contains('d-none'),
            'Form is hidden in success state'
        );
        
        TestUtils.assert(
            !successView.classList.contains('d-none'),
            'Success view is visible'
        );
        
        TestUtils.assert(
            sentToEmail.textContent === 'test@example.com',
            'Email is displayed correctly'
        );
        
        // Test resend link
        const resendLink = document.getElementById('resendResetLink');
        TestUtils.assert(
            resendLink !== null,
            'Resend link exists'
        );
        
        // Click resend to go back to form
        resendLink.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            !form.classList.contains('d-none'),
            'Form is visible after clicking resend'
        );
        
        TestUtils.assert(
            successView.classList.contains('d-none'),
            'Success view is hidden after clicking resend'
        );
        
        console.groupEnd();
    },
    
    async testRateLimiting() {
        console.group('⏱️ Rate Limiting Test');
        
        const forgotPage = window.currentForgotPasswordPage;
        
        if (!forgotPage) {
            console.warn('Forgot password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test rate limit check
        forgotPage.requestCount = 0;
        forgotPage.lastRequestTime = 0;
        
        TestUtils.assert(
            forgotPage.checkRateLimit() === true,
            'First request is allowed'
        );
        
        // Simulate hitting rate limit
        forgotPage.requestCount = 3;
        forgotPage.lastRequestTime = Date.now();
        
        TestUtils.assert(
            forgotPage.checkRateLimit() === false,
            'Rate limit blocks after max requests'
        );
        
        const rateLimitWarning = document.getElementById('rateLimitWarning');
        TestUtils.assert(
            !rateLimitWarning.classList.contains('d-none'),
            'Rate limit warning is shown'
        );
        
        // Test rate limit message
        const rateLimitMessage = document.getElementById('rateLimitMessage');
        TestUtils.assert(
            rateLimitMessage.textContent.includes('Too many requests'),
            'Rate limit message is displayed'
        );
        
        // Reset for other tests
        forgotPage.hideRateLimit();
        forgotPage.requestCount = 0;
        forgotPage.lastRequestTime = 0;
        
        console.groupEnd();
    },
    
    async testLoadingState() {
        console.group('🔄 Loading State Test');
        
        const forgotPage = window.currentForgotPasswordPage;
        const submitBtn = document.getElementById('forgotPasswordBtn');
        
        if (!forgotPage) {
            console.warn('Forgot password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test loading state
        forgotPage.setLoading(true);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            submitBtn.disabled === true,
            'Button is disabled during loading'
        );
        
        const spinner = submitBtn.querySelector('.spinner-border');
        TestUtils.assert(
            !spinner.classList.contains('d-none'),
            'Spinner is visible during loading'
        );
        
        TestUtils.assert(
            submitBtn.querySelector('.btn-text').textContent === 'Sending...',
            'Button text changes during loading'
        );
        
        // Reset loading state
        forgotPage.setLoading(false);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            submitBtn.disabled === false,
            'Button is enabled after loading'
        );
        
        TestUtils.assert(
            spinner.classList.contains('d-none'),
            'Spinner is hidden after loading'
        );
        
        TestUtils.assert(
            submitBtn.querySelector('.btn-text').textContent === 'Send Reset Link',
            'Button text resets after loading'
        );
        
        console.groupEnd();
    }
};

// Helper to navigate to forgot password page
const navigateToForgotPassword = () => {
    if (window.router) {
        window.router.navigate('/forgot-password');
    } else {
        console.log('Router not available. Navigate manually to: /forgot-password');
    }
};

// Run tests if on forgot password page
const currentView = document.querySelector('.view:not([style*="display: none"])');
if (currentView && currentView.id === 'forgot-password-view') {
    console.log('🚀 Starting Forgot Password Tests...');
    ForgotPasswordTests.runAll().then(() => {
        console.log('✨ All tests completed!');
    });
} else {
    console.log('⚠️ Please navigate to the forgot password page to run tests');
    console.log('Run: navigateToForgotPassword()');
}