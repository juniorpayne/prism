/**
 * Email Verification Flow Handlers for Prism DNS
 * Handles email sent confirmation and verification processing
 */

// Email Sent Page Handler
class EmailSentPage {
    constructor() {
        this.resendBtn = document.getElementById('resendBtn');
        this.resendMessage = document.getElementById('resendMessage');
        this.userEmail = document.getElementById('userEmail');
        
        // Get email from session storage or registration flow
        const email = sessionStorage.getItem('registeredEmail') || 'your email';
        this.userEmail.textContent = email;
        
        this.resendCooldown = false;
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.resendBtn?.addEventListener('click', () => this.resendEmail());
    }
    
    async resendEmail() {
        const email = sessionStorage.getItem('registeredEmail');
        if (!email) {
            this.showMessage('Please register first', 'danger');
            setTimeout(() => {
                if (window.router) {
                    window.router.navigate('/register');
                }
            }, 2000);
            return;
        }
        
        // Prevent rapid clicking
        if (this.resendCooldown) {
            return;
        }
        
        this.setLoading(true);
        this.resendMessage.innerHTML = '';
        
        try {
            const response = await window.api.post('/auth/resend-verification', { email });
            
            if (response.ok) {
                this.showMessage('Verification email sent! Please check your inbox.', 'success');
                // Implement rate limiting on frontend
                this.startCooldown();
            } else {
                const error = await response.json();
                if (response.status === 429) {
                    this.showMessage('Too many requests. Please wait before trying again.', 'warning');
                } else if (response.status === 409) {
                    this.showMessage('Email already verified. You can login now.', 'info');
                    setTimeout(() => {
                        if (window.router) {
                            window.router.navigate('/login');
                        }
                    }, 2000);
                } else {
                    this.showMessage(error.detail || 'Failed to send email. Please try again.', 'danger');
                }
            }
        } catch (error) {
            console.error('Resend email error:', error);
            this.showMessage('Network error. Please check your connection.', 'danger');
        } finally {
            this.setLoading(false);
        }
    }
    
    startCooldown() {
        this.resendCooldown = true;
        this.resendBtn.disabled = true;
        let countdown = 60;
        
        const interval = setInterval(() => {
            countdown--;
            this.resendBtn.querySelector('.btn-text').textContent = 
                `Resend available in ${countdown}s`;
            
            if (countdown <= 0) {
                clearInterval(interval);
                this.resendCooldown = false;
                this.resendBtn.disabled = false;
                this.resendBtn.querySelector('.btn-text').textContent = 
                    'Resend Verification Email';
            }
        }, 1000);
    }
    
    setLoading(loading) {
        const spinner = this.resendBtn.querySelector('.spinner-border');
        const text = this.resendBtn.querySelector('.btn-text');
        
        if (loading) {
            spinner.classList.remove('d-none');
            text.textContent = 'Sending...';
            this.resendBtn.disabled = true;
        } else {
            spinner.classList.add('d-none');
            if (!this.resendCooldown) {
                text.textContent = 'Resend Verification Email';
                this.resendBtn.disabled = false;
            }
        }
    }
    
    showMessage(message, type) {
        this.resendMessage.innerHTML = `
            <div class="alert alert-${type} alert-sm">
                <i class="bi bi-${this.getIconForType(type)}"></i>
                <span class="ms-2">${escapeHtml(message)}</span>
            </div>
        `;
    }
    
    getIconForType(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    destroy() {
        // Clean up if needed
        this.resendBtn?.removeEventListener('click', this.resendEmail);
    }
}

// Email Verification Page Handler
class EmailVerificationPage {
    constructor() {
        this.verifyingState = document.getElementById('verifyingState');
        this.successState = document.getElementById('successState');
        this.errorState = document.getElementById('errorState');
        this.errorMessage = document.getElementById('errorMessage');
        this.requestNewLink = document.getElementById('requestNewLink');
        
        // Get token from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.token = urlParams.get('token');
        
        if (this.token) {
            this.verifyEmail();
        } else {
            this.showError('No verification token provided');
        }
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.requestNewLink?.addEventListener('click', () => {
            this.showResendForm();
        });
    }
    
    showResendForm() {
        // Replace error state with resend form
        this.errorState.innerHTML = `
            <div class="text-center">
                <i class="bi bi-envelope text-primary" style="font-size: 3rem;"></i>
                <h3 class="mt-3">Request New Verification Link</h3>
                <p class="text-muted mb-4">Enter your email address to receive a new verification link.</p>
                <form id="resendForm" class="text-start">
                    <div class="mb-3">
                        <label for="resendEmail" class="form-label">Email Address</label>
                        <input type="email" class="form-control" id="resendEmail" required 
                               placeholder="Enter your email">
                    </div>
                    <div id="resendMessage"></div>
                    <button type="submit" class="btn btn-primary w-100">
                        <span class="spinner-border spinner-border-sm d-none" role="status"></span>
                        <span class="btn-text">Send Verification Link</span>
                    </button>
                    <button type="button" class="btn btn-link w-100 mt-2" onclick="location.reload()">
                        Back to Error
                    </button>
                </form>
            </div>
        `;
        
        // Set up form handler
        const form = document.getElementById('resendForm');
        const emailInput = document.getElementById('resendEmail');
        const message = document.getElementById('resendMessage');
        const submitBtn = form.querySelector('button[type="submit"]');
        const spinner = submitBtn.querySelector('.spinner-border');
        const btnText = submitBtn.querySelector('.btn-text');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = emailInput.value.trim();
            if (!email) return;
            
            // Show loading state
            spinner.classList.remove('d-none');
            btnText.textContent = 'Sending...';
            submitBtn.disabled = true;
            message.innerHTML = '';
            
            try {
                const response = await window.api.post('/auth/resend-verification', { email });
                
                if (response.ok) {
                    message.innerHTML = `
                        <div class="alert alert-success">
                            <i class="bi bi-check-circle"></i>
                            Verification email sent! Please check your inbox.
                        </div>
                    `;
                    emailInput.value = '';
                    // Disable form for 60 seconds
                    this.startResendCooldown(submitBtn, btnText);
                } else if (response.status === 429) {
                    message.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            Too many requests. Please wait before trying again.
                        </div>
                    `;
                } else {
                    message.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-circle"></i>
                            Failed to send email. Please try again.
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Resend error:', error);
                message.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-circle"></i>
                        Network error. Please check your connection.
                    </div>
                `;
            } finally {
                spinner.classList.add('d-none');
                if (!submitBtn.disabled) {
                    btnText.textContent = 'Send Verification Link';
                    submitBtn.disabled = false;
                }
            }
        });
    }
    
    startResendCooldown(button, textElement) {
        button.disabled = true;
        let countdown = 60;
        
        const interval = setInterval(() => {
            countdown--;
            textElement.textContent = `Resend available in ${countdown}s`;
            
            if (countdown <= 0) {
                clearInterval(interval);
                button.disabled = false;
                textElement.textContent = 'Send Verification Link';
            }
        }, 1000);
    }
    
    async verifyEmail() {
        try {
            const response = await window.api.get(`/auth/verify-email/${encodeURIComponent(this.token)}`);
            
            if (response.ok) {
                const data = await response.json();
                this.showSuccess();
                
                // Store success message for login page
                sessionStorage.setItem('verificationSuccess', 'true');
                
                // Auto-redirect to login after 3 seconds
                setTimeout(() => {
                    if (window.router) {
                        window.router.navigate('/login');
                    } else {
                        window.location.href = '/login';
                    }
                }, 3000);
            } else {
                const error = await response.json();
                let errorMsg = 'Verification failed';
                
                if (response.status === 400) {
                    errorMsg = 'Invalid verification link';
                } else if (response.status === 404) {
                    errorMsg = 'Verification token not found';
                } else if (response.status === 410) {
                    errorMsg = 'This verification link has expired';
                } else if (response.status === 409) {
                    // Already verified
                    this.showSuccess();
                    this.successState.querySelector('p').innerHTML = 
                        'Your email is already verified.<br>You can login to your account.';
                    setTimeout(() => {
                        if (window.router) {
                            window.router.navigate('/login');
                        }
                    }, 2000);
                    return;
                } else if (error.detail) {
                    errorMsg = error.detail;
                }
                
                this.showError(errorMsg);
            }
        } catch (error) {
            console.error('Verification error:', error);
            this.showError('Network error. Please check your connection and try again.');
        }
    }
    
    showSuccess() {
        this.verifyingState.classList.add('d-none');
        this.successState.classList.remove('d-none');
        this.errorState.classList.add('d-none');
        
        // Add success animation
        const icon = this.successState.querySelector('.bi-check-circle');
        icon.style.animation = 'pulse 1s ease-in-out';
    }
    
    showError(message) {
        this.verifyingState.classList.add('d-none');
        this.successState.classList.add('d-none');
        this.errorState.classList.remove('d-none');
        this.errorMessage.textContent = message;
    }
    
    destroy() {
        // Clean up if needed
        this.requestNewLink?.removeEventListener('click', this.handleRequestNewLink);
    }
}

// Export for use in router
window.EmailSentPage = EmailSentPage;
window.EmailVerificationPage = EmailVerificationPage;