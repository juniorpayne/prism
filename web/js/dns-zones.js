/**
 * DNS Zones Management Module
 * Handles the DNS zones landing page with stats, table, search, and sorting
 */

class DNSZonesManager {
    constructor() {
        // Use service adapter instead of direct mock service
        this.dnsService = DNSServiceFactory.getAdapter();
        this.searchFilter = new DNSSearchFilter();
        this.importExport = new DNSImportExport();
        this.preferenceManager = window.dnsPreferenceManager || new DNSPreferenceManager();
        this.breadcrumbNav = null; // Will be initialized after DOM is ready
        this.zones = [];
        this.filteredZones = [];
        this.currentSort = this.preferenceManager.getSortPreferences();
        this.currentPage = 1;
        this.itemsPerPage = this.preferenceManager.getItemsPerPage();
        this.searchTerm = '';
        this.selectedZones = new Set();
        this.viewMode = this.preferenceManager.getViewMode(); // 'tree' or 'flat'
        this.loadingStates = new Map(); // Track loading states for different operations
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
        
        // Initialize breadcrumb navigation
        if (!this.breadcrumbNav) {
            this.breadcrumbNav = new DNSBreadcrumbNav(this);
            // Make it globally accessible
            window.dnsBreadcrumbNav = this.breadcrumbNav;
        }
        
        // Attach event handlers
        this.attachEventHandlers();
        
        // Load data
        await this.loadZones();
        
        // Initialize breadcrumb after zones are loaded
        this.breadcrumbNav.initialize();
    }

    buildDNSZonesHTML() {
        return `
            <div class="row mb-4">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center mb-4">
                        <h2><i class="bi bi-diagram-3"></i> DNS Zones</h2>
                        <div class="btn-toolbar">
                            <!-- View Toggle -->
                            <div class="btn-group me-2">
                                <button class="btn btn-outline-secondary ${this.viewMode === 'tree' ? 'active' : ''}" 
                                        id="tree-view-btn" title="Tree View">
                                    <i class="bi bi-diagram-3"></i>
                                </button>
                                <button class="btn btn-outline-secondary ${this.viewMode === 'flat' ? 'active' : ''}" 
                                        id="flat-view-btn" title="Flat View">
                                    <i class="bi bi-list"></i>
                                </button>
                            </div>
                            
                            <!-- Tree Controls (only in tree view) -->
                            <div class="btn-group me-2" id="tree-controls" style="${this.viewMode === 'flat' ? 'display: none;' : ''}">
                                <button class="btn btn-outline-secondary" id="expand-all-btn" title="Expand All">
                                    <i class="bi bi-chevron-double-down"></i>
                                </button>
                                <button class="btn btn-outline-secondary" id="collapse-all-btn" title="Collapse All">
                                    <i class="bi bi-chevron-double-up"></i>
                                </button>
                            </div>
                            
                            <!-- Import/Export -->
                            <div class="btn-group me-2">
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
                            </div>
                            
                            <!-- Settings Dropdown -->
                            <div class="btn-group me-2">
                                <button class="btn btn-outline-secondary dropdown-toggle" 
                                        data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="bi bi-gear"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><h6 class="dropdown-header">Preferences</h6></li>
                                    <li>
                                        <a class="dropdown-item" href="#" id="reset-tree-state">
                                            <i class="bi bi-arrow-clockwise me-2"></i>Reset Tree State
                                        </a>
                                    </li>
                                    <li>
                                        <a class="dropdown-item" href="#" id="reset-all-preferences">
                                            <i class="bi bi-trash me-2"></i>Reset All Preferences
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li>
                                        <a class="dropdown-item" href="#" id="export-preferences">
                                            <i class="bi bi-download me-2"></i>Export Preferences
                                        </a>
                                    </li>
                                </ul>
                            </div>
                            
                            <!-- Create Zone -->
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
            itemsPerPageSelect.value = this.itemsPerPage; // Set saved value
            itemsPerPageSelect.addEventListener('change', (e) => {
                this.itemsPerPage = parseInt(e.target.value);
                this.preferenceManager.setItemsPerPage(this.itemsPerPage);
                this.currentPage = 1;
                this.displayZones();
            });
        }
        
        // View mode toggle
        const treeViewBtn = document.getElementById('tree-view-btn');
        const flatViewBtn = document.getElementById('flat-view-btn');
        
        if (treeViewBtn) {
            treeViewBtn.addEventListener('click', () => {
                this.setViewMode('tree');
            });
        }
        
        if (flatViewBtn) {
            flatViewBtn.addEventListener('click', () => {
                this.setViewMode('flat');
            });
        }
        
        // Tree controls
        const expandAllBtn = document.getElementById('expand-all-btn');
        const collapseAllBtn = document.getElementById('collapse-all-btn');
        
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => {
                this.expandAllZones();
            });
        }
        
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => {
                this.collapseAllZones();
            });
        }
        
        // Preference management
        const resetTreeBtn = document.getElementById('reset-tree-state');
        const resetAllBtn = document.getElementById('reset-all-preferences');
        const exportPrefsBtn = document.getElementById('export-preferences');
        
        if (resetTreeBtn) {
            resetTreeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (confirm('Reset tree expansion state?')) {
                    this.preferenceManager.resetTreeState();
                    this.restoreTreeState();
                    this.displayZones();
                    this.showNotification('success', 'Tree state reset to default');
                }
            });
        }
        
        if (resetAllBtn) {
            resetAllBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (confirm('Reset all preferences to defaults? This cannot be undone.')) {
                    this.preferenceManager.resetPreferences();
                    location.reload(); // Easiest way to ensure all preferences are reset
                }
            });
        }
        
        if (exportPrefsBtn) {
            exportPrefsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const prefs = this.preferenceManager.exportPreferences();
                const blob = new Blob([prefs], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dns-preferences-${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
                this.showNotification('success', 'Preferences exported successfully');
            });
        }
        
        // Restore filter preferences
        const savedFilters = this.preferenceManager.getActiveFilters();
        if (savedFilters) {
            // Apply saved filters to search filter
            this.searchFilter.activeFilters = { ...this.searchFilter.activeFilters, ...savedFilters };
        }
    }

    async loadZones() {
        try {
            // Show loading
            this.showLoading();
            this.setLoadingState('zones', true);

            // Load zones and stats using service adapter
            const [zonesResult, stats] = await Promise.all([
                this.dnsService.getZones(1, 500), // Get up to 500 zones (API limit)
                this.dnsService.getStats()
            ]);

            // Extract zones from paginated result
            const zones = zonesResult.zones || [];

            // Store zones directly in PowerDNS format
            this.zones = zones;
            this.filteredZones = zones;

            // Update stats
            this.updateStats(stats);

            // Display zones
            this.filterAndDisplayZones();

        } catch (error) {
            console.error('Error loading zones:', error);
            this.showError(`Failed to load DNS zones: ${error.message || 'Unknown error'}`);
        } finally {
            this.setLoadingState('zones', false);
            this.hideLoading();
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
            // Restore expansion state from preferences
            zone.isExpanded = this.preferenceManager.isZoneExpanded(zone.id);
            zone.isVisible = true; // Default visible
        });
        
        // First pass: identify parent-child relationships
        this.filteredZones.forEach(zone => {
            // Remove trailing dot for parsing, then add it back
            const cleanName = zone.name.endsWith('.') ? zone.name.slice(0, -1) : zone.name;
            const parts = cleanName.split('.');
            
            if (parts.length > 2) { // Potential subdomain (more than domain.tld)
                // Try to find the closest parent by removing parts one by one
                for (let i = 1; i < parts.length - 1; i++) {
                    const potentialParentClean = parts.slice(i).join('.');
                    const potentialParent = potentialParentClean + '.'; // Add dot back
                    const parent = this.filteredZones.find(z => z.name === potentialParent);
                    if (parent) {
                        zone.isSubdomain = true;
                        zone.parentZone = parent.name;
                        zone.depth = parts.length - parent.name.split('.').length + 1;
                        console.log(`Found subdomain: ${zone.name} -> parent: ${parent.name} (depth: ${zone.depth})`);
                        break; // Found the closest parent, stop looking
                    }
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
     * Build hierarchical view - recursive approach for multi-level support
     */
    buildHierarchicalView() {
        const result = [];
        
        // Helper function to add zone and its descendants
        const addZoneAndDescendants = (zone, parentExpanded = true) => {
            zone.isVisible = parentExpanded;
            result.push(zone);
            
            if (zone.childCount > 0 && zone.isExpanded && parentExpanded) {
                // Find all direct children and add them recursively
                this.filteredZones
                    .filter(child => child.parentZone === zone.name)
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .forEach(child => {
                        addZoneAndDescendants(child, true);
                    });
            }
        };
        
        // Start with root zones (non-subdomains)
        this.filteredZones
            .filter(zone => !zone.isSubdomain)
            .sort((a, b) => a.name.localeCompare(b.name))
            .forEach(zone => {
                addZoneAndDescendants(zone);
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
            // Save expansion state
            this.preferenceManager.setZoneExpanded(zoneId, zone.isExpanded);
            this.displayZones();
        }
    }

    /**
     * Load record counts for each zone asynchronously
     */
    async loadRecordCounts() {
        for (const zone of this.filteredZones) {
            try {
                const fullZone = await this.dnsService.getZone(zone.id);
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

        // Save sort preferences
        this.preferenceManager.setSortPreferences(this.currentSort.column, this.currentSort.direction);

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

        // Get zones based on view mode
        let zonesToDisplay;
        if (this.viewMode === 'tree') {
            // Build hierarchical view
            zonesToDisplay = this.buildHierarchicalView();
        } else {
            // Flat view - just show all zones sorted
            zonesToDisplay = [...this.filteredZones];
        }

        // Calculate pagination
        const totalPages = Math.ceil(zonesToDisplay.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pagezones = zonesToDisplay.slice(startIndex, endIndex);

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
            
            // Multi-level indentation based on depth (only in tree view)
            const depth = zone.depth || 0;
            const showTreeFeatures = this.viewMode === 'tree' && zone.isSubdomain;
            const indent = showTreeFeatures && depth > 0 ? `style="padding-left: ${depth * 25}px;"` : '';
            const icon = this.viewMode === 'tree' && zone.childCount > 0 ? 
                `<i class="bi bi-chevron-${zone.isExpanded ? 'down' : 'right'} me-1" 
                    style="cursor: pointer;" 
                    onclick="dnsZonesManager.toggleZone('${zone.id}'); event.stopPropagation(); return false;"></i>` : 
                '<span class="me-3"></span>';
            
            return `
            <tr class="${zone.isVisible ? '' : 'd-none'}" data-zone-id="${zone.id}">
                <td>
                    <input type="checkbox" class="zone-checkbox form-check-input" data-zone-id="${zone.id}">
                </td>
                <td>
                    <div ${indent}>
                        ${icon}
                        <a href="#" class="text-decoration-none" onclick="dnsZonesManager.showZoneDetail('${zone.id}'); return false;">
                            <i class="bi bi-${zone.isSubdomain ? 'folder' : 'globe2'}"></i> ${highlightedZoneName}
                        </a>
                        ${zone.childCount > 0 ? `<span class="badge bg-secondary ms-2">${zone.childCount}</span>` : ''}
                    </div>
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
                this.updateBulkOperationsUI();
            });
        }

        // Individual checkboxes with right-click for tree selection
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
                
                this.updateBulkOperationsUI();
            });
            
            // Add context menu for tree selection
            cb.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const zoneId = e.target.dataset.zoneId;
                this.showTreeSelectionMenu(e, zoneId);
            });
        });
    }

    /**
     * Show tree selection context menu
     */
    showTreeSelectionMenu(event, zoneId) {
        // Remove any existing context menu
        const existingMenu = document.querySelector('.tree-selection-menu');
        if (existingMenu) existingMenu.remove();
        
        const zone = this.zones.find(z => z.id === zoneId);
        if (!zone) return;
        
        const menu = document.createElement('div');
        menu.className = 'tree-selection-menu dropdown-menu show';
        menu.style.position = 'fixed';
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        menu.style.zIndex = '9999';
        
        menu.innerHTML = `
            <h6 class="dropdown-header">${zone.name}</h6>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#" data-action="select-zone">
                <i class="bi bi-check2-square me-2"></i>Select Zone Only
            </a>
            ${zone.childCount > 0 ? `
                <a class="dropdown-item" href="#" data-action="select-with-children">
                    <i class="bi bi-diagram-3 me-2"></i>Select with All Subdomains (${zone.childCount})
                </a>
            ` : ''}
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#" data-action="deselect-all">
                <i class="bi bi-x-square me-2"></i>Deselect All
            </a>
        `;
        
        document.body.appendChild(menu);
        
        // Handle menu clicks
        menu.addEventListener('click', (e) => {
            e.preventDefault();
            const action = e.target.closest('[data-action]')?.dataset.action;
            
            switch (action) {
                case 'select-zone':
                    this.selectZone(zoneId);
                    break;
                case 'select-with-children':
                    this.selectZoneWithChildren(zoneId);
                    break;
                case 'deselect-all':
                    this.deselectAllZones();
                    break;
            }
            
            menu.remove();
        });
        
        // Remove menu on click outside
        setTimeout(() => {
            document.addEventListener('click', () => menu.remove(), { once: true });
        }, 0);
    }
    
    /**
     * Select a single zone
     */
    selectZone(zoneId) {
        this.selectedZones.add(zoneId);
        const checkbox = document.querySelector(`input[data-zone-id="${zoneId}"]`);
        if (checkbox) checkbox.checked = true;
        this.updateBulkOperationsUI();
    }
    
    /**
     * Select zone with all its children
     */
    selectZoneWithChildren(zoneId) {
        const zone = this.zones.find(z => z.id === zoneId);
        if (!zone) return;
        
        // Select the zone itself
        this.selectZone(zoneId);
        
        // Find and select all descendants
        this.zones.forEach(z => {
            if (this.isDescendantOf(z.name, zone.name)) {
                this.selectZone(z.id);
            }
        });
    }
    
    /**
     * Check if a zone is a descendant of another
     */
    isDescendantOf(childName, parentName) {
        const child = childName.endsWith('.') ? childName.slice(0, -1) : childName;
        const parent = parentName.endsWith('.') ? parentName.slice(0, -1) : parentName;
        return child !== parent && child.endsWith('.' + parent);
    }
    
    /**
     * Deselect all zones
     */
    deselectAllZones() {
        this.selectedZones.clear();
        document.querySelectorAll('.zone-checkbox').forEach(cb => {
            cb.checked = false;
        });
        this.updateBulkOperationsUI();
    }
    
    /**
     * Update bulk operations UI based on selection
     */
    updateBulkOperationsUI() {
        const selectedCount = this.selectedZones.size;
        
        // Update or create bulk operations bar
        let bulkBar = document.getElementById('bulk-operations-bar');
        if (selectedCount > 0) {
            if (!bulkBar) {
                bulkBar = this.createBulkOperationsBar();
            }
            
            // Update selection count
            const countElement = bulkBar.querySelector('#selected-count');
            if (countElement) {
                countElement.textContent = `${selectedCount} zone${selectedCount > 1 ? 's' : ''} selected`;
            }
            
            bulkBar.style.display = 'block';
        } else if (bulkBar) {
            bulkBar.style.display = 'none';
        }
    }
    
    /**
     * Create bulk operations bar
     */
    createBulkOperationsBar() {
        const container = document.querySelector('#zones-table-container');
        if (!container) return null;
        
        const bulkBar = document.createElement('div');
        bulkBar.id = 'bulk-operations-bar';
        bulkBar.className = 'alert alert-info d-flex justify-content-between align-items-center mb-3';
        bulkBar.style.display = 'none';
        
        bulkBar.innerHTML = `
            <div>
                <i class="bi bi-check2-square me-2"></i>
                <span id="selected-count">0 zones selected</span>
            </div>
            <div class="btn-group">
                <button class="btn btn-sm btn-outline-primary" onclick="dnsZonesManager.showBulkExportModal()">
                    <i class="bi bi-download me-1"></i>Export
                </button>
                <button class="btn btn-sm btn-outline-warning" onclick="dnsZonesManager.showBulkNameserverModal()">
                    <i class="bi bi-hdd-network me-1"></i>Change Nameservers
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="dnsZonesManager.showBulkDeleteModal()">
                    <i class="bi bi-trash me-1"></i>Delete
                </button>
                <button class="btn btn-sm btn-secondary ms-2" onclick="dnsZonesManager.deselectAllZones()">
                    <i class="bi bi-x-circle me-1"></i>Clear Selection
                </button>
            </div>
        `;
        
        // Insert before the table
        const table = container.querySelector('.table-responsive');
        if (table) {
            container.insertBefore(bulkBar, table);
        }
        
        return bulkBar;
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
        // Update breadcrumb navigation when viewing zone details
        if (this.breadcrumbNav) {
            const zone = this.zones.find(z => z.id === zoneId);
            if (zone) {
                this.breadcrumbNav.setPathForZone(zone);
            }
        }
        
        const detailManager = new DNSZoneDetailManager();
        // Make it globally accessible for onclick handlers
        window.dnsZoneDetailManager = detailManager;
        detailManager.showZoneDetail(zoneId);
    }

    showCreateZoneModal() {
        // Use the new simplified wizard
        const wizard = new DNSZoneWizardV2();
        // Pass zones for parent detection
        wizard.show({ zones: this.zones });
    }

    editZone(zoneId) {
        console.log('Edit zone:', zoneId);
        alert('Edit functionality coming soon!');
    }

    async deleteZone(zoneId) {
        try {
            this.setLoadingState(`delete-${zoneId}`, true);
            
            // Get zone details for the confirmation dialog
            const zone = await this.dnsService.getZone(zoneId);
            
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
            await this.dnsService.deleteZone(zoneId);
            
            // Show success notification
            this.showNotification('success', `Zone ${zone.name} has been deleted successfully.`);
            
            // Reload zones list
            await this.loadZones();
            
        } catch (error) {
            console.error('Error deleting zone:', error);
            this.showNotification('error', 'Failed to delete zone: ' + error.message);
        } finally {
            this.setLoadingState(`delete-${zoneId}`, false);
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
    
    /**
     * Show bulk delete modal with cascade preview
     */
    async showBulkDeleteModal() {
        if (this.selectedZones.size === 0) {
            this.showNotification('error', 'No zones selected');
            return;
        }
        
        // Get selected zones and their children
        const selectedZoneData = await this.getSelectedZonesWithChildren();
        
        const modalHtml = `
            <div class="modal fade" id="bulkDeleteModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-trash me-2"></i>
                                Delete Multiple Zones
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-warning">
                                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                                <strong>Warning:</strong> This action cannot be undone!
                            </div>
                            
                            <h6>Zones to be deleted:</h6>
                            <div class="border rounded p-3 mb-3" style="max-height: 300px; overflow-y: auto;">
                                ${this.renderZoneHierarchy(selectedZoneData)}
                            </div>
                            
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="cascadeDelete" checked>
                                <label class="form-check-label" for="cascadeDelete">
                                    <strong>Delete all subdomains</strong> (recommended to maintain consistency)
                                </label>
                            </div>
                            
                            <div class="alert alert-info" id="deleteStats">
                                ${this.calculateDeleteStats(selectedZoneData)}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" onclick="dnsZonesManager.performBulkDelete()">
                                <i class="bi bi-trash me-2"></i>Delete Zones
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('bulkDeleteModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('bulkDeleteModal'));
        modal.show();
        
        // Update stats when cascade option changes
        document.getElementById('cascadeDelete').addEventListener('change', () => {
            document.getElementById('deleteStats').innerHTML = this.calculateDeleteStats(selectedZoneData);
        });
    }
    
    /**
     * Show bulk export modal
     */
    showBulkExportModal() {
        if (this.selectedZones.size === 0) {
            this.showNotification('error', 'No zones selected');
            return;
        }
        
        const modalHtml = `
            <div class="modal fade" id="bulkExportModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-download me-2"></i>
                                Export Selected Zones
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>Export ${this.selectedZones.size} selected zone(s):</p>
                            
                            <div class="list-group">
                                <button class="list-group-item list-group-item-action" 
                                        onclick="dnsZonesManager.performBulkExport('bind')">
                                    <i class="bi bi-file-text me-2"></i>
                                    <strong>BIND Format</strong>
                                    <div class="small text-muted">Standard zone file format</div>
                                </button>
                                <button class="list-group-item list-group-item-action" 
                                        onclick="dnsZonesManager.performBulkExport('json')">
                                    <i class="bi bi-file-code me-2"></i>
                                    <strong>JSON Format</strong>
                                    <div class="small text-muted">PowerDNS API format</div>
                                </button>
                                <button class="list-group-item list-group-item-action" 
                                        onclick="dnsZonesManager.performBulkExport('csv')">
                                    <i class="bi bi-file-spreadsheet me-2"></i>
                                    <strong>CSV Format</strong>
                                    <div class="small text-muted">Spreadsheet compatible</div>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('bulkExportModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('bulkExportModal'));
        modal.show();
    }
    
    /**
     * Show bulk nameserver change modal
     */
    showBulkNameserverModal() {
        if (this.selectedZones.size === 0) {
            this.showNotification('error', 'No zones selected');
            return;
        }
        
        const modalHtml = `
            <div class="modal fade" id="bulkNameserverModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-hdd-network me-2"></i>
                                Change Nameservers
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>Change nameservers for ${this.selectedZones.size} selected zone(s):</p>
                            
                            <div class="mb-3">
                                <label class="form-label">New Nameservers</label>
                                <textarea class="form-control" id="newNameservers" rows="4" 
                                          placeholder="ns1.example.com.&#10;ns2.example.com.">ns1.example.com.
ns2.example.com.</textarea>
                                <div class="form-text">Enter one nameserver per line. Include trailing dot.</div>
                            </div>
                            
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle me-2"></i>
                                This will update the NS records for all selected zones.
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-warning" onclick="dnsZonesManager.performBulkNameserverChange()">
                                <i class="bi bi-hdd-network me-2"></i>Update Nameservers
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('bulkNameserverModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('bulkNameserverModal'));
        modal.show();
    }
    
    /**
     * Get selected zones with their children
     */
    async getSelectedZonesWithChildren() {
        const result = [];
        
        for (const zoneId of this.selectedZones) {
            const zone = this.zones.find(z => z.id === zoneId);
            if (!zone) continue;
            
            const zoneData = {
                zone: zone,
                children: []
            };
            
            // Find all children
            this.zones.forEach(z => {
                if (this.isDescendantOf(z.name, zone.name)) {
                    zoneData.children.push(z);
                }
            });
            
            result.push(zoneData);
        }
        
        return result;
    }
    
    /**
     * Render zone hierarchy for preview
     */
    renderZoneHierarchy(zoneData) {
        let html = '<ul class="list-unstyled mb-0">';
        
        zoneData.forEach(item => {
            html += `
                <li class="mb-2">
                    <i class="bi bi-globe2 text-primary me-2"></i>
                    <strong>${item.zone.name}</strong>
                    ${item.children.length > 0 ? `
                        <ul class="mt-1">
                            ${item.children.map(child => `
                                <li class="text-muted">
                                    <i class="bi bi-folder me-2"></i>${child.name}
                                </li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </li>
            `;
        });
        
        html += '</ul>';
        return html;
    }
    
    /**
     * Calculate delete statistics
     */
    calculateDeleteStats(zoneData) {
        const cascadeChecked = document.getElementById('cascadeDelete')?.checked ?? true;
        let totalZones = zoneData.length;
        let totalSubdomains = 0;
        
        if (cascadeChecked) {
            zoneData.forEach(item => {
                totalSubdomains += item.children.length;
            });
        }
        
        const total = totalZones + totalSubdomains;
        
        return `
            <i class="bi bi-info-circle me-2"></i>
            <strong>Total zones to be deleted:</strong> ${total}
            <ul class="mb-0 mt-2">
                <li>Primary zones: ${totalZones}</li>
                ${cascadeChecked ? `<li>Subdomains: ${totalSubdomains}</li>` : ''}
            </ul>
        `;
    }
    
    /**
     * Perform bulk delete operation
     */
    async performBulkDelete() {
        const cascadeDelete = document.getElementById('cascadeDelete').checked;
        const zonesToDelete = new Set(this.selectedZones);
        
        // Add children if cascade is enabled
        if (cascadeDelete) {
            for (const zoneId of this.selectedZones) {
                const zone = this.zones.find(z => z.id === zoneId);
                if (!zone) continue;
                
                this.zones.forEach(z => {
                    if (this.isDescendantOf(z.name, zone.name)) {
                        zonesToDelete.add(z.id);
                    }
                });
            }
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('bulkDeleteModal'));
        modal.hide();
        
        // Show progress
        this.showProgressModal('Deleting Zones', zonesToDelete.size);
        
        let completed = 0;
        const errors = [];
        
        for (const zoneId of zonesToDelete) {
            try {
                await this.dnsService.deleteZone(zoneId);
                completed++;
                this.updateProgress(completed, zonesToDelete.size);
            } catch (error) {
                errors.push({ zoneId, error: error.message });
            }
        }
        
        // Hide progress
        this.hideProgressModal();
        
        // Show result
        if (errors.length === 0) {
            this.showNotification('success', `Successfully deleted ${completed} zone(s)`);
        } else {
            this.showNotification('error', `Deleted ${completed} zone(s), but ${errors.length} failed`);
        }
        
        // Clear selection and reload
        this.deselectAllZones();
        await this.loadZones();
    }
    
    /**
     * Perform bulk export
     */
    async performBulkExport(format) {
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('bulkExportModal'));
        modal.hide();
        
        try {
            const zoneIds = Array.from(this.selectedZones);
            await this.importExport.exportMultipleZones(zoneIds, format);
            this.showNotification('success', `Exported ${zoneIds.length} zone(s) in ${format.toUpperCase()} format`);
        } catch (error) {
            this.showNotification('error', `Export failed: ${error.message}`);
        }
    }
    
    /**
     * Perform bulk nameserver change
     */
    async performBulkNameserverChange() {
        const nameserversText = document.getElementById('newNameservers').value.trim();
        if (!nameserversText) {
            this.showNotification('error', 'Please enter at least one nameserver');
            return;
        }
        
        const nameservers = nameserversText.split('\n')
            .map(ns => ns.trim())
            .filter(ns => ns.length > 0);
        
        // Validate nameservers
        for (const ns of nameservers) {
            if (!ns.endsWith('.')) {
                this.showNotification('error', `Nameserver ${ns} must end with a dot`);
                return;
            }
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('bulkNameserverModal'));
        modal.hide();
        
        // Show progress
        this.showProgressModal('Updating Nameservers', this.selectedZones.size);
        
        let completed = 0;
        const errors = [];
        
        for (const zoneId of this.selectedZones) {
            try {
                const zone = await this.dnsService.getZone(zoneId);
                if (zone) {
                    // Update nameservers
                    zone.nameservers = nameservers;
                    await this.dnsService.updateZone(zoneId, zone);
                    completed++;
                    this.updateProgress(completed, this.selectedZones.size);
                }
            } catch (error) {
                errors.push({ zoneId, error: error.message });
            }
        }
        
        // Hide progress
        this.hideProgressModal();
        
        // Show result
        if (errors.length === 0) {
            this.showNotification('success', `Successfully updated nameservers for ${completed} zone(s)`);
        } else {
            this.showNotification('error', `Updated ${completed} zone(s), but ${errors.length} failed`);
        }
        
        // Reload zones
        await this.loadZones();
    }
    
    /**
     * Show progress modal
     */
    showProgressModal(title, total) {
        const modalHtml = `
            <div class="modal fade" id="progressModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-body text-center py-4">
                            <h6>${title}</h6>
                            <div class="progress mt-3 mb-3">
                                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 0%"></div>
                            </div>
                            <div id="progressText">0 / ${total}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('progressModal'));
        modal.show();
    }
    
    /**
     * Update progress
     */
    updateProgress(completed, total) {
        const percent = Math.round((completed / total) * 100);
        const progressBar = document.querySelector('#progressModal .progress-bar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) {
            progressBar.style.width = percent + '%';
        }
        if (progressText) {
            progressText.textContent = `${completed} / ${total}`;
        }
    }
    
    /**
     * Hide progress modal
     */
    hideProgressModal() {
        const modalElement = document.getElementById('progressModal');
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) modal.hide();
            setTimeout(() => modalElement.remove(), 300);
        }
    }
    
    /**
     * Set view mode (tree or flat)
     */
    setViewMode(mode) {
        if (mode !== 'tree' && mode !== 'flat') return;
        
        this.viewMode = mode;
        this.preferenceManager.setViewMode(mode);
        
        // Update button states
        const treeBtn = document.getElementById('tree-view-btn');
        const flatBtn = document.getElementById('flat-view-btn');
        const treeControls = document.getElementById('tree-controls');
        
        if (mode === 'tree') {
            treeBtn?.classList.add('active');
            flatBtn?.classList.remove('active');
            if (treeControls) treeControls.style.display = '';
        } else {
            treeBtn?.classList.remove('active');
            flatBtn?.classList.add('active');
            if (treeControls) treeControls.style.display = 'none';
        }
        
        this.displayZones();
    }
    
    /**
     * Expand all zones
     */
    expandAllZones() {
        const zoneIds = this.filteredZones
            .filter(z => z.childCount > 0)
            .map(z => z.id);
            
        this.preferenceManager.expandAllZones(zoneIds);
        
        // Update zone states
        this.filteredZones.forEach(zone => {
            if (zone.childCount > 0) {
                zone.isExpanded = true;
            }
        });
        
        this.displayZones();
    }
    
    /**
     * Collapse all zones
     */
    collapseAllZones() {
        this.preferenceManager.collapseAllZones();
        
        // Update zone states
        this.filteredZones.forEach(zone => {
            zone.isExpanded = false;
        });
        
        this.displayZones();
    }
    
    /**
     * Restore tree state from preferences
     */
    restoreTreeState() {
        this.filteredZones.forEach(zone => {
            zone.isExpanded = this.preferenceManager.isZoneExpanded(zone.id);
        });
    }
    
    /**
     * Apply filters and save preferences
     */
    applyFilters(filters) {
        // Save filter preferences
        this.preferenceManager.updateFilters(filters);
        this.filterAndDisplayZones();
    }

    /**
     * Set loading state for a specific operation
     */
    setLoadingState(operation, isLoading) {
        this.loadingStates.set(operation, isLoading);
        
        // Update UI elements based on operation
        if (operation.startsWith('delete-')) {
            const zoneId = operation.replace('delete-', '');
            const deleteBtn = document.querySelector(`button[onclick*="deleteZone('${zoneId}')"]`);
            if (deleteBtn) {
                deleteBtn.disabled = isLoading;
                if (isLoading) {
                    deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Deleting...';
                } else {
                    deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
                }
            }
        }
    }

    /**
     * Check if any operation is loading
     */
    isLoading() {
        for (const [operation, loading] of this.loadingStates) {
            if (loading) return true;
        }
        return false;
    }

    /**
     * Show loading overlay
     */
    showLoading() {
        const container = document.getElementById('dns-zones-table-container');
        if (container && !document.getElementById('zones-loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'zones-loading-overlay';
            overlay.className = 'd-flex justify-content-center align-items-center';
            overlay.style.cssText = 'position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.8); z-index: 1000;';
            overlay.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary mb-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div>Loading zones...</div>
                </div>
            `;
            container.style.position = 'relative';
            container.appendChild(overlay);
        }
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('zones-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
}

// Initialize the DNS Zones Manager
const dnsZonesManager = new DNSZonesManager();