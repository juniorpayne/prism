/**
 * API Token Management Module
 * Handles creation, display, and revocation of API tokens
 */
(function() {
    'use strict';

    // State
    let tokens = [];
    let tokenModal = null;
    let tokenDisplayModal = null;

    /**
     * Initialize token management
     */
    function init() {
        console.log('[TokenManagement] Initializing token management...');
        
        // Get modal instances
        const tokenModalEl = document.getElementById('tokenModal');
        const tokenDisplayModalEl = document.getElementById('tokenDisplayModal');
        
        console.log('[TokenManagement] Modal elements:', {
            tokenModal: !!tokenModalEl,
            tokenDisplayModal: !!tokenDisplayModalEl
        });
        
        if (tokenModalEl) {
            tokenModal = new bootstrap.Modal(tokenModalEl);
        }
        
        if (tokenDisplayModalEl) {
            tokenDisplayModal = new bootstrap.Modal(tokenDisplayModalEl);
        }

        // Set up event listeners
        setupEventListeners();
        
        // Load tokens when on API tokens settings page
        const currentSection = window.location.hash;
        console.log('[TokenManagement] Current section:', currentSection);
        if (currentSection === '#settings/api-tokens') {
            loadTokens();
        }
    }

    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        console.log('[TokenManagement] Setting up event listeners...');
        
        // Generate token button
        const generateBtn = document.getElementById('generate-token-btn');
        console.log('[TokenManagement] Generate button found:', !!generateBtn);
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                console.log('[TokenManagement] Generate button clicked');
                showTokenModal();
            });
        }

        // Token form submission
        const tokenForm = document.getElementById('token-form');
        if (tokenForm) {
            tokenForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await generateToken();
            });
        }

        // Copy token button
        const copyBtn = document.getElementById('copy-token-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', copyTokenToClipboard);
        }

        // Settings navigation
        document.querySelectorAll('[data-section="api-tokens"]').forEach(link => {
            link.addEventListener('click', () => {
                // Load tokens when navigating to the section
                setTimeout(loadTokens, 100);
            });
        });
    }

    /**
     * Load and display tokens
     */
    async function loadTokens() {
        try {
            // The API client returns parsed JSON directly
            tokens = await window.api.request('/v1/tokens', {
                method: 'GET'
            });
            
            displayTokens();
        } catch (error) {
            console.error('Error loading tokens:', error);
            window.utils.showNotification('Failed to load API tokens', 'error');
        }
    }

    /**
     * Display tokens in the table
     */
    function displayTokens() {
        const tbody = document.querySelector('#tokens-table tbody');
        const noTokensDiv = document.getElementById('no-tokens');
        const tableContainer = document.querySelector('#tokens-table').parentElement;
        
        if (!tbody) return;

        tbody.innerHTML = '';

        if (tokens.length === 0) {
            // Show no tokens message
            tableContainer.classList.add('d-none');
            noTokensDiv?.classList.remove('d-none');
            return;
        }

        // Hide no tokens message and show table
        tableContainer.classList.remove('d-none');
        noTokensDiv?.classList.add('d-none');

        tokens.forEach(token => {
            const row = createTokenRow(token);
            tbody.appendChild(row);
        });
    }

    /**
     * Create a table row for a token
     */
    function createTokenRow(token) {
        const row = document.createElement('tr');
        const isRevoked = !token.is_active || token.revoked_at;
        
        if (isRevoked) {
            row.classList.add('table-secondary');
        }

        row.innerHTML = `
            <td>${window.utils.escapeHtml(token.name)}</td>
            <td>${token.last_used_at ? window.utils.formatDateTime(token.last_used_at) : 'Never'}</td>
            <td>${window.utils.formatDateTime(token.created_at)}</td>
            <td>${token.expires_at ? window.utils.formatDateTime(token.expires_at) : 'Never'}</td>
            <td>
                ${isRevoked ? 
                    `<span class="badge bg-danger">Revoked</span>
                     ${token.revoked_at ? `<br><small class="text-muted">${window.utils.formatDateTime(token.revoked_at)}</small>` : ''}` :
                    '<span class="badge bg-success">Active</span>'}
            </td>
            <td>
                ${!isRevoked ? 
                    `<button class="btn btn-sm btn-danger" onclick="window.tokenManagement.revokeToken('${token.id}', '${window.utils.escapeHtml(token.name)}')">
                        <i class="bi bi-trash"></i> Revoke
                    </button>` : 
                    '<span class="text-muted">-</span>'}
            </td>
        `;

        return row;
    }

    /**
     * Show token generation modal
     */
    function showTokenModal() {
        // Reset form
        const form = document.getElementById('token-form');
        if (form) {
            form.reset();
        }

        // Initialize modal if not already done
        if (!tokenModal) {
            const tokenModalEl = document.getElementById('tokenModal');
            if (tokenModalEl) {
                tokenModal = new bootstrap.Modal(tokenModalEl);
            }
        }

        // Show modal
        if (tokenModal) {
            tokenModal.show();
        } else {
            console.error('[TokenManagement] Could not initialize token modal');
        }
    }

    /**
     * Generate a new token
     */
    async function generateToken() {
        const nameInput = document.getElementById('token-name');
        const expirySelect = document.getElementById('token-expiry');
        const submitBtn = document.querySelector('#tokenModal button[type="submit"]');
        
        if (!nameInput || !nameInput.value.trim()) {
            window.utils.showNotification('Please enter a token name', 'error');
            return;
        }

        const name = nameInput.value.trim();
        const expiryDays = expirySelect.value;

        // Show loading state
        if (submitBtn) {
            const spinner = submitBtn.querySelector('.spinner-border');
            const btnText = submitBtn.querySelector('.btn-text');
            spinner?.classList.remove('d-none');
            if (btnText) btnText.textContent = 'Generating...';
            submitBtn.disabled = true;
        }

        try {
            const body = { name };
            if (expiryDays) {
                body.expires_in_days = parseInt(expiryDays);
            }

            const data = await window.api.request('/v1/tokens', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            });
            
            // Hide generation modal
            tokenModal?.hide();
            
            // Display the new token
            displayNewToken(data.token);
            
            // Reload token list
            await loadTokens();
            
            window.utils.showNotification('Token generated successfully', 'success');
        } catch (error) {
            console.error('Error generating token:', error);
            window.utils.showNotification(error.message, 'error');
        } finally {
            // Reset button state
            if (submitBtn) {
                const spinner = submitBtn.querySelector('.spinner-border');
                const btnText = submitBtn.querySelector('.btn-text');
                spinner?.classList.add('d-none');
                if (btnText) btnText.textContent = 'Generate Token';
                submitBtn.disabled = false;
            }
        }
    }

    /**
     * Display newly generated token
     */
    function displayNewToken(token) {
        const tokenValueInput = document.getElementById('token-value');
        const tokenPreview = document.getElementById('token-preview');
        
        if (tokenValueInput) {
            tokenValueInput.value = token;
        }
        
        if (tokenPreview) {
            tokenPreview.textContent = token;
        }
        
        // Show display modal
        if (tokenDisplayModal) {
            tokenDisplayModal.show();
        }
    }

    /**
     * Copy token to clipboard
     */
    async function copyTokenToClipboard() {
        const tokenInput = document.getElementById('token-value');
        const copyBtn = document.getElementById('copy-token-btn');
        
        if (!tokenInput) return;

        try {
            // Select and copy
            tokenInput.select();
            tokenInput.setSelectionRange(0, 99999); // For mobile devices

            // Try modern clipboard API first
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(tokenInput.value);
            } else {
                // Fallback for older browsers
                document.execCommand('copy');
            }

            // Update button icon temporarily
            const icon = copyBtn.querySelector('i');
            if (icon) {
                icon.classList.remove('bi-clipboard');
                icon.classList.add('bi-check2');
                
                setTimeout(() => {
                    icon.classList.remove('bi-check2');
                    icon.classList.add('bi-clipboard');
                }, 2000);
            }

            window.utils.showNotification('Token copied to clipboard!', 'success');
        } catch (error) {
            console.error('Failed to copy token:', error);
            window.utils.showNotification('Failed to copy token', 'error');
        }
    }

    /**
     * Revoke a token
     */
    async function revokeToken(tokenId, tokenName) {
        const confirmed = await window.utils.showConfirmDialog({
            title: 'Revoke API Token?',
            message: `Are you sure you want to revoke "${tokenName}"? This action cannot be undone.`,
            confirmText: 'Revoke Token',
            confirmClass: 'btn-danger'
        });

        if (!confirmed) return;

        try {
            await window.api.request(`/v1/tokens/${tokenId}`, {
                method: 'DELETE'
            });
            
            window.utils.showNotification('Token revoked successfully', 'success');
            await loadTokens(); // Refresh the list
        } catch (error) {
            console.error('Error revoking token:', error);
            window.utils.showNotification(error.message, 'error');
        }
    }

    /**
     * Revoke all tokens (emergency action)
     */
    async function revokeAllTokens() {
        const confirmed = await window.utils.showConfirmDialog({
            title: 'Revoke All Tokens?',
            message: 'This will revoke ALL your API tokens. All TCP clients using these tokens will stop working immediately. This action cannot be undone.',
            confirmText: 'Revoke All Tokens',
            confirmClass: 'btn-danger',
            requireTyping: true,
            typingPrompt: 'Type "REVOKE ALL" to confirm:'
        });

        if (!confirmed) return;

        try {
            const result = await window.api.request('/v1/tokens/revoke-all', {
                method: 'POST'
            });
            
            window.utils.showNotification(`${result.revoked_count} tokens revoked`, 'success');
            await loadTokens();
        } catch (error) {
            console.error('Error revoking all tokens:', error);
            window.utils.showNotification(error.message, 'error');
        }
    }

    /**
     * Re-setup event listeners for the generate button
     * Call this when the API tokens section becomes visible
     */
    function setupGenerateButton() {
        console.log('[TokenManagement] Setting up generate button...');
        const generateBtn = document.getElementById('generate-token-btn');
        if (generateBtn) {
            // Remove any existing listeners first
            const newBtn = generateBtn.cloneNode(true);
            generateBtn.parentNode.replaceChild(newBtn, generateBtn);
            
            // Add the click listener
            newBtn.addEventListener('click', () => {
                console.log('[TokenManagement] Generate button clicked');
                showTokenModal();
            });
            console.log('[TokenManagement] Generate button listener attached');
        } else {
            console.log('[TokenManagement] Generate button not found in DOM');
        }
    }

    // Export public API
    window.tokenManagement = {
        init,
        loadTokens,
        revokeToken,
        revokeAllTokens,
        setupGenerateButton
    };
})();