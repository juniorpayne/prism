/**
 * DNS Service Adapter Pattern (SCRUM-122)
 * Provides a unified interface for DNS operations with ability to switch between
 * mock and real PowerDNS services based on configuration and feature flags
 */

class DNSServiceAdapter {
    constructor(config = {}) {
        this.config = {
            useRealService: false,
            enableFeatureFlags: true,
            featureFlags: {
                zones: {
                    list: false,
                    get: false,
                    create: false,
                    update: false,
                    delete: false
                },
                records: {
                    list: false,
                    get: false,
                    create: false,
                    update: false,
                    delete: false
                },
                search: false,
                import: false,
                export: false
            },
            fallbackToMock: true,
            logServiceSelection: true,
            performanceMonitoring: true,
            ...config
        };
        
        // Initialize services
        this.mockService = new DNSMockDataService();
        this.realService = new DNSRealService(window.api);
        
        // Performance tracking
        this.performanceMetrics = {
            mock: { calls: 0, totalTime: 0, errors: 0 },
            real: { calls: 0, totalTime: 0, errors: 0 }
        };
        
        // Service health status
        this.serviceHealth = {
            mock: { healthy: true, lastCheck: Date.now() },
            real: { healthy: true, lastCheck: Date.now() }
        };
        
        // Initialize health check interval
        this.startHealthChecks();
    }
    
    /**
     * Start periodic health checks for services
     */
    startHealthChecks() {
        // Check health every 30 seconds
        this.healthCheckInterval = setInterval(() => {
            this.checkServiceHealth();
        }, 30000);
    }
    
    /**
     * Stop health checks (cleanup)
     */
    stopHealthChecks() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
    }
    
    /**
     * Check health of both services
     */
    async checkServiceHealth() {
        // Check mock service (always healthy)
        this.serviceHealth.mock = {
            healthy: true,
            lastCheck: Date.now()
        };
        
        // Check real service
        try {
            const health = await window.api.getDnsHealth();
            this.serviceHealth.real = {
                healthy: health.status === 'healthy',
                lastCheck: Date.now()
            };
        } catch (error) {
            this.serviceHealth.real = {
                healthy: false,
                lastCheck: Date.now(),
                error: error.message
            };
        }
    }
    
    /**
     * Determine which service to use based on configuration and feature flags
     */
    selectService(operation, feature = null) {
        let useReal = this.config.useRealService;
        
        // Check feature flags if enabled
        if (this.config.enableFeatureFlags && feature) {
            const [category, action] = feature.split('.');
            if (this.config.featureFlags[category] && 
                this.config.featureFlags[category][action] !== undefined) {
                useReal = this.config.featureFlags[category][action];
            }
        }
        
        // Check service health
        if (useReal && !this.serviceHealth.real.healthy && this.config.fallbackToMock) {
            if (this.config.logServiceSelection) {
                console.warn(`Real DNS service unhealthy, falling back to mock for ${operation}`);
            }
            useReal = false;
        }
        
        const selectedService = useReal ? 'real' : 'mock';
        
        if (this.config.logServiceSelection) {
            console.log(`[DNS Adapter] Using ${selectedService} service for ${operation}`);
        }
        
        return useReal ? this.realService : this.mockService;
    }
    
    /**
     * Execute operation with performance monitoring and error handling
     */
    async executeOperation(operation, feature, method, ...args) {
        const service = this.selectService(operation, feature);
        const serviceName = service === this.realService ? 'real' : 'mock';
        const startTime = performance.now();
        
        try {
            const result = await service[method](...args);
            
            // Track performance
            if (this.config.performanceMonitoring) {
                const duration = performance.now() - startTime;
                this.performanceMetrics[serviceName].calls++;
                this.performanceMetrics[serviceName].totalTime += duration;
            }
            
            return result;
        } catch (error) {
            // Track errors
            if (this.config.performanceMonitoring) {
                this.performanceMetrics[serviceName].errors++;
            }
            
            // Attempt fallback if configured
            if (serviceName === 'real' && this.config.fallbackToMock) {
                console.warn(`Real service failed for ${operation}, attempting mock fallback`, error);
                
                try {
                    return await this.mockService[method](...args);
                } catch (fallbackError) {
                    console.error(`Mock fallback also failed for ${operation}`, fallbackError);
                    throw error; // Throw original error
                }
            }
            
            throw error;
        }
    }
    
    // ==============================================
    // Zone Management Methods
    // ==============================================
    
    /**
     * Get all zones with pagination
     */
    async getZones(page = 1, limit = 50, search = '', filters = {}) {
        return this.executeOperation(
            'getZones',
            'zones.list',
            'getZones',
            page, limit, search, filters
        );
    }
    
    /**
     * Get specific zone details
     */
    async getZone(zoneId) {
        return this.executeOperation(
            'getZone',
            'zones.get',
            'getZone',
            zoneId
        );
    }
    
    /**
     * Create a new zone
     */
    async createZone(zoneData) {
        return this.executeOperation(
            'createZone',
            'zones.create',
            'createZone',
            zoneData
        );
    }
    
    /**
     * Update zone configuration
     */
    async updateZone(zoneId, zoneData) {
        return this.executeOperation(
            'updateZone',
            'zones.update',
            'updateZone',
            zoneId, zoneData
        );
    }
    
    /**
     * Delete a zone
     */
    async deleteZone(zoneId) {
        return this.executeOperation(
            'deleteZone',
            'zones.delete',
            'deleteZone',
            zoneId
        );
    }
    
    // ==============================================
    // Record Management Methods
    // ==============================================
    
    /**
     * Get records for a zone
     */
    async getRecords(zoneId, page = 1, limit = 50, filters = {}) {
        return this.executeOperation(
            'getRecords',
            'records.list',
            'getRecords',
            zoneId, page, limit, filters
        );
    }
    
    /**
     * Get specific record
     */
    async getRecord(zoneId, name, type) {
        return this.executeOperation(
            'getRecord',
            'records.get',
            'getRecord',
            zoneId, name, type
        );
    }
    
    /**
     * Create a new record
     */
    async createRecord(zoneId, recordData) {
        return this.executeOperation(
            'createRecord',
            'records.create',
            'createRecord',
            zoneId, recordData
        );
    }
    
    /**
     * Update a record
     */
    async updateRecord(zoneId, name, type, recordData) {
        return this.executeOperation(
            'updateRecord',
            'records.update',
            'updateRecord',
            zoneId, name, type, recordData
        );
    }
    
    /**
     * Delete a record
     */
    async deleteRecord(zoneId, name, type) {
        return this.executeOperation(
            'deleteRecord',
            'records.delete',
            'deleteRecord',
            zoneId, name, type
        );
    }
    
    // ==============================================
    // Search and Filter Methods
    // ==============================================
    
    /**
     * Search zones
     */
    async searchZones(query, filters = {}) {
        return this.executeOperation(
            'searchZones',
            'search',
            'searchZones',
            query, filters
        );
    }
    
    /**
     * Search records
     */
    async searchRecords(query, filters = {}) {
        return this.executeOperation(
            'searchRecords',
            'search',
            'searchRecords',
            query, filters
        );
    }
    
    /**
     * Filter zones with advanced criteria
     */
    async filterZones(filters = {}, sortBy = 'name', sortOrder = 'asc') {
        return this.executeOperation(
            'filterZones',
            'search',
            'filterZones',
            filters, sortBy, sortOrder
        );
    }
    
    // ==============================================
    // Import/Export Methods
    // ==============================================
    
    /**
     * Export zones
     */
    async exportZones(format = 'json', zones = null, includeDnssec = true) {
        return this.executeOperation(
            'exportZones',
            'export',
            'exportZones',
            format, zones, includeDnssec
        );
    }
    
    /**
     * Import zones
     */
    async importZones(data, format = 'json', mode = 'merge', dryRun = false) {
        return this.executeOperation(
            'importZones',
            'import',
            'importZones',
            data, format, mode, dryRun
        );
    }
    
    /**
     * Preview import
     */
    async previewImport(data, format = 'json', mode = 'merge') {
        return this.executeOperation(
            'previewImport',
            'import',
            'previewImport',
            data, format, mode
        );
    }
    
    // ==============================================
    // Utility Methods
    // ==============================================
    
    /**
     * Get statistics
     */
    async getStats() {
        return this.executeOperation(
            'getStats',
            null,
            'getStats'
        );
    }
    
    /**
     * Get service health status
     */
    getServiceHealth() {
        return {
            mock: { ...this.serviceHealth.mock },
            real: { ...this.serviceHealth.real },
            selectedService: this.config.useRealService ? 'real' : 'mock'
        };
    }
    
    /**
     * Get performance metrics
     */
    getPerformanceMetrics() {
        const metrics = {};
        
        for (const service of ['mock', 'real']) {
            const data = this.performanceMetrics[service];
            metrics[service] = {
                calls: data.calls,
                errors: data.errors,
                errorRate: data.calls > 0 ? (data.errors / data.calls) * 100 : 0,
                avgResponseTime: data.calls > 0 ? data.totalTime / data.calls : 0
            };
        }
        
        return metrics;
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = {
            ...this.config,
            ...newConfig
        };
    }
    
    /**
     * Update feature flags
     */
    updateFeatureFlags(flags) {
        this.config.featureFlags = {
            ...this.config.featureFlags,
            ...flags
        };
    }
    
    /**
     * Enable/disable real service globally
     */
    setUseRealService(useReal) {
        this.config.useRealService = useReal;
        console.log(`[DNS Adapter] Switched to ${useReal ? 'real' : 'mock'} service globally`);
    }
    
    /**
     * Migration utility: Compare responses between services
     */
    async compareServices(operation, ...args) {
        const results = {
            operation,
            timestamp: new Date().toISOString(),
            mock: { success: false, data: null, error: null, duration: 0 },
            real: { success: false, data: null, error: null, duration: 0 },
            match: false
        };
        
        // Test mock service
        const mockStart = performance.now();
        try {
            results.mock.data = await this.mockService[operation](...args);
            results.mock.success = true;
        } catch (error) {
            results.mock.error = error.message;
        }
        results.mock.duration = performance.now() - mockStart;
        
        // Test real service
        const realStart = performance.now();
        try {
            results.real.data = await this.realService[operation](...args);
            results.real.success = true;
        } catch (error) {
            results.real.error = error.message;
        }
        results.real.duration = performance.now() - realStart;
        
        // Compare results (basic comparison)
        if (results.mock.success && results.real.success) {
            results.match = JSON.stringify(results.mock.data) === JSON.stringify(results.real.data);
        }
        
        return results;
    }
}

/**
 * DNS Real Service - Wrapper around the API client
 */
class DNSRealService {
    constructor(apiClient) {
        this.api = apiClient;
    }
    
    // Zone Management
    async getZones(page, limit, search, filters) {
        const result = await this.api.getZones(page, limit, search, filters);
        // Transform to match mock service format if needed
        return result.zones || [];
    }
    
    async getZone(zoneId) {
        return await this.api.getZone(zoneId);
    }
    
    async createZone(zoneData) {
        return await this.api.createZone(zoneData);
    }
    
    async updateZone(zoneId, zoneData) {
        return await this.api.updateZone(zoneId, zoneData);
    }
    
    async deleteZone(zoneId) {
        return await this.api.deleteZone(zoneId);
    }
    
    // Record Management
    async getRecords(zoneId, page, limit, filters) {
        const result = await this.api.getRecords(zoneId, page, limit, filters);
        return result.records || [];
    }
    
    async getRecord(zoneId, name, type) {
        return await this.api.getRecord(zoneId, name, type);
    }
    
    async createRecord(zoneId, recordData) {
        return await this.api.createRecord(zoneId, recordData);
    }
    
    async updateRecord(zoneId, name, type, recordData) {
        return await this.api.updateRecord(zoneId, name, type, recordData);
    }
    
    async deleteRecord(zoneId, name, type) {
        return await this.api.deleteRecord(zoneId, name, type);
    }
    
    // Search and Filter
    async searchZones(query, filters) {
        const result = await this.api.searchZones(query, filters);
        return result.zones || [];
    }
    
    async searchRecords(query, filters) {
        const result = await this.api.searchRecords(query, filters);
        return result.records || [];
    }
    
    async filterZones(filters, sortBy, sortOrder) {
        const result = await this.api.filterZones(filters, sortBy, sortOrder);
        return result.zones || [];
    }
    
    // Import/Export
    async exportZones(format, zones, includeDnssec) {
        return await this.api.exportZones(format, zones, includeDnssec);
    }
    
    async importZones(data, format, mode, dryRun) {
        return await this.api.importZones(data, format, mode, dryRun);
    }
    
    async previewImport(data, format, mode) {
        return await this.api.previewImport(data, format, mode);
    }
    
    // Utility
    async getStats() {
        // Real API doesn't have getStats, so we'll simulate it
        const zones = await this.api.getZones(1, 1000);
        return {
            totalZones: zones.pagination ? zones.pagination.total : 0,
            activeZones: zones.pagination ? zones.pagination.total : 0,
            totalRecords: 0, // Would need to iterate through zones
            recentChanges: 0
        };
    }
}

/**
 * Service Factory
 */
class DNSServiceFactory {
    static instance = null;
    
    /**
     * Create or get the singleton adapter instance
     */
    static getAdapter(config) {
        if (!this.instance) {
            this.instance = new DNSServiceAdapter(config);
        }
        return this.instance;
    }
    
    /**
     * Reset the singleton instance
     */
    static reset() {
        if (this.instance) {
            this.instance.stopHealthChecks();
            this.instance = null;
        }
    }
    
    /**
     * Update adapter configuration
     */
    static updateConfig(config) {
        const adapter = this.getAdapter();
        adapter.updateConfig(config);
        return adapter;
    }
}

// Export for use
window.DNSServiceAdapter = DNSServiceAdapter;
window.DNSRealService = DNSRealService;
window.DNSServiceFactory = DNSServiceFactory;