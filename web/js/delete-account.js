/**
 * Delete Account Page for Prism DNS
 * Handles multi-step account deletion with strong confirmation
 */

class DeleteAccountPage {
    constructor() {
        // Steps
        this.step1 = document.getElementById('deleteStep1');
        this.step2 = document.getElementById('deleteStep2');
        this.step3 = document.getElementById('deleteStep3');
        this.successStep = document.getElementById('deleteSuccess');
        
        // Step 1 elements
        this.understandCheckbox = document.getElementById('understandConsequences');
        this.proceedBtn = document.getElementById('proceedToStep2');
        this.cancelBtn1 = document.getElementById('cancelDeletion1');
        
        // Step 2 elements
        this.passwordForm = document.getElementById('deletePasswordForm');
        this.passwordInput = document.getElementById('deletePassword');
        this.usernameInput = document.getElementById('confirmUsername');
        this.togglePassword = document.getElementById('toggleDeletePassword');
        this.verifySpinner = document.getElementById('verifySpinner');
        this.cancelBtn2 = document.getElementById('cancelDeletion2');
        
        // Step 3 elements
        this.confirmBtn = document.getElementById('confirmDeletion');
        this.deleteSpinner = document.getElementById('deleteSpinner');
        this.cancelBtn3 = document.getElementById('cancelDeletion3');
        
        // Success elements
        this.countdownSpan = document.getElementById('redirectCountdown');
        
        this.currentStep = 1;
        this.username = '';
        this.isDestroyed = false;
        
        this.init();
    }
    
    async init() {
        if (!this.step1) {
            console.error('Delete account elements not found');
            return;
        }
        
        this.setupEventListeners();
        await this.loadUserData();
    }
    
    async loadUserData() {
        try {
            const response = await window.api.get('/users/me');
            this.username = response.username || response.email || 'user';
            const usernameDisplay = document.getElementById('usernameToType');
            if (usernameDisplay) {
                usernameDisplay.textContent = this.username;
            }
        } catch (error) {
            console.error('Failed to load user data:', error);
        }
    }
    
    setupEventListeners() {
        // Step 1
        this.understandCheckbox?.addEventListener('change', () => {
            this.proceedBtn.disabled = !this.understandCheckbox.checked;
        });
        
        this.proceedBtn?.addEventListener('click', () => {
            this.showStep(2);
        });
        
        this.cancelBtn1?.addEventListener('click', () => {
            this.handleCancel();
        });
        
        // Step 2
        this.passwordForm?.addEventListener('submit', (e) => {
            this.handlePasswordVerification(e);
        });
        
        this.togglePassword?.addEventListener('click', () => {
            this.togglePasswordVisibility();
        });
        
        this.cancelBtn2?.addEventListener('click', () => {
            this.handleCancel();
        });
        
        // Username validation
        this.usernameInput?.addEventListener('input', () => {
            this.validateUsername();
        });
        
        // Step 3
        this.confirmBtn?.addEventListener('click', () => {
            this.handleFinalDeletion();
        });
        
        this.cancelBtn3?.addEventListener('click', () => {
            this.handleCancel();
        });
    }
    
    showStep(step) {
        if (this.isDestroyed) return;
        
        // Hide all steps
        [this.step1, this.step2, this.step3, this.successStep].forEach(s => {
            if (s) s.style.display = 'none';
        });
        
        // Show requested step
        switch (step) {
            case 1:
                if (this.step1) {
                    this.step1.style.display = 'block';
                }
                break;
            case 2:
                if (this.step2) {
                    this.step2.style.display = 'block';
                    this.passwordInput?.focus();
                }
                break;
            case 3:
                if (this.step3) {
                    this.step3.style.display = 'block';
                }
                break;
            case 'success':
                if (this.successStep) {
                    this.successStep.style.display = 'block';
                    this.startRedirectCountdown();
                }
                break;
        }
        
        this.currentStep = step;
    }
    
    togglePasswordVisibility() {
        if (!this.passwordInput || !this.togglePassword) return;
        
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
        
        const icon = this.togglePassword.querySelector('i');
        if (icon) {
            icon.classList.toggle('bi-eye');
            icon.classList.toggle('bi-eye-slash');
        }
    }
    
    validateUsername() {
        if (!this.usernameInput) return false;
        
        const enteredUsername = this.usernameInput.value.trim();
        
        if (enteredUsername === this.username) {
            this.usernameInput.classList.remove('is-invalid');
            this.usernameInput.classList.add('is-valid');
            return true;
        } else if (enteredUsername) {
            this.usernameInput.classList.add('is-invalid');
            this.usernameInput.classList.remove('is-valid');
            return false;
        } else {
            this.usernameInput.classList.remove('is-invalid', 'is-valid');
            return false;
        }
    }
    
    async handlePasswordVerification(event) {
        event.preventDefault();
        
        if (this.isDestroyed) return;
        
        // Validate username match
        if (!this.validateUsername()) {
            this.passwordForm.classList.add('was-validated');
            return;
        }
        
        // Show loading
        const submitBtn = event.target.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.disabled = true;
        if (this.verifySpinner) this.verifySpinner.classList.remove('d-none');
        
        try {
            // Verify password
            await window.api.post('/auth/verify-password', {
                password: this.passwordInput.value
            });
            
            // Password is correct, move to final step
            this.showStep(3);
            
        } catch (error) {
            console.error('Password verification failed:', error);
            if (this.passwordInput) {
                this.passwordInput.classList.add('is-invalid');
            }
            this.passwordForm.classList.add('was-validated');
        } finally {
            if (submitBtn) submitBtn.disabled = false;
            if (this.verifySpinner) this.verifySpinner.classList.add('d-none');
        }
    }
    
    async handleFinalDeletion() {
        if (this.isDestroyed) return;
        
        // Show loading
        if (this.confirmBtn) this.confirmBtn.disabled = true;
        if (this.cancelBtn3) this.cancelBtn3.disabled = true;
        if (this.deleteSpinner) this.deleteSpinner.classList.remove('d-none');
        
        try {
            // Delete account
            await window.api.delete('/users/me', {
                password: this.passwordInput.value
            });
            
            // Show success
            this.showStep('success');
            
        } catch (error) {
            console.error('Account deletion failed:', error);
            
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show mb-3';
            alert.innerHTML = `
                <i class="bi bi-exclamation-circle"></i>
                Failed to delete account. Please try again.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            if (this.step3) {
                this.step3.insertBefore(alert, this.step3.firstChild);
            }
            
            if (this.confirmBtn) this.confirmBtn.disabled = false;
            if (this.cancelBtn3) this.cancelBtn3.disabled = false;
            if (this.deleteSpinner) this.deleteSpinner.classList.add('d-none');
        }
    }
    
    startRedirectCountdown() {
        if (this.isDestroyed) return;
        
        let countdown = 5;
        
        const interval = setInterval(() => {
            if (this.isDestroyed) {
                clearInterval(interval);
                return;
            }
            
            countdown--;
            if (this.countdownSpan) {
                this.countdownSpan.textContent = countdown;
            }
            
            if (countdown <= 0) {
                clearInterval(interval);
                
                // Clear all auth data
                if (window.api?.tokenManager) {
                    window.api.tokenManager.clearTokens();
                }
                
                // Clear any session storage
                sessionStorage.clear();
                localStorage.removeItem('redirectAfterLogin');
                
                // Dispatch logout event
                window.dispatchEvent(new Event('tokenClear'));
                
                // Redirect to home
                window.location.href = '/';
            }
        }, 1000);
    }
    
    handleCancel() {
        if (this.isDestroyed) return;
        
        // Clear form data
        if (this.passwordForm) this.passwordForm.reset();
        if (this.understandCheckbox) {
            this.understandCheckbox.checked = false;
        }
        if (this.proceedBtn) {
            this.proceedBtn.disabled = true;
        }
        
        // Remove validation states
        if (this.passwordInput) {
            this.passwordInput.classList.remove('is-invalid', 'is-valid');
        }
        if (this.usernameInput) {
            this.usernameInput.classList.remove('is-invalid', 'is-valid');
        }
        if (this.passwordForm) {
            this.passwordForm.classList.remove('was-validated');
        }
        
        // Go back to settings
        if (window.router) {
            window.router.navigate('/settings');
        } else {
            window.location.hash = 'settings/account';
        }
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        this.isDestroyed = true;
        
        // Clear any alerts
        const alerts = document.querySelectorAll('.delete-step .alert-dismissible');
        alerts.forEach(alert => alert.remove());
        
        // Reset form
        if (this.passwordForm) {
            this.passwordForm.reset();
            this.passwordForm.classList.remove('was-validated');
        }
        
        // Reset to step 1
        this.showStep(1);
        
        // Reset checkbox
        if (this.understandCheckbox) {
            this.understandCheckbox.checked = false;
        }
        if (this.proceedBtn) {
            this.proceedBtn.disabled = true;
        }
    }
}

// Export for use in other modules
window.DeleteAccountPage = DeleteAccountPage;