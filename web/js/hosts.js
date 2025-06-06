/**
 * Host Management for Prism DNS Web Interface
 * Handles host list view, search, filtering, and detail views
 */

class HostManager {
    constructor() {
        this.hosts = [];
        this.filteredHosts = [];
        this.currentSort = { field: 'hostname', direction: 'asc' };
        this.searchQuery = '';
        this.statusFilter = '';
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
        this.refreshIntervalMs = 30000; // 30 seconds
        
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.elements = {
            // Containers
            loadingHosts: document.getElementById('loading-hosts'),
            hostsError: document.getElementById('hosts-error'),
            hostsTableContainer: document.getElementById('hosts-table-container'),
            hostsTableBody: document.getElementById('hosts-table-body'),
            noHosts: document.getElementById('no-hosts'),
            hostsCount: document.getElementById('hosts-count'),
            
            // Search and filter
            searchInput: document.getElementById('search-hosts'),
            statusFilter: document.getElementById('filter-status'),
            clearFilters: document.getElementById('clear-filters'),
            
            // Buttons
            refreshButton: document.getElementById('refresh-hosts'),
            retryButton: document.getElementById('retry-hosts'),
            
            // Modal
            hostDetailModal: document.getElementById('hostDetailModal'),
            hostDetailContent: document.getElementById('host-detail-content'),
            hostDetailLoading: document.getElementById('host-detail-loading'),
            hostDetailError: document.getElementById('host-detail-error')
        };
    }

    bindEvents() {
        // Search with debouncing
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', 
                debounce((e) => this.handleSearch(e.target.value), 300)
            );
        }

        // Status filter
        if (this.elements.statusFilter) {
            this.elements.statusFilter.addEventListener('change', (e) => {
                this.handleStatusFilter(e.target.value);
            });
        }

        // Clear filters
        if (this.elements.clearFilters) {
            this.elements.clearFilters.addEventListener('click', () => {
                this.clearFilters();
            });
        }

        // Refresh button
        if (this.elements.refreshButton) {
            this.elements.refreshButton.addEventListener('click', () => {
                this.loadHosts();
            });
        }

        // Retry button
        if (this.elements.retryButton) {
            this.elements.retryButton.addEventListener('click', () => {
                this.loadHosts();
            });
        }

        // Table sorting
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', (e) => {
                const field = e.currentTarget.dataset.sort;
                this.sortHosts(field);
            });
        });

        // Modal events
        if (this.elements.hostDetailModal) {
            this.elements.hostDetailModal.addEventListener('hidden.bs.modal', () => {
                this.clearHostDetail();
            });
        }
    }

    async loadHosts() {
        try {
            this.showLoading();
            
            const response = await api.getHosts();
            this.hosts = response.hosts || response || [];
            
            this.applyFilters();
            this.renderHosts();
            this.updateHostsCount();
            
            this.showTable();
            
        } catch (error) {
            console.error('Failed to load hosts:', error);
            this.showError(error.getUserMessage());
        }
    }

    showLoading() {
        hideElement(this.elements.hostsError);
        hideElement(this.elements.hostsTableContainer);
        hideElement(this.elements.noHosts);
        showElement(this.elements.loadingHosts);
    }

    showTable() {
        hideElement(this.elements.loadingHosts);
        hideElement(this.elements.hostsError);
        hideElement(this.elements.noHosts);
        showElement(this.elements.hostsTableContainer);
    }

    showError(message) {
        hideElement(this.elements.loadingHosts);
        hideElement(this.elements.hostsTableContainer);
        hideElement(this.elements.noHosts);
        
        this.elements.hostsError.querySelector('.error-message').textContent = message;
        showElement(this.elements.hostsError);
    }

    showNoHosts() {
        hideElement(this.elements.loadingHosts);
        hideElement(this.elements.hostsError);
        hideElement(this.elements.hostsTableContainer);
        showElement(this.elements.noHosts);
    }

    handleSearch(query) {
        this.searchQuery = query.toLowerCase();
        this.applyFilters();
        this.renderHosts();
        this.updateHostsCount();
    }

    handleStatusFilter(status) {
        this.statusFilter = status;
        this.applyFilters();
        this.renderHosts();
        this.updateHostsCount();
    }

    clearFilters() {
        this.searchQuery = '';
        this.statusFilter = '';
        
        if (this.elements.searchInput) {
            this.elements.searchInput.value = '';
        }
        if (this.elements.statusFilter) {
            this.elements.statusFilter.value = '';
        }
        
        this.applyFilters();
        this.renderHosts();
        this.updateHostsCount();
    }

    applyFilters() {
        this.filteredHosts = this.hosts.filter(host => {
            // Search filter
            if (this.searchQuery) {
                const searchMatch = 
                    host.hostname.toLowerCase().includes(this.searchQuery) ||
                    host.current_ip.toLowerCase().includes(this.searchQuery);
                if (!searchMatch) return false;
            }
            
            // Status filter
            if (this.statusFilter && host.status !== this.statusFilter) {
                return false;
            }
            
            return true;
        });
        
        this.sortHosts(this.currentSort.field, this.currentSort.direction, false);
    }

    sortHosts(field, direction = null, rerender = true) {
        // Toggle direction if same field
        if (field === this.currentSort.field && direction === null) {
            direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else if (direction === null) {
            direction = 'asc';
        }
        
        this.currentSort = { field, direction };
        
        this.filteredHosts.sort((a, b) => {
            let aVal = a[field];
            let bVal = b[field];
            
            // Handle dates
            if (field === 'last_seen' || field === 'first_seen') {
                aVal = new Date(aVal);
                bVal = new Date(bVal);
            }
            
            // Handle strings
            if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = bVal.toLowerCase();
            }
            
            let result = 0;
            if (aVal < bVal) result = -1;
            else if (aVal > bVal) result = 1;
            
            return direction === 'desc' ? -result : result;
        });
        
        if (rerender) {
            this.renderHosts();
            this.updateSortIndicators();
        }
    }

    updateSortIndicators() {
        // Reset all sort indicators
        document.querySelectorAll('.sortable').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Set current sort indicator
        const currentHeader = document.querySelector(`[data-sort="${this.currentSort.field}"]`);
        if (currentHeader) {
            currentHeader.classList.add(`sort-${this.currentSort.direction}`);
        }
    }

    renderHosts() {
        if (!this.elements.hostsTableBody) return;
        
        if (this.filteredHosts.length === 0) {
            if (this.hosts.length === 0) {
                this.showNoHosts();
            } else {
                // Show table with "no results" message
                this.elements.hostsTableBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-4">
                            <i class="bi bi-search fs-2 text-muted"></i>
                            <p class="mt-2 text-muted">No hosts match your search criteria</p>
                        </td>
                    </tr>
                `;
                this.showTable();
            }
            return;
        }
        
        const rows = this.filteredHosts.map(host => {
            return `
                <tr class="host-row" data-hostname="${escapeHtml(host.hostname)}">
                    <td>
                        <span class="cursor-pointer text-primary" onclick="hostManager.showHostDetail('${escapeHtml(host.hostname)}')">
                            ${escapeHtml(host.hostname)}
                        </span>
                    </td>
                    <td class="text-monospace">
                        <span class="cursor-pointer" onclick="copyToClipboard('${escapeHtml(host.current_ip)}')" title="Click to copy">
                            ${escapeHtml(host.current_ip)}
                        </span>
                    </td>
                    <td>
                        ${getStatusIcon(host.status)} ${getStatusBadge(host.status)}
                    </td>
                    <td>
                        <span title="${escapeHtml(new Date(host.last_seen).toLocaleString())}">
                            ${formatTimestamp(host.last_seen)}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="hostManager.showHostDetail('${escapeHtml(host.hostname)}')" title="View Details">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-secondary ms-1" onclick="copyToClipboard('${escapeHtml(host.current_ip)}')" title="Copy IP">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        
        this.elements.hostsTableBody.innerHTML = rows;
        this.showTable();
    }

    updateHostsCount() {
        if (!this.elements.hostsCount) return;
        
        const total = this.hosts.length;
        const filtered = this.filteredHosts.length;
        
        if (total === filtered) {
            this.elements.hostsCount.textContent = `${total} host${total !== 1 ? 's' : ''}`;
        } else {
            this.elements.hostsCount.textContent = `${filtered} of ${total} host${total !== 1 ? 's' : ''}`;
        }
    }

    async showHostDetail(hostname) {
        if (!this.elements.hostDetailModal) return;
        
        // Show modal
        const modal = new bootstrap.Modal(this.elements.hostDetailModal);
        modal.show();
        
        // Show loading state
        showElement(this.elements.hostDetailLoading);
        hideElement(this.elements.hostDetailContent);
        hideElement(this.elements.hostDetailError);
        
        try {
            const host = await api.getHost(hostname);
            this.renderHostDetail(host);
            
            hideElement(this.elements.hostDetailLoading);
            showElement(this.elements.hostDetailContent);
            
        } catch (error) {
            console.error('Failed to load host detail:', error);
            
            hideElement(this.elements.hostDetailLoading);
            hideElement(this.elements.hostDetailContent);
            
            this.elements.hostDetailError.querySelector('i').nextSibling.textContent = 
                ` ${error.getUserMessage()}`;
            showElement(this.elements.hostDetailError);
        }
    }

    renderHostDetail(host) {
        if (!this.elements.hostDetailContent) return;
        
        const timeSinceLastSeen = new Date() - new Date(host.last_seen);
        const isStale = timeSinceLastSeen > 300000; // 5 minutes
        
        this.elements.hostDetailContent.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="host-detail-item">
                        <div class="host-detail-label">Hostname</div>
                        <div class="host-detail-value">${escapeHtml(host.hostname)}</div>
                    </div>
                    <div class="host-detail-item">
                        <div class="host-detail-label">Current IP Address</div>
                        <div class="host-detail-value">
                            ${escapeHtml(host.current_ip)}
                            <button class="btn btn-sm btn-outline-secondary ms-2" onclick="copyToClipboard('${escapeHtml(host.current_ip)}')" title="Copy IP">
                                <i class="bi bi-clipboard"></i>
                            </button>
                        </div>
                    </div>
                    <div class="host-detail-item">
                        <div class="host-detail-label">Status</div>
                        <div class="host-detail-value">
                            ${getStatusIcon(host.status)} ${getStatusBadge(host.status)}
                            ${isStale ? '<span class="text-warning ms-2">(Stale)</span>' : ''}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="host-detail-item">
                        <div class="host-detail-label">First Seen</div>
                        <div class="host-detail-value">${formatTimestamp(host.first_seen, false)}</div>
                    </div>
                    <div class="host-detail-item">
                        <div class="host-detail-label">Last Seen</div>
                        <div class="host-detail-value">
                            ${formatTimestamp(host.last_seen, false)}
                            <br><small class="text-muted">(${formatTimestamp(host.last_seen, true)})</small>
                        </div>
                    </div>
                    <div class="host-detail-item">
                        <div class="host-detail-label">Time Since Last Contact</div>
                        <div class="host-detail-value">
                            ${formatUptime(Math.floor(timeSinceLastSeen / 1000))}
                            ${isStale ? '<span class="text-warning"> - Contact may be lost</span>' : ''}
                        </div>
                    </div>
                </div>
            </div>
            
            ${host.previous_ip ? `
                <hr>
                <div class="host-detail-item">
                    <div class="host-detail-label">Previous IP Address</div>
                    <div class="host-detail-value text-muted">${escapeHtml(host.previous_ip)}</div>
                </div>
            ` : ''}
            
            <hr>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">
                    Data refreshed: ${formatTimestamp(new Date())}
                </small>
                <button class="btn btn-sm btn-primary" onclick="hostManager.showHostDetail('${escapeHtml(host.hostname)}')">
                    <i class="bi bi-arrow-clockwise"></i> Refresh
                </button>
            </div>
        `;
    }

    clearHostDetail() {
        if (this.elements.hostDetailContent) {
            this.elements.hostDetailContent.innerHTML = '';
        }
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.autoRefreshEnabled) {
            this.refreshInterval = setInterval(() => {
                this.loadHosts();
            }, this.refreshIntervalMs);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    setAutoRefresh(enabled) {
        this.autoRefreshEnabled = enabled;
        if (enabled) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

// Global host manager instance
let hostManager = null;