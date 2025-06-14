/**
 * JWT Token Manager for Prism DNS
 * Handles secure token storage, refresh, and lifecycle management
 */

class TokenManager {
    constructor() {
        this.accessToken = null;
        this.refreshToken = null;
        this.refreshPromise = null;
        this.tokenRefreshInterval = null;
        
        // Load tokens from storage on initialization
        this.loadTokens();
        
        // Start automatic token refresh check
        this.startTokenRefreshTimer();
    }
    
    /**
     * Load tokens from localStorage
     */
    loadTokens() {
        try {
            this.accessToken = localStorage.getItem('accessToken');
            this.refreshToken = localStorage.getItem('refreshToken');
            
            // Validate tokens on load
            if (this.accessToken && !this.isValidToken(this.accessToken)) {
                console.warn('Invalid access token in storage, clearing...');
                this.clearTokens();
            }
        } catch (error) {
            console.error('Error loading tokens:', error);
            this.clearTokens();
        }
    }
    
    /**
     * Set new tokens and persist to storage
     * @param {string} access - Access token
     * @param {string} refresh - Refresh token (optional)
     */
    setTokens(access, refresh = null) {
        if (!access) {
            throw new Error('Access token is required');
        }
        
        this.accessToken = access;
        localStorage.setItem('accessToken', access);
        
        if (refresh) {
            this.refreshToken = refresh;
            localStorage.setItem('refreshToken', refresh);
        }
        
        // Restart refresh timer with new token
        this.startTokenRefreshTimer();
        
        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('tokensUpdated', {
            detail: { hasToken: true }
        }));
    }
    
    /**
     * Clear all tokens from memory and storage
     */
    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        this.refreshPromise = null;
        
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        
        // Stop refresh timer
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
            this.tokenRefreshInterval = null;
        }
        
        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('tokensCleared', {
            detail: { hasToken: false }
        }));
    }
    
    /**
     * Get current access token
     * @returns {string|null} Access token or null
     */
    getAccessToken() {
        return this.accessToken;
    }
    
    /**
     * Get current refresh token
     * @returns {string|null} Refresh token or null
     */
    getRefreshToken() {
        return this.refreshToken;
    }
    
    /**
     * Check if a token is valid format
     * @param {string} token - Token to validate
     * @returns {boolean} True if valid JWT format
     */
    isValidToken(token) {
        if (!token || typeof token !== 'string') return false;
        
        const parts = token.split('.');
        if (parts.length !== 3) return false;
        
        try {
            // Try to decode each part
            JSON.parse(atob(parts[0].replace(/-/g, '+').replace(/_/g, '/')));
            JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
            return true;
        } catch (error) {
            return false;
        }
    }
    
    /**
     * Check if token is expired
     * @param {string} token - JWT token to check
     * @returns {boolean} True if token is expired
     */
    isTokenExpired(token) {
        if (!token || !this.isValidToken(token)) return true;
        
        try {
            const parts = token.split('.');
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
            
            if (!payload.exp) {
                // No expiration claim
                return false;
            }
            
            // Add 30 second buffer to account for clock skew
            const expirationTime = payload.exp * 1000 - 30000;
            return Date.now() >= expirationTime;
            
        } catch (error) {
            console.error('Error checking token expiry:', error);
            return true;
        }
    }
    
    /**
     * Get token expiration time
     * @param {string} token - JWT token
     * @returns {number|null} Expiration timestamp in milliseconds or null
     */
    getTokenExpiry(token) {
        if (!token || !this.isValidToken(token)) return null;
        
        try {
            const parts = token.split('.');
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
            return payload.exp ? payload.exp * 1000 : null;
        } catch (error) {
            return null;
        }
    }
    
    /**
     * Check if access token needs refresh
     * @returns {boolean} True if token should be refreshed
     */
    shouldRefreshToken() {
        if (!this.accessToken) return false;
        if (!this.refreshToken) return false;
        
        const expiry = this.getTokenExpiry(this.accessToken);
        if (!expiry) return false;
        
        // Refresh if less than 5 minutes remaining
        const timeUntilExpiry = expiry - Date.now();
        return timeUntilExpiry < 5 * 60 * 1000;
    }
    
    /**
     * Refresh the access token using refresh token
     * @returns {Promise<string>} New access token
     */
    async refreshAccessToken() {
        // Prevent multiple simultaneous refresh requests
        if (this.refreshPromise) {
            return this.refreshPromise;
        }
        
        if (!this.refreshToken) {
            throw new Error('No refresh token available');
        }
        
        this.refreshPromise = fetch('/api/auth/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                refresh_token: this.refreshToken
            })
        })
        .then(async response => {
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Token refresh failed');
            }
            return response.json();
        })
        .then(data => {
            // Update only access token (refresh token stays the same)
            this.setTokens(data.access_token);
            return data.access_token;
        })
        .catch(error => {
            console.error('Token refresh failed:', error);
            
            // Clear tokens on refresh failure
            this.clearTokens();
            
            // Redirect to login
            if (window.app && window.app.router) {
                window.app.router.navigate('/login');
            }
            
            throw error;
        })
        .finally(() => {
            this.refreshPromise = null;
        });
        
        return this.refreshPromise;
    }
    
    /**
     * Start automatic token refresh timer
     */
    startTokenRefreshTimer() {
        // Clear existing timer
        if (this.tokenRefreshInterval) {
            clearInterval(this.tokenRefreshInterval);
        }
        
        // Check every minute
        this.tokenRefreshInterval = setInterval(() => {
            if (this.shouldRefreshToken()) {
                console.log('Auto-refreshing access token...');
                this.refreshAccessToken().catch(error => {
                    console.error('Auto-refresh failed:', error);
                });
            }
        }, 60 * 1000);
    }
    
    /**
     * Get decoded token payload
     * @param {string} token - JWT token to decode
     * @returns {Object|null} Decoded payload or null
     */
    decodeToken(token) {
        if (!token || !this.isValidToken(token)) return null;
        
        try {
            const parts = token.split('.');
            return JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
        } catch (error) {
            console.error('Error decoding token:', error);
            return null;
        }
    }
    
    /**
     * Get current user info from access token
     * @returns {Object|null} User info or null
     */
    getCurrentUser() {
        if (!this.accessToken) return null;
        
        const payload = this.decodeToken(this.accessToken);
        if (!payload) return null;
        
        return {
            id: payload.sub,
            username: payload.username,
            email: payload.email,
            isActive: payload.is_active,
            isVerified: payload.is_verified,
            exp: payload.exp
        };
    }
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if user has valid access token
     */
    isAuthenticated() {
        return this.accessToken && !this.isTokenExpired(this.accessToken);
    }
}

// Export for use in other modules
window.TokenManager = TokenManager;