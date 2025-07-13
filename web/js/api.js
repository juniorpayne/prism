/**
 * API Client for Prism DNS Server
 * Handles all HTTP requests with error handling and retry logic
 */

class PrismAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.timeout = 10000; // 10 seconds
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second
        this.tokenManager = null; // Will be initialized after TokenManager is loaded
    }
    
    /**
     * Initialize token manager
     */
    initTokenManager() {
        // Use PersistentTokenManager if available, otherwise fall back to regular TokenManager
        if (window.PersistentTokenManager) {
            this.tokenManager = new PersistentTokenManager();
            
            // Initialize session sync for cross-tab coordination
            if (window.SessionStorageSync) {
                this.sessionSync = new SessionStorageSync(this.tokenManager);
            }
        } else if (window.TokenManager) {
            this.tokenManager = new TokenManager();
        }
    }

    /**
     * Make HTTP request with error handling and retry logic
     */
    async request(endpoint, options = {}) {
        // Check if token needs refresh before making request
        if (this.tokenManager && this.tokenManager.shouldRefreshToken()) {
            try {
                await this.tokenManager.refreshAccessToken();
            } catch (error) {
                console.warn('Token refresh failed before request:', error);
            }
        }
        
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        // Add authentication header if token is available
        if (this.tokenManager && this.tokenManager.getAccessToken()) {
            config.headers['Authorization'] = `Bearer ${this.tokenManager.getAccessToken()}`;
        }

        let lastError;
        let tokenRefreshed = false;
        
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                // Handle 401 Unauthorized
                if (response.status === 401 && this.tokenManager && !tokenRefreshed) {
                    tokenRefreshed = true;
                    try {
                        // Try to refresh token
                        const newToken = await this.tokenManager.refreshAccessToken();
                        // Update authorization header with new token
                        config.headers['Authorization'] = `Bearer ${newToken}`;
                        // Retry the request
                        continue;
                    } catch (refreshError) {
                        console.error('Token refresh failed:', refreshError);
                        // Let the 401 error propagate
                    }
                }
                
                // For raw fetch methods (used in other parts of the app), return the response directly
                if (options.returnResponse) {
                    return response;
                }
                
                if (!response.ok) {
                    throw new APIError(
                        `HTTP ${response.status}: ${response.statusText}`,
                        response.status,
                        endpoint
                    );
                }
                
                const data = await response.json();
                return data;
                
            } catch (error) {
                lastError = error;
                
                // Don't retry on client errors (4xx) except 401
                if (error.status >= 400 && error.status < 500 && error.status !== 401) {
                    throw error;
                }
                
                // Don't retry on the last attempt
                if (attempt === this.retryAttempts) {
                    throw error;
                }
                
                // Wait before retrying
                await this.sleep(this.retryDelay * attempt);
            }
        }
        
        throw lastError;
    }

    /**
     * HTTP method wrappers
     */
    async get(endpoint, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'GET',
            returnResponse: true
        });
    }

    async post(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data),
            returnResponse: true
        });
    }

    async put(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data),
            returnResponse: true
        });
    }

    async delete(endpoint, data = {}, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'DELETE',
            body: data ? JSON.stringify(data) : undefined,
            returnResponse: true
        });
    }

    /**
     * Get all hosts with optional pagination
     */
    async getHosts(page = 1, limit = 100) {
        try {
            const response = await this.request(`/hosts?page=${page}&limit=${limit}`);
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch hosts: ${error.message}`, error.status, '/hosts');
        }
    }

    /**
     * Get specific host by hostname
     */
    async getHost(hostname) {
        try {
            const response = await this.request(`/hosts/${encodeURIComponent(hostname)}`);
            return response;
        } catch (error) {
            if (error.status === 404) {
                throw new APIError(`Host '${hostname}' not found`, 404, `/hosts/${hostname}`);
            }
            throw new APIError(`Failed to fetch host: ${error.message}`, error.status, `/hosts/${hostname}`);
        }
    }

    /**
     * Get hosts by status
     */
    async getHostsByStatus(status) {
        try {
            const response = await this.request(`/hosts/status/${encodeURIComponent(status)}`);
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch hosts by status: ${error.message}`, error.status, `/hosts/status/${status}`);
        }
    }

    /**
     * Get server health status
     */
    async getHealth() {
        try {
            const response = await this.request('/health');
            return response;
        } catch (error) {
            throw new APIError(`Health check failed: ${error.message}`, error.status, '/health');
        }
    }

    /**
     * Get server statistics
     */
    async getStats() {
        try {
            const response = await this.request('/stats');
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch stats: ${error.message}`, error.status, '/stats');
        }
    }

    /**
     * Search hosts by hostname pattern
     */
    async searchHosts(query) {
        try {
            const response = await this.request(`/hosts?search=${encodeURIComponent(query)}`);
            return response;
        } catch (error) {
            throw new APIError(`Search failed: ${error.message}`, error.status, '/hosts');
        }
    }
    
    /**
     * Make POST request that returns the full response
     */
    async post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
            returnResponse: true
        });
    }
    
    /**
     * Login user
     */
    async login(username, password) {
        try {
            const response = await this.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            
            // Store tokens
            if (this.tokenManager && response.access_token) {
                this.tokenManager.setTokens(response.access_token, response.refresh_token);
            }
            
            return response;
        } catch (error) {
            throw new APIError(`Login failed: ${error.message}`, error.status, '/auth/login');
        }
    }
    
    /**
     * Logout user
     */
    async logout() {
        try {
            await this.request('/auth/logout', {
                method: 'POST'
            });
        } catch (error) {
            console.warn('Logout request failed:', error);
        } finally {
            // Always clear tokens locally
            if (this.tokenManager) {
                this.tokenManager.clearTokens();
            }
        }
    }
    
    /**
     * Register new user
     */
    async register(userData) {
        try {
            const response = await this.request('/auth/register', {
                method: 'POST',
                body: JSON.stringify(userData)
            });
            return response;
        } catch (error) {
            throw new APIError(`Registration failed: ${error.message}`, error.status, '/auth/register');
        }
    }
    
    /**
     * Get current user info
     */
    async getCurrentUser() {
        try {
            const response = await this.request('/auth/me');
            return response;
        } catch (error) {
            throw new APIError(`Failed to get user info: ${error.message}`, error.status, '/auth/me');
        }
    }
    
    /**
     * Request password reset
     */
    async forgotPassword(email) {
        try {
            const response = await this.request('/auth/forgot-password', {
                method: 'POST',
                body: JSON.stringify({ email })
            });
            return response;
        } catch (error) {
            throw new APIError(`Password reset request failed: ${error.message}`, error.status, '/auth/forgot-password');
        }
    }
    
    /**
     * Reset password with token
     */
    async resetPassword(token, newPassword) {
        try {
            const response = await this.request('/auth/reset-password', {
                method: 'POST',
                body: JSON.stringify({ token, password: newPassword })
            });
            return response;
        } catch (error) {
            throw new APIError(`Password reset failed: ${error.message}`, error.status, '/auth/reset-password');
        }
    }
    
    /**
     * Verify email with token
     */
    async verifyEmail(token) {
        try {
            const response = await this.request(`/auth/verify-email/${encodeURIComponent(token)}`, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            throw new APIError(`Email verification failed: ${error.message}`, error.status, '/auth/verify-email');
        }
    }

    /**
     * Utility function to sleep for a given duration
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Check if the API is reachable
     */
    async ping() {
        try {
            await this.getHealth();
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Get API configuration
     */
    getConfig() {
        return {
            baseUrl: this.baseUrl,
            timeout: this.timeout,
            retryAttempts: this.retryAttempts,
            retryDelay: this.retryDelay
        };
    }

    /**
     * Update API configuration
     */
    updateConfig(config) {
        if (config.baseUrl) this.baseUrl = config.baseUrl;
        if (config.timeout) this.timeout = config.timeout;
        if (config.retryAttempts) this.retryAttempts = config.retryAttempts;
        if (config.retryDelay) this.retryDelay = config.retryDelay;
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(message, status, endpoint) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.endpoint = endpoint;
        this.timestamp = new Date().toISOString();
    }

    /**
     * Get user-friendly error message
     */
    getUserMessage() {
        switch (this.status) {
            case 404:
                return 'The requested resource was not found.';
            case 500:
                return 'Server error occurred. Please try again later.';
            case 503:
                return 'Service is temporarily unavailable. Please try again later.';
            case 0:
            case undefined:
                return 'Unable to connect to the server. Please check your connection.';
            default:
                if (this.status >= 500) {
                    return 'Server error occurred. Please try again later.';
                } else if (this.status >= 400) {
                    return 'Invalid request. Please check your input.';
                } else {
                    return 'An unexpected error occurred. Please try again.';
                }
        }
    }

    /**
     * Get technical error details for logging
     */
    getTechnicalDetails() {
        return {
            message: this.message,
            status: this.status,
            endpoint: this.endpoint,
            timestamp: this.timestamp,
            stack: this.stack
        };
    }
}

/**
 * Global API instance
 */
window.api = new PrismAPI('/api');
window.APIError = APIError;