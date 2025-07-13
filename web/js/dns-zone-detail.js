/**
 * DNS Zone Detail Modal Manager
 * Handles the display and management of detailed zone information in a modal interface
 */

class DNSZoneDetailManager {
    constructor() {
        this.mockService = new DNSMockDataService();
        this.currentZone = null;
        this.modal = null;
        this.activeTab = 'overview';
        this.hasUnsavedChanges = false;
        this.isLoading = false;
        this.recordsManager = null;
    }

    /**
     * Show zone detail modal for a specific zone
     * @param {string} zoneId - The ID of the zone to display
     */
    async showZoneDetail(zoneId) {
        try {
            this.isLoading = true;
            await this.loadZone(zoneId);
            this.createModal();
            this.bindEvents();
            this.showTab('overview');
        } catch (error) {
            console.error('Error showing zone detail:', error);
            this.showError('Failed to load zone details');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Load zone data from mock service
     * @param {string} zoneId - Zone ID to load
     */
    async loadZone(zoneId) {
        const zone = await this.mockService.getZone(zoneId);
        if (!zone) {
            throw new Error('Zone not found');
        }
        this.currentZone = zone;
    }

    /**
     * Create and display the modal
     */
    createModal() {
        // Remove existing modal if any
        const existingModal = document.getElementById('dnsZoneDetailModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="dnsZoneDetailModal" tabindex="-1" aria-labelledby="zoneDetailModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="zoneDetailModalLabel">
                                <i class="fas fa-globe me-2"></i>${this.currentZone.name}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${this.renderTabs()}
                            <div class="tab-content mt-3" id="zoneDetailTabContent">
                                ${this.renderOverviewTab()}
                                ${this.renderRecordsTab()}
                                ${this.renderSettingsTab()}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-danger" id="deleteZoneBtn">
                                <i class="bi bi-trash me-2"></i>Delete Zone
                            </button>
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="saveZoneChanges" style="display: none;">
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Initialize Bootstrap modal
        this.modal = new bootstrap.Modal(document.getElementById('dnsZoneDetailModal'));
        this.modal.show();
        
        // Update record count
        this.updateRecordCount();
    }

    /**
     * Render tabs navigation
     */
    renderTabs() {
        return `
            <ul class="nav nav-tabs" id="zoneDetailTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" 
                            data-bs-target="#overview" type="button" role="tab" 
                            aria-controls="overview" aria-selected="true">
                        <i class="fas fa-info-circle me-2"></i>Overview
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="records-tab" data-bs-toggle="tab" 
                            data-bs-target="#records" type="button" role="tab" 
                            aria-controls="records" aria-selected="false">
                        <i class="fas fa-list me-2"></i>Records
                        <span class="badge bg-secondary ms-2" id="zone-records-count">...</span>
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="settings-tab" data-bs-toggle="tab" 
                            data-bs-target="#settings" type="button" role="tab" 
                            aria-controls="settings" aria-selected="false">
                        <i class="fas fa-cog me-2"></i>Settings
                    </button>
                </li>
            </ul>
        `;
    }

    /**
     * Render Overview tab content
     */
    renderOverviewTab() {
        const zone = this.currentZone;
        
        // Parse SOA record from rrsets
        const soaRrset = zone.rrsets ? zone.rrsets.find(rrset => rrset.type === 'SOA') : null;
        const soaData = soaRrset ? this.parseSOARecord(soaRrset) : null;
        
        return `
            <div class="tab-pane fade show active" id="overview" role="tabpanel" aria-labelledby="overview-tab">
                <div class="row">
                    <div class="col-md-6">
                        <div class="card mb-3">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-info me-2"></i>Zone Information</h6>
                            </div>
                            <div class="card-body">
                                <dl class="row mb-0">
                                    <dt class="col-sm-4">Domain Name</dt>
                                    <dd class="col-sm-8">${zone.name}</dd>
                                    
                                    <dt class="col-sm-4">Zone Kind</dt>
                                    <dd class="col-sm-8">
                                        <span class="badge bg-primary">${zone.kind}</span>
                                    </dd>
                                    
                                    <dt class="col-sm-4">DNSSEC</dt>
                                    <dd class="col-sm-8">
                                        <span class="badge bg-${zone.dnssec ? 'warning' : 'secondary'}">
                                            ${zone.dnssec ? 'Enabled' : 'Disabled'}
                                        </span>
                                    </dd>
                                    
                                    <dt class="col-sm-4">Serial</dt>
                                    <dd class="col-sm-8"><code>${zone.serial || 'N/A'}</code></dd>
                                    
                                    <dt class="col-sm-4">Account</dt>
                                    <dd class="col-sm-8">${zone.account || 'None'}</dd>
                                </dl>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-server me-2"></i>Name Servers</h6>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    ${zone.nameservers && zone.nameservers.length > 0 ? zone.nameservers.map(ns => `
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            <span><i class="fas fa-server text-muted me-2"></i>${ns}</span>
                                            <button class="btn btn-sm btn-outline-danger" onclick="alert('Remove nameserver functionality - SCRUM-99')">
                                                <i class="fas fa-times"></i>
                                            </button>
                                        </li>
                                    `).join('') : '<li class="list-group-item text-muted">No nameservers configured</li>'}
                                </ul>
                                <button class="btn btn-sm btn-outline-primary mt-2" onclick="alert('Add nameserver functionality - SCRUM-99')">
                                    <i class="fas fa-plus me-1"></i>Add Name Server
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <div class="card mb-3">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-bookmark me-2"></i>SOA (Start of Authority)</h6>
                            </div>
                            <div class="card-body">
                                ${soaData ? `
                                <dl class="row mb-0">
                                    <dt class="col-sm-5">Primary NS</dt>
                                    <dd class="col-sm-7">${soaData.primaryNs}</dd>
                                    
                                    <dt class="col-sm-5">Admin Email</dt>
                                    <dd class="col-sm-7">${soaData.email}</dd>
                                    
                                    <dt class="col-sm-5">Serial Number</dt>
                                    <dd class="col-sm-7"><code>${soaData.serial}</code></dd>
                                    
                                    <dt class="col-sm-5">Refresh</dt>
                                    <dd class="col-sm-7">${soaData.refresh} seconds</dd>
                                    
                                    <dt class="col-sm-5">Retry</dt>
                                    <dd class="col-sm-7">${soaData.retry} seconds</dd>
                                    
                                    <dt class="col-sm-5">Expire</dt>
                                    <dd class="col-sm-7">${soaData.expire} seconds</dd>
                                    
                                    <dt class="col-sm-5">Minimum TTL</dt>
                                    <dd class="col-sm-7">${soaData.ttl} seconds</dd>
                                </dl>
                                ` : '<p class="text-muted">No SOA record found</p>'}
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-heartbeat me-2"></i>Health Status</h6>
                            </div>
                            <div class="card-body">
                                ${this.renderHealthStatus()}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render health status indicator
     */
    renderHealthStatus() {
        // Simulate health check data
        const healthCheck = {
            status: 'healthy',
            lastCheck: new Date().toISOString(),
            issues: []
        };

        const statusColor = healthCheck.status === 'healthy' ? 'success' : 
                          healthCheck.status === 'warning' ? 'warning' : 'danger';
        
        const statusIcon = healthCheck.status === 'healthy' ? 'check-circle' : 
                         healthCheck.status === 'warning' ? 'exclamation-triangle' : 'times-circle';

        return `
            <div class="text-center">
                <i class="fas fa-${statusIcon} fa-3x text-${statusColor} mb-3"></i>
                <h5 class="text-${statusColor}">
                    ${healthCheck.status.charAt(0).toUpperCase() + healthCheck.status.slice(1)}
                </h5>
                <p class="text-muted mb-0">
                    Last checked: ${new Date(healthCheck.lastCheck).toLocaleString()}
                </p>
                ${healthCheck.issues.length > 0 ? `
                    <div class="alert alert-warning mt-3 text-start">
                        <h6>Issues:</h6>
                        <ul class="mb-0">
                            ${healthCheck.issues.map(issue => `<li>${issue}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Render Records tab content
     */
    renderRecordsTab() {
        return `
            <div class="tab-pane fade" id="records" role="tabpanel" aria-labelledby="records-tab">
                <!-- Records content will be managed by DNSRecordsManager -->
            </div>
        `;
    }

    /**
     * Render Settings tab content
     */
    renderSettingsTab() {
        return `
            <div class="tab-pane fade" id="settings" role="tabpanel" aria-labelledby="settings-tab">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Zone settings and configuration will be implemented in SCRUM-99
                </div>
                <div class="text-center py-5">
                    <i class="fas fa-cog fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Settings interface coming soon</p>
                </div>
            </div>
        `;
    }

    /**
     * Bind modal events
     */
    bindEvents() {
        const modalElement = document.getElementById('dnsZoneDetailModal');
        
        // Handle modal close
        modalElement.addEventListener('hidden.bs.modal', () => {
            if (this.hasUnsavedChanges) {
                if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
                    this.modal.show();
                    return;
                }
            }
            this.cleanup();
        });

        // Handle ESC key
        document.addEventListener('keydown', this.handleEscKey);

        // Handle tab switching
        const tabButtons = modalElement.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(button => {
            button.addEventListener('shown.bs.tab', (event) => {
                this.activeTab = event.target.getAttribute('aria-controls');
                
                // Initialize records manager when records tab is shown
                if (this.activeTab === 'records' && this.currentZone) {
                    if (!this.recordsManager) {
                        this.recordsManager = new DNSRecordsManager(this);
                        // Make it globally accessible for the modal
                        window.dnsRecordsManager = this.recordsManager;
                    }
                    this.recordsManager.initialize(this.currentZone);
                }
            });
        });

        // Handle save button
        const saveButton = document.getElementById('saveZoneChanges');
        if (saveButton) {
            saveButton.addEventListener('click', () => this.saveChanges());
        }
        
        // Handle delete button
        const deleteButton = document.getElementById('deleteZoneBtn');
        if (deleteButton) {
            deleteButton.addEventListener('click', () => this.deleteZone());
        }
    }

    /**
     * Handle ESC key press
     */
    handleEscKey = (event) => {
        if (event.key === 'Escape' && this.modal) {
            if (this.hasUnsavedChanges) {
                if (confirm('You have unsaved changes. Are you sure you want to close?')) {
                    this.modal.hide();
                }
                event.preventDefault();
            }
        }
    }

    /**
     * Show specific tab
     * @param {string} tabName - Name of tab to show
     */
    showTab(tabName) {
        const tabButton = document.querySelector(`#${tabName}-tab`);
        if (tabButton) {
            const tab = new bootstrap.Tab(tabButton);
            tab.show();
        }
    }

    /**
     * Save changes (placeholder)
     */
    async saveChanges() {
        try {
            // Placeholder for save functionality
            alert('Save functionality will be implemented in future stories');
            this.hasUnsavedChanges = false;
            document.getElementById('saveZoneChanges').style.display = 'none';
        } catch (error) {
            console.error('Error saving changes:', error);
            this.showError('Failed to save changes');
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, 'error');
        } else {
            alert(message);
        }
    }

    /**
     * Cleanup on modal close
     */
    cleanup() {
        document.removeEventListener('keydown', this.handleEscKey);
        this.currentZone = null;
        this.hasUnsavedChanges = false;
        this.activeTab = 'overview';
    }

    /**
     * Parse SOA record from PowerDNS rrset format
     */
    parseSOARecord(soaRrset) {
        if (!soaRrset || !soaRrset.records || soaRrset.records.length === 0) {
            return null;
        }

        // SOA content format: "primary.ns. email. serial refresh retry expire ttl"
        const content = soaRrset.records[0].content;
        const parts = content.split(' ');

        if (parts.length < 7) {
            return null;
        }

        return {
            primaryNs: parts[0],
            email: parts[1].replace('.', '@'), // Convert DNS email format
            serial: parts[2],
            refresh: parts[3],
            retry: parts[4],
            expire: parts[5],
            ttl: parts[6]
        };
    }

    /**
     * Update record count in the tab
     */
    updateRecordCount() {
        if (!this.currentZone || !this.currentZone.rrsets) return;
        
        let recordCount = 0;
        
        // Count all records except SOA and NS
        this.currentZone.rrsets.forEach(rrset => {
            if (rrset.type !== 'SOA' && rrset.type !== 'NS') {
                recordCount += rrset.records.length;
            }
        });
        
        const countElement = document.getElementById('zone-records-count');
        if (countElement) {
            countElement.textContent = recordCount;
        }
    }

    /**
     * Delete zone
     */
    async deleteZone() {
        if (!this.currentZone) return;
        
        // Close this modal first
        this.modal.hide();
        
        // Wait a bit for modal to close
        setTimeout(() => {
            // Use the zones manager delete function which has the confirmation
            if (window.dnsZonesManager) {
                window.dnsZonesManager.deleteZone(this.currentZone.id);
            }
        }, 300);
    }
}

// Export for use in other modules
window.DNSZoneDetailManager = DNSZoneDetailManager;