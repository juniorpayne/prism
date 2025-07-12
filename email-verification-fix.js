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