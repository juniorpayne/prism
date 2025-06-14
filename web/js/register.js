/**
 * Registration Page Handler for Prism DNS
 * Handles user registration with password strength validation
 */

class RegisterPage {
    constructor() {
        this.form = document.getElementById('registerForm');
        this.emailInput = document.getElementById('email');
        this.usernameInput = document.getElementById('reg-username');
        this.passwordInput = document.getElementById('reg-password');
        this.confirmPasswordInput = document.getElementById('confirmPassword');
        this.termsCheckbox = document.getElementById('terms');
        this.registerBtn = document.getElementById('registerBtn');
        this.passwordReqs = document.getElementById('passwordReqs');
        
        this.passwordRequirements = {
            length: false,
            uppercase: false,
            lowercase: false,
            number: false,
            special: false
        };
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.form?.addEventListener('submit', (e) => this.handleSubmit(e));
        this.passwordInput?.addEventListener('input', () => this.checkPasswordStrength());
        this.passwordInput?.addEventListener('focus', () => this.showPasswordRequirements());
        this.passwordInput?.addEventListener('blur', () => this.hidePasswordRequirements());
        this.confirmPasswordInput?.addEventListener('input', () => this.checkPasswordMatch());
        this.usernameInput?.addEventListener('input', () => this.validateUsername());
        this.emailInput?.addEventListener('input', () => this.validateEmail());
        this.emailInput?.addEventListener('blur', () => this.checkEmailAvailability());
    }
    
    /**
     * Show password requirements panel
     */
    showPasswordRequirements() {
        this.passwordReqs.classList.remove('d-none');
    }
    
    /**
     * Hide password requirements panel if password is empty
     */
    hidePasswordRequirements() {
        if (this.passwordInput.value.length === 0) {
            this.passwordReqs.classList.add('d-none');
        }
    }
    
    /**
     * Check password strength and update UI
     */
    checkPasswordStrength() {
        const password = this.passwordInput.value;
        const strengthBar = document.getElementById('passwordStrength');
        const strengthText = document.getElementById('strengthText');
        
        // Check requirements
        this.passwordRequirements.length = password.length >= 12;
        this.passwordRequirements.uppercase = /[A-Z]/.test(password);
        this.passwordRequirements.lowercase = /[a-z]/.test(password);
        this.passwordRequirements.number = /[0-9]/.test(password);
        this.passwordRequirements.special = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        
        // Update requirement indicators
        Object.keys(this.passwordRequirements).forEach(req => {
            const element = document.querySelector(`[data-req="${req}"]`);
            if (element) {
                const icon = element.querySelector('i');
                if (this.passwordRequirements[req]) {
                    icon.classList.remove('bi-circle');
                    icon.classList.add('bi-check-circle-fill', 'text-success');
                } else {
                    icon.classList.remove('bi-check-circle-fill', 'text-success');
                    icon.classList.add('bi-circle');
                }
            }
        });
        
        // Calculate strength
        const metRequirements = Object.values(this.passwordRequirements).filter(v => v).length;
        const strength = (metRequirements / 5) * 100;
        
        // Update progress bar
        strengthBar.style.width = `${strength}%`;
        strengthBar.className = 'progress-bar';
        
        if (password.length === 0) {
            strengthBar.style.width = '0%';
            strengthText.textContent = 'Enter password';
        } else if (strength <= 20) {
            strengthBar.classList.add('bg-danger');
            strengthText.textContent = 'Very weak';
        } else if (strength <= 40) {
            strengthBar.classList.add('bg-warning');
            strengthText.textContent = 'Weak';
        } else if (strength <= 60) {
            strengthBar.classList.add('bg-info');
            strengthText.textContent = 'Fair';
        } else if (strength <= 80) {
            strengthBar.classList.add('bg-primary');
            strengthText.textContent = 'Good';
        } else {
            strengthBar.classList.add('bg-success');
            strengthText.textContent = 'Strong';
        }
        
        // Also check password match if confirm field has value
        if (this.confirmPasswordInput.value) {
            this.checkPasswordMatch();
        }
    }
    
    /**
     * Check if passwords match
     */
    checkPasswordMatch() {
        const password = this.passwordInput.value;
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
    
    /**
     * Validate username format
     */
    validateUsername() {
        const username = this.usernameInput.value;
        const isValid = /^[a-zA-Z0-9_]{3,30}$/.test(username);
        
        if (username.length > 0) {
            if (!isValid) {
                this.usernameInput.classList.add('is-invalid');
                this.usernameInput.classList.remove('is-valid');
            } else {
                this.usernameInput.classList.remove('is-invalid');
                this.usernameInput.classList.add('is-valid');
            }
        } else {
            this.usernameInput.classList.remove('is-invalid', 'is-valid');
        }
    }
    
    /**
     * Validate email format
     */
    validateEmail() {
        const email = this.emailInput.value;
        const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        
        if (email.length > 0) {
            if (!isValid) {
                this.emailInput.classList.add('is-invalid');
                this.emailInput.classList.remove('is-valid');
            } else {
                this.emailInput.classList.remove('is-invalid');
                this.emailInput.classList.add('is-valid');
            }
        } else {
            this.emailInput.classList.remove('is-invalid', 'is-valid');
        }
    }
    
    /**
     * Check if email is already registered (optional)
     */
    async checkEmailAvailability() {
        // This could be implemented with a dedicated endpoint
        // that doesn't reveal user existence for security
        // For now, we'll skip this check
    }
    
    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        // Clear any existing error
        this.clearError();
        
        // Validate all requirements met
        const allRequirementsMet = Object.values(this.passwordRequirements).every(v => v);
        if (!allRequirementsMet) {
            this.showError('Password does not meet all requirements');
            this.passwordInput.focus();
            return;
        }
        
        // Validate password match
        if (this.passwordInput.value !== this.confirmPasswordInput.value) {
            this.showError('Passwords do not match');
            this.confirmPasswordInput.focus();
            return;
        }
        
        // Validate form
        if (!this.form.checkValidity()) {
            this.form.classList.add('was-validated');
            return;
        }
        
        // Show loading state
        this.setLoading(true);
        
        try {
            const response = await window.api.post('/auth/register', {
                email: this.emailInput.value.trim().toLowerCase(),
                username: this.usernameInput.value.trim().toLowerCase(),
                password: this.passwordInput.value
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Store email for verification page
                sessionStorage.setItem('registeredEmail', this.emailInput.value.trim().toLowerCase());
                
                // Show success message
                this.showSuccess('Account created! Please check your email to verify your account.');
                
                // Disable form to prevent duplicate submissions
                this.disableForm();
                
                // Redirect to verification page after delay
                setTimeout(() => {
                    if (window.router) {
                        window.router.navigate('/verify-email-sent');
                    } else {
                        window.location.href = '/verify-email-sent';
                    }
                }, 2000);
            } else {
                const error = await response.json();
                
                // Handle specific error cases
                if (response.status === 409) {
                    if (error.detail?.includes('email')) {
                        this.showError('This email is already registered');
                        this.emailInput.focus();
                    } else if (error.detail?.includes('username')) {
                        this.showError('This username is already taken');
                        this.usernameInput.focus();
                    } else {
                        this.showError(error.detail || 'Registration failed');
                    }
                } else if (response.status === 400) {
                    this.showError(error.detail || 'Invalid registration data');
                } else {
                    this.showError(error.detail || 'Registration failed. Please try again.');
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Set loading state
     */
    setLoading(loading) {
        const spinner = this.registerBtn.querySelector('.spinner-border');
        const text = this.registerBtn.querySelector('.btn-text');
        
        if (loading) {
            spinner.classList.remove('d-none');
            text.textContent = 'Creating account...';
            this.registerBtn.disabled = true;
            this.form.querySelectorAll('input, button').forEach(el => {
                if (el.id !== 'registerBtn') {
                    el.disabled = true;
                }
            });
        } else {
            spinner.classList.add('d-none');
            text.textContent = 'Create Account';
            this.registerBtn.disabled = false;
            this.form.querySelectorAll('input, button').forEach(el => {
                el.disabled = false;
            });
        }
    }
    
    /**
     * Disable form after successful registration
     */
    disableForm() {
        this.form.querySelectorAll('input, button').forEach(el => {
            el.disabled = true;
        });
    }
    
    /**
     * Show error message
     */
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    /**
     * Show success message
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    /**
     * Show alert message
     */
    showAlert(message, type) {
        let alert = document.getElementById('registerAlert');
        if (!alert) {
            alert = document.createElement('div');
            alert.id = 'registerAlert';
            this.form.parentElement.insertBefore(alert, this.form);
        }
        
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            <span class="ms-2">${escapeHtml(message)}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
    }
    
    /**
     * Clear error message
     */
    clearError() {
        const alert = document.getElementById('registerAlert');
        if (alert) {
            alert.remove();
        }
    }
    
    /**
     * Clean up event listeners
     */
    destroy() {
        // Remove event listeners if needed
        this.form?.removeEventListener('submit', this.handleSubmit);
    }
}

// Export for use in router
window.RegisterPage = RegisterPage;