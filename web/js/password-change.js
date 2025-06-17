/**
 * Password Change Page for Prism DNS
 * Handles secure password updates with validation
 */

class PasswordChangePage {
    constructor() {
        this.form = document.getElementById('passwordChangeForm');
        this.currentPassword = document.getElementById('currentPassword');
        this.newPassword = document.getElementById('newPassword');
        this.confirmPassword = document.getElementById('confirmPassword');
        this.submitBtn = document.getElementById('changePasswordSubmitBtn');
        this.cancelBtn = document.getElementById('cancelPasswordChangeBtn');
        this.spinner = document.getElementById('changePasswordSpinner');
        
        // Password visibility toggles
        this.toggleCurrent = document.getElementById('toggleCurrentPassword');
        this.toggleNew = document.getElementById('toggleNewPassword');
        this.toggleConfirm = document.getElementById('toggleConfirmPassword');
        
        // Password requirements
        this.requirementsDiv = document.getElementById('passwordRequirements');
        this.strengthIndicator = document.getElementById('passwordStrengthIndicator');
        this.strengthText = document.getElementById('passwordStrengthText');
        
        // Initialize password validator
        this.passwordValidator = window.PasswordValidator ? new PasswordValidator() : null;
        
        this.isDestroyed = false;
        this.init();
    }
    
    init() {
        if (!this.form) {
            console.error('Password change form not found');
            return;
        }
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Cancel button
        this.cancelBtn?.addEventListener('click', () => {
            window.location.hash = 'settings/security';
        });
        
        // Password visibility toggles
        this.setupPasswordToggle(this.toggleCurrent, this.currentPassword);
        this.setupPasswordToggle(this.toggleNew, this.newPassword);
        this.setupPasswordToggle(this.toggleConfirm, this.confirmPassword);
        
        // Password validation
        this.newPassword?.addEventListener('focus', () => {
            this.requirementsDiv.classList.remove('d-none');
        });
        
        this.newPassword?.addEventListener('blur', () => {
            if (!this.newPassword.value) {
                this.requirementsDiv.classList.add('d-none');
            }
        });
        
        this.newPassword?.addEventListener('input', () => {
            this.validateNewPassword();
            this.checkPasswordMatch();
        });
        
        this.confirmPassword?.addEventListener('input', () => {
            this.checkPasswordMatch();
        });
        
        // Real-time validation
        this.currentPassword?.addEventListener('blur', () => {
            this.validateCurrentPassword();
        });
    }
    
    setupPasswordToggle(button, input) {
        if (!button || !input) return;
        
        button.addEventListener('click', () => {
            const type = input.type === 'password' ? 'text' : 'password';
            input.type = type;
            
            const icon = button.querySelector('i');
            icon.classList.toggle('bi-eye');
            icon.classList.toggle('bi-eye-slash');
        });
    }
    
    validateCurrentPassword() {
        if (!this.currentPassword.value) {
            this.currentPassword.classList.add('is-invalid');
            this.currentPassword.classList.remove('is-valid');
            return false;
        }
        
        this.currentPassword.classList.remove('is-invalid');
        this.currentPassword.classList.add('is-valid');
        return true;
    }
    
    validateNewPassword() {
        const password = this.newPassword.value;
        
        if (!password) {
            this.newPassword.classList.remove('is-valid', 'is-invalid');
            this.updateStrengthIndicator('', 0);
            return false;
        }
        
        // Use password validator if available
        if (this.passwordValidator) {
            const validation = this.passwordValidator.validate(password);
            
            // Update requirements list
            this.updateRequirement('reqLength', validation.requirements.length);
            this.updateRequirement('reqUppercase', validation.requirements.uppercase);
            this.updateRequirement('reqLowercase', validation.requirements.lowercase);
            this.updateRequirement('reqNumber', validation.requirements.number);
            this.updateRequirement('reqSpecial', validation.requirements.special);
            
            // Update strength indicator
            this.updateStrengthIndicator(validation.strength, validation.score);
            
            // Update validation state
            if (validation.isValid) {
                this.newPassword.classList.remove('is-invalid');
                this.newPassword.classList.add('is-valid');
            } else {
                this.newPassword.classList.add('is-invalid');
                this.newPassword.classList.remove('is-valid');
            }
            
            return validation.isValid;
        } else {
            // Fallback validation
            const requirements = {
                length: password.length >= 12,
                uppercase: /[A-Z]/.test(password),
                lowercase: /[a-z]/.test(password),
                number: /\d/.test(password),
                special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
            };
            
            // Update requirements
            Object.keys(requirements).forEach(req => {
                this.updateRequirement(`req${req.charAt(0).toUpperCase() + req.slice(1)}`, requirements[req]);
            });
            
            // Calculate score
            const score = Object.values(requirements).filter(Boolean).length;
            const strength = this.getStrengthText(score);
            this.updateStrengthIndicator(strength, score);
            
            const isValid = score === 5;
            if (isValid) {
                this.newPassword.classList.remove('is-invalid');
                this.newPassword.classList.add('is-valid');
            } else {
                this.newPassword.classList.add('is-invalid');
                this.newPassword.classList.remove('is-valid');
            }
            
            return isValid;
        }
    }
    
    updateRequirement(reqId, met) {
        const element = document.getElementById(reqId);
        if (!element) return;
        
        const icon = element.querySelector('i');
        if (met) {
            element.classList.remove('text-danger');
            element.classList.add('text-success');
            icon.classList.remove('bi-circle');
            icon.classList.add('bi-check-circle-fill');
        } else {
            element.classList.remove('text-success');
            element.classList.add('text-danger');
            icon.classList.remove('bi-check-circle-fill');
            icon.classList.add('bi-circle');
        }
    }
    
    getStrengthText(score) {
        if (score <= 1) return 'Very Weak';
        if (score <= 2) return 'Weak';
        if (score <= 3) return 'Fair';
        if (score <= 4) return 'Good';
        return 'Strong';
    }
    
    updateStrengthIndicator(strength, score) {
        const percentage = (score / 5) * 100;
        this.strengthIndicator.style.width = `${percentage}%`;
        
        // Remove all classes
        this.strengthIndicator.className = 'progress-bar';
        
        // Add appropriate class
        switch (strength) {
            case 'Very Weak':
            case 'Weak':
                this.strengthIndicator.classList.add('bg-danger');
                break;
            case 'Fair':
                this.strengthIndicator.classList.add('bg-warning');
                break;
            case 'Good':
                this.strengthIndicator.classList.add('bg-info');
                break;
            case 'Strong':
                this.strengthIndicator.classList.add('bg-success');
                break;
        }
        
        this.strengthText.textContent = strength ? `Password strength: ${strength}` : 'Enter password';
    }
    
    checkPasswordMatch() {
        if (!this.confirmPassword.value) {
            this.confirmPassword.classList.remove('is-invalid', 'is-valid');
            return true;
        }
        
        if (this.newPassword.value === this.confirmPassword.value) {
            this.confirmPassword.classList.remove('is-invalid');
            this.confirmPassword.classList.add('is-valid');
            return true;
        } else {
            this.confirmPassword.classList.add('is-invalid');
            this.confirmPassword.classList.remove('is-valid');
            return false;
        }
    }
    
    async handleSubmit(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Clear any existing errors
        this.clearErrors();
        
        // Validate all fields
        const isCurrentValid = this.validateCurrentPassword();
        const isNewValid = this.validateNewPassword();
        const isMatchValid = this.checkPasswordMatch();
        
        if (!isCurrentValid || !isNewValid || !isMatchValid) {
            this.form.classList.add('was-validated');
            return;
        }
        
        // Check if new password is same as current
        if (this.currentPassword.value === this.newPassword.value) {
            this.showError('New password must be different from current password.');
            this.newPassword.classList.add('is-invalid');
            return;
        }
        
        // Show loading state
        this.submitBtn.disabled = true;
        this.spinner.classList.remove('d-none');
        
        try {
            await window.api.put('/api/users/me/password', {
                current_password: this.currentPassword.value,
                new_password: this.newPassword.value
            });
            
            // Show success message
            this.showSuccess('Password changed successfully! You will be logged out in 3 seconds...');
            
            // Clear form
            this.form.reset();
            this.form.classList.remove('was-validated');
            this.clearValidation();
            
            // Logout after delay
            setTimeout(async () => {
                // Clear all sessions
                if (window.api?.tokenManager) {
                    window.api.tokenManager.clearTokens();
                }
                
                // Dispatch logout event
                window.dispatchEvent(new Event('tokenClear'));
                
                // Show notification
                showToast('You have been logged out for security reasons', 'info');
                
                // Redirect to login
                if (window.router) {
                    window.router.navigate('/login');
                } else {
                    window.location.hash = 'login';
                }
            }, 3000);
            
        } catch (error) {
            console.error('Failed to change password:', error);
            
            if (error.message && (error.message.includes('incorrect') || error.message.includes('wrong'))) {
                this.showError('Current password is incorrect.');
                this.currentPassword.classList.add('is-invalid');
            } else {
                this.showError(error.message || 'Failed to change password. Please try again.');
            }
        } finally {
            this.submitBtn.disabled = false;
            this.spinner.classList.add('d-none');
        }
    }
    
    clearValidation() {
        const inputs = this.form.querySelectorAll('.is-valid, .is-invalid');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        // Remove existing alerts
        this.clearErrors();
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        this.form.parentNode.insertBefore(alert, this.form);
        
        // Auto-remove after delay
        if (type === 'success') {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 10000);
        }
    }
    
    clearErrors() {
        const alerts = this.form.parentNode.querySelectorAll('.alert');
        alerts.forEach(alert => alert.remove());
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        this.isDestroyed = true;
        this.clearErrors();
        // Event listeners are automatically cleaned up when elements are removed from DOM
    }
}

// Export for use in other modules
window.PasswordChangePage = PasswordChangePage;