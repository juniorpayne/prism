/**
 * DNS Zone Detail Modal Manager
 * Handles the display and management of detailed zone information in a modal interface
 */

class DNSZoneDetailManager {
    constructor() {
        // Use service adapter instead of direct mock service
        this.dnsService = DNSServiceFactory.getAdapter();
        this.importExport = new DNSImportExport();
        this.currentZone = null;
        this.modal = null;
        this.activeTab = 'overview';
        this.hasUnsavedChanges = false;
        this.isLoading = false;
        this.recordsManager = null;
        this.settingsManager = null;
        this.loadingStates = new Map(); // Track loading states for different operations
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
     * Load zone data using service adapter
     * @param {string} zoneId - Zone ID to load
     */
    async loadZone(zoneId) {
        this.setLoadingState('zone', true);
        try {
            const zone = await this.dnsService.getZone(zoneId);
            if (!zone) {
                throw new Error('Zone not found');
            }
        
            // Enrich zone with hierarchy information from zones manager
            if (window.dnsZonesManager && window.dnsZonesManager.zones) {
                const enrichedZone = window.dnsZonesManager.zones.find(z => z.id === zoneId);
                if (enrichedZone) {
                    // Copy hierarchy properties from the enriched zone
                    zone.isSubdomain = enrichedZone.isSubdomain;
                    zone.parentZone = enrichedZone.parentZone;
                    zone.childCount = enrichedZone.childCount;
                    zone.isExpanded = enrichedZone.isExpanded;
                    zone.isVisible = enrichedZone.isVisible;
                }
            }
            
            this.currentZone = zone;
        } catch (error) {
            console.error('Error loading zone:', error);
            throw error;
        } finally {
            this.setLoadingState('zone', false);
        }
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
                            <div class="w-100">
                                <div class="d-flex justify-content-between align-items-center">
                                    <h5 class="modal-title" id="zoneDetailModalLabel">
                                        <i class="fas fa-globe me-2"></i>${this.currentZone.name}
                                    </h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                </div>
                                ${this.renderBreadcrumb()}
                            </div>
                        </div>
                        <div class="modal-body">
                            ${this.renderTabs()}
                            <div class="tab-content mt-3" id="zoneDetailTabContent">
                                ${this.renderOverviewTab()}
                                ${this.renderRecordsTab()}
                                ${this.renderSubdomainsTab()}
                                ${this.renderSettingsTab()}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <div class="me-auto">
                                <div class="dropdown">
                                    <button class="btn btn-outline-primary dropdown-toggle" type="button" 
                                            data-bs-toggle="dropdown" aria-expanded="false">
                                        <i class="bi bi-download me-2"></i>Export Zone
                                    </button>
                                    <ul class="dropdown-menu">
                                        <li><a class="dropdown-item export-zone" href="#" data-format="bind">
                                            <i class="bi bi-file-text me-2"></i>BIND Format
                                        </a></li>
                                        <li><a class="dropdown-item export-zone" href="#" data-format="json">
                                            <i class="bi bi-file-code me-2"></i>JSON Format
                                        </a></li>
                                        <li><a class="dropdown-item export-zone" href="#" data-format="csv">
                                            <i class="bi bi-file-spreadsheet me-2"></i>CSV Format
                                        </a></li>
                                    </ul>
                                </div>
                            </div>
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
                    <button class="nav-link" id="subdomains-tab" data-bs-toggle="tab" 
                            data-bs-target="#subdomains" type="button" role="tab" 
                            aria-controls="subdomains" aria-selected="false">
                        <i class="fas fa-sitemap me-2"></i>Subdomains
                        <span class="badge bg-secondary ms-2" id="zone-subdomains-count">...</span>
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
     * Render breadcrumb navigation for modal
     */
    renderBreadcrumb() {
        if (!this.currentZone) return '';
        
        // Use the global breadcrumb navigation if available
        if (window.dnsBreadcrumbNav) {
            return window.dnsBreadcrumbNav.showInModal(this.currentZone);
        }
        
        // Fallback simple breadcrumb if navigation not available
        return `
            <nav aria-label="DNS zone navigation" class="mt-2">
                <ol class="breadcrumb mb-0 bg-light p-2 rounded">
                    <li class="breadcrumb-item">
                        <a href="#" class="text-decoration-none" onclick="bootstrap.Modal.getInstance(document.getElementById('dnsZoneDetailModal')).hide(); return false;">
                            <i class="bi bi-house-door me-1"></i>All Zones
                        </a>
                    </li>
                    <li class="breadcrumb-item active" aria-current="page">
                        <i class="bi bi-globe2 me-1"></i>${this.currentZone.name.replace(/\.$/, '')}
                    </li>
                </ol>
            </nav>
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
                        ${this.renderHierarchyInfo(zone)}
                        
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
                                        ${this.getInheritanceIndicator('kind')}
                                    </dd>
                                    
                                    <dt class="col-sm-4">DNSSEC</dt>
                                    <dd class="col-sm-8">
                                        <span class="badge bg-${zone.dnssec ? 'warning' : 'secondary'}">
                                            ${zone.dnssec ? 'Enabled' : 'Disabled'}
                                        </span>
                                        ${this.getInheritanceIndicator('dnssec')}
                                    </dd>
                                    
                                    <dt class="col-sm-4">Serial</dt>
                                    <dd class="col-sm-8">
                                        <code>${zone.serial || 'N/A'}</code>
                                        ${this.getInheritanceIndicator('serial')}
                                    </dd>
                                    
                                    <dt class="col-sm-4">Account</dt>
                                    <dd class="col-sm-8">
                                        ${zone.account || 'None'}
                                        ${this.getInheritanceIndicator('account')}
                                    </dd>
                                </dl>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0"><i class="fas fa-server me-2"></i>Name Servers</h6>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush" id="nameserversList">
                                    ${zone.nameservers && zone.nameservers.length > 0 ? zone.nameservers.map(ns => `
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            <span><i class="fas fa-server text-muted me-2"></i>${ns}</span>
                                            <button class="btn btn-sm btn-outline-danger" onclick="window.dnsZoneDetailManager.removeNameserver('${ns}')">
                                                <i class="fas fa-times"></i>
                                            </button>
                                        </li>
                                    `).join('') : '<li class="list-group-item text-muted">No nameservers configured</li>'}
                                </ul>
                                <button class="btn btn-sm btn-outline-primary mt-2" onclick="window.dnsZoneDetailManager.showAddNameserverModal()">
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
     * Render Subdomains tab content
     */
    renderSubdomainsTab() {
        return `
            <div class="tab-pane fade" id="subdomains" role="tabpanel" aria-labelledby="subdomains-tab">
                <!-- Subdomains content will be managed by SubdomainManager -->
                <div id="subdomains-content">
                    <div class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading subdomains...</span>
                        </div>
                        <p class="mt-2 text-muted">Loading subdomains...</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render Settings tab content
     */
    renderSettingsTab() {
        return `
            <div class="tab-pane fade" id="settings" role="tabpanel" aria-labelledby="settings-tab">
                <!-- Settings content will be managed by DNSZoneSettingsManager -->
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
                
                // Initialize subdomains manager when subdomains tab is shown
                if (this.activeTab === 'subdomains' && this.currentZone) {
                    if (!this.subdomainManager) {
                        this.subdomainManager = new DNSSubdomainManager(this);
                        // Make it globally accessible for the modal
                        window.dnsSubdomainManager = this.subdomainManager;
                    }
                    this.subdomainManager.initialize(this.currentZone);
                }
                
                // Initialize settings manager when settings tab is shown
                if (this.activeTab === 'settings' && this.currentZone) {
                    if (!this.settingsManager) {
                        this.settingsManager = new DNSZoneSettingsManager(this);
                        // Make it globally accessible for the modal
                        window.dnsZoneSettings = this.settingsManager;
                    }
                    this.settingsManager.initialize(this.currentZone);
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
        
        // Handle export buttons
        document.querySelectorAll('.export-zone').forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const format = e.target.closest('.export-zone').dataset.format;
                await this.exportZone(format);
            });
        });
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
        this.recordsManager = null;
        this.subdomainManager = null;
        this.settingsManager = null;
        window.dnsRecordsManager = null;
        window.dnsSubdomainManager = null;
        window.dnsZoneSettings = null;
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

    /**
     * Export zone in specified format
     */
    async exportZone(format) {
        try {
            if (!this.currentZone) return;
            
            await this.importExport.exportZone(this.currentZone.id, format);
            
            // Show success notification
            if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
                window.dnsZonesManager.showNotification('success', 
                    `Zone ${this.currentZone.name} exported successfully in ${format.toUpperCase()} format.`);
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showError('Failed to export zone: ' + error.message);
        }
    }

    /**
     * Show modal to add nameserver
     */
    showAddNameserverModal() {
        const modalHtml = `
            <div class="modal fade" id="addNameserverModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-plus-circle me-2"></i>Add Name Server
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="newNameserver" class="form-label">Name Server</label>
                                <input type="text" class="form-control" id="newNameserver" 
                                       placeholder="ns1.example.com." 
                                       pattern="^([a-zA-Z0-9]([a-zA-Z0-9\\-]{0,61}[a-zA-Z0-9])?\\.)+[a-zA-Z]{2,}\\.$"
                                       required>
                                <div class="form-text">
                                    Enter the fully qualified domain name ending with a dot (e.g., ns1.example.com.)
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="window.dnsZoneDetailManager.addNameserver()">
                                <i class="bi bi-plus-circle me-2"></i>Add Name Server
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existing = document.getElementById('addNameserverModal');
        if (existing) existing.remove();

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('addNameserverModal'));
        modal.show();

        // Focus on input when modal is shown
        document.getElementById('addNameserverModal').addEventListener('shown.bs.modal', () => {
            document.getElementById('newNameserver').focus();
        });

        // Handle enter key in input
        document.getElementById('newNameserver').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.addNameserver();
            }
        });
    }

    /**
     * Add a new nameserver
     */
    async addNameserver() {
        const input = document.getElementById('newNameserver');
        const nameserver = input.value.trim();

        // Validate nameserver
        if (!nameserver) {
            input.classList.add('is-invalid');
            return;
        }

        // Ensure it ends with a dot
        const nsWithDot = nameserver.endsWith('.') ? nameserver : nameserver + '.';

        // Check if already exists
        if (this.currentZone.nameservers && this.currentZone.nameservers.includes(nsWithDot)) {
            alert('This nameserver already exists!');
            return;
        }

        try {
            // Update nameservers array
            if (!this.currentZone.nameservers) {
                this.currentZone.nameservers = [];
            }
            this.currentZone.nameservers.push(nsWithDot);

            // Save to mock service
            await this.dnsService.updateZone(this.currentZone.id, {
                nameservers: this.currentZone.nameservers
            });

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addNameserverModal'));
            modal.hide();

            // Update UI
            this.updateNameserversList();

            // Show success
            if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
                window.dnsZonesManager.showNotification('success', `Name server ${nsWithDot} added successfully.`);
            }
        } catch (error) {
            console.error('Error adding nameserver:', error);
            this.showError('Failed to add nameserver: ' + error.message);
        }
    }

    /**
     * Remove a nameserver
     */
    async removeNameserver(nameserver) {
        // Confirm removal
        if (!confirm(`Are you sure you want to remove nameserver ${nameserver}?`)) {
            return;
        }

        // Check if it's the last nameserver
        if (this.currentZone.nameservers && this.currentZone.nameservers.length <= 2) {
            alert('A zone must have at least 2 nameservers. Add another nameserver before removing this one.');
            return;
        }

        try {
            // Update nameservers array
            this.currentZone.nameservers = this.currentZone.nameservers.filter(ns => ns !== nameserver);

            // Save to mock service
            await this.dnsService.updateZone(this.currentZone.id, {
                nameservers: this.currentZone.nameservers
            });

            // Update UI
            this.updateNameserversList();

            // Show success
            if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
                window.dnsZonesManager.showNotification('success', `Name server ${nameserver} removed successfully.`);
            }
        } catch (error) {
            console.error('Error removing nameserver:', error);
            this.showError('Failed to remove nameserver: ' + error.message);
        }
    }

    /**
     * Update nameservers list in UI
     */
    updateNameserversList() {
        const listElement = document.getElementById('nameserversList');
        if (!listElement) return;

        if (this.currentZone.nameservers && this.currentZone.nameservers.length > 0) {
            listElement.innerHTML = this.currentZone.nameservers.map(ns => `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-server text-muted me-2"></i>${ns}</span>
                    <button class="btn btn-sm btn-outline-danger" onclick="window.dnsZoneDetailManager.removeNameserver('${ns}')">
                        <i class="fas fa-times"></i>
                    </button>
                </li>
            `).join('');
        } else {
            listElement.innerHTML = '<li class="list-group-item text-muted">No nameservers configured</li>';
        }
    }

    /**
     * Render hierarchy information card
     */
    renderHierarchyInfo(zone) {
        // Only show hierarchy info for subdomains
        if (!zone.isSubdomain && !zone.parentZone) {
            return '';
        }

        // Get parent zone info
        const parentZone = this.getParentZone(zone);
        const hierarchyChain = this.buildHierarchyChain(zone);

        return `
            <div class="card mb-3 border-info">
                <div class="card-header bg-info text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-sitemap me-2"></i>Zone Hierarchy
                    </h6>
                </div>
                <div class="card-body">
                    <dl class="row mb-3">
                        <dt class="col-sm-4">Zone Type</dt>
                        <dd class="col-sm-8">
                            <span class="badge bg-secondary">
                                <i class="bi bi-folder me-1"></i>Subdomain
                            </span>
                        </dd>
                        
                        ${parentZone ? `
                            <dt class="col-sm-4">Parent Zone</dt>
                            <dd class="col-sm-8">
                                <a href="#" class="text-decoration-none" 
                                   onclick="window.dnsZoneDetailManager.viewParentZone('${parentZone.id}'); return false;">
                                    <i class="bi bi-${parentZone.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                                    ${parentZone.name.replace(/\.$/, '')}
                                </a>
                                <button class="btn btn-sm btn-outline-primary ms-2" 
                                        onclick="window.dnsZoneDetailManager.viewParentZone('${parentZone.id}')">
                                    <i class="bi bi-eye me-1"></i>View Parent
                                </button>
                            </dd>
                        ` : ''}
                        
                        <dt class="col-sm-4">Hierarchy Path</dt>
                        <dd class="col-sm-8">
                            <nav aria-label="Zone hierarchy">
                                <ol class="breadcrumb mb-0 bg-light">
                                    ${hierarchyChain.map((z, index) => {
                                        const isLast = index === hierarchyChain.length - 1;
                                        const zoneName = z.name.replace(/\.$/, '');
                                        
                                        if (isLast) {
                                            return `
                                                <li class="breadcrumb-item active" aria-current="page">
                                                    <i class="bi bi-${z.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                                                    ${zoneName}
                                                </li>
                                            `;
                                        } else {
                                            return `
                                                <li class="breadcrumb-item">
                                                    <a href="#" onclick="window.dnsZoneDetailManager.viewParentZone('${z.id}'); return false;">
                                                        <i class="bi bi-${z.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                                                        ${zoneName}
                                                    </a>
                                                </li>
                                            `;
                                        }
                                    }).join('')}
                                </ol>
                            </nav>
                        </dd>
                    </dl>
                    
                    ${this.renderInheritanceInfo(zone, parentZone)}
                </div>
            </div>
        `;
    }

    /**
     * Render inheritance information
     */
    renderInheritanceInfo(zone, parentZone) {
        if (!parentZone) return '';

        const inheritedSettings = this.getInheritedSettings(zone, parentZone);
        
        if (inheritedSettings.length === 0) {
            return `
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle me-2"></i>
                    This zone uses its own settings (no inheritance from parent zone).
                </div>
            `;
        }

        return `
            <div class="mt-3">
                <h6 class="text-muted mb-2">
                    <i class="bi bi-arrow-down-circle me-1"></i>Inherited Settings
                </h6>
                <div class="list-group list-group-flush">
                    ${inheritedSettings.map(setting => `
                        <div class="list-group-item d-flex justify-content-between align-items-center py-2">
                            <span>
                                <i class="bi bi-arrow-down text-success me-2"></i>
                                ${setting.name}: <strong>${setting.value}</strong>
                            </span>
                            <span class="badge bg-success" 
                                  title="Inherited from ${parentZone.name}">
                                Inherited
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Get inheritance indicator for a field
     */
    getInheritanceIndicator(fieldName) {
        if (!this.currentZone.isSubdomain && !this.currentZone.parentZone) {
            return '';
        }

        const parentZone = this.getParentZone(this.currentZone);
        if (!parentZone) return '';

        const isInherited = this.isSettingInherited(fieldName, this.currentZone, parentZone);
        
        if (isInherited) {
            return `
                <i class="bi bi-arrow-down-circle text-success ms-2" 
                   title="Inherited from ${parentZone.name.replace(/\.$/, '')}"
                   data-bs-toggle="tooltip"></i>
            `;
        } else {
            return `
                <i class="bi bi-pencil-square text-warning ms-2" 
                   title="Overridden (custom value for this zone)"
                   data-bs-toggle="tooltip"></i>
            `;
        }
    }

    /**
     * Get parent zone object
     */
    getParentZone(zone) {
        if (!zone.parentZone && window.dnsZonesManager) {
            // Try to determine parent from zones manager
            const zones = window.dnsZonesManager.zones || [];
            const cleanName = zone.name.endsWith('.') ? zone.name.slice(0, -1) : zone.name;
            const parts = cleanName.split('.');
            
            if (parts.length > 2) {
                const potentialParentClean = parts.slice(1).join('.');
                const potentialParent = potentialParentClean + '.';
                return zones.find(z => z.name === potentialParent);
            }
        }
        
        if (window.dnsZonesManager && window.dnsZonesManager.zones) {
            return window.dnsZonesManager.zones.find(z => z.name === zone.parentZone);
        }
        
        return null;
    }

    /**
     * Build hierarchy chain from root to current zone
     */
    buildHierarchyChain(zone) {
        const chain = [];
        let currentZone = zone;
        
        // Add current zone
        chain.unshift(currentZone);
        
        // Walk up the hierarchy
        while (currentZone && currentZone.parentZone) {
            const parent = this.getParentZone(currentZone);
            if (parent && !chain.find(z => z.id === parent.id)) {
                chain.unshift(parent);
                currentZone = parent;
            } else {
                break; // Avoid infinite loops
            }
        }
        
        return chain;
    }

    /**
     * Get list of inherited settings
     */
    getInheritedSettings(zone, parentZone) {
        const inherited = [];
        
        // Check nameservers inheritance
        if (this.arraysEqual(zone.nameservers, parentZone.nameservers)) {
            inherited.push({
                name: 'Name Servers',
                value: zone.nameservers ? zone.nameservers.length + ' servers' : 'None'
            });
        }
        
        // Check zone kind inheritance
        if (zone.kind === parentZone.kind) {
            inherited.push({
                name: 'Zone Kind',
                value: zone.kind
            });
        }
        
        // Check account inheritance
        if (zone.account === parentZone.account) {
            inherited.push({
                name: 'Account',
                value: zone.account || 'None'
            });
        }
        
        return inherited;
    }

    /**
     * Check if a specific setting is inherited
     */
    isSettingInherited(fieldName, zone, parentZone) {
        switch (fieldName) {
            case 'kind':
                return zone.kind === parentZone.kind;
            case 'account':
                return zone.account === parentZone.account;
            case 'dnssec':
                return zone.dnssec === parentZone.dnssec;
            case 'nameservers':
                return this.arraysEqual(zone.nameservers, parentZone.nameservers);
            default:
                return false;
        }
    }

    /**
     * Navigate to parent zone
     */
    async viewParentZone(parentZoneId) {
        // Close current modal
        if (this.modal) {
            this.modal.hide();
        }
        
        // Wait a bit for modal to close, then open parent zone
        setTimeout(() => {
            if (window.dnsZonesManager) {
                window.dnsZonesManager.showZoneDetail(parentZoneId);
            }
        }, 300);
    }

    /**
     * Helper function to compare arrays
     */
    arraysEqual(a, b) {
        if (!a && !b) return true;
        if (!a || !b) return false;
        if (a.length !== b.length) return false;
        
        const sortedA = [...a].sort();
        const sortedB = [...b].sort();
        
        return sortedA.every((val, index) => val === sortedB[index]);
    }

    /**
     * Set loading state for an operation
     * @param {string} operation - Operation identifier
     * @param {boolean} isLoading - Loading state
     */
    setLoadingState(operation, isLoading) {
        this.loadingStates.set(operation, isLoading);
        
        // Update UI loading indicators
        if (operation === 'zone') {
            const modal = document.getElementById('dnsZoneDetailModal');
            if (modal) {
                if (isLoading) {
                    this.showModalLoading(modal);
                } else {
                    this.hideModalLoading(modal);
                }
            }
        }
    }

    /**
     * Show loading overlay in modal
     * @param {Element} modal - Modal element
     */
    showModalLoading(modal) {
        const existingOverlay = modal.querySelector('.loading-overlay');
        if (existingOverlay) return;
        
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.cssText = 'background: rgba(255,255,255,0.8); z-index: 1050;';
        overlay.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="mt-2">Loading zone details...</div>
            </div>
        `;
        
        modal.querySelector('.modal-content').style.position = 'relative';
        modal.querySelector('.modal-content').appendChild(overlay);
    }

    /**
     * Hide loading overlay in modal
     * @param {Element} modal - Modal element
     */
    hideModalLoading(modal) {
        const overlay = modal.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
}

// Export for use in other modules
window.DNSZoneDetailManager = DNSZoneDetailManager;