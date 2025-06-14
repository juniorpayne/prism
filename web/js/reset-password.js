/**
 * Reset Password Page Handler
 * Manages password reset functionality with token validation
 */

class ResetPasswordPage {
    constructor() {
        // Get token from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.token = urlParams.get('token');
        
        // Elements
        this.validatingState = document.getElementById('validatingState');
        this.invalidTokenState = document.getElementById('invalidTokenState');
        this.invalidTokenMessage = document.getElementById('invalidTokenMessage');
        this.form = document.getElementById('resetPasswordForm');
        this.successState = document.getElementById('resetSuccessState');
        
        this.newPasswordInput = document.getElementById('newPassword');
        this.confirmPasswordInput = document.getElementById('resetConfirmPassword');
        this.resetBtn = document.getElementById('resetBtn');
        
        this.toggleNewPassword = document.getElementById('toggleNewPassword');
        this.toggleConfirmPassword = document.getElementById('toggleConfirmPassword');
        
        // Password validator with custom IDs
        this.passwordValidator = new PasswordValidator({
            strengthBarId: 'resetPasswordStrength',
            strengthTextId: 'resetStrengthText',
            requirementsId: 'resetPasswordReqs'
        });
        
        // Initialize
        if (this.token) {
            this.validateToken();
        } else {
            this.showInvalidToken('No reset token provided');
        }
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Password strength checker
        this.newPasswordInput.addEventListener('input', () => {
            this.passwordValidator.checkStrength(this.newPasswordInput.value);
            this.checkPasswordMatch();
        });
        
        // Password match checker
        this.confirmPasswordInput.addEventListener('input', () => this.checkPasswordMatch());
        
        // Toggle password visibility
        this.toggleNewPassword.addEventListener('click', () => 
            this.togglePasswordVisibility('newPassword', 'toggleNewPassword'));
        this.toggleConfirmPassword.addEventListener('click', () => 
            this.togglePasswordVisibility('resetConfirmPassword', 'toggleConfirmPassword'));
        
        // Focus on password field when form is shown
        this.newPasswordInput.addEventListener('focus', () => {
            const reqs = document.getElementById('resetPasswordReqs');
            if (reqs) {
                reqs.classList.remove('d-none');
            }
        });
    }
    
    async validateToken() {
        // In a real implementation, you might want to validate the token
        // with a separate endpoint first. For now, we'll show the form
        // and let the reset endpoint handle validation
        
        // Simulate validation delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Show form
        this.validatingState.classList.add('d-none');
        this.form.classList.remove('d-none');
        
        // Focus on password field
        this.newPasswordInput.focus();
    }
    
    showInvalidToken(message = 'Invalid or expired reset link') {
        this.validatingState.classList.add('d-none');
        this.form.classList.add('d-none');
        this.successState.classList.add('d-none');
        this.invalidTokenState.classList.remove('d-none');
        
        // Update error message
        this.invalidTokenMessage.textContent = message;
    }
    
    showSuccess() {
        this.form.classList.add('d-none');
        this.validatingState.classList.add('d-none');
        this.invalidTokenState.classList.add('d-none');
        this.successState.classList.remove('d-none');
        
        // Auto-redirect to login after 5 seconds
        let countdown = 5;
        const continueBtn = this.successState.querySelector('.btn-primary');
        const originalText = continueBtn.textContent;
        
        const interval = setInterval(() => {
            countdown--;
            continueBtn.textContent = `${originalText} (${countdown})`;
            
            if (countdown <= 0) {
                clearInterval(interval);
                if (window.router) {
                    window.router.navigate('/login');
                } else {
                    window.location.href = '/login';
                }
            }
        }, 1000);
    }
    
    togglePasswordVisibility(inputId, buttonId) {
        const input = document.getElementById(inputId);
        const button = document.getElementById(buttonId);
        const icon = button.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('bi-eye');
            icon.classList.add('bi-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('bi-eye-slash');
            icon.classList.add('bi-eye');
        }
    }
    
    checkPasswordMatch() {
        const password = this.newPasswordInput.value;
        const confirmPassword = this.confirmPasswordInput.value;
        
        if (confirmPassword.length > 0) {
            if (password !== confirmPassword) {
                this.confirmPasswordInput.classList.add('is-invalid');
                this.confirmPasswordInput.classList.remove('is-valid');
            } else {
                this.confirmPasswordInput.classList.remove('is-invalid');
                this.confirmPasswordInput.classList.add('is-valid');
            }
        } else {
            this.confirmPasswordInput.classList.remove('is-invalid', 'is-valid');
        }
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        // Clear any existing errors
        this.clearError();
        
        // Validate password requirements
        if (!this.passwordValidator.isValid()) {
            const unmetReqs = this.passwordValidator.getUnmetRequirements();
            this.showError(`Password does not meet requirements: ${unmetReqs.join(', ')}`);
            this.newPasswordInput.focus();
            return;
        }
        
        // Validate password match
        if (this.newPasswordInput.value !== this.confirmPasswordInput.value) {
            this.confirmPasswordInput.classList.add('is-invalid');
            this.showError('Passwords do not match');
            this.confirmPasswordInput.focus();
            return;
        }
        
        // Show loading state
        this.setLoading(true);
        
        try {
            const response = await window.api.resetPassword(this.token, this.newPasswordInput.value);
            
            // Show success state
            this.showSuccess();
            
            // Clear form
            this.form.reset();
            this.passwordValidator.reset();
            
        } catch (error) {
            console.error('Reset password error:', error);
            
            if (error.status === 400 || error.status === 401) {
                // Invalid or expired token
                this.showInvalidToken(error.message || 'This reset link is invalid or has expired');
            } else if (error.status === 422) {
                // Validation error
                this.showError(error.message || 'Password does not meet requirements');
            } else {
                // Generic error
                this.showError(error.message || 'Failed to reset password. Please try again.');
            }
        } finally {
            this.setLoading(false);
        }
    }
    
    showError(message) {
        // Create or update error alert
        let alert = document.getElementById('resetError');
        if (!alert) {
            alert = document.createElement('div');
            alert.id = 'resetError';
            alert.className = 'alert alert-danger alert-dismissible fade show mb-3';
            this.form.insertBefore(alert, this.form.firstChild);
        }
        
        alert.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    }
    
    clearError() {
        const alert = document.getElementById('resetError');
        if (alert) {
            alert.remove();
        }
    }
    
    setLoading(loading) {
        const spinner = this.resetBtn.querySelector('.spinner-border');
        const text = this.resetBtn.querySelector('.btn-text');
        
        if (loading) {
            spinner.classList.remove('d-none');
            text.textContent = 'Resetting password...';
            this.resetBtn.disabled = true;
            this.newPasswordInput.disabled = true;
            this.confirmPasswordInput.disabled = true;
            this.toggleNewPassword.disabled = true;
            this.toggleConfirmPassword.disabled = true;
        } else {
            spinner.classList.add('d-none');
            text.textContent = 'Reset Password';
            this.resetBtn.disabled = false;
            this.newPasswordInput.disabled = false;
            this.confirmPasswordInput.disabled = false;
            this.toggleNewPassword.disabled = false;
            this.toggleConfirmPassword.disabled = false;
        }
    }
    
    destroy() {
        // Clean up
        this.form.reset();
        this.passwordValidator.reset();
        this.clearError();
        
        // Reset to initial state
        this.validatingState.classList.remove('d-none');
        this.form.classList.add('d-none');
        this.invalidTokenState.classList.add('d-none');
        this.successState.classList.add('d-none');
    }
}

// Export for use in router
window.ResetPasswordPage = ResetPasswordPage;