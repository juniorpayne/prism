/**
 * Login Page Handler for Prism DNS
 * Handles user authentication and login form interactions
 */

class LoginPage {
    constructor() {
        this.form = document.getElementById('loginForm');
        this.usernameInput = document.getElementById('username');
        this.passwordInput = document.getElementById('password');
        this.rememberMe = document.getElementById('rememberMe');
        this.loginBtn = document.getElementById('loginBtn');
        this.toggleBtn = document.getElementById('togglePassword');
        
        this.initEventListeners();
        this.checkRememberedUser();
    }
    
    initEventListeners() {
        this.form?.addEventListener('submit', (e) => this.handleSubmit(e));
        this.toggleBtn?.addEventListener('click', () => this.togglePassword());
    }
    
    /**
     * Check if user selected "Remember me" previously
     */
    checkRememberedUser() {
        const remembered = localStorage.getItem('rememberMe');
        if (remembered === 'true') {
            this.rememberMe.checked = true;
            // Optionally pre-fill username if stored
            const savedUsername = localStorage.getItem('rememberedUsername');
            if (savedUsername) {
                this.usernameInput.value = savedUsername;
            }
        }
    }
    
    /**
     * Toggle password visibility
     */
    togglePassword() {
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
        const icon = this.toggleBtn.querySelector('i');
        icon.classList.toggle('bi-eye');
        icon.classList.toggle('bi-eye-slash');
    }
    
    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        // Clear any existing error
        this.clearError();
        
        // Validate form
        if (!this.form.checkValidity()) {
            this.form.classList.add('was-validated');
            return;
        }
        
        // Show loading state
        this.setLoading(true);
        
        try {
            const response = await window.api.post('/auth/login', {
                username: this.usernameInput.value.trim(),
                password: this.passwordInput.value
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Store tokens using TokenManager
                if (window.api.tokenManager) {
                    window.api.tokenManager.setTokens(data.access_token, data.refresh_token);
                }
                
                // Handle remember me
                if (this.rememberMe.checked) {
                    localStorage.setItem('rememberMe', 'true');
                    localStorage.setItem('rememberedUsername', this.usernameInput.value.trim());
                } else {
                    localStorage.removeItem('rememberMe');
                    localStorage.removeItem('rememberedUsername');
                }
                
                // Show success message
                showToast('Login successful! Redirecting...', 'success');
                
                // Redirect to intended page or dashboard
                setTimeout(() => {
                    if (window.router) {
                        window.router.redirectAfterLogin();
                    } else {
                        window.location.href = '/';
                    }
                }, 1000);
            } else {
                const error = await response.json();
                let errorMessage = 'Invalid credentials';
                
                // Handle specific error cases
                if (response.status === 401) {
                    errorMessage = 'Invalid username or password';
                } else if (response.status === 403) {
                    errorMessage = error.detail || 'Account not verified. Please check your email.';
                } else if (response.status === 429) {
                    errorMessage = 'Too many login attempts. Please try again later.';
                } else if (error.detail) {
                    errorMessage = error.detail;
                }
                
                this.showError(errorMessage);
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Set loading state
     */
    setLoading(loading) {
        const spinner = this.loginBtn.querySelector('.spinner-border');
        const text = this.loginBtn.querySelector('.btn-text');
        
        if (loading) {
            spinner.classList.remove('d-none');
            text.textContent = 'Signing in...';
            this.loginBtn.disabled = true;
            this.usernameInput.disabled = true;
            this.passwordInput.disabled = true;
            this.toggleBtn.disabled = true;
        } else {
            spinner.classList.add('d-none');
            text.textContent = 'Sign In';
            this.loginBtn.disabled = false;
            this.usernameInput.disabled = false;
            this.passwordInput.disabled = false;
            this.toggleBtn.disabled = false;
        }
    }
    
    /**
     * Show error message
     */
    showError(message) {
        // Create or update alert
        let alert = document.getElementById('loginError');
        if (!alert) {
            alert = document.createElement('div');
            alert.id = 'loginError';
            this.form.parentElement.insertBefore(alert, this.form);
        }
        
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            <i class="bi bi-exclamation-circle"></i>
            <span class="error-message ms-2">${escapeHtml(message)}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Focus on username field for retry
        this.usernameInput.focus();
    }
    
    /**
     * Clear error message
     */
    clearError() {
        const alert = document.getElementById('loginError');
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
        this.toggleBtn?.removeEventListener('click', this.togglePassword);
    }
}

// Export for use in router
window.LoginPage = LoginPage;