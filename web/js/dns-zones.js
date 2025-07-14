/**
 * DNS Zones Management Module
 * Handles the DNS zones landing page with stats, table, search, and sorting
 */

class DNSZonesManager {
    constructor() {
        this.mockService = new DNSMockDataService();
        this.searchFilter = new DNSSearchFilter();
        this.importExport = new DNSImportExport();
        this.zones = [];
        this.filteredZones = [];
        this.currentSort = { column: 'name', direction: 'asc' };
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.searchTerm = '';
        this.selectedZones = new Set();
        this.initialize();
    }

    initialize() {
        // Set up event listeners when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        // Listen for navigation to DNS zones
        document.addEventListener('navigateTo', (e) => {
            if (e.detail && e.detail.view === 'dns-zones') {
                this.showDNSZonesView();
            }
        });

        // Check if we're already on the DNS zones page
        if (window.location.pathname === '/dns-zones') {
            this.showDNSZonesView();
        }
    }

    async showDNSZonesView() {
        const container = document.getElementById('dns-zones-view');
        if (!container) return;

        // Build the UI
        container.innerHTML = this.buildDNSZonesHTML();
        
        // Attach event handlers
        this.attachEventHandlers();
        
        // Load data
        await this.loadZones();
    }

    buildDNSZonesHTML() {
        return `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h2><i class="bi bi-diagram-3"></i> DNS Zones</h2>
                        <div class="btn-group">
                            <button class="btn btn-outline-primary" id="import-zones-btn">
                                <i class="bi bi-upload"></i> Import
                            </button>
                            <button class="btn btn-outline-primary dropdown-toggle" 
                                    data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-download"></i> Export
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item export-option" href="#" data-format="bind">
                                    <i class="bi bi-file-text me-2"></i>BIND Format
                                </a></li>
                                <li><a class="dropdown-item export-option" href="#" data-format="json">
                                    <i class="bi bi-file-code me-2"></i>JSON Format
                                </a></li>
                                <li><a class="dropdown-item export-option" href="#" data-format="csv">
                                    <i class="bi bi-file-spreadsheet me-2"></i>CSV Format
                                </a></li>
                            </ul>
                            <button class="btn btn-primary" id="create-zone-btn">
                                <i class="bi bi-plus-circle"></i> Create Zone
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Stats Cards -->
            <div class="row mb-4">
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h4 class="mb-0" id="total-zones">0</h4>
                                    <small>Total Zones</small>
                                </div>
                                <i class="bi bi-globe fs-1 opacity-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card bg-success text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h4 class="mb-0" id="active-zones">0</h4>
                                    <small>Active Zones</small>
                                </div>
                                <i class="bi bi-check-circle fs-1 opacity-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card bg-info text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h4 class="mb-0" id="total-records">0</h4>
                                    <small>Total Records</small>
                                </div>
                                <i class="bi bi-list-ul fs-1 opacity-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h4 class="mb-0" id="recent-changes">0</h4>
                                    <small>Recent Changes</small>
                                </div>
                                <i class="bi bi-clock-history fs-1 opacity-50"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Search and Filter -->
            ${this.searchFilter.createFilterUI()}

            <!-- Zones Table -->
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-body">
                            <!-- Loading State -->
                            <div id="zones-loading" class="text-center py-5">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 text-muted">Loading DNS zones...</p>
                            </div>

                            <!-- Table -->
                            <div id="zones-table-container" style="display: none;">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead>
                                            <tr>
                                                <th style="width: 40px;">
                                                    <input type="checkbox" id="selectAllZones" class="form-check-input">
                                                </th>
                                                <th class="sortable" data-sort="name">
                                                    Zone Name <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th class="sortable" data-sort="dnssec">
                                                    Status <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th class="sortable" data-sort="kind">
                                                    Kind <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th>Records</th>
                                                <th>Name Servers</th>
                                                <th class="sortable" data-sort="serial">
                                                    Serial <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="zones-tbody">
                                            <!-- Zones will be populated here -->
                                        </tbody>
                                    </table>
                                </div>

                                <!-- Pagination -->
                                <div class="d-flex justify-content-between align-items-center mt-3">
                                    <div>
                                        <select class="form-select form-select-sm" id="items-per-page" style="width: auto;">
                                            <option value="10">10 per page</option>
                                            <option value="25">25 per page</option>
                                            <option value="50">50 per page</option>
                                        </select>
                                    </div>
                                    <nav>
                                        <ul class="pagination pagination-sm mb-0" id="pagination">
                                            <!-- Pagination will be populated here -->
                                        </ul>
                                    </nav>
                                </div>
                            </div>

                            <!-- Empty State -->
                            <div id="zones-empty" class="text-center py-5" style="display: none;">
                                <i class="bi bi-inbox fs-1 text-muted"></i>
                                <p class="mt-2 text-muted">No DNS zones found</p>
                                <button class="btn btn-primary mt-2" onclick="dnsZonesManager.showCreateZoneModal()">
                                    <i class="bi bi-plus-circle"></i> Create Your First Zone
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    attachEventHandlers() {
        // Initialize search and filter handlers
        this.searchFilter.initializeEventHandlers((filters) => {
            this.applyFilters(filters);
        });

        // Refresh
        const refreshBtn = document.getElementById('refresh-zones');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadZones());
        }

        // Create Zone
        const createBtn = document.getElementById('create-zone-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateZoneModal());
        }

        // Import Zones
        const importBtn = document.getElementById('import-zones-btn');
        if (importBtn) {
            importBtn.addEventListener('click', () => {
                if (window.dnsImportModal) {
                    window.dnsImportModal.show();
                }
            });
        }

        // Export options
        document.querySelectorAll('.export-option').forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const format = e.target.closest('.export-option').dataset.format;
                await this.exportSelectedZones(format);
            });
        });

        // Sorting
        document.querySelectorAll('.sortable').forEach(th => {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                const column = th.dataset.sort;
                this.sortZones(column);
            });
        });

        // Items per page
        const itemsPerPageSelect = document.getElementById('items-per-page');
        if (itemsPerPageSelect) {
            itemsPerPageSelect.addEventListener('change', (e) => {
                this.itemsPerPage = parseInt(e.target.value);
                this.currentPage = 1;
                this.displayZones();
            });
        }
    }

    async loadZones() {
        try {
            // Show loading
            this.showLoading();

            // Load zones and stats
            const [zones, stats] = await Promise.all([
                this.mockService.getAllZones(),
                this.mockService.getStats()
            ]);

            // Store zones directly in PowerDNS format
            this.zones = zones;
            this.filteredZones = zones;

            // Update stats
            this.updateStats(stats);

            // Display zones
            this.filterAndDisplayZones();

        } catch (error) {
            console.error('Error loading zones:', error);
            this.showError('Failed to load DNS zones');
        }
    }

    updateStats(stats) {
        document.getElementById('total-zones').textContent = stats.totalZones;
        document.getElementById('active-zones').textContent = stats.activeZones;
        document.getElementById('total-records').textContent = stats.totalRecords;
        document.getElementById('recent-changes').textContent = stats.recentChanges;
    }

    filterAndDisplayZones() {
        // Apply filters using the search filter module
        this.filteredZones = this.searchFilter.filterZones(this.zones);

        // Organize zones hierarchically
        this.organizeHierarchy();

        // Reset to first page when filtering
        this.currentPage = 1;
        this.displayZones();
        
        // Load record counts asynchronously
        this.loadRecordCounts();
    }

    /**
     * Simple method to mark which zones are subdomains
     */
    organizeHierarchy() {
        // Initialize all zones
        this.filteredZones.forEach(zone => {
            zone.isSubdomain = false;
            zone.parentZone = null;
            zone.childCount = 0;
            zone.isExpanded = true; // Start expanded
            zone.isVisible = true; // Default visible
        });
        
        // First pass: identify parent-child relationships
        this.filteredZones.forEach(zone => {
            // Remove trailing dot for parsing, then add it back
            const cleanName = zone.name.endsWith('.') ? zone.name.slice(0, -1) : zone.name;
            const parts = cleanName.split('.');
            
            if (parts.length > 2) { // Potential subdomain (more than domain.tld)
                // Try to find parent by removing first part
                const potentialParentClean = parts.slice(1).join('.');
                const potentialParent = potentialParentClean + '.'; // Add dot back
                const parent = this.filteredZones.find(z => z.name === potentialParent);
                if (parent) {
                    zone.isSubdomain = true;
                    zone.parentZone = parent.name;
                    console.log(`Found subdomain: ${zone.name} -> parent: ${parent.name}`);
                }
            }
        });
        
        // Second pass: count children
        this.filteredZones.forEach(zone => {
            if (zone.isSubdomain && zone.parentZone) {
                const parent = this.filteredZones.find(z => z.name === zone.parentZone);
                if (parent) {
                    parent.childCount = (parent.childCount || 0) + 1;
                }
            }
        });
        
        // Log summary
        const parents = this.filteredZones.filter(z => z.childCount > 0);
        console.log(`Hierarchy built: ${parents.length} parent zones found`);
        parents.forEach(p => console.log(`  ${p.name}: ${p.childCount} children`));
    }

    /**
     * Apply filters from the search filter module
     */
    applyFilters(filters) {
        this.filterAndDisplayZones();
    }

    /**
     * Build hierarchical view - simple approach
     */
    buildHierarchicalView() {
        const result = [];
        
        // First add all root zones (non-subdomains)
        this.filteredZones.forEach(zone => {
            if (!zone.isSubdomain) {
                zone.isVisible = true;
                result.push(zone);
                
                // Then add its children right after
                if (zone.childCount > 0 && zone.isExpanded) {
                    this.filteredZones.forEach(child => {
                        if (child.parentZone === zone.name) {
                            child.isVisible = true;
                            result.push(child);
                        }
                    });
                }
            }
        });
        
        return result;
    }

    /**
     * Toggle zone expansion
     */
    toggleZone(zoneId) {
        const zone = this.filteredZones.find(z => z.id === zoneId);
        if (zone) {
            zone.isExpanded = !zone.isExpanded;
            this.displayZones();
        }
    }

    /**
     * Load record counts for each zone asynchronously
     */
    async loadRecordCounts() {
        for (const zone of this.filteredZones) {
            try {
                const fullZone = await this.mockService.getZone(zone.id);
                let recordCount = 0;
                
                if (fullZone.rrsets) {
                    // Count all records in all rrsets (excluding SOA and NS)
                    fullZone.rrsets.forEach(rrset => {
                        if (rrset.type !== 'SOA' && rrset.type !== 'NS') {
                            recordCount += rrset.records.length;
                        }
                    });
                }
                
                // Update the count in the table
                const countElement = document.getElementById(`zone-${zone.id}-records`);
                if (countElement) {
                    countElement.textContent = recordCount;
                }
            } catch (error) {
                console.error(`Error loading record count for zone ${zone.id}:`, error);
            }
        }
    }

    sortZones(column) {
        // Toggle direction if same column
        if (this.currentSort.column === column) {
            this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.currentSort.column = column;
            this.currentSort.direction = 'asc';
        }

        // Sort the filtered zones
        this.filteredZones.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            // Handle special cases
            if (column === 'records') {
                // Can't sort by records since we load them async
                return 0;
            } else if (column === 'serial') {
                aVal = a.serial || 0;
                bVal = b.serial || 0;
            }

            if (aVal < bVal) return this.currentSort.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.currentSort.direction === 'asc' ? 1 : -1;
            return 0;
        });

        this.displayZones();
    }

    displayZones() {
        const tbody = document.getElementById('zones-tbody');
        if (!tbody) return;

        // Build hierarchical view
        const hierarchicalZones = this.buildHierarchicalView();

        // Calculate pagination on the hierarchical list
        const totalPages = Math.ceil(hierarchicalZones.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pagezones = hierarchicalZones.slice(startIndex, endIndex);

        // Show appropriate view
        if (this.zones.length === 0) {
            this.showEmpty();
            return;
        }

        this.showTable();

        // Populate table with search highlighting
        const searchTerm = this.searchFilter.activeFilters.search;
        tbody.innerHTML = pagezones.map(zone => {
            // Apply highlighting to zone name
            const highlightedZoneName = this.searchFilter.highlightSearchTerm(zone.name, searchTerm);
            // Apply highlighting to nameservers
            const highlightedNameservers = zone.nameservers ? 
                zone.nameservers.map(ns => this.searchFilter.highlightSearchTerm(ns, searchTerm)).join(', ') : 
                'N/A';
            
            // Simple indentation for subdomains
            const indent = zone.isSubdomain ? 'ps-4' : '';
            const icon = zone.childCount > 0 ? 
                `<i class="bi bi-chevron-${zone.isExpanded ? 'down' : 'right'} me-1" 
                    style="cursor: pointer;" 
                    onclick="dnsZonesManager.toggleZone('${zone.id}'); event.stopPropagation(); return false;"></i>` : 
                '<span class="me-3"></span>';
            
            return `
            <tr class="${zone.isVisible ? '' : 'd-none'}" data-zone-id="${zone.id}">
                <td>
                    <input type="checkbox" class="zone-checkbox form-check-input" data-zone-id="${zone.id}">
                </td>
                <td class="${indent}">
                    ${icon}
                    <a href="#" class="text-decoration-none" onclick="dnsZonesManager.showZoneDetail('${zone.id}'); return false;">
                        <i class="bi bi-${zone.isSubdomain ? 'folder' : 'globe2'}"></i> ${highlightedZoneName}
                    </a>
                    ${zone.childCount > 0 ? `<span class="badge bg-secondary ms-2">${zone.childCount}</span>` : ''}
                </td>
                <td>
                    <span class="badge bg-${zone.dnssec ? 'warning' : 'success'}">
                        ${zone.dnssec ? 'DNSSEC' : 'Active'}
                    </span>
                </td>
                <td>${zone.kind}</td>
                <td>
                    <span class="badge bg-info" id="zone-${zone.id}-records">...</span>
                </td>
                <td>
                    <small>${highlightedNameservers}</small>
                </td>
                <td>
                    <small>Serial: ${zone.serial || 'N/A'}</small>
                </td>
                <td>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                                data-bs-toggle="dropdown">
                            Actions
                        </button>
                        <ul class="dropdown-menu">
                            <li>
                                <a class="dropdown-item" href="#" 
                                   onclick="dnsZonesManager.showZoneDetail('${zone.id}'); return false;">
                                    <i class="bi bi-eye"></i> View Details
                                </a>
                            </li>
                            <li>
                                <a class="dropdown-item" href="#" 
                                   onclick="dnsZonesManager.editZone('${zone.id}'); return false;">
                                    <i class="bi bi-pencil"></i> Edit
                                </a>
                            </li>
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a class="dropdown-item text-danger" href="#" 
                                   onclick="dnsZonesManager.deleteZone('${zone.id}'); return false;">
                                    <i class="bi bi-trash"></i> Delete
                                </a>
                            </li>
                        </ul>
                    </div>
                </td>
            </tr>
        `}).join('');

        // Update pagination
        this.updatePagination(totalPages);
        
        // Add checkbox event handlers
        this.attachCheckboxHandlers();
    }

    /**
     * Attach checkbox event handlers
     */
    attachCheckboxHandlers() {
        // Select all checkbox
        const selectAll = document.getElementById('selectAllZones');
        if (selectAll) {
            selectAll.addEventListener('change', (e) => {
                const checkboxes = document.querySelectorAll('.zone-checkbox');
                checkboxes.forEach(cb => {
                    cb.checked = e.target.checked;
                    if (e.target.checked) {
                        this.selectedZones.add(cb.dataset.zoneId);
                    } else {
                        this.selectedZones.delete(cb.dataset.zoneId);
                    }
                });
            });
        }

        // Individual checkboxes
        document.querySelectorAll('.zone-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedZones.add(e.target.dataset.zoneId);
                } else {
                    this.selectedZones.delete(e.target.dataset.zoneId);
                }
                
                // Update select all checkbox
                const allChecked = document.querySelectorAll('.zone-checkbox:checked').length === 
                                 document.querySelectorAll('.zone-checkbox').length;
                if (selectAll) {
                    selectAll.checked = allChecked;
                }
            });
        });
    }

    /**
     * Export selected zones
     */
    async exportSelectedZones(format) {
        try {
            if (this.selectedZones.size === 0) {
                // If no zones selected, export all zones
                const confirmExport = confirm('No zones selected. Export all zones?');
                if (!confirmExport) return;
                
                const allZoneIds = this.filteredZones.map(z => z.id);
                await this.importExport.exportMultipleZones(allZoneIds, format);
            } else {
                // Export selected zones
                const zoneIds = Array.from(this.selectedZones);
                await this.importExport.exportMultipleZones(zoneIds, format);
            }
            
            this.showNotification('success', `Zones exported successfully in ${format.toUpperCase()} format.`);
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('error', 'Failed to export zones: ' + error.message);
        }
    }

    updatePagination(totalPages) {
        const pagination = document.getElementById('pagination');
        if (!pagination) return;

        let html = '';

        // Previous button
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="dnsZonesManager.goToPage(${this.currentPage - 1}); return false;">
                    Previous
                </a>
            </li>
        `;

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            // Show first, last, and pages around current
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `
                    <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="dnsZonesManager.goToPage(${i}); return false;">
                            ${i}
                        </a>
                    </li>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += '<li class="page-item disabled"><a class="page-link">...</a></li>';
            }
        }

        // Next button
        html += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="dnsZonesManager.goToPage(${this.currentPage + 1}); return false;">
                    Next
                </a>
            </li>
        `;

        pagination.innerHTML = html;
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.filteredZones.length / this.itemsPerPage);
        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.displayZones();
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    showLoading() {
        document.getElementById('zones-loading').style.display = 'block';
        document.getElementById('zones-table-container').style.display = 'none';
        document.getElementById('zones-empty').style.display = 'none';
    }

    showTable() {
        document.getElementById('zones-loading').style.display = 'none';
        document.getElementById('zones-table-container').style.display = 'block';
        document.getElementById('zones-empty').style.display = 'none';
    }

    showEmpty() {
        document.getElementById('zones-loading').style.display = 'none';
        document.getElementById('zones-table-container').style.display = 'none';
        document.getElementById('zones-empty').style.display = 'block';
    }

    showError(message) {
        // Use existing status bar if available
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) {
            statusMessage.textContent = message;
            statusMessage.parentElement.classList.add('alert-danger');
            statusMessage.parentElement.classList.remove('alert-info');
        }
    }

    // Zone detail modal
    showZoneDetail(zoneId) {
        const detailManager = new DNSZoneDetailManager();
        // Make it globally accessible for onclick handlers
        window.dnsZoneDetailManager = detailManager;
        detailManager.showZoneDetail(zoneId);
    }

    showCreateZoneModal() {
        // Use the new simplified wizard
        const wizard = new DNSZoneWizardV2();
        wizard.show();
    }

    editZone(zoneId) {
        console.log('Edit zone:', zoneId);
        alert('Edit functionality coming soon!');
    }

    async deleteZone(zoneId) {
        try {
            // Get zone details for the confirmation dialog
            const zone = await this.mockService.getZone(zoneId);
            
            // Count records (excluding SOA and NS)
            let recordCount = 0;
            if (zone.rrsets) {
                zone.rrsets.forEach(rrset => {
                    if (rrset.type !== 'SOA' && rrset.type !== 'NS') {
                        recordCount += rrset.records.length;
                    }
                });
            }
            
            // Show confirmation dialog
            const confirmed = await this.showDeleteConfirmation(zone, recordCount);
            
            if (!confirmed) {
                return;
            }
            
            // Delete the zone
            await this.mockService.deleteZone(zoneId);
            
            // Show success notification
            this.showNotification('success', `Zone ${zone.name} has been deleted successfully.`);
            
            // Reload zones list
            await this.loadZones();
            
        } catch (error) {
            console.error('Error deleting zone:', error);
            this.showNotification('error', 'Failed to delete zone: ' + error.message);
        }
    }

    /**
     * Show delete confirmation dialog
     */
    async showDeleteConfirmation(zone, recordCount) {
        return new Promise((resolve) => {
            const requireTypeConfirm = recordCount > 10;
            
            const modalHtml = `
                <div class="modal fade" id="deleteZoneModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header bg-danger text-white">
                                <h5 class="modal-title">
                                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                                    Delete DNS Zone
                                </h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-warning">
                                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                                    <strong>Warning:</strong> This action cannot be undone!
                                </div>
                                
                                <h6>You are about to delete:</h6>
                                <ul>
                                    <li><strong>Zone:</strong> ${zone.name}</li>
                                    <li><strong>Records:</strong> ${recordCount} DNS records</li>
                                    <li><strong>Nameservers:</strong> ${zone.nameservers ? zone.nameservers.length : 0}</li>
                                </ul>
                                
                                ${recordCount > 0 ? `
                                    <div class="alert alert-danger mt-3">
                                        <strong>Active Services Warning:</strong>
                                        <p class="mb-0">This zone contains active DNS records. Deleting it may affect:</p>
                                        <ul class="mb-0">
                                            <li>Website availability</li>
                                            <li>Email delivery</li>
                                            <li>Other services depending on these DNS records</li>
                                        </ul>
                                    </div>
                                ` : ''}
                                
                                ${requireTypeConfirm ? `
                                    <div class="mt-3">
                                        <label class="form-label text-danger">
                                            Type <strong>${zone.name}</strong> to confirm deletion:
                                        </label>
                                        <input type="text" class="form-control" id="confirmZoneName" 
                                               placeholder="Enter zone name to confirm">
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-danger" id="confirmDeleteBtn">
                                    <i class="bi bi-trash me-2"></i>Delete Zone
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if any
            const existingModal = document.getElementById('deleteZoneModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Get modal instance
            const modalElement = document.getElementById('deleteZoneModal');
            const modal = new bootstrap.Modal(modalElement);
            
            // Handle confirm button
            const confirmBtn = document.getElementById('confirmDeleteBtn');
            confirmBtn.addEventListener('click', () => {
                if (requireTypeConfirm) {
                    const input = document.getElementById('confirmZoneName');
                    if (input.value !== zone.name) {
                        input.classList.add('is-invalid');
                        return;
                    }
                }
                
                modal.hide();
                resolve(true);
            });
            
            // Clean up on modal close
            modalElement.addEventListener('hidden.bs.modal', () => {
                modalElement.remove();
                resolve(false);
            });
            
            // Show modal
            modal.show();
        });
    }

    /**
     * Show notification
     */
    showNotification(type, message) {
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const icon = type === 'success' ? 'check-circle-fill' : 'exclamation-triangle-fill';
        
        const notification = `
            <div class="alert ${alertClass} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" 
                 style="z-index: 9999; min-width: 300px;" role="alert">
                <i class="bi bi-${icon} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = document.querySelector('.alert.position-fixed');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize the DNS Zones Manager
const dnsZonesManager = new DNSZonesManager();