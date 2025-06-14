/**
 * Test script for Login Page functionality
 * Run this in the browser console while on the login page
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

// Test suite for Login Page
const LoginPageTests = {
    async runAll() {
        console.group('🧪 Login Page Tests');
        
        await this.testPageElements();
        await this.testFormValidation();
        await this.testPasswordToggle();
        await this.testRememberMe();
        await this.testLoadingState();
        await this.testErrorHandling();
        
        console.groupEnd();
    },
    
    async testPageElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('loginForm') !== null,
            'Login form exists'
        );
        
        TestUtils.assert(
            document.getElementById('username') !== null,
            'Username input exists'
        );
        
        TestUtils.assert(
            document.getElementById('password') !== null,
            'Password input exists'
        );
        
        TestUtils.assert(
            document.getElementById('rememberMe') !== null,
            'Remember me checkbox exists'
        );
        
        TestUtils.assert(
            document.getElementById('loginBtn') !== null,
            'Login button exists'
        );
        
        TestUtils.assert(
            document.getElementById('togglePassword') !== null,
            'Password toggle button exists'
        );
        
        TestUtils.assert(
            document.querySelector('a[href="/forgot-password"]') !== null,
            'Forgot password link exists'
        );
        
        TestUtils.assert(
            document.querySelector('a[href="/register"]') !== null,
            'Register link exists'
        );
        
        console.groupEnd();
    },
    
    async testFormValidation() {
        console.group('✔️ Form Validation Test');
        
        const form = document.getElementById('loginForm');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const loginBtn = document.getElementById('loginBtn');
        
        // Clear inputs
        usernameInput.value = '';
        passwordInput.value = '';
        
        // Try to submit empty form
        loginBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            form.classList.contains('was-validated'),
            'Form shows validation state'
        );
        
        // Fill username only
        usernameInput.value = 'testuser';
        passwordInput.value = '';
        loginBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            form.classList.contains('was-validated'),
            'Form still shows validation with only username'
        );
        
        // Fill both fields
        passwordInput.value = 'testpass';
        TestUtils.assert(
            form.checkValidity(),
            'Form is valid with both fields filled'
        );
        
        console.groupEnd();
    },
    
    async testPasswordToggle() {
        console.group('👁️ Password Toggle Test');
        
        const passwordInput = document.getElementById('password');
        const toggleBtn = document.getElementById('togglePassword');
        const icon = toggleBtn.querySelector('i');
        
        // Initial state
        TestUtils.assert(
            passwordInput.type === 'password',
            'Password input starts as password type'
        );
        
        TestUtils.assert(
            icon.classList.contains('bi-eye'),
            'Toggle icon starts as eye icon'
        );
        
        // Toggle to show
        toggleBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            passwordInput.type === 'text',
            'Password input changes to text type'
        );
        
        TestUtils.assert(
            icon.classList.contains('bi-eye-slash'),
            'Toggle icon changes to eye-slash'
        );
        
        // Toggle back to hide
        toggleBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            passwordInput.type === 'password',
            'Password input changes back to password type'
        );
        
        console.groupEnd();
    },
    
    async testRememberMe() {
        console.group('💾 Remember Me Test');
        
        const rememberMe = document.getElementById('rememberMe');
        const usernameInput = document.getElementById('username');
        
        // Clear localStorage
        localStorage.removeItem('rememberMe');
        localStorage.removeItem('rememberedUsername');
        
        // Check remember me
        rememberMe.checked = true;
        usernameInput.value = 'testuser';
        
        // Simulate successful login (would normally be done after API call)
        if (rememberMe.checked) {
            localStorage.setItem('rememberMe', 'true');
            localStorage.setItem('rememberedUsername', usernameInput.value);
        }
        
        TestUtils.assert(
            localStorage.getItem('rememberMe') === 'true',
            'Remember me saved to localStorage'
        );
        
        TestUtils.assert(
            localStorage.getItem('rememberedUsername') === 'testuser',
            'Username saved to localStorage'
        );
        
        // Clean up
        localStorage.removeItem('rememberMe');
        localStorage.removeItem('rememberedUsername');
        
        console.groupEnd();
    },
    
    async testLoadingState() {
        console.group('⏳ Loading State Test');
        
        const loginBtn = document.getElementById('loginBtn');
        const spinner = loginBtn.querySelector('.spinner-border');
        const btnText = loginBtn.querySelector('.btn-text');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        
        // Get login page instance
        const loginPage = window.currentLoginPage;
        if (!loginPage) {
            console.warn('Login page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test loading state
        loginPage.setLoading(true);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            !spinner.classList.contains('d-none'),
            'Spinner is visible during loading'
        );
        
        TestUtils.assert(
            btnText.textContent === 'Signing in...',
            'Button text changes during loading'
        );
        
        TestUtils.assert(
            loginBtn.disabled === true,
            'Login button is disabled during loading'
        );
        
        TestUtils.assert(
            usernameInput.disabled === true,
            'Username input is disabled during loading'
        );
        
        // Reset loading state
        loginPage.setLoading(false);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            spinner.classList.contains('d-none'),
            'Spinner is hidden after loading'
        );
        
        TestUtils.assert(
            btnText.textContent === 'Sign In',
            'Button text resets after loading'
        );
        
        console.groupEnd();
    },
    
    async testErrorHandling() {
        console.group('❌ Error Handling Test');
        
        const loginPage = window.currentLoginPage;
        if (!loginPage) {
            console.warn('Login page not initialized');
            console.groupEnd();
            return;
        }
        
        // Show error
        loginPage.showError('Test error message');
        await TestUtils.delay(100);
        
        const errorAlert = document.getElementById('loginError');
        TestUtils.assert(
            errorAlert !== null,
            'Error alert is created'
        );
        
        TestUtils.assert(
            errorAlert.querySelector('.error-message').textContent.includes('Test error message'),
            'Error message is displayed correctly'
        );
        
        // Clear error
        loginPage.clearError();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            document.getElementById('loginError') === null,
            'Error alert is removed'
        );
        
        console.groupEnd();
    }
};

// Run tests if on login page
if (window.location.pathname === '/login' || document.getElementById('login-view')?.style.display !== 'none') {
    console.log('🚀 Starting Login Page Tests...');
    LoginPageTests.runAll().then(() => {
        console.log('✨ All tests completed!');
    });
} else {
    console.log('⚠️ Please navigate to the login page to run tests');
    console.log('Run: router.navigate("/login")');
}