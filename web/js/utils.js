/**
 * Utility functions for Prism DNS Web Interface
 */

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp, relative = true) {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (relative && diff < 86400000) { // Less than 24 hours
        if (diff < 60000) { // Less than 1 minute
            return 'Just now';
        } else if (diff < 3600000) { // Less than 1 hour
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
        } else { // Less than 24 hours
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
        }
    }
    
    return date.toLocaleString();
}

/**
 * Format uptime in human-readable format
 */
function formatUptime(seconds) {
    if (!seconds || seconds < 0) return '0s';
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
    
    return parts.join(' ');
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const statusLower = status.toLowerCase();
    let badgeClass = 'status-badge ';
    
    switch (statusLower) {
        case 'online':
            badgeClass += 'status-online';
            break;
        case 'offline':
            badgeClass += 'status-offline';
            break;
        default:
            badgeClass += 'status-warning';
    }
    
    return `<span class="${badgeClass}">${status}</span>`;
}

/**
 * Get status icon
 */
function getStatusIcon(status) {
    const statusLower = status.toLowerCase();
    
    switch (statusLower) {
        case 'online':
            return '<i class="bi bi-check-circle-fill text-success"></i>';
        case 'offline':
            return '<i class="bi bi-x-circle-fill text-danger"></i>';
        default:
            return '<i class="bi bi-question-circle-fill text-warning"></i>';
    }
}

/**
 * Debounce function calls
 */
function debounce(func, wait, immediate = false) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/**
 * Format bytes to human readable format
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Show notification (alias for showToast)
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Map common notification types to Bootstrap toast types
    const typeMap = {
        'error': 'danger',
        'warning': 'warning',
        'success': 'success',
        'info': 'info'
    };
    
    const toastType = typeMap[type] || 'info';
    showToast(message, toastType, duration);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 5000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${escapeHtml(message)}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1060';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Show error message in UI
 */
function showError(container, message, showRetry = false, retryCallback = null) {
    container.innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i>
            <span class="error-message">${escapeHtml(message)}</span>
            ${showRetry ? `
                <button class="btn btn-outline-danger btn-sm ms-2" onclick="${retryCallback}">
                    <i class="bi bi-arrow-clockwise"></i> Retry
                </button>
            ` : ''}
        </div>
    `;
    container.style.display = 'block';
}

/**
 * Show loading state
 */
function showLoading(container, message = 'Loading...') {
    container.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">${escapeHtml(message)}</p>
        </div>
    `;
    container.style.display = 'block';
}

/**
 * Hide element
 */
function hideElement(element) {
    if (element) {
        element.style.display = 'none';
    }
}

/**
 * Show element
 */
function showElement(element) {
    if (element) {
        element.style.display = 'block';
    }
}

/**
 * Toggle element visibility
 */
function toggleElement(element) {
    if (element) {
        element.style.display = element.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success', 2000);
        return true;
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showToast('Failed to copy to clipboard', 'error', 3000);
        return false;
    }
}

/**
 * Validate IP address
 */
function isValidIP(ip) {
    const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
    return ipv4Regex.test(ip) || ipv6Regex.test(ip);
}

/**
 * Validate hostname
 */
function isValidHostname(hostname) {
    const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    return hostnameRegex.test(hostname) && hostname.length <= 253;
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get browser info
 */
function getBrowserInfo() {
    const userAgent = navigator.userAgent;
    let browserName = 'Unknown';
    
    if (userAgent.indexOf('Chrome') > -1) {
        browserName = 'Chrome';
    } else if (userAgent.indexOf('Safari') > -1) {
        browserName = 'Safari';
    } else if (userAgent.indexOf('Firefox') > -1) {
        browserName = 'Firefox';
    } else if (userAgent.indexOf('Edge') > -1) {
        browserName = 'Edge';
    }
    
    return {
        name: browserName,
        userAgent: userAgent,
        platform: navigator.platform,
        language: navigator.language
    };
}

/**
 * Local storage helpers
 */
const storage = {
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Failed to save to localStorage:', e);
            return false;
        }
    },
    
    get: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Failed to read from localStorage:', e);
            return defaultValue;
        }
    },
    
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('Failed to remove from localStorage:', e);
            return false;
        }
    },
    
    clear: () => {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('Failed to clear localStorage:', e);
            return false;
        }
    }
};

/**
 * URL helpers
 */
const url = {
    getParams: () => {
        return new URLSearchParams(window.location.search);
    },
    
    setParam: (key, value) => {
        const params = new URLSearchParams(window.location.search);
        params.set(key, value);
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newUrl);
    },
    
    removeParam: (key) => {
        const params = new URLSearchParams(window.location.search);
        params.delete(key);
        const newUrl = params.toString() ? 
            `${window.location.pathname}?${params.toString()}` : 
            window.location.pathname;
        window.history.replaceState({}, '', newUrl);
    }
};

/**
 * JWT helpers
 */
const jwt = {
    /**
     * Parse JWT token
     * @param {string} token - JWT token to parse
     * @returns {Object|null} Parsed token object with header, payload, and signature
     */
    parse: (token) => {
        if (!token || typeof token !== 'string') return null;
        
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        
        try {
            const header = JSON.parse(atob(parts[0].replace(/-/g, '+').replace(/_/g, '/')));
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
            
            return {
                header,
                payload,
                signature: parts[2],
                raw: token
            };
        } catch (error) {
            console.error('Failed to parse JWT:', error);
            return null;
        }
    },
    
    /**
     * Get token expiration date
     * @param {string} token - JWT token
     * @returns {Date|null} Expiration date or null
     */
    getExpiration: (token) => {
        const parsed = jwt.parse(token);
        if (!parsed || !parsed.payload.exp) return null;
        
        return new Date(parsed.payload.exp * 1000);
    },
    
    /**
     * Check if token is expired
     * @param {string} token - JWT token
     * @returns {boolean} True if token is expired
     */
    isExpired: (token) => {
        const expiration = jwt.getExpiration(token);
        if (!expiration) return false;
        
        return expiration < new Date();
    },
    
    /**
     * Get time until expiration
     * @param {string} token - JWT token
     * @returns {number} Milliseconds until expiration (negative if expired)
     */
    timeUntilExpiry: (token) => {
        const expiration = jwt.getExpiration(token);
        if (!expiration) return Infinity;
        
        return expiration.getTime() - Date.now();
    },
    
    /**
     * Format time until expiry in human-readable format
     * @param {string} token - JWT token
     * @returns {string} Formatted time string
     */
    formatTimeUntilExpiry: (token) => {
        const ms = jwt.timeUntilExpiry(token);
        
        if (ms === Infinity) return 'Never expires';
        if (ms < 0) return 'Expired';
        
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days} day${days !== 1 ? 's' : ''}`;
        if (hours > 0) return `${hours} hour${hours !== 1 ? 's' : ''}`;
        if (minutes > 0) return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
        return `${seconds} second${seconds !== 1 ? 's' : ''}`;
    },
    
    /**
     * Get user info from token
     * @param {string} token - JWT token
     * @returns {Object|null} User info object
     */
    getUserInfo: (token) => {
        const parsed = jwt.parse(token);
        if (!parsed) return null;
        
        const { payload } = parsed;
        return {
            id: payload.sub,
            username: payload.username,
            email: payload.email,
            isActive: payload.is_active,
            isVerified: payload.is_verified,
            exp: payload.exp,
            iat: payload.iat
        };
    }
};

// Export jwt utilities to window
window.jwt = jwt;

// Export utility functions to window.utils
window.utils = {
    formatTimestamp,
    formatUptime,
    formatBytes,
    escapeHtml,
    showNotification,
    showError,
    showLoading,
    hideElement,
    formatDateTime: formatTimestamp,
    
    /**
     * Show a confirmation dialog
     * @param {Object} options - Dialog options
     * @returns {Promise<boolean>} Promise that resolves to true if confirmed, false if cancelled
     */
    showConfirmDialog: async (options = {}) => {
        const {
            title = 'Confirm',
            message = 'Are you sure?',
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            confirmClass = 'btn-primary',
            requireTyping = false,
            typingPrompt = ''
        } = options;
        
        return new Promise((resolve) => {
            // Create modal HTML
            const modalId = 'confirmModal-' + Date.now();
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1" data-bs-backdrop="static">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${escapeHtml(title)}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p>${escapeHtml(message)}</p>
                                ${requireTyping ? `
                                    <div class="mt-3">
                                        <label class="form-label">${escapeHtml(typingPrompt)}</label>
                                        <input type="text" class="form-control" id="${modalId}-input" autocomplete="off">
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${escapeHtml(cancelText)}</button>
                                <button type="button" class="btn ${confirmClass}" id="${modalId}-confirm">${escapeHtml(confirmText)}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Add modal to body
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modalEl = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalEl);
            
            // Handle confirm button
            const confirmBtn = document.getElementById(`${modalId}-confirm`);
            const inputEl = document.getElementById(`${modalId}-input`);
            
            if (requireTyping && inputEl) {
                confirmBtn.disabled = true;
                inputEl.addEventListener('input', () => {
                    confirmBtn.disabled = inputEl.value !== 'REVOKE ALL';
                });
            }
            
            confirmBtn.addEventListener('click', () => {
                modal.hide();
                resolve(true);
            });
            
            // Handle modal close
            modalEl.addEventListener('hidden.bs.modal', () => {
                modalEl.remove();
                resolve(false);
            });
            
            // Show modal
            modal.show();
        });
    }
};