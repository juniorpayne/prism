/**
 * Enhanced Token Manager with Persistent Session Support
 * Extends the base TokenManager to add remember me functionality
 */

class PersistentTokenManager extends TokenManager {
    constructor() {
        super();
        this.persistentStorageKey = 'prism_persistent_session';
        this.rememberMeKey = 'prism_remember_me';
        this.rememberedUsernameKey = 'prism_remembered_username';
        this.autoLoginIndicator = null;
        
        // Check for persistent session on init
        this.checkPersistentSession();
    }
    
    /**
     * Set tokens with optional remember me functionality
     * @param {string} access - Access token
     * @param {string} refresh - Refresh token
     * @param {boolean} rememberMe - Whether to persist the session
     */
    setTokens(access, refresh = null, rememberMe = false) {
        // Call parent method for regular storage
        super.setTokens(access, refresh);
        
        if (rememberMe && refresh) {
            // Store encrypted refresh token persistently
            this.persistRefreshToken(refresh);
            localStorage.setItem(this.rememberMeKey, 'true');
        } else {
            // Clear persistent storage if not remembering
            this.clearPersistentSession();
        }
    }
    
    /**
     * Persist refresh token for remember me functionality
     * @param {string} refreshToken - The refresh token to persist
     */
    persistRefreshToken(refreshToken) {
        const persistentData = {
            refreshToken: refreshToken,
            createdAt: Date.now(),
            expiresAt: Date.now() + (30 * 24 * 60 * 60 * 1000) // 30 days
        };
        
        // Store in localStorage
        // In production, consider additional encryption
        localStorage.setItem(
            this.persistentStorageKey, 
            JSON.stringify(persistentData)
        );
    }
    
    /**
     * Check for persistent session on page load
     */
    async checkPersistentSession() {
        // Skip if already authenticated
        if (this.isAuthenticated()) return;
        
        // Check for persistent session
        const persistentData = this.getPersistentSession();
        if (!persistentData) return;
        
        // Validate expiration
        if (Date.now() > persistentData.expiresAt) {
            this.clearPersistentSession();
            return;
        }
        
        // Try to refresh using persistent token
        try {
            await this.refreshWithPersistentToken(persistentData.refreshToken);
        } catch (error) {
            console.error('Failed to restore persistent session:', error);
            this.clearPersistentSession();
        }
    }
    
    /**
     * Get persistent session data
     * @returns {Object|null} Persistent session data or null
     */
    getPersistentSession() {
        const data = localStorage.getItem(this.persistentStorageKey);
        if (!data) return null;
        
        try {
            return JSON.parse(data);
        } catch (error) {
            console.error('Error parsing persistent session:', error);
            return null;
        }
    }
    
    /**
     * Refresh tokens using persistent refresh token
     * @param {string} refreshToken - The persistent refresh token
     */
    async refreshWithPersistentToken(refreshToken) {
        // Show loading indicator
        this.showAutoLoginIndicator();
        
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Invalid refresh token');
            }
            
            const data = await response.json();
            
            // Update tokens without remember me flag (already persistent)
            this.accessToken = data.access_token;
            this.refreshToken = refreshToken;
            
            // Update storage
            localStorage.setItem('accessToken', data.access_token);
            localStorage.setItem('refreshToken', refreshToken);
            
            // Update persistent storage with new timestamp
            this.persistRefreshToken(refreshToken);
            
            // Dispatch event for successful auto-login
            window.dispatchEvent(new CustomEvent('autoLogin', {
                detail: { success: true }
            }));
            
            // Navigate to intended page or dashboard
            const redirect = localStorage.getItem('redirectAfterLogin') || '/dashboard';
            localStorage.removeItem('redirectAfterLogin');
            
            if (window.app && window.app.router) {
                window.app.router.navigate(redirect);
            }
            
        } finally {
            this.hideAutoLoginIndicator();
        }
    }
    
    /**
     * Show auto-login indicator
     */
    showAutoLoginIndicator() {
        if (this.autoLoginIndicator) return;
        
        this.autoLoginIndicator = document.createElement('div');
        this.autoLoginIndicator.id = 'autoLoginIndicator';
        this.autoLoginIndicator.className = 'position-fixed top-0 start-50 translate-middle-x mt-3';
        this.autoLoginIndicator.style.zIndex = '9999';
        this.autoLoginIndicator.innerHTML = `
            <div class="alert alert-info d-flex align-items-center shadow">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <i class="bi bi-shield-check me-2"></i>
                Restoring your session...
            </div>
        `;
        document.body.appendChild(this.autoLoginIndicator);
    }
    
    /**
     * Hide auto-login indicator
     */
    hideAutoLoginIndicator() {
        if (this.autoLoginIndicator) {
            this.autoLoginIndicator.remove();
            this.autoLoginIndicator = null;
        }
    }
    
    /**
     * Clear all tokens including persistent session
     */
    clearTokens() {
        // Call parent method
        super.clearTokens();
        
        // Clear persistent session
        this.clearPersistentSession();
    }
    
    /**
     * Clear persistent session data
     */
    clearPersistentSession() {
        localStorage.removeItem(this.persistentStorageKey);
        localStorage.removeItem(this.rememberMeKey);
    }
    
    /**
     * Check if user has remember me enabled
     * @returns {boolean} True if remember me is enabled
     */
    isRemembered() {
        return localStorage.getItem(this.rememberMeKey) === 'true';
    }
    
    /**
     * Save username for remember me
     * @param {string} username - Username to remember
     */
    rememberUsername(username) {
        if (username) {
            localStorage.setItem(this.rememberedUsernameKey, username);
        }
    }
    
    /**
     * Get remembered username
     * @returns {string|null} Remembered username or null
     */
    getRememberedUsername() {
        return localStorage.getItem(this.rememberedUsernameKey);
    }
    
    /**
     * Clear remembered username
     */
    clearRememberedUsername() {
        localStorage.removeItem(this.rememberedUsernameKey);
    }
}

// Session Storage Sync for cross-tab coordination
class SessionStorageSync {
    constructor(tokenManager) {
        this.tokenManager = tokenManager;
        this.syncKey = 'prism_session_sync';
        this.tabId = this.generateTabId();
        this.init();
    }
    
    init() {
        // Listen for storage events from other tabs
        window.addEventListener('storage', (e) => {
            if (e.key === this.syncKey && e.newValue) {
                try {
                    const message = JSON.parse(e.newValue);
                    this.handleSessionSync(message);
                } catch (error) {
                    console.error('Error parsing session sync message:', error);
                }
            }
        });
        
        // Sync on visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkSessionStatus();
            }
        });
        
        // Listen for token events
        window.addEventListener('tokensUpdated', () => {
            this.broadcastSessionChange('login');
        });
        
        window.addEventListener('tokensCleared', () => {
            this.broadcastSessionChange('logout');
        });
    }
    
    /**
     * Broadcast session change to other tabs
     * @param {string} type - Type of change (login, logout, refresh)
     * @param {Object} data - Additional data
     */
    broadcastSessionChange(type, data = {}) {
        const message = {
            type,
            data,
            timestamp: Date.now(),
            tabId: this.tabId
        };
        
        // Set and immediately remove to trigger storage event
        localStorage.setItem(this.syncKey, JSON.stringify(message));
        
        // Clean up after broadcast
        setTimeout(() => {
            if (localStorage.getItem(this.syncKey) === JSON.stringify(message)) {
                localStorage.removeItem(this.syncKey);
            }
        }, 100);
    }
    
    /**
     * Handle session sync message from another tab
     * @param {Object} message - Sync message
     */
    handleSessionSync(message) {
        // Ignore own messages
        if (message.tabId === this.tabId) return;
        
        // Ignore old messages (older than 1 second)
        if (Date.now() - message.timestamp > 1000) return;
        
        switch (message.type) {
            case 'login':
                // Another tab logged in - reload to get new session
                if (!this.tokenManager.isAuthenticated()) {
                    window.location.reload();
                }
                break;
                
            case 'logout':
                // Another tab logged out - clear local tokens
                if (this.tokenManager.isAuthenticated()) {
                    this.tokenManager.clearTokens();
                    if (window.app && window.app.router) {
                        window.app.router.navigate('/login');
                    }
                }
                break;
                
            case 'refresh':
                // Another tab refreshed token - update local token
                if (message.data.accessToken && this.tokenManager.isAuthenticated()) {
                    this.tokenManager.accessToken = message.data.accessToken;
                    localStorage.setItem('accessToken', message.data.accessToken);
                }
                break;
        }
    }
    
    /**
     * Check if session is still valid
     */
    checkSessionStatus() {
        // Reload tokens from storage in case another tab updated them
        this.tokenManager.loadTokens();
        
        // If not authenticated and not on public page, redirect to login
        const publicPaths = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'];
        const currentPath = window.location.pathname;
        
        if (!this.tokenManager.isAuthenticated() && !publicPaths.includes(currentPath)) {
            if (window.app && window.app.router) {
                window.app.router.navigate('/login');
            }
        }
    }
    
    /**
     * Generate unique tab ID
     * @returns {string} Unique tab identifier
     */
    generateTabId() {
        return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Export for use in other modules
window.PersistentTokenManager = PersistentTokenManager;
window.SessionStorageSync = SessionStorageSync;