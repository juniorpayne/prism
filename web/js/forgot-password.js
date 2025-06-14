/**
 * Forgot Password Page Handler
 * Manages password reset request functionality
 */

class ForgotPasswordPage {
    constructor() {
        this.form = document.getElementById('forgotPasswordForm');
        this.emailInput = document.getElementById('forgotEmail');
        this.submitBtn = document.getElementById('forgotPasswordBtn');
        this.successView = document.getElementById('forgotPasswordSuccess');
        this.rateLimitWarning = document.getElementById('rateLimitWarning');
        this.rateLimitMessage = document.getElementById('rateLimitMessage');
        this.sentToEmail = document.getElementById('sentToEmail');
        this.resendLink = document.getElementById('resendResetLink');
        
        // Rate limiting
        this.lastRequestTime = 0;
        this.requestCount = 0;
        this.rateLimitWindow = 60000; // 1 minute
        this.maxRequests = 3;
        this.cooldownPeriod = 300000; // 5 minutes
        
        this.initializeEventListeners();
        this.showForm();
    }
    
    initializeEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Email validation on input
        this.emailInput.addEventListener('input', () => this.validateEmail());
        
        // Resend link
        this.resendLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showForm();
            // Pre-fill email if we have it
            if (this.sentToEmail.textContent !== 'your email') {
                this.emailInput.value = this.sentToEmail.textContent;
                this.validateEmail();
            }
        });
    }
    
    showForm() {
        this.form.classList.remove('d-none');
        this.successView.classList.add('d-none');
        this.rateLimitWarning.classList.add('d-none');
        this.emailInput.focus();
    }
    
    showSuccess(email) {
        this.form.classList.add('d-none');
        this.successView.classList.remove('d-none');
        this.sentToEmail.textContent = email;
    }
    
    showRateLimit(message, remainingTime = null) {
        this.rateLimitWarning.classList.remove('d-none');
        
        if (remainingTime) {
            const minutes = Math.ceil(remainingTime / 60000);
            this.rateLimitMessage.textContent = `Too many requests. Please wait ${minutes} minute${minutes > 1 ? 's' : ''} before trying again.`;
        } else {
            this.rateLimitMessage.textContent = message || 'Too many requests. Please wait before trying again.';
        }
    }
    
    hideRateLimit() {
        this.rateLimitWarning.classList.add('d-none');
    }
    
    checkRateLimit() {
        const now = Date.now();
        const timeSinceLastRequest = now - this.lastRequestTime;
        
        // Reset counter if window has passed
        if (timeSinceLastRequest > this.rateLimitWindow) {
            this.requestCount = 0;
        }
        
        // Check if in cooldown
        if (this.requestCount >= this.maxRequests && timeSinceLastRequest < this.cooldownPeriod) {
            const remainingTime = this.cooldownPeriod - timeSinceLastRequest;
            this.showRateLimit('Too many requests.', remainingTime);
            return false;
        }
        
        // Allow request
        this.hideRateLimit();
        return true;
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        // Check rate limit
        if (!this.checkRateLimit()) {
            return;
        }
        
        // Validate form
        if (!this.validateEmail()) {
            this.emailInput.focus();
            return;
        }
        
        const email = this.emailInput.value.trim();
        
        // Set loading state
        this.setLoading(true);
        
        try {
            // Make API request
            const response = await window.api.forgotPassword(email);
            
            // Update rate limit tracking
            this.lastRequestTime = Date.now();
            this.requestCount++;
            
            // Show success state
            this.showSuccess(email);
            
            // Clear form
            this.form.reset();
            this.form.classList.remove('was-validated');
            
        } catch (error) {
            console.error('Forgot password error:', error);
            
            // Check for rate limit error
            if (error.status === 429) {
                this.showRateLimit(error.message || 'Too many requests. Please try again later.');
                // Still count this request
                this.lastRequestTime = Date.now();
                this.requestCount++;
            } else if (error.status === 404) {
                // Email not found - still show success for security
                this.showSuccess(email);
            } else {
                // Show generic error
                this.showError(error.message || 'Failed to send reset email. Please try again.');
            }
        } finally {
            this.setLoading(false);
        }
    }
    
    validateEmail() {
        const email = this.emailInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!email) {
            this.emailInput.classList.remove('is-valid', 'is-invalid');
            return false;
        }
        
        if (emailRegex.test(email)) {
            this.emailInput.classList.remove('is-invalid');
            this.emailInput.classList.add('is-valid');
            return true;
        } else {
            this.emailInput.classList.remove('is-valid');
            this.emailInput.classList.add('is-invalid');
            return false;
        }
    }
    
    setLoading(loading) {
        if (loading) {
            this.submitBtn.disabled = true;
            this.submitBtn.querySelector('.spinner-border').classList.remove('d-none');
            this.submitBtn.querySelector('.btn-text').textContent = 'Sending...';
        } else {
            this.submitBtn.disabled = false;
            this.submitBtn.querySelector('.spinner-border').classList.add('d-none');
            this.submitBtn.querySelector('.btn-text').textContent = 'Send Reset Link';
        }
    }
    
    showError(message) {
        // Create or update error alert
        let errorAlert = this.form.querySelector('.alert-danger');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.className = 'alert alert-danger alert-dismissible fade show mb-3';
            errorAlert.innerHTML = `
                <i class="bi bi-exclamation-circle"></i>
                <span class="error-message"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            this.form.insertBefore(errorAlert, this.form.firstChild);
        }
        
        errorAlert.querySelector('.error-message').textContent = ' ' + message;
    }
    
    destroy() {
        // Clean up event listeners if needed
        this.form.reset();
        this.form.classList.remove('was-validated');
        this.showForm();
        this.hideRateLimit();
    }
}

// Export for use in router
window.ForgotPasswordPage = ForgotPasswordPage;