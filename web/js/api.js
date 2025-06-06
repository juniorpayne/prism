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
    }

    /**
     * Make HTTP request with error handling and retry logic
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        let lastError;
        
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
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
                
                // Don't retry on client errors (4xx)
                if (error.status >= 400 && error.status < 500) {
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
     * Get all hosts with optional pagination
     */
    async getHosts(page = 1, limit = 100) {
        try {
            const response = await this.request(`/api/hosts?page=${page}&limit=${limit}`);
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch hosts: ${error.message}`, error.status, '/api/hosts');
        }
    }

    /**
     * Get specific host by hostname
     */
    async getHost(hostname) {
        try {
            const response = await this.request(`/api/hosts/${encodeURIComponent(hostname)}`);
            return response;
        } catch (error) {
            if (error.status === 404) {
                throw new APIError(`Host '${hostname}' not found`, 404, `/api/hosts/${hostname}`);
            }
            throw new APIError(`Failed to fetch host: ${error.message}`, error.status, `/api/hosts/${hostname}`);
        }
    }

    /**
     * Get hosts by status
     */
    async getHostsByStatus(status) {
        try {
            const response = await this.request(`/api/hosts/status/${encodeURIComponent(status)}`);
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch hosts by status: ${error.message}`, error.status, `/api/hosts/status/${status}`);
        }
    }

    /**
     * Get server health status
     */
    async getHealth() {
        try {
            const response = await this.request('/api/health');
            return response;
        } catch (error) {
            throw new APIError(`Health check failed: ${error.message}`, error.status, '/api/health');
        }
    }

    /**
     * Get server statistics
     */
    async getStats() {
        try {
            const response = await this.request('/api/stats');
            return response;
        } catch (error) {
            throw new APIError(`Failed to fetch stats: ${error.message}`, error.status, '/api/stats');
        }
    }

    /**
     * Search hosts by hostname pattern
     */
    async searchHosts(query) {
        try {
            const response = await this.request(`/api/hosts?search=${encodeURIComponent(query)}`);
            return response;
        } catch (error) {
            throw new APIError(`Search failed: ${error.message}`, error.status, '/api/hosts');
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
window.api = new PrismAPI();
window.APIError = APIError;