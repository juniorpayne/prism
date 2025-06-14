/**
 * Test script for Reset Password functionality
 * Run this in the browser console while on the reset password page
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

// Test suite for Reset Password
const ResetPasswordTests = {
    async runAll() {
        console.group('🧪 Reset Password Tests');
        
        await this.testPageElements();
        await this.testTokenValidation();
        await this.testPasswordValidation();
        await this.testPasswordMatch();
        await this.testPasswordToggles();
        await this.testFormSubmission();
        
        console.groupEnd();
    },
    
    async testPageElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('validatingState') !== null,
            'Validating state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('invalidTokenState') !== null,
            'Invalid token state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('resetPasswordForm') !== null,
            'Reset password form exists'
        );
        
        TestUtils.assert(
            document.getElementById('resetSuccessState') !== null,
            'Success state container exists'
        );
        
        TestUtils.assert(
            document.getElementById('newPassword') !== null,
            'New password input exists'
        );
        
        TestUtils.assert(
            document.getElementById('resetConfirmPassword') !== null,
            'Confirm password input exists'
        );
        
        TestUtils.assert(
            document.getElementById('toggleNewPassword') !== null,
            'New password toggle button exists'
        );
        
        TestUtils.assert(
            document.getElementById('toggleConfirmPassword') !== null,
            'Confirm password toggle button exists'
        );
        
        TestUtils.assert(
            document.getElementById('resetBtn') !== null,
            'Reset button exists'
        );
        
        TestUtils.assert(
            document.querySelector('.bi-shield-lock') !== null,
            'Shield lock icon exists'
        );
        
        console.groupEnd();
    },
    
    async testTokenValidation() {
        console.group('🔑 Token Validation Test');
        
        const resetPage = window.currentResetPasswordPage;
        
        if (!resetPage) {
            console.warn('Reset password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Check if token was extracted from URL
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        
        TestUtils.assert(
            resetPage.token === token,
            'Token extracted from URL correctly'
        );
        
        // Test invalid token display
        resetPage.showInvalidToken('Test invalid token message');
        await TestUtils.delay(100);
        
        const invalidTokenState = document.getElementById('invalidTokenState');
        const invalidTokenMessage = document.getElementById('invalidTokenMessage');
        
        TestUtils.assert(
            !invalidTokenState.classList.contains('d-none'),
            'Invalid token state is visible'
        );
        
        TestUtils.assert(
            invalidTokenMessage.textContent === 'Test invalid token message',
            'Invalid token message displays correctly'
        );
        
        // Reset to form view for other tests
        resetPage.validatingState.classList.add('d-none');
        resetPage.invalidTokenState.classList.add('d-none');
        resetPage.form.classList.remove('d-none');
        
        console.groupEnd();
    },
    
    async testPasswordValidation() {
        console.group('🔐 Password Validation Test');
        
        const resetPage = window.currentResetPasswordPage;
        const passwordInput = document.getElementById('newPassword');
        
        if (!resetPage || !resetPage.passwordValidator) {
            console.warn('Reset page or password validator not initialized');
            console.groupEnd();
            return;
        }
        
        // Test weak password
        passwordInput.value = 'weak';
        passwordInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            !resetPage.passwordValidator.isValid(),
            'Weak password fails validation'
        );
        
        const strengthBar = document.getElementById('resetPasswordStrength');
        TestUtils.assert(
            strengthBar.classList.contains('bg-danger'),
            'Strength bar shows danger for weak password'
        );
        
        // Test strong password
        passwordInput.value = 'StrongP@ssw0rd123!';
        passwordInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            resetPage.passwordValidator.isValid(),
            'Strong password passes validation'
        );
        
        TestUtils.assert(
            strengthBar.classList.contains('bg-success'),
            'Strength bar shows success for strong password'
        );
        
        // Test requirements display
        const requirementsEl = document.getElementById('resetPasswordReqs');
        TestUtils.assert(
            !requirementsEl.classList.contains('d-none'),
            'Password requirements are visible when typing'
        );
        
        // Check all requirements are met
        const metRequirements = requirementsEl.querySelectorAll('.bi-check-circle-fill').length;
        TestUtils.assert(
            metRequirements === 5,
            'All 5 password requirements show as met'
        );
        
        console.groupEnd();
    },
    
    async testPasswordMatch() {
        console.group('🔄 Password Match Test');
        
        const resetPage = window.currentResetPasswordPage;
        const passwordInput = document.getElementById('newPassword');
        const confirmInput = document.getElementById('resetConfirmPassword');
        
        if (!resetPage) {
            console.warn('Reset password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Set password
        passwordInput.value = 'TestP@ssw0rd123!';
        passwordInput.dispatchEvent(new Event('input'));
        
        // Test non-matching password
        confirmInput.value = 'DifferentP@ssw0rd123!';
        confirmInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            confirmInput.classList.contains('is-invalid'),
            'Non-matching password shows invalid state'
        );
        
        // Test matching password
        confirmInput.value = 'TestP@ssw0rd123!';
        confirmInput.dispatchEvent(new Event('input'));
        await TestUtils.delay(100);
        
        TestUtils.assert(
            confirmInput.classList.contains('is-valid'),
            'Matching password shows valid state'
        );
        
        TestUtils.assert(
            !confirmInput.classList.contains('is-invalid'),
            'Invalid state removed when passwords match'
        );
        
        console.groupEnd();
    },
    
    async testPasswordToggles() {
        console.group('👁️ Password Toggle Test');
        
        const resetPage = window.currentResetPasswordPage;
        const passwordInput = document.getElementById('newPassword');
        const confirmInput = document.getElementById('resetConfirmPassword');
        const toggleNew = document.getElementById('toggleNewPassword');
        const toggleConfirm = document.getElementById('toggleConfirmPassword');
        
        if (!resetPage) {
            console.warn('Reset password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Set passwords
        passwordInput.value = 'TestP@ssw0rd123!';
        confirmInput.value = 'TestP@ssw0rd123!';
        
        // Test new password toggle
        TestUtils.assert(
            passwordInput.type === 'password',
            'New password input starts as password type'
        );
        
        toggleNew.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            passwordInput.type === 'text',
            'New password input changes to text type'
        );
        
        const newIcon = toggleNew.querySelector('i');
        TestUtils.assert(
            newIcon.classList.contains('bi-eye-slash'),
            'New password toggle icon changes to eye-slash'
        );
        
        // Toggle back
        toggleNew.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            passwordInput.type === 'password',
            'New password input reverts to password type'
        );
        
        // Test confirm password toggle
        toggleConfirm.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            confirmInput.type === 'text',
            'Confirm password input changes to text type'
        );
        
        console.groupEnd();
    },
    
    async testFormSubmission() {
        console.group('📤 Form Submission Test');
        
        const resetPage = window.currentResetPasswordPage;
        const resetBtn = document.getElementById('resetBtn');
        
        if (!resetPage) {
            console.warn('Reset password page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test loading state
        resetPage.setLoading(true);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            resetBtn.disabled === true,
            'Reset button is disabled during loading'
        );
        
        const spinner = resetBtn.querySelector('.spinner-border');
        TestUtils.assert(
            !spinner.classList.contains('d-none'),
            'Spinner is visible during loading'
        );
        
        TestUtils.assert(
            resetBtn.querySelector('.btn-text').textContent === 'Resetting password...',
            'Button text changes during loading'
        );
        
        // Test inputs disabled during loading
        TestUtils.assert(
            document.getElementById('newPassword').disabled === true,
            'Password input is disabled during loading'
        );
        
        // Reset loading state
        resetPage.setLoading(false);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            resetBtn.disabled === false,
            'Reset button is enabled after loading'
        );
        
        // Test success state
        resetPage.showSuccess();
        await TestUtils.delay(100);
        
        const successState = document.getElementById('resetSuccessState');
        TestUtils.assert(
            !successState.classList.contains('d-none'),
            'Success state is visible'
        );
        
        TestUtils.assert(
            resetPage.form.classList.contains('d-none'),
            'Form is hidden on success'
        );
        
        console.groupEnd();
    }
};

// Helper to navigate to reset password page with token
const navigateToResetPassword = (token = 'test-token-12345') => {
    if (window.router) {
        window.router.navigate(`/reset-password?token=${token}`);
    } else {
        console.log('Router not available. Navigate manually to:', `/reset-password?token=${token}`);
    }
};

// Run tests if on reset password page
const currentView = document.querySelector('.view:not([style*="display: none"])');
if (currentView && currentView.id === 'reset-password-view') {
    console.log('🚀 Starting Reset Password Tests...');
    ResetPasswordTests.runAll().then(() => {
        console.log('✨ All tests completed!');
    });
} else {
    console.log('⚠️ Please navigate to the reset password page to run tests');
    console.log('Run: navigateToResetPassword("your-token-here")');
}