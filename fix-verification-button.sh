#!/bin/bash
# Hotfix script to fix the verification button issue

echo "Applying email verification button fix..."

# SSH into the server and update the file in the container
ssh -i citadel.pem ubuntu@35.170.180.10 << 'EOF'
cd ~/prism-deployment

# Create a temporary file with the fix
cat > /tmp/email-verification-patch.js << 'PATCH'
// Find the initEventListeners function and replace it
sed -i '/initEventListeners() {/,/^    }/c\
    initEventListeners() {\
        this.requestNewLink?.addEventListener('"'"'click'"'"', () => {\
            this.showResendForm();\
        });\
    }\
    \
    showResendForm() {\
        // Replace error state with resend form\
        this.errorState.innerHTML = `\
            <div class="text-center">\
                <i class="bi bi-envelope text-primary" style="font-size: 3rem;"></i>\
                <h3 class="mt-3">Request New Verification Link</h3>\
                <p class="text-muted mb-4">Enter your email address to receive a new verification link.</p>\
                <form id="resendForm" class="text-start">\
                    <div class="mb-3">\
                        <label for="resendEmail" class="form-label">Email Address</label>\
                        <input type="email" class="form-control" id="resendEmail" required \
                               placeholder="Enter your email">\
                    </div>\
                    <div id="resendMessage"></div>\
                    <button type="submit" class="btn btn-primary w-100">\
                        <span class="spinner-border spinner-border-sm d-none" role="status"></span>\
                        <span class="btn-text">Send Verification Link</span>\
                    </button>\
                    <button type="button" class="btn btn-link w-100 mt-2" onclick="location.reload()">\
                        Back to Error\
                    </button>\
                </form>\
            </div>\
        `;\
        \
        // Set up form handler\
        const form = document.getElementById('"'"'resendForm'"'"');\
        const emailInput = document.getElementById('"'"'resendEmail'"'"');\
        const message = document.getElementById('"'"'resendMessage'"'"');\
        const submitBtn = form.querySelector('"'"'button[type="submit"]'"'"');\
        const spinner = submitBtn.querySelector('"'"'.spinner-border'"'"');\
        const btnText = submitBtn.querySelector('"'"'.btn-text'"'"');\
        \
        form.addEventListener('"'"'submit'"'"', async (e) => {\
            e.preventDefault();\
            \
            const email = emailInput.value.trim();\
            if (!email) return;\
            \
            // Show loading state\
            spinner.classList.remove('"'"'d-none'"'"');\
            btnText.textContent = '"'"'Sending...'"'"';\
            submitBtn.disabled = true;\
            message.innerHTML = '"'"''"'"';\
            \
            try {\
                const response = await window.api.post('"'"'/auth/resend-verification'"'"', { email });\
                \
                if (response.ok) {\
                    message.innerHTML = `\
                        <div class="alert alert-success">\
                            <i class="bi bi-check-circle"></i>\
                            Verification email sent! Please check your inbox.\
                        </div>\
                    `;\
                    emailInput.value = '"'"''"'"';\
                    // Disable form for 60 seconds\
                    this.startResendCooldown(submitBtn, btnText);\
                } else if (response.status === 429) {\
                    message.innerHTML = `\
                        <div class="alert alert-warning">\
                            <i class="bi bi-exclamation-triangle"></i>\
                            Too many requests. Please wait before trying again.\
                        </div>\
                    `;\
                } else {\
                    message.innerHTML = `\
                        <div class="alert alert-danger">\
                            <i class="bi bi-exclamation-circle"></i>\
                            Failed to send email. Please try again.\
                        </div>\
                    `;\
                }\
            } catch (error) {\
                console.error('"'"'Resend error:'"'"', error);\
                message.innerHTML = `\
                    <div class="alert alert-danger">\
                        <i class="bi bi-exclamation-circle"></i>\
                        Network error. Please check your connection.\
                    </div>\
                `;\
            } finally {\
                spinner.classList.add('"'"'d-none'"'"');\
                if (!submitBtn.disabled) {\
                    btnText.textContent = '"'"'Send Verification Link'"'"';\
                    submitBtn.disabled = false;\
                }\
            }\
        });\
    }\
    \
    startResendCooldown(button, textElement) {\
        button.disabled = true;\
        let countdown = 60;\
        \
        const interval = setInterval(() => {\
            countdown--;\
            textElement.textContent = `Resend available in ${countdown}s`;\
            \
            if (countdown <= 0) {\
                clearInterval(interval);\
                button.disabled = false;\
                textElement.textContent = '"'"'Send Verification Link'"'"';\
            }\
        }, 1000);\
    }' /tmp/email-verification.js
PATCH

# Copy the current file from the container
docker cp prism-nginx:/usr/share/nginx/html/js/email-verification.js /tmp/email-verification-current.js

# Create a backup
cp /tmp/email-verification-current.js /tmp/email-verification-backup.js

# Apply the patch by replacing the specific function
# First, let's just replace the initEventListeners for EmailVerificationPage
docker exec prism-nginx sh -c "cat > /tmp/fix.js << 'JSFIX'
// Fix for EmailVerificationPage.initEventListeners
const fixScript = \`
    // Override the initEventListeners method
    if (window.EmailVerificationPage) {
        window.EmailVerificationPage.prototype.initEventListeners = function() {
            this.requestNewLink?.addEventListener('click', () => {
                this.showResendForm();
            });
        };
        
        window.EmailVerificationPage.prototype.showResendForm = function() {
            // Replace error state with resend form
            this.errorState.innerHTML = \\\`
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
            \\\`;
            
            // Set up form handler
            const form = document.getElementById('resendForm');
            const emailInput = document.getElementById('resendEmail');
            const message = document.getElementById('resendMessage');
            const submitBtn = form.querySelector('button[type=\"submit\"]');
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
                        message.innerHTML = \\\`
                            <div class="alert alert-success">
                                <i class="bi bi-check-circle"></i>
                                Verification email sent! Please check your inbox.
                            </div>
                        \\\`;
                        emailInput.value = '';
                        // Disable form for 60 seconds
                        this.startResendCooldown(submitBtn, btnText);
                    } else if (response.status === 429) {
                        message.innerHTML = \\\`
                            <div class="alert alert-warning">
                                <i class="bi bi-exclamation-triangle"></i>
                                Too many requests. Please wait before trying again.
                            </div>
                        \\\`;
                    } else {
                        message.innerHTML = \\\`
                            <div class="alert alert-danger">
                                <i class="bi bi-exclamation-circle"></i>
                                Failed to send email. Please try again.
                            </div>
                        \\\`;
                    }
                } catch (error) {
                    console.error('Resend error:', error);
                    message.innerHTML = \\\`
                        <div class="alert alert-danger">
                            <i class="bi bi-exclamation-circle"></i>
                            Network error. Please check your connection.
                        </div>
                    \\\`;
                } finally {
                    spinner.classList.add('d-none');
                    if (!submitBtn.disabled) {
                        btnText.textContent = 'Send Verification Link';
                        submitBtn.disabled = false;
                    }
                }
            });
        };
        
        window.EmailVerificationPage.prototype.startResendCooldown = function(button, textElement) {
            button.disabled = true;
            let countdown = 60;
            
            const interval = setInterval(() => {
                countdown--;
                textElement.textContent = \\\`Resend available in \\\${countdown}s\\\`;
                
                if (countdown <= 0) {
                    clearInterval(interval);
                    button.disabled = false;
                    textElement.textContent = 'Send Verification Link';
                }
            }, 1000);
        };
    }
    
    // Re-initialize if we're on the verify-email page
    if (window.location.pathname === '/verify-email' && window.EmailVerificationPage) {
        // Find and re-init the existing instance
        const existingInstance = window.emailVerificationPageInstance;
        if (existingInstance) {
            existingInstance.initEventListeners();
        }
    }
\`;

// Append the fix to the main app.js
echo \"\$fixScript\" >> /usr/share/nginx/html/js/app.js
JSFIX"

echo "Applied verification button fix!"
echo "Testing the fix..."

# Test if the page loads correctly
curl -s https://prism.thepaynes.ca/js/app.js | tail -20

echo "Fix applied successfully!"
EOF

echo "Done!"