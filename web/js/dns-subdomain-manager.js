/**
 * DNS Subdomain Manager Component
 * Manages the display and manipulation of child zones within the zone detail modal
 */

class DNSSubdomainManager {
    constructor(zoneDetailManager) {
        this.zoneDetailManager = zoneDetailManager;
        // Use service adapter from zone detail manager
        this.dnsService = zoneDetailManager.dnsService || DNSServiceFactory.getAdapter();
        this.currentZone = null;
        this.childZones = [];
        this.isLoading = false;
        this.loadingStates = new Map(); // Track loading states for operations
    }

    /**
     * Initialize the subdomain manager for a specific zone
     * @param {Object} zone - The parent zone object
     */
    async initialize(zone) {
        this.currentZone = zone;
        await this.loadChildZones();
        this.render();
        this.updateSubdomainCount();
    }

    /**
     * Load all child zones for the current zone
     */
    async loadChildZones() {
        if (!this.currentZone) return;

        this.isLoading = true;
        this.childZones = [];

        try {
            // Get all zones from zones manager and filter for children
            if (window.dnsZonesManager && window.dnsZonesManager.zones) {
                const allZones = window.dnsZonesManager.zones;
                
                // Find all descendants (not just direct children)
                this.childZones = allZones.filter(zone => {
                    return this.isDescendantDomain(zone.name, this.currentZone.name);
                });

                // Get additional details for each child zone
                for (const childZone of this.childZones) {
                    try {
                        const fullZone = await this.dnsService.getZone(childZone.id);
                        if (fullZone) {
                            // Count records (excluding SOA and NS)
                            let recordCount = 0;
                            if (fullZone.rrsets) {
                                fullZone.rrsets.forEach(rrset => {
                                    if (rrset.type !== 'SOA' && rrset.type !== 'NS') {
                                        recordCount += rrset.records.length;
                                    }
                                });
                            }
                            childZone.recordCount = recordCount;
                            childZone.status = 'Active'; // PowerDNS doesn't have zone status
                        }
                    } catch (error) {
                        console.error(`Error loading details for child zone ${childZone.id}:`, error);
                        childZone.recordCount = 0;
                        childZone.status = 'Unknown';
                    }
                }
            }
        } catch (error) {
            console.error('Error loading child zones:', error);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Check if a domain is a descendant of another domain (any level)
     */
    isDescendantDomain(childName, parentName) {
        if (!childName || !parentName) return false;
        
        // Remove trailing dots for comparison
        const child = childName.endsWith('.') ? childName.slice(0, -1) : childName;
        const parent = parentName.endsWith('.') ? parentName.slice(0, -1) : parentName;
        
        // Check if child ends with parent domain and is not the same
        return child !== parent && child.endsWith('.' + parent);
    }
    
    /**
     * Get the depth level of a subdomain relative to parent
     */
    getRelativeDepth(childName, parentName) {
        const child = childName.endsWith('.') ? childName.slice(0, -1) : childName;
        const parent = parentName.endsWith('.') ? parentName.slice(0, -1) : parentName;
        
        const childParts = child.split('.');
        const parentParts = parent.split('.');
        
        return childParts.length - parentParts.length;
    }

    /**
     * Render the subdomains tab content
     */
    render() {
        const container = document.getElementById('subdomains-content');
        if (!container) return;

        if (this.isLoading) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading subdomains...</span>
                    </div>
                    <p class="mt-2 text-muted">Loading subdomains...</p>
                </div>
            `;
            return;
        }

        if (this.childZones.length === 0) {
            container.innerHTML = this.renderEmptyState();
        } else {
            container.innerHTML = this.renderSubdomainsList();
        }
    }

    /**
     * Render empty state when no subdomains exist
     */
    renderEmptyState() {
        return `
            <div class="text-center py-5">
                <i class="bi bi-folder-plus fs-1 text-muted mb-3"></i>
                <h5 class="text-muted">No Subdomains</h5>
                <p class="text-muted mb-4">
                    This zone doesn't have any subdomains yet.<br>
                    Create your first subdomain to get started.
                </p>
                <button class="btn btn-primary" onclick="window.dnsSubdomainManager.showCreateSubdomainModal()">
                    <i class="bi bi-plus-circle me-2"></i>Create Subdomain
                </button>
            </div>
        `;
    }

    /**
     * Render the list of subdomains
     */
    renderSubdomainsList() {
        // Sort zones by name to ensure proper hierarchy display
        const sortedZones = [...this.childZones].sort((a, b) => a.name.localeCompare(b.name));
        
        return `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">
                    <i class="bi bi-folder me-2"></i>
                    Subdomains (${this.childZones.length})
                </h6>
                <button class="btn btn-primary btn-sm" onclick="window.dnsSubdomainManager.showCreateSubdomainModal()">
                    <i class="bi bi-plus-circle me-1"></i>Create Subdomain
                </button>
            </div>

            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Subdomain Name</th>
                            <th>Status</th>
                            <th>Records</th>
                            <th>Kind</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sortedZones.map(zone => this.renderSubdomainRow(zone)).join('')}
                    </tbody>
                </table>
            </div>

            <div class="mt-3">
                <small class="text-muted">
                    <i class="bi bi-info-circle me-1"></i>
                    All subdomains under <strong>${this.currentZone.name.replace(/\.$/, '')}</strong>
                </small>
            </div>
        `;
    }

    /**
     * Render a single subdomain row
     */
    renderSubdomainRow(zone) {
        const zoneName = zone.name.replace(/\.$/, ''); // Remove trailing dot for display
        const depth = this.getRelativeDepth(zone.name, this.currentZone.name);
        const indent = depth * 20; // 20px per level

        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center" style="padding-left: ${indent}px;">
                        <i class="bi bi-folder text-primary me-2"></i>
                        <div>
                            <div class="fw-medium">${this.escapeHtml(zoneName)}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge bg-success">${zone.status || 'Active'}</span>
                </td>
                <td>
                    <span class="badge bg-info">${zone.recordCount || 0}</span>
                </td>
                <td>
                    <span class="badge bg-primary">${zone.kind || 'Native'}</span>
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" 
                                onclick="window.dnsSubdomainManager.viewSubdomain('${zone.id}')"
                                title="View Details">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-outline-secondary dropdown-toggle dropdown-toggle-split" 
                                data-bs-toggle="dropdown" aria-expanded="false">
                            <span class="visually-hidden">Toggle Dropdown</span>
                        </button>
                        <ul class="dropdown-menu">
                            <li>
                                <a class="dropdown-item" href="#" 
                                   onclick="window.dnsSubdomainManager.viewSubdomain('${zone.id}'); return false;">
                                    <i class="bi bi-eye me-2"></i>View Details
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item" href="#" 
                                   onclick="window.dnsSubdomainManager.editSubdomain('${zone.id}'); return false;">
                                    <i class="bi bi-pencil me-2"></i>Edit Zone
                                </a>
                            </li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a class="dropdown-item text-danger" href="#" 
                                   onclick="window.dnsSubdomainManager.deleteSubdomain('${zone.id}'); return false;">
                                    <i class="bi bi-trash me-2"></i>Delete Subdomain
                                </a>
                            </li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Update the subdomain count badge in the tab
     */
    updateSubdomainCount() {
        const countElement = document.getElementById('zone-subdomains-count');
        if (countElement) {
            countElement.textContent = this.childZones.length;
            
            // Hide badge if no subdomains
            if (this.childZones.length === 0) {
                countElement.style.display = 'none';
            } else {
                countElement.style.display = 'inline';
            }
        }
    }

    /**
     * Show create subdomain modal
     */
    showCreateSubdomainModal() {
        if (!this.currentZone) return;
        
        // Close current zone detail modal
        if (this.zoneDetailManager && this.zoneDetailManager.modal) {
            this.zoneDetailManager.modal.hide();
        }
        
        // Wait for modal to close, then open create zone wizard with parent pre-filled
        setTimeout(() => {
            if (window.DNSZoneWizardV2) {
                const wizard = new DNSZoneWizardV2();
                // Pre-fill parent zone if the wizard supports it
                wizard.show({
                    parentZone: this.currentZone.name,
                    suggestedName: `subdomain.${this.currentZone.name.replace(/\.$/, '')}.`,
                    zones: window.dnsZonesManager?.zones || []
                });
            } else {
                alert('Zone creation wizard not available. Please use the main Create Zone button.');
            }
        }, 300);
    }

    /**
     * View subdomain details
     */
    viewSubdomain(subdomainId) {
        // Close current modal and open subdomain details
        if (this.zoneDetailManager && this.zoneDetailManager.modal) {
            this.zoneDetailManager.modal.hide();
        }
        
        setTimeout(() => {
            if (window.dnsZonesManager) {
                window.dnsZonesManager.showZoneDetail(subdomainId);
            }
        }, 300);
    }

    /**
     * Edit subdomain (placeholder)
     */
    editSubdomain(subdomainId) {
        console.log('Edit subdomain:', subdomainId);
        alert('Edit subdomain functionality coming in future updates!');
    }

    /**
     * Delete subdomain
     */
    async deleteSubdomain(subdomainId) {
        if (!confirm('Are you sure you want to delete this subdomain? This action cannot be undone.')) {
            return;
        }

        try {
            // Find the subdomain zone
            const subdomain = this.childZones.find(z => z.id === subdomainId);
            if (!subdomain) {
                throw new Error('Subdomain not found');
            }

            // Delete the zone
            await this.dnsService.deleteZone(subdomainId);
            
            // Show success notification
            if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
                window.dnsZonesManager.showNotification('success', 
                    `Subdomain ${subdomain.name} has been deleted successfully.`);
            }
            
            // Reload the subdomains list
            await this.loadChildZones();
            this.render();
            this.updateSubdomainCount();
            
            // Refresh the main zones list
            if (window.dnsZonesManager) {
                window.dnsZonesManager.loadZones();
            }
            
        } catch (error) {
            console.error('Error deleting subdomain:', error);
            if (window.dnsZonesManager && window.dnsZonesManager.showNotification) {
                window.dnsZonesManager.showNotification('error', 
                    'Failed to delete subdomain: ' + error.message);
            }
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Refresh the subdomains list
     */
    async refresh() {
        await this.loadChildZones();
        this.render();
        this.updateSubdomainCount();
    }
}

// Export for use in other modules
window.DNSSubdomainManager = DNSSubdomainManager;