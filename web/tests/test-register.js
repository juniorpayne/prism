/**
 * Test script for Registration Page functionality
 * Run this in the browser console while on the registration page
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

// Test suite for Registration Page
const RegisterPageTests = {
    async runAll() {
        console.group('🧪 Registration Page Tests');
        
        await this.testPageElements();
        await this.testEmailValidation();
        await this.testUsernameValidation();
        await this.testPasswordStrength();
        await this.testPasswordMatching();
        await this.testFormValidation();
        await this.testLoadingState();
        
        console.groupEnd();
    },
    
    async testPageElements() {
        console.group('📋 Page Elements Test');
        
        TestUtils.assert(
            document.getElementById('registerForm') !== null,
            'Registration form exists'
        );
        
        TestUtils.assert(
            document.getElementById('email') !== null,
            'Email input exists'
        );
        
        TestUtils.assert(
            document.getElementById('reg-username') !== null,
            'Username input exists'
        );
        
        TestUtils.assert(
            document.getElementById('reg-password') !== null,
            'Password input exists'
        );
        
        TestUtils.assert(
            document.getElementById('confirmPassword') !== null,
            'Confirm password input exists'
        );
        
        TestUtils.assert(
            document.getElementById('terms') !== null,
            'Terms checkbox exists'
        );
        
        TestUtils.assert(
            document.getElementById('registerBtn') !== null,
            'Register button exists'
        );
        
        TestUtils.assert(
            document.getElementById('passwordStrength') !== null,
            'Password strength bar exists'
        );
        
        TestUtils.assert(
            document.getElementById('passwordReqs') !== null,
            'Password requirements panel exists'
        );
        
        console.groupEnd();
    },
    
    async testEmailValidation() {
        console.group('📧 Email Validation Test');
        
        const emailInput = document.getElementById('email');
        const registerPage = window.currentRegisterPage;
        
        // Test invalid emails
        const invalidEmails = ['test', 'test@', '@test.com', 'test@test'];
        for (const email of invalidEmails) {
            emailInput.value = email;
            registerPage.validateEmail();
            await TestUtils.delay(100);
            
            TestUtils.assert(
                emailInput.classList.contains('is-invalid'),
                `Invalid email "${email}" marked as invalid`
            );
        }
        
        // Test valid emails
        const validEmails = ['test@example.com', 'user.name@domain.co.uk', 'test+tag@test.org'];
        for (const email of validEmails) {
            emailInput.value = email;
            registerPage.validateEmail();
            await TestUtils.delay(100);
            
            TestUtils.assert(
                emailInput.classList.contains('is-valid'),
                `Valid email "${email}" marked as valid`
            );
        }
        
        console.groupEnd();
    },
    
    async testUsernameValidation() {
        console.group('👤 Username Validation Test');
        
        const usernameInput = document.getElementById('reg-username');
        const registerPage = window.currentRegisterPage;
        
        // Test invalid usernames
        const invalidUsernames = ['ab', 'a', 'user-name', 'user@name', 'a'.repeat(31)];
        for (const username of invalidUsernames) {
            usernameInput.value = username;
            registerPage.validateUsername();
            await TestUtils.delay(100);
            
            TestUtils.assert(
                usernameInput.classList.contains('is-invalid'),
                `Invalid username "${username}" marked as invalid`
            );
        }
        
        // Test valid usernames
        const validUsernames = ['user', 'test_user', 'User123', 'a'.repeat(30)];
        for (const username of validUsernames) {
            usernameInput.value = username;
            registerPage.validateUsername();
            await TestUtils.delay(100);
            
            TestUtils.assert(
                usernameInput.classList.contains('is-valid'),
                `Valid username "${username}" marked as valid`
            );
        }
        
        console.groupEnd();
    },
    
    async testPasswordStrength() {
        console.group('🔐 Password Strength Test');
        
        const passwordInput = document.getElementById('reg-password');
        const strengthBar = document.getElementById('passwordStrength');
        const strengthText = document.getElementById('strengthText');
        const registerPage = window.currentRegisterPage;
        
        // Test password strength levels
        const passwordTests = [
            { password: '', expectedWidth: '0%', expectedText: 'Enter password' },
            { password: 'pass', expectedWidth: '20%', expectedText: 'Very weak' },
            { password: 'password', expectedWidth: '20%', expectedText: 'Very weak' },
            { password: 'Password1', expectedWidth: '60%', expectedText: 'Fair' },
            { password: 'Password123', expectedWidth: '80%', expectedText: 'Good' },
            { password: 'Password123!@#', expectedWidth: '100%', expectedText: 'Strong' }
        ];
        
        for (const test of passwordTests) {
            passwordInput.value = test.password;
            passwordInput.focus();
            registerPage.checkPasswordStrength();
            await TestUtils.delay(100);
            
            TestUtils.assert(
                strengthBar.style.width === test.expectedWidth,
                `Password "${test.password}" shows ${test.expectedWidth} strength`
            );
            
            TestUtils.assert(
                strengthText.textContent === test.expectedText,
                `Password "${test.password}" shows "${test.expectedText}" text`
            );
        }
        
        // Test requirement indicators
        passwordInput.value = 'Password123!@#';
        registerPage.checkPasswordStrength();
        await TestUtils.delay(100);
        
        const requirements = ['length', 'uppercase', 'lowercase', 'number', 'special'];
        for (const req of requirements) {
            const element = document.querySelector(`[data-req="${req}"]`);
            const icon = element.querySelector('i');
            
            TestUtils.assert(
                icon.classList.contains('bi-check-circle-fill'),
                `Requirement "${req}" shows as met`
            );
        }
        
        console.groupEnd();
    },
    
    async testPasswordMatching() {
        console.group('🔄 Password Matching Test');
        
        const passwordInput = document.getElementById('reg-password');
        const confirmInput = document.getElementById('confirmPassword');
        const registerPage = window.currentRegisterPage;
        
        // Test non-matching passwords
        passwordInput.value = 'Password123!';
        confirmInput.value = 'Password123';
        registerPage.checkPasswordMatch();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            confirmInput.classList.contains('is-invalid'),
            'Non-matching passwords marked as invalid'
        );
        
        // Test matching passwords
        confirmInput.value = 'Password123!';
        registerPage.checkPasswordMatch();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            confirmInput.classList.contains('is-valid'),
            'Matching passwords marked as valid'
        );
        
        console.groupEnd();
    },
    
    async testFormValidation() {
        console.group('📝 Form Validation Test');
        
        const form = document.getElementById('registerForm');
        const emailInput = document.getElementById('email');
        const usernameInput = document.getElementById('reg-username');
        const passwordInput = document.getElementById('reg-password');
        const confirmInput = document.getElementById('confirmPassword');
        const termsCheckbox = document.getElementById('terms');
        const registerBtn = document.getElementById('registerBtn');
        const registerPage = window.currentRegisterPage;
        
        // Clear form
        form.classList.remove('was-validated');
        emailInput.value = '';
        usernameInput.value = '';
        passwordInput.value = '';
        confirmInput.value = '';
        termsCheckbox.checked = false;
        
        // Try to submit empty form
        registerBtn.click();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            form.classList.contains('was-validated'),
            'Form shows validation state on empty submit'
        );
        
        // Fill form with valid data
        emailInput.value = 'test@example.com';
        usernameInput.value = 'testuser';
        passwordInput.value = 'StrongPass123!@#';
        confirmInput.value = 'StrongPass123!@#';
        termsCheckbox.checked = true;
        
        // Update password strength
        registerPage.checkPasswordStrength();
        registerPage.checkPasswordMatch();
        await TestUtils.delay(100);
        
        TestUtils.assert(
            form.checkValidity(),
            'Form is valid with all fields correctly filled'
        );
        
        console.groupEnd();
    },
    
    async testLoadingState() {
        console.group('⏳ Loading State Test');
        
        const registerBtn = document.getElementById('registerBtn');
        const spinner = registerBtn.querySelector('.spinner-border');
        const btnText = registerBtn.querySelector('.btn-text');
        const form = document.getElementById('registerForm');
        
        const registerPage = window.currentRegisterPage;
        if (!registerPage) {
            console.warn('Register page not initialized');
            console.groupEnd();
            return;
        }
        
        // Test loading state
        registerPage.setLoading(true);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            !spinner.classList.contains('d-none'),
            'Spinner is visible during loading'
        );
        
        TestUtils.assert(
            btnText.textContent === 'Creating account...',
            'Button text changes during loading'
        );
        
        TestUtils.assert(
            registerBtn.disabled === true,
            'Register button is disabled during loading'
        );
        
        TestUtils.assert(
            form.querySelectorAll('input:disabled').length > 0,
            'Form inputs are disabled during loading'
        );
        
        // Reset loading state
        registerPage.setLoading(false);
        await TestUtils.delay(100);
        
        TestUtils.assert(
            spinner.classList.contains('d-none'),
            'Spinner is hidden after loading'
        );
        
        TestUtils.assert(
            btnText.textContent === 'Create Account',
            'Button text resets after loading'
        );
        
        console.groupEnd();
    }
};

// Run tests if on register page
if (window.location.pathname === '/register' || document.getElementById('register-view')?.style.display !== 'none') {
    console.log('🚀 Starting Registration Page Tests...');
    RegisterPageTests.runAll().then(() => {
        console.log('✨ All tests completed!');
    });
} else {
    console.log('⚠️ Please navigate to the registration page to run tests');
    console.log('Run: router.navigate("/register")');
}