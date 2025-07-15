/**
 * DNS Zone Settings Manager
 * Handles the settings tab in the zone detail modal
 */

class DNSZoneSettingsManager {
    constructor(zoneDetailManager) {
        this.zoneDetailManager = zoneDetailManager;
        // Use service adapter from zone detail manager
        this.dnsService = zoneDetailManager.dnsService || DNSServiceFactory.getAdapter();
        this.currentZone = null;
        this.originalSettings = null;
        this.currentSettings = null;
        this.hasChanges = false;
        this.changeListeners = new Set();
        this.loadingStates = new Map(); // Track loading states for operations
    }

    /**
     * Initialize settings for a zone
     */
    initialize(zone) {
        this.currentZone = zone;
        this.loadSettings();
        this.render();
        this.bindEvents();
    }

    /**
     * Load settings from zone data
     */
    loadSettings() {
        // Extract settings from zone data or use defaults
        const soaRrset = this.currentZone.rrsets?.find(r => r.type === 'SOA');
        const soaData = soaRrset ? this.parseSOARecord(soaRrset) : null;
        
        this.originalSettings = {
            // TTL Settings
            ttl: {
                default: soaRrset?.ttl || 3600,
                minimum: soaData?.minimumTtl || 300,
                maximum: 86400,
                negative: soaData?.minimumTtl || 3600
            },
            // Zone Transfer Settings
            transfer: {
                allowTransfer: this.currentZone.allowTransfer || false,
                allowedIPs: this.currentZone.allowedTransferIPs || [],
                notifyTargets: this.currentZone.notifyTargets || [],
                alsoNotify: this.currentZone.alsoNotify || []
            },
            // DNSSEC Settings
            dnssec: {
                enabled: this.currentZone.dnssec || false,
                algorithm: this.currentZone.dnssecAlgorithm || 'RSASHA256',
                keySize: this.currentZone.dnssecKeySize || 2048,
                dsRecords: this.currentZone.dsRecords || []
            }
        };
        
        // Deep clone for current settings
        this.currentSettings = JSON.parse(JSON.stringify(this.originalSettings));
        this.hasChanges = false;
    }

    /**
     * Parse SOA record for settings
     */
    parseSOARecord(soaRrset) {
        if (!soaRrset || !soaRrset.records || soaRrset.records.length === 0) {
            return null;
        }

        const content = soaRrset.records[0].content;
        const parts = content.split(' ');

        if (parts.length < 7) {
            return null;
        }

        return {
            primaryNs: parts[0],
            email: parts[1],
            serial: parts[2],
            refresh: parseInt(parts[3]),
            retry: parseInt(parts[4]),
            expire: parseInt(parts[5]),
            minimumTtl: parseInt(parts[6])
        };
    }

    /**
     * Render settings tab content
     */
    render() {
        const container = document.getElementById('settings');
        if (!container) return;

        container.innerHTML = `
            <div class="row">
                <div class="col-12">
                    <!-- Change Indicator -->
                    <div id="settingsChangeIndicator" class="alert alert-warning d-none">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        You have unsaved changes. Don't forget to save before closing.
                    </div>

                    <!-- TTL Settings Section -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="bi bi-clock me-2"></i>TTL Settings
                                <button type="button" class="btn btn-sm btn-link float-end" 
                                        data-bs-toggle="tooltip" 
                                        title="Time To Live (TTL) controls how long DNS resolvers cache your records">
                                    <i class="bi bi-question-circle"></i>
                                </button>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label for="defaultTTL" class="form-label">
                                        Default TTL
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="Default cache time for all records (in seconds)"></i>
                                    </label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="defaultTTL" 
                                               value="${this.currentSettings.ttl.default}" 
                                               min="60" max="86400">
                                        <span class="input-group-text">seconds</span>
                                    </div>
                                    <div class="form-text">Common: 3600 (1 hour)</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="minimumTTL" class="form-label">
                                        Minimum TTL
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="Minimum allowed TTL for any record"></i>
                                    </label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="minimumTTL" 
                                               value="${this.currentSettings.ttl.minimum}" 
                                               min="60" max="86400">
                                        <span class="input-group-text">seconds</span>
                                    </div>
                                    <div class="form-text">Common: 300 (5 minutes)</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="maximumTTL" class="form-label">
                                        Maximum TTL
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="Maximum allowed TTL for any record"></i>
                                    </label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="maximumTTL" 
                                               value="${this.currentSettings.ttl.maximum}" 
                                               min="60" max="604800">
                                        <span class="input-group-text">seconds</span>
                                    </div>
                                    <div class="form-text">Common: 86400 (24 hours)</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="negativeTTL" class="form-label">
                                        Negative Cache TTL
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="How long to cache negative responses (NXDOMAIN)"></i>
                                    </label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="negativeTTL" 
                                               value="${this.currentSettings.ttl.negative}" 
                                               min="60" max="86400">
                                        <span class="input-group-text">seconds</span>
                                    </div>
                                    <div class="form-text">Common: 3600 (1 hour)</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Zone Transfer Settings Section -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="bi bi-arrow-left-right me-2"></i>Zone Transfer Settings
                                <button type="button" class="btn btn-sm btn-link float-end" 
                                        data-bs-toggle="tooltip" 
                                        title="Control how your zone data is transferred to secondary DNS servers">
                                    <i class="bi bi-question-circle"></i>
                                </button>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="form-check form-switch mb-3">
                                <input class="form-check-input" type="checkbox" id="allowTransfer" 
                                       ${this.currentSettings.transfer.allowTransfer ? 'checked' : ''}>
                                <label class="form-check-label" for="allowTransfer">
                                    Allow Zone Transfers (AXFR/IXFR)
                                </label>
                            </div>
                            
                            <div id="transferSettings" class="${!this.currentSettings.transfer.allowTransfer ? 'd-none' : ''}">
                                <div class="mb-3">
                                    <label class="form-label">
                                        Allowed Transfer IPs
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="IP addresses allowed to transfer this zone"></i>
                                    </label>
                                    <div id="allowedIPsList">
                                        ${this.renderIPList('allowedIPs', this.currentSettings.transfer.allowedIPs)}
                                    </div>
                                    <button type="button" class="btn btn-sm btn-outline-primary mt-2" 
                                            onclick="dnsZoneSettings.addIP('allowedIPs')">
                                        <i class="bi bi-plus-circle me-1"></i>Add IP
                                    </button>
                                </div>
                                
                                <div class="mb-3">
                                    <label class="form-label">
                                        Also Notify
                                        <i class="bi bi-info-circle text-muted small" 
                                           data-bs-toggle="tooltip" 
                                           title="Additional servers to notify of zone changes"></i>
                                    </label>
                                    <div id="alsoNotifyList">
                                        ${this.renderIPList('alsoNotify', this.currentSettings.transfer.alsoNotify)}
                                    </div>
                                    <button type="button" class="btn btn-sm btn-outline-primary mt-2" 
                                            onclick="dnsZoneSettings.addIP('alsoNotify')">
                                        <i class="bi bi-plus-circle me-1"></i>Add Server
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- DNSSEC Settings Section -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="bi bi-shield-check me-2"></i>DNSSEC Configuration
                                <button type="button" class="btn btn-sm btn-link float-end" 
                                        data-bs-toggle="tooltip" 
                                        title="DNS Security Extensions provide authentication and integrity for DNS data">
                                    <i class="bi bi-question-circle"></i>
                                </button>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="form-check form-switch mb-3">
                                <input class="form-check-input" type="checkbox" id="dnssecEnabled" 
                                       ${this.currentSettings.dnssec.enabled ? 'checked' : ''}>
                                <label class="form-check-label" for="dnssecEnabled">
                                    Enable DNSSEC
                                </label>
                            </div>
                            
                            <div id="dnssecSettings" class="${!this.currentSettings.dnssec.enabled ? 'd-none' : ''}">
                                <div class="row g-3">
                                    <div class="col-md-6">
                                        <label for="dnssecAlgorithm" class="form-label">
                                            Signing Algorithm
                                            <i class="bi bi-info-circle text-muted small" 
                                               data-bs-toggle="tooltip" 
                                               title="Cryptographic algorithm for DNSSEC signatures"></i>
                                        </label>
                                        <select class="form-select" id="dnssecAlgorithm">
                                            <option value="RSASHA256" ${this.currentSettings.dnssec.algorithm === 'RSASHA256' ? 'selected' : ''}>
                                                RSASHA256 (Recommended)
                                            </option>
                                            <option value="RSASHA512" ${this.currentSettings.dnssec.algorithm === 'RSASHA512' ? 'selected' : ''}>
                                                RSASHA512
                                            </option>
                                            <option value="ECDSAP256SHA256" ${this.currentSettings.dnssec.algorithm === 'ECDSAP256SHA256' ? 'selected' : ''}>
                                                ECDSAP256SHA256
                                            </option>
                                            <option value="ECDSAP384SHA384" ${this.currentSettings.dnssec.algorithm === 'ECDSAP384SHA384' ? 'selected' : ''}>
                                                ECDSAP384SHA384
                                            </option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label for="dnssecKeySize" class="form-label">
                                            Key Size
                                            <i class="bi bi-info-circle text-muted small" 
                                               data-bs-toggle="tooltip" 
                                               title="Size of the cryptographic key in bits"></i>
                                        </label>
                                        <select class="form-select" id="dnssecKeySize">
                                            <option value="1024" ${this.currentSettings.dnssec.keySize === 1024 ? 'selected' : ''}>
                                                1024 bits
                                            </option>
                                            <option value="2048" ${this.currentSettings.dnssec.keySize === 2048 ? 'selected' : ''}>
                                                2048 bits (Recommended)
                                            </option>
                                            <option value="4096" ${this.currentSettings.dnssec.keySize === 4096 ? 'selected' : ''}>
                                                4096 bits
                                            </option>
                                        </select>
                                    </div>
                                </div>
                                
                                <div class="mt-3">
                                    <label class="form-label">DS Records for Parent Zone</label>
                                    <div class="alert alert-info">
                                        <i class="bi bi-info-circle me-2"></i>
                                        <small>Add these DS records to your parent zone (registrar) to complete DNSSEC chain of trust.</small>
                                    </div>
                                    <div class="bg-light p-3 rounded font-monospace small">
                                        ${this.currentSettings.dnssec.dsRecords.length > 0 ? 
                                            this.currentSettings.dnssec.dsRecords.map(ds => 
                                                `<div>${ds}</div>`
                                            ).join('') : 
                                            '<span class="text-muted">DS records will be generated when DNSSEC is enabled</span>'
                                        }
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Import/Export Section -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <h6 class="mb-0">
                                <i class="bi bi-arrow-down-up me-2"></i>Import/Export Zone
                            </h6>
                        </div>
                        <div class="card-body">
                            <p class="text-muted">Import and export functionality is available from the main DNS Zones page and the zone modal footer.</p>
                            <div class="d-flex gap-2">
                                <button type="button" class="btn btn-outline-primary" onclick="dnsImportModal.show()">
                                    <i class="bi bi-upload me-2"></i>Import Zone File
                                </button>
                                <div class="dropdown">
                                    <button class="btn btn-outline-primary dropdown-toggle" type="button" 
                                            data-bs-toggle="dropdown" aria-expanded="false">
                                        <i class="bi bi-download me-2"></i>Export Zone
                                    </button>
                                    <ul class="dropdown-menu">
                                        <li><a class="dropdown-item" href="#" onclick="dnsZoneSettings.exportZone('bind')">
                                            <i class="bi bi-file-text me-2"></i>BIND Format
                                        </a></li>
                                        <li><a class="dropdown-item" href="#" onclick="dnsZoneSettings.exportZone('json')">
                                            <i class="bi bi-file-code me-2"></i>JSON Format
                                        </a></li>
                                        <li><a class="dropdown-item" href="#" onclick="dnsZoneSettings.exportZone('csv')">
                                            <i class="bi bi-file-spreadsheet me-2"></i>CSV Format
                                        </a></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="d-flex justify-content-between">
                        <button type="button" class="btn btn-outline-secondary" onclick="dnsZoneSettings.resetToDefaults()">
                            <i class="bi bi-arrow-counterclockwise me-2"></i>Reset to Defaults
                        </button>
                        <div>
                            <button type="button" class="btn btn-outline-danger me-2" onclick="dnsZoneSettings.discardChanges()">
                                <i class="bi bi-x-circle me-2"></i>Discard Changes
                            </button>
                            <button type="button" class="btn btn-primary" id="saveSettingsBtn" onclick="dnsZoneSettings.saveSettings()" disabled>
                                <i class="bi bi-save me-2"></i>Save Settings
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Render IP list
     */
    renderIPList(listType, ips) {
        if (!ips || ips.length === 0) {
            return '<div class="text-muted">No IPs configured</div>';
        }

        return ips.map((ip, index) => `
            <div class="input-group mb-2">
                <input type="text" class="form-control ip-input" 
                       data-list="${listType}" data-index="${index}" 
                       value="${ip}" placeholder="IP address or subnet">
                <button class="btn btn-outline-danger" type="button" 
                        onclick="dnsZoneSettings.removeIP('${listType}', ${index})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `).join('');
    }

    /**
     * Bind event handlers
     */
    bindEvents() {
        // TTL inputs
        ['defaultTTL', 'minimumTTL', 'maximumTTL', 'negativeTTL'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('input', () => this.handleTTLChange(id));
            }
        });

        // Zone transfer toggle
        const allowTransfer = document.getElementById('allowTransfer');
        if (allowTransfer) {
            allowTransfer.addEventListener('change', (e) => {
                this.currentSettings.transfer.allowTransfer = e.target.checked;
                document.getElementById('transferSettings').classList.toggle('d-none', !e.target.checked);
                this.markAsChanged();
            });
        }

        // DNSSEC toggle
        const dnssecEnabled = document.getElementById('dnssecEnabled');
        if (dnssecEnabled) {
            dnssecEnabled.addEventListener('change', (e) => {
                this.currentSettings.dnssec.enabled = e.target.checked;
                document.getElementById('dnssecSettings').classList.toggle('d-none', !e.target.checked);
                if (e.target.checked && this.currentSettings.dnssec.dsRecords.length === 0) {
                    // Generate mock DS records
                    this.generateDSRecords();
                }
                this.markAsChanged();
            });
        }

        // DNSSEC settings
        const dnssecAlgorithm = document.getElementById('dnssecAlgorithm');
        if (dnssecAlgorithm) {
            dnssecAlgorithm.addEventListener('change', (e) => {
                this.currentSettings.dnssec.algorithm = e.target.value;
                this.generateDSRecords();
                this.markAsChanged();
            });
        }

        const dnssecKeySize = document.getElementById('dnssecKeySize');
        if (dnssecKeySize) {
            dnssecKeySize.addEventListener('change', (e) => {
                this.currentSettings.dnssec.keySize = parseInt(e.target.value);
                this.generateDSRecords();
                this.markAsChanged();
            });
        }

        // IP inputs - use event delegation
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('ip-input')) {
                const list = e.target.dataset.list;
                const index = parseInt(e.target.dataset.index);
                this.currentSettings.transfer[list][index] = e.target.value;
                this.markAsChanged();
            }
        });
    }

    /**
     * Handle TTL change
     */
    handleTTLChange(fieldId) {
        const input = document.getElementById(fieldId);
        const value = parseInt(input.value);
        
        // Map field IDs to settings paths
        const fieldMap = {
            'defaultTTL': 'default',
            'minimumTTL': 'minimum',
            'maximumTTL': 'maximum',
            'negativeTTL': 'negative'
        };
        
        const field = fieldMap[fieldId];
        if (field) {
            this.currentSettings.ttl[field] = value;
            this.markAsChanged();
        }
    }

    /**
     * Add IP to list
     */
    addIP(listType) {
        if (!this.currentSettings.transfer[listType]) {
            this.currentSettings.transfer[listType] = [];
        }
        
        this.currentSettings.transfer[listType].push('');
        this.render();
        this.bindEvents();
        this.markAsChanged();
        
        // Focus on the new input
        const inputs = document.querySelectorAll(`[data-list="${listType}"]`);
        if (inputs.length > 0) {
            inputs[inputs.length - 1].focus();
        }
    }

    /**
     * Remove IP from list
     */
    removeIP(listType, index) {
        this.currentSettings.transfer[listType].splice(index, 1);
        this.render();
        this.bindEvents();
        this.markAsChanged();
    }

    /**
     * Generate mock DS records
     */
    generateDSRecords() {
        if (this.currentSettings.dnssec.enabled) {
            // Generate mock DS records based on algorithm and key size
            const keyTag = Math.floor(Math.random() * 65535);
            const digest = this.generateRandomHex(64);
            
            this.currentSettings.dnssec.dsRecords = [
                `${this.currentZone.name} IN DS ${keyTag} ${this.getAlgorithmNumber()} 1 ${digest}`,
                `${this.currentZone.name} IN DS ${keyTag} ${this.getAlgorithmNumber()} 2 ${this.generateRandomHex(64)}`
            ];
            
            // Re-render DNSSEC section
            this.render();
            this.bindEvents();
        }
    }

    /**
     * Get algorithm number for DNSSEC
     */
    getAlgorithmNumber() {
        const algorithms = {
            'RSASHA256': 8,
            'RSASHA512': 10,
            'ECDSAP256SHA256': 13,
            'ECDSAP384SHA384': 14
        };
        return algorithms[this.currentSettings.dnssec.algorithm] || 8;
    }

    /**
     * Generate random hex string
     */
    generateRandomHex(length) {
        let result = '';
        const characters = '0123456789ABCDEF';
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * characters.length));
        }
        return result;
    }

    /**
     * Mark settings as changed
     */
    markAsChanged() {
        this.hasChanges = !this.isSettingsEqual(this.originalSettings, this.currentSettings);
        
        // Update UI
        document.getElementById('settingsChangeIndicator').classList.toggle('d-none', !this.hasChanges);
        document.getElementById('saveSettingsBtn').disabled = !this.hasChanges;
        
        // Update zone detail modal save button
        if (this.zoneDetailManager.modal) {
            const modalSaveBtn = document.getElementById('saveZoneChanges');
            if (modalSaveBtn) {
                modalSaveBtn.style.display = this.hasChanges ? 'inline-block' : 'none';
            }
        }
        
        // Notify zone detail manager
        this.zoneDetailManager.hasUnsavedChanges = this.hasChanges;
    }

    /**
     * Check if settings are equal
     */
    isSettingsEqual(a, b) {
        return JSON.stringify(a) === JSON.stringify(b);
    }

    /**
     * Save settings
     */
    async saveSettings() {
        try {
            // Show loading state
            const saveBtn = document.getElementById('saveSettingsBtn');
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
            
            // Update zone with new settings
            const updateData = {
                // Update SOA if TTL changed
                rrsets: []
            };
            
            // If default TTL changed, update SOA record
            if (this.currentSettings.ttl.default !== this.originalSettings.ttl.default ||
                this.currentSettings.ttl.minimum !== this.originalSettings.ttl.minimum) {
                
                const soaRrset = this.currentZone.rrsets.find(r => r.type === 'SOA');
                if (soaRrset) {
                    const soaData = this.parseSOARecord(soaRrset);
                    const newContent = `${soaData.primaryNs} ${soaData.email} ${soaData.serial} ${soaData.refresh} ${soaData.retry} ${soaData.expire} ${this.currentSettings.ttl.minimum}`;
                    
                    updateData.rrsets.push({
                        name: this.currentZone.name,
                        type: 'SOA',
                        ttl: this.currentSettings.ttl.default,
                        changetype: 'REPLACE',
                        records: [{
                            content: newContent,
                            disabled: false
                        }]
                    });
                }
            }
            
            // Save additional settings to zone metadata
            this.currentZone.dnssec = this.currentSettings.dnssec.enabled;
            this.currentZone.allowTransfer = this.currentSettings.transfer.allowTransfer;
            this.currentZone.allowedTransferIPs = this.currentSettings.transfer.allowedIPs;
            this.currentZone.alsoNotify = this.currentSettings.transfer.alsoNotify;
            this.currentZone.dnssecAlgorithm = this.currentSettings.dnssec.algorithm;
            this.currentZone.dnssecKeySize = this.currentSettings.dnssec.keySize;
            this.currentZone.dsRecords = this.currentSettings.dnssec.dsRecords;
            
            // Update zone via mock service
            if (updateData.rrsets.length > 0) {
                await this.dnsService.updateZone(this.currentZone.id, updateData);
            }
            
            // Update original settings
            this.originalSettings = JSON.parse(JSON.stringify(this.currentSettings));
            this.hasChanges = false;
            this.markAsChanged();
            
            // Show success
            this.showNotification('success', 'Zone settings saved successfully');
            
            // Reload zone data
            if (this.zoneDetailManager) {
                await this.zoneDetailManager.loadZone(this.currentZone.id);
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('error', 'Failed to save settings: ' + error.message);
        } finally {
            const saveBtn = document.getElementById('saveSettingsBtn');
            saveBtn.disabled = !this.hasChanges;
            saveBtn.innerHTML = '<i class="bi bi-save me-2"></i>Save Settings';
        }
    }

    /**
     * Reset to defaults
     */
    resetToDefaults() {
        if (!confirm('Reset all settings to default values? This will discard any unsaved changes.')) {
            return;
        }
        
        this.currentSettings = {
            ttl: {
                default: 3600,
                minimum: 300,
                maximum: 86400,
                negative: 3600
            },
            transfer: {
                allowTransfer: false,
                allowedIPs: [],
                notifyTargets: [],
                alsoNotify: []
            },
            dnssec: {
                enabled: false,
                algorithm: 'RSASHA256',
                keySize: 2048,
                dsRecords: []
            }
        };
        
        this.render();
        this.bindEvents();
        this.markAsChanged();
    }

    /**
     * Discard changes
     */
    discardChanges() {
        if (!this.hasChanges || confirm('Discard all unsaved changes?')) {
            this.currentSettings = JSON.parse(JSON.stringify(this.originalSettings));
            this.render();
            this.bindEvents();
            this.markAsChanged();
        }
    }

    /**
     * Export zone
     */
    async exportZone(format) {
        if (this.zoneDetailManager.importExport) {
            await this.zoneDetailManager.importExport.exportZone(this.currentZone.id, format);
        }
    }

    /**
     * Show notification
     */
    showNotification(type, message) {
        // Use zone manager's notification if available
        if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
            window.dnsZonesManager.showNotification(type, message);
        } else {
            alert(message);
        }
    }
}

// Export for use in other modules
window.DNSZoneSettingsManager = DNSZoneSettingsManager;