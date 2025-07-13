/**
 * DNS Zones Management Module
 * Handles the DNS zones landing page with stats, table, search, and sorting
 */

class DNSZonesManager {
    constructor() {
        this.mockService = new DNSMockDataService();
        this.zones = [];
        this.filteredZones = [];
        this.currentSort = { column: 'name', direction: 'asc' };
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.searchTerm = '';
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
                        <button class="btn btn-primary" id="create-zone-btn">
                            <i class="bi bi-plus-circle"></i> Create Zone
                        </button>
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
            <div class="row mb-3">
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text">
                            <i class="bi bi-search"></i>
                        </span>
                        <input type="text" class="form-control" id="search-zones" 
                               placeholder="Search zones by name...">
                    </div>
                </div>
                <div class="col-md-6 text-end">
                    <button class="btn btn-outline-secondary" id="refresh-zones">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                </div>
            </div>

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
                                                <th class="sortable" data-sort="name">
                                                    Zone Name <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th class="sortable" data-sort="status">
                                                    Status <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th>Type</th>
                                                <th class="sortable" data-sort="records">
                                                    Records <i class="bi bi-arrow-down-up"></i>
                                                </th>
                                                <th>Name Servers</th>
                                                <th class="sortable" data-sort="modified">
                                                    Last Modified <i class="bi bi-arrow-down-up"></i>
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
        // Search
        const searchInput = document.getElementById('search-zones');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.filterAndDisplayZones();
            });
        }

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
        // Apply search filter
        if (this.searchTerm) {
            this.filteredZones = this.zones.filter(zone => 
                zone.name.toLowerCase().includes(this.searchTerm) ||
                zone.nameservers.some(ns => ns.toLowerCase().includes(this.searchTerm))
            );
        } else {
            this.filteredZones = [...this.zones];
        }

        // Reset to first page when filtering
        this.currentPage = 1;
        this.displayZones();
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
                aVal = a.records.length;
                bVal = b.records.length;
            } else if (column === 'modified') {
                aVal = new Date(a.modified);
                bVal = new Date(b.modified);
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

        // Calculate pagination
        const totalPages = Math.ceil(this.filteredZones.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const pagezones = this.filteredZones.slice(startIndex, endIndex);

        // Show appropriate view
        if (this.zones.length === 0) {
            this.showEmpty();
            return;
        }

        this.showTable();

        // Populate table
        tbody.innerHTML = pagezones.map(zone => `
            <tr>
                <td>
                    <a href="#" class="text-decoration-none" onclick="dnsZonesManager.showZoneDetail('${zone.id}'); return false;">
                        <i class="bi bi-globe2"></i> ${zone.name}
                    </a>
                </td>
                <td>
                    <span class="badge bg-${zone.status === 'Active' ? 'success' : 'secondary'}">
                        ${zone.status}
                    </span>
                </td>
                <td>${zone.type}</td>
                <td>
                    <span class="badge bg-info">${zone.records.length}</span>
                </td>
                <td>
                    <small>${zone.nameservers.join(', ')}</small>
                </td>
                <td>
                    <small>${this.formatDate(zone.modified)}</small>
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
        `).join('');

        // Update pagination
        this.updatePagination(totalPages);
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
        detailManager.showZoneDetail(zoneId);
    }

    showCreateZoneModal() {
        // Use the global wizard instance if available, otherwise create new one
        if (window.dnsZoneWizard) {
            window.dnsZoneWizard.showWizard();
        } else {
            // Fallback: create new instance
            const wizard = new DNSZoneWizard();
            wizard.showWizard();
        }
    }

    editZone(zoneId) {
        console.log('Edit zone:', zoneId);
        alert('Edit functionality coming soon!');
    }

    deleteZone(zoneId) {
        console.log('Delete zone:', zoneId);
        alert('Delete functionality coming soon! (SCRUM-100)');
    }
}

// Initialize the DNS Zones Manager
const dnsZonesManager = new DNSZonesManager();