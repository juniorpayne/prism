/**
 * DNS Service Adapter Configuration (SCRUM-122)
 * Configuration management for DNS service adapter
 */

class DNSAdapterConfig {
    constructor() {
        this.storageKey = 'prism-dns-adapter-config';
        this.defaultConfig = {
            // Global switch to use real service
            useRealService: false,
            
            // Enable feature flag granular control
            enableFeatureFlags: true,
            
            // Feature flags for gradual migration
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
            
            // Fallback options
            fallbackToMock: true,
            
            // Logging and monitoring
            logServiceSelection: true,
            performanceMonitoring: true,
            
            // A/B testing configuration
            abTesting: {
                enabled: false,
                percentage: 0, // Percentage of users to use real service
                userGroup: null // Specific user group for testing
            }
        };
        
        this.loadConfig();
    }
    
    /**
     * Load configuration from localStorage
     */
    loadConfig() {
        const stored = localStorage.getItem(this.storageKey);
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                this.config = { ...this.defaultConfig, ...parsed };
            } catch (error) {
                console.error('Failed to parse DNS adapter config:', error);
                this.config = { ...this.defaultConfig };
            }
        } else {
            this.config = { ...this.defaultConfig };
        }
    }
    
    /**
     * Save configuration to localStorage
     */
    saveConfig() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.config));
            // Notify adapter of config change
            if (window.dnsAdapter) {
                window.dnsAdapter.updateConfig(this.config);
            }
        } catch (error) {
            console.error('Failed to save DNS adapter config:', error);
        }
    }
    
    /**
     * Get current configuration
     */
    getConfig() {
        return { ...this.config };
    }
    
    /**
     * Update configuration
     */
    updateConfig(updates) {
        this.config = { ...this.config, ...updates };
        this.saveConfig();
    }
    
    /**
     * Update specific feature flag
     */
    setFeatureFlag(category, action, enabled) {
        if (this.config.featureFlags[category] && 
            this.config.featureFlags[category][action] !== undefined) {
            this.config.featureFlags[category][action] = enabled;
            this.saveConfig();
        }
    }
    
    /**
     * Enable all features for a category
     */
    enableCategory(category) {
        if (this.config.featureFlags[category]) {
            Object.keys(this.config.featureFlags[category]).forEach(action => {
                this.config.featureFlags[category][action] = true;
            });
            this.saveConfig();
        }
    }
    
    /**
     * Disable all features for a category
     */
    disableCategory(category) {
        if (this.config.featureFlags[category]) {
            Object.keys(this.config.featureFlags[category]).forEach(action => {
                this.config.featureFlags[category][action] = false;
            });
            this.saveConfig();
        }
    }
    
    /**
     * Enable all real service features
     */
    enableAllRealService() {
        this.config.useRealService = true;
        Object.keys(this.config.featureFlags).forEach(category => {
            if (typeof this.config.featureFlags[category] === 'object') {
                Object.keys(this.config.featureFlags[category]).forEach(action => {
                    this.config.featureFlags[category][action] = true;
                });
            } else {
                this.config.featureFlags[category] = true;
            }
        });
        this.saveConfig();
    }
    
    /**
     * Disable all real service features (use mock only)
     */
    disableAllRealService() {
        this.config.useRealService = false;
        Object.keys(this.config.featureFlags).forEach(category => {
            if (typeof this.config.featureFlags[category] === 'object') {
                Object.keys(this.config.featureFlags[category]).forEach(action => {
                    this.config.featureFlags[category][action] = false;
                });
            } else {
                this.config.featureFlags[category] = false;
            }
        });
        this.saveConfig();
    }
    
    /**
     * Get migration progress
     */
    getMigrationProgress() {
        let totalFlags = 0;
        let enabledFlags = 0;
        
        Object.keys(this.config.featureFlags).forEach(category => {
            if (typeof this.config.featureFlags[category] === 'object') {
                Object.keys(this.config.featureFlags[category]).forEach(action => {
                    totalFlags++;
                    if (this.config.featureFlags[category][action]) {
                        enabledFlags++;
                    }
                });
            } else {
                totalFlags++;
                if (this.config.featureFlags[category]) {
                    enabledFlags++;
                }
            }
        });
        
        return {
            total: totalFlags,
            enabled: enabledFlags,
            percentage: totalFlags > 0 ? (enabledFlags / totalFlags) * 100 : 0
        };
    }
    
    /**
     * Check if A/B testing should use real service
     */
    shouldUseRealServiceForUser(userId) {
        if (!this.config.abTesting.enabled) {
            return false;
        }
        
        // Simple hash-based A/B testing
        const hash = this.hashCode(userId || 'anonymous');
        const bucket = Math.abs(hash) % 100;
        
        return bucket < this.config.abTesting.percentage;
    }
    
    /**
     * Simple hash function for A/B testing
     */
    hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash;
    }
    
    /**
     * Reset to default configuration
     */
    reset() {
        this.config = { ...this.defaultConfig };
        this.saveConfig();
    }
}

// Create global configuration instance
window.dnsAdapterConfig = new DNSAdapterConfig();

// Migration helper UI
class DNSMigrationUI {
    static createControlPanel() {
        const panel = document.createElement('div');
        panel.id = 'dns-migration-panel';
        panel.className = 'dns-migration-panel';
        panel.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 14px;
            min-width: 300px;
            display: none;
        `;
        
        const config = window.dnsAdapterConfig.getConfig();
        const progress = window.dnsAdapterConfig.getMigrationProgress();
        
        panel.innerHTML = `
            <h4 style="margin: 0 0 10px 0; font-size: 16px;">DNS Service Migration</h4>
            <div style="margin-bottom: 10px;">
                <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="dns-use-real" ${config.useRealService ? 'checked' : ''} 
                           style="margin-right: 8px;">
                    Use Real DNS Service
                </label>
            </div>
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>Migration Progress</span>
                    <span>${progress.enabled}/${progress.total} (${progress.percentage.toFixed(0)}%)</span>
                </div>
                <div style="background: #e0e0e0; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: #4caf50; height: 100%; width: ${progress.percentage}%; 
                                transition: width 0.3s;"></div>
                </div>
            </div>
            <div style="margin-bottom: 10px;">
                <button id="dns-enable-all" style="margin-right: 5px; padding: 5px 10px; 
                        background: #4caf50; color: white; border: none; border-radius: 4px; 
                        cursor: pointer;">
                    Enable All
                </button>
                <button id="dns-disable-all" style="margin-right: 5px; padding: 5px 10px; 
                        background: #f44336; color: white; border: none; border-radius: 4px; 
                        cursor: pointer;">
                    Disable All
                </button>
                <button id="dns-view-details" style="padding: 5px 10px; 
                        background: #2196f3; color: white; border: none; border-radius: 4px; 
                        cursor: pointer;">
                    Details
                </button>
            </div>
            <div style="font-size: 12px; color: #666;">
                <div>Mock Service: <span style="color: #4caf50;">● Healthy</span></div>
                <div id="dns-real-health">Real Service: <span style="color: #999;">● Unknown</span></div>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Event handlers
        document.getElementById('dns-use-real').addEventListener('change', (e) => {
            window.dnsAdapterConfig.updateConfig({ useRealService: e.target.checked });
        });
        
        document.getElementById('dns-enable-all').addEventListener('click', () => {
            window.dnsAdapterConfig.enableAllRealService();
            this.updatePanel();
        });
        
        document.getElementById('dns-disable-all').addEventListener('click', () => {
            window.dnsAdapterConfig.disableAllRealService();
            this.updatePanel();
        });
        
        document.getElementById('dns-view-details').addEventListener('click', () => {
            this.showDetailsModal();
        });
        
        // Update health status
        if (window.dnsAdapter) {
            const health = window.dnsAdapter.getServiceHealth();
            this.updateHealthStatus(health);
        }
        
        return panel;
    }
    
    static updatePanel() {
        const panel = document.getElementById('dns-migration-panel');
        if (panel) {
            panel.remove();
            this.createControlPanel();
            this.show();
        }
    }
    
    static updateHealthStatus(health) {
        const healthElement = document.getElementById('dns-real-health');
        if (healthElement && health.real) {
            const status = health.real.healthy ? 
                '<span style="color: #4caf50;">● Healthy</span>' : 
                '<span style="color: #f44336;">● Unhealthy</span>';
            healthElement.innerHTML = `Real Service: ${status}`;
        }
    }
    
    static show() {
        let panel = document.getElementById('dns-migration-panel');
        if (!panel) {
            panel = this.createControlPanel();
        }
        panel.style.display = 'block';
    }
    
    static hide() {
        const panel = document.getElementById('dns-migration-panel');
        if (panel) {
            panel.style.display = 'none';
        }
    }
    
    static showDetailsModal() {
        // Implementation for detailed feature flag modal
        alert('Feature flag details modal - to be implemented');
    }
}

// Export migration UI
window.DNSMigrationUI = DNSMigrationUI;