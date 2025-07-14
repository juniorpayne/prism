/**
 * DNS Search and Filter Module
 * Provides advanced search and filtering capabilities for DNS zones and records
 */

class DNSSearchFilter {
    constructor() {
        this.searchHistory = [];
        this.savedFilters = {};
        this.activeFilters = {
            search: '',
            status: 'all',
            type: 'all',
            recordCountMin: null,
            recordCountMax: null,
            lastModifiedFrom: null,
            lastModifiedTo: null,
            useRegex: false,
            caseSensitive: false,
            // Hierarchy-aware search options
            useWildcard: false,
            pathSearch: false,
            depthLevel: 'all'
        };
        this.debounceTimer = null;
        this.loadSavedData();
    }

    /**
     * Load saved search history and filters from localStorage
     */
    loadSavedData() {
        try {
            const history = localStorage.getItem('dns-search-history');
            if (history) {
                this.searchHistory = JSON.parse(history);
            }
            
            const filters = localStorage.getItem('dns-saved-filters');
            if (filters) {
                this.savedFilters = JSON.parse(filters);
            }
        } catch (error) {
            console.error('Error loading saved search data:', error);
        }
    }

    /**
     * Save search history to localStorage
     */
    saveSearchHistory() {
        try {
            // Keep only last 20 searches
            this.searchHistory = this.searchHistory.slice(-20);
            localStorage.setItem('dns-search-history', JSON.stringify(this.searchHistory));
        } catch (error) {
            console.error('Error saving search history:', error);
        }
    }

    /**
     * Add search term to history
     */
    addToHistory(searchTerm) {
        if (searchTerm && !this.searchHistory.includes(searchTerm)) {
            this.searchHistory.push(searchTerm);
            this.saveSearchHistory();
        }
    }

    /**
     * Create advanced filter UI
     */
    createFilterUI() {
        return `
            <div class="row mb-3">
                <!-- Enhanced Search Bar -->
                <div class="col-md-6">
                    <div class="position-relative">
                        <div class="input-group">
                            <span class="input-group-text">
                                <i class="bi bi-search"></i>
                            </span>
                            <input type="text" class="form-control" id="search-zones" 
                                   placeholder="Search zones, paths, wildcards (e.g., *.example.com)..."
                                   autocomplete="off">
                            <button class="btn btn-outline-secondary dropdown-toggle" 
                                    type="button" id="searchOptionsBtn"
                                    data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-gear"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="searchOptionsBtn">
                                <li class="px-3 py-2">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="useWildcard">
                                        <label class="form-check-label" for="useWildcard">
                                            Enable Wildcards (*)
                                        </label>
                                    </div>
                                </li>
                                <li class="px-3 py-2">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="pathSearch">
                                        <label class="form-check-label" for="pathSearch">
                                            Path-based Search
                                        </label>
                                    </div>
                                </li>
                                <li class="px-3 py-2">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="useRegex">
                                        <label class="form-check-label" for="useRegex">
                                            Use Regular Expression
                                        </label>
                                    </div>
                                </li>
                                <li class="px-3 py-2">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="caseSensitive">
                                        <label class="form-check-label" for="caseSensitive">
                                            Case Sensitive
                                        </label>
                                    </div>
                                </li>
                                <li><hr class="dropdown-divider"></li>
                                <li>
                                    <a class="dropdown-item" href="#" id="clearSearchHistory">
                                        <i class="bi bi-trash me-2"></i>Clear History
                                    </a>
                                </li>
                            </ul>
                        </div>
                        <!-- Search Suggestions Dropdown -->
                        <div class="dropdown-menu w-100" id="searchSuggestions" style="display: none;">
                            <!-- Suggestions will be populated here -->
                        </div>
                    </div>
                </div>
                
                <!-- Filter Controls -->
                <div class="col-md-6">
                    <div class="d-flex gap-2 justify-content-end">
                        <!-- Filter Button -->
                        <button class="btn btn-outline-primary" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#advancedFilters">
                            <i class="bi bi-funnel"></i> Filters
                            <span class="badge bg-primary ms-1" id="activeFilterCount" style="display: none;">0</span>
                        </button>
                        
                        <!-- Saved Filters Dropdown -->
                        <div class="dropdown">
                            <button class="btn btn-outline-secondary dropdown-toggle" type="button"
                                    id="savedFiltersBtn" data-bs-toggle="dropdown">
                                <i class="bi bi-bookmark"></i>
                            </button>
                            <ul class="dropdown-menu" aria-labelledby="savedFiltersBtn">
                                <li class="px-3 py-2">
                                    <strong>Saved Filters</strong>
                                </li>
                                <li><hr class="dropdown-divider"></li>
                                <li id="savedFiltersList">
                                    <span class="dropdown-item-text text-muted">No saved filters</span>
                                </li>
                                <li><hr class="dropdown-divider"></li>
                                <li>
                                    <a class="dropdown-item" href="#" id="saveCurrentFilter">
                                        <i class="bi bi-plus-circle me-2"></i>Save Current Filter
                                    </a>
                                </li>
                            </ul>
                        </div>
                        
                        <!-- Refresh Button -->
                        <button class="btn btn-outline-secondary" id="refresh-zones">
                            <i class="bi bi-arrow-clockwise"></i> Refresh
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Advanced Filters Panel -->
            <div class="collapse" id="advancedFilters">
                <div class="card card-body mb-3">
                    <div class="row g-3">
                        <!-- Status Filter -->
                        <div class="col-md-3">
                            <label for="filterStatus" class="form-label">Status</label>
                            <select class="form-select" id="filterStatus">
                                <option value="all">All</option>
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                                <option value="dnssec">DNSSEC Enabled</option>
                            </select>
                        </div>
                        
                        <!-- Type Filter -->
                        <div class="col-md-3">
                            <label for="filterType" class="form-label">Zone Type</label>
                            <select class="form-select" id="filterType">
                                <option value="all">All</option>
                                <option value="Native">Master</option>
                                <option value="Slave">Slave</option>
                            </select>
                        </div>
                        
                        <!-- Domain Depth Filter -->
                        <div class="col-md-3">
                            <label for="filterDepth" class="form-label">Domain Level</label>
                            <select class="form-select" id="filterDepth">
                                <option value="all">All Levels</option>
                                <option value="root">Root Domains</option>
                                <option value="2">2nd Level</option>
                                <option value="3">3rd Level</option>
                                <option value="4">4th Level</option>
                                <option value="5+">5+ Levels</option>
                            </select>
                        </div>
                        
                        <!-- Record Count Range -->
                        <div class="col-md-3">
                            <label class="form-label">Record Count</label>
                            <div class="input-group input-group-sm">
                                <input type="number" class="form-control" id="recordCountMin" 
                                       placeholder="Min" min="0">
                                <span class="input-group-text">-</span>
                                <input type="number" class="form-control" id="recordCountMax" 
                                       placeholder="Max" min="0">
                            </div>
                        </div>
                        
                        <!-- Date Range -->
                        <div class="col-md-4">
                            <label class="form-label">Last Modified</label>
                            <select class="form-select" id="dateRangeQuick">
                                <option value="">Any time</option>
                                <option value="today">Today</option>
                                <option value="week">Last 7 days</option>
                                <option value="month">Last 30 days</option>
                                <option value="custom">Custom range...</option>
                            </select>
                        </div>
                        
                        <!-- Custom Date Range (hidden by default) -->
                        <div class="col-12" id="customDateRange" style="display: none;">
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <input type="date" class="form-control" id="dateFrom" 
                                           placeholder="From date">
                                </div>
                                <div class="col-md-6">
                                    <input type="date" class="form-control" id="dateTo" 
                                           placeholder="To date">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Filter Actions -->
                        <div class="col-12 text-end">
                            <button class="btn btn-sm btn-secondary" id="clearFilters">
                                <i class="bi bi-x-circle me-1"></i>Clear Filters
                            </button>
                            <button class="btn btn-sm btn-primary" id="applyFilters">
                                <i class="bi bi-check-circle me-1"></i>Apply Filters
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Initialize filter event handlers
     */
    initializeEventHandlers(onFilterChange) {
        // Search input with debouncing
        const searchInput = document.getElementById('search-zones');
        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.activeFilters.search = e.target.value;
                this.showSearchSuggestions(e.target.value);
                onFilterChange(this.activeFilters);
            }, 300);
        });

        // Search on Enter
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.addToHistory(e.target.value);
                this.hideSearchSuggestions();
            }
        });

        // Search options
        document.getElementById('useWildcard').addEventListener('change', (e) => {
            this.activeFilters.useWildcard = e.target.checked;
            // Disable regex if wildcard is enabled
            if (e.target.checked) {
                document.getElementById('useRegex').checked = false;
                this.activeFilters.useRegex = false;
            }
            onFilterChange(this.activeFilters);
        });

        document.getElementById('pathSearch').addEventListener('change', (e) => {
            this.activeFilters.pathSearch = e.target.checked;
            onFilterChange(this.activeFilters);
        });

        document.getElementById('useRegex').addEventListener('change', (e) => {
            this.activeFilters.useRegex = e.target.checked;
            // Disable wildcard if regex is enabled
            if (e.target.checked) {
                document.getElementById('useWildcard').checked = false;
                this.activeFilters.useWildcard = false;
            }
            onFilterChange(this.activeFilters);
        });

        document.getElementById('caseSensitive').addEventListener('change', (e) => {
            this.activeFilters.caseSensitive = e.target.checked;
            onFilterChange(this.activeFilters);
        });

        // Clear search history
        document.getElementById('clearSearchHistory').addEventListener('click', (e) => {
            e.preventDefault();
            this.searchHistory = [];
            this.saveSearchHistory();
            this.hideSearchSuggestions();
        });

        // Date range quick select
        document.getElementById('dateRangeQuick').addEventListener('change', (e) => {
            const customRange = document.getElementById('customDateRange');
            if (e.target.value === 'custom') {
                customRange.style.display = 'block';
            } else {
                customRange.style.display = 'none';
                this.applyDateRangeFilter(e.target.value);
            }
        });

        // Apply filters button
        document.getElementById('applyFilters').addEventListener('click', () => {
            this.applyAllFilters();
            onFilterChange(this.activeFilters);
        });

        // Clear filters button
        document.getElementById('clearFilters').addEventListener('click', () => {
            this.clearAllFilters();
            onFilterChange(this.activeFilters);
        });

        // Save current filter
        document.getElementById('saveCurrentFilter').addEventListener('click', (e) => {
            e.preventDefault();
            this.saveCurrentFilter();
        });

        // Click outside to hide suggestions
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.position-relative')) {
                this.hideSearchSuggestions();
            }
        });
    }

    /**
     * Show search suggestions
     */
    showSearchSuggestions(searchTerm) {
        const suggestionsDiv = document.getElementById('searchSuggestions');
        
        if (!searchTerm) {
            // Show search history
            if (this.searchHistory.length > 0) {
                let html = '<h6 class="dropdown-header">Recent Searches</h6>';
                this.searchHistory.slice(-5).reverse().forEach(term => {
                    html += `<a class="dropdown-item search-suggestion" href="#">
                        <i class="bi bi-clock-history me-2"></i>${this.escapeHtml(term)}
                    </a>`;
                });
                suggestionsDiv.innerHTML = html;
                suggestionsDiv.style.display = 'block';
                
                // Add click handlers
                suggestionsDiv.querySelectorAll('.search-suggestion').forEach(item => {
                    item.addEventListener('click', (e) => {
                        e.preventDefault();
                        document.getElementById('search-zones').value = item.textContent.trim();
                        this.activeFilters.search = item.textContent.trim();
                        this.hideSearchSuggestions();
                    });
                });
            } else {
                this.hideSearchSuggestions();
            }
        } else {
            // Show hierarchy-aware suggestions
            this.showHierarchySuggestions(searchTerm);
        }
    }

    /**
     * Show hierarchy-aware search suggestions
     */
    showHierarchySuggestions(searchTerm) {
        const suggestionsDiv = document.getElementById('searchSuggestions');
        const suggestions = [];
        
        // Get zones from the zones manager
        const zones = window.dnsZonesManager?.zones || [];
        const searchLower = searchTerm.toLowerCase();
        
        // Find matching zones
        zones.forEach(zone => {
            const zoneLower = zone.name.toLowerCase();
            if (zoneLower.includes(searchLower)) {
                suggestions.push({
                    type: 'zone',
                    name: zone.name,
                    isSubdomain: zone.isSubdomain,
                    depth: this.getDomainDepth(zone.name)
                });
            }
        });
        
        // Add wildcard suggestions if appropriate
        if (this.activeFilters.useWildcard && searchTerm.length > 2) {
            suggestions.push({
                type: 'wildcard',
                name: `*.${searchTerm}`,
                description: 'All subdomains'
            });
        }
        
        // Add path search suggestion
        if (this.activeFilters.pathSearch && searchTerm.includes('.')) {
            suggestions.push({
                type: 'path',
                name: searchTerm,
                description: 'Path-based search'
            });
        }
        
        // Limit suggestions
        const limitedSuggestions = suggestions.slice(0, 10);
        
        if (limitedSuggestions.length > 0) {
            let html = '<h6 class="dropdown-header">Suggestions</h6>';
            
            limitedSuggestions.forEach(suggestion => {
                const icon = suggestion.type === 'zone' ? 
                    (suggestion.isSubdomain ? 'bi-folder' : 'bi-globe2') :
                    suggestion.type === 'wildcard' ? 'bi-asterisk' : 'bi-diagram-3';
                    
                const depth = suggestion.depth ? ` <small class="text-muted">(Level ${suggestion.depth})</small>` : '';
                const desc = suggestion.description ? ` <small class="text-muted">- ${suggestion.description}</small>` : '';
                
                html += `<a class="dropdown-item search-suggestion" href="#" data-value="${this.escapeHtml(suggestion.name)}">
                    <i class="bi ${icon} me-2"></i>${this.escapeHtml(suggestion.name)}${depth}${desc}
                </a>`;
            });
            
            suggestionsDiv.innerHTML = html;
            suggestionsDiv.style.display = 'block';
            
            // Add click handlers
            suggestionsDiv.querySelectorAll('.search-suggestion').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const value = item.dataset.value;
                    document.getElementById('search-zones').value = value;
                    this.activeFilters.search = value;
                    this.hideSearchSuggestions();
                    
                    // Trigger search
                    if (window.dnsZonesManager) {
                        window.dnsZonesManager.applyFilters(this.activeFilters);
                    }
                });
            });
        } else {
            this.hideSearchSuggestions();
        }
    }

    /**
     * Hide search suggestions
     */
    hideSearchSuggestions() {
        document.getElementById('searchSuggestions').style.display = 'none';
    }

    /**
     * Apply date range filter
     */
    applyDateRangeFilter(range) {
        const today = new Date();
        let fromDate = null;
        
        switch (range) {
            case 'today':
                fromDate = new Date(today.setHours(0, 0, 0, 0));
                break;
            case 'week':
                fromDate = new Date(today.setDate(today.getDate() - 7));
                break;
            case 'month':
                fromDate = new Date(today.setDate(today.getDate() - 30));
                break;
        }
        
        this.activeFilters.lastModifiedFrom = fromDate;
        this.activeFilters.lastModifiedTo = new Date();
    }

    /**
     * Apply all filters from the form
     */
    applyAllFilters() {
        this.activeFilters.status = document.getElementById('filterStatus').value;
        this.activeFilters.type = document.getElementById('filterType').value;
        this.activeFilters.depthLevel = document.getElementById('filterDepth').value;
        this.activeFilters.recordCountMin = parseInt(document.getElementById('recordCountMin').value) || null;
        this.activeFilters.recordCountMax = parseInt(document.getElementById('recordCountMax').value) || null;
        
        // Custom date range
        const dateFrom = document.getElementById('dateFrom').value;
        const dateTo = document.getElementById('dateTo').value;
        if (dateFrom) {
            this.activeFilters.lastModifiedFrom = new Date(dateFrom);
        }
        if (dateTo) {
            this.activeFilters.lastModifiedTo = new Date(dateTo);
        }
        
        this.updateActiveFilterCount();
    }

    /**
     * Clear all filters
     */
    clearAllFilters() {
        this.activeFilters = {
            search: '',
            status: 'all',
            type: 'all',
            recordCountMin: null,
            recordCountMax: null,
            lastModifiedFrom: null,
            lastModifiedTo: null,
            useRegex: false,
            caseSensitive: false,
            useWildcard: false,
            pathSearch: false,
            depthLevel: 'all'
        };
        
        // Reset form
        document.getElementById('search-zones').value = '';
        document.getElementById('filterStatus').value = 'all';
        document.getElementById('filterType').value = 'all';
        document.getElementById('filterDepth').value = 'all';
        document.getElementById('recordCountMin').value = '';
        document.getElementById('recordCountMax').value = '';
        document.getElementById('dateRangeQuick').value = '';
        document.getElementById('dateFrom').value = '';
        document.getElementById('dateTo').value = '';
        document.getElementById('useWildcard').checked = false;
        document.getElementById('pathSearch').checked = false;
        document.getElementById('useRegex').checked = false;
        document.getElementById('caseSensitive').checked = false;
        
        this.updateActiveFilterCount();
    }

    /**
     * Update active filter count badge
     */
    updateActiveFilterCount() {
        let count = 0;
        
        if (this.activeFilters.search) count++;
        if (this.activeFilters.status !== 'all') count++;
        if (this.activeFilters.type !== 'all') count++;
        if (this.activeFilters.depthLevel !== 'all') count++;
        if (this.activeFilters.recordCountMin !== null || this.activeFilters.recordCountMax !== null) count++;
        if (this.activeFilters.lastModifiedFrom || this.activeFilters.lastModifiedTo) count++;
        if (this.activeFilters.useWildcard) count++;
        if (this.activeFilters.pathSearch) count++;
        if (this.activeFilters.useRegex) count++;
        if (this.activeFilters.caseSensitive) count++;
        
        const badge = document.getElementById('activeFilterCount');
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }

    /**
     * Save current filter configuration
     */
    saveCurrentFilter() {
        const name = prompt('Enter a name for this filter:');
        if (name) {
            this.savedFilters[name] = { ...this.activeFilters };
            localStorage.setItem('dns-saved-filters', JSON.stringify(this.savedFilters));
            this.updateSavedFiltersList();
        }
    }

    /**
     * Update saved filters dropdown
     */
    updateSavedFiltersList() {
        const listElement = document.getElementById('savedFiltersList');
        const filterNames = Object.keys(this.savedFilters);
        
        if (filterNames.length === 0) {
            listElement.innerHTML = '<span class="dropdown-item-text text-muted">No saved filters</span>';
        } else {
            listElement.innerHTML = filterNames.map(name => `
                <div class="d-flex justify-content-between align-items-center">
                    <a class="dropdown-item filter-load" href="#" data-filter="${name}">
                        ${this.escapeHtml(name)}
                    </a>
                    <button class="btn btn-sm btn-link text-danger filter-delete" 
                            data-filter="${name}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `).join('');
            
            // Add event handlers
            listElement.querySelectorAll('.filter-load').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.loadSavedFilter(item.dataset.filter);
                });
            });
            
            listElement.querySelectorAll('.filter-delete').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.deleteSavedFilter(btn.dataset.filter);
                });
            });
        }
    }

    /**
     * Load a saved filter
     */
    loadSavedFilter(name) {
        if (this.savedFilters[name]) {
            this.activeFilters = { ...this.savedFilters[name] };
            // Update UI to reflect loaded filter
            // This would need to be implemented based on the actual UI elements
        }
    }

    /**
     * Delete a saved filter
     */
    deleteSavedFilter(name) {
        delete this.savedFilters[name];
        localStorage.setItem('dns-saved-filters', JSON.stringify(this.savedFilters));
        this.updateSavedFiltersList();
    }

    /**
     * Filter zones based on active filters
     */
    filterZones(zones) {
        return zones.filter(zone => {
            // Depth level filter
            if (this.activeFilters.depthLevel !== 'all') {
                const depth = this.getDomainDepth(zone.name);
                
                if (this.activeFilters.depthLevel === 'root' && depth !== 2) return false;
                if (this.activeFilters.depthLevel === '2' && depth !== 2) return false;
                if (this.activeFilters.depthLevel === '3' && depth !== 3) return false;
                if (this.activeFilters.depthLevel === '4' && depth !== 4) return false;
                if (this.activeFilters.depthLevel === '5+' && depth < 5) return false;
            }
            
            // Search filter - now includes wildcard and path-based search
            if (this.activeFilters.search) {
                const searchTerm = this.activeFilters.search;
                const searchLower = this.activeFilters.caseSensitive ? searchTerm : searchTerm.toLowerCase();
                
                let matches = false;
                
                // Wildcard search
                if (this.activeFilters.useWildcard && (searchTerm.includes('*') || searchTerm.includes('?'))) {
                    try {
                        const wildcardRegex = this.wildcardToRegex(searchTerm);
                        matches = wildcardRegex.test(zone.name);
                        
                        // Also check nameservers
                        if (!matches && zone.nameservers) {
                            matches = zone.nameservers.some(ns => wildcardRegex.test(ns));
                        }
                    } catch (e) {
                        console.error('Wildcard search error:', e);
                        matches = this.performBasicSearch(zone, searchLower);
                    }
                }
                // Path-based search
                else if (this.activeFilters.pathSearch) {
                    matches = this.matchesPathSearch(zone.name, searchTerm);
                }
                // Regex search
                else if (this.activeFilters.useRegex) {
                    try {
                        const regex = new RegExp(searchTerm, this.activeFilters.caseSensitive ? 'g' : 'gi');
                        // Check zone name
                        if (regex.test(zone.name)) {
                            matches = true;
                        }
                        // Check nameservers
                        if (!matches && zone.nameservers) {
                            matches = zone.nameservers.some(ns => regex.test(ns));
                        }
                    } catch (e) {
                        // Invalid regex, fall back to regular search
                        matches = this.performBasicSearch(zone, searchLower);
                    }
                } else {
                    matches = this.performBasicSearch(zone, searchLower);
                }
                
                if (!matches) return false;
            }
            
            // Status filter
            if (this.activeFilters.status !== 'all') {
                if (this.activeFilters.status === 'active' && zone.dnssec) return false;
                if (this.activeFilters.status === 'inactive' && !zone.dnssec) return false;
                if (this.activeFilters.status === 'dnssec' && !zone.dnssec) return false;
            }
            
            // Type filter
            if (this.activeFilters.type !== 'all' && zone.kind !== this.activeFilters.type) {
                return false;
            }
            
            // Record count filter would need to be implemented with actual record counts
            
            // Date filter would need to be implemented with actual dates
            
            return true;
        });
    }

    /**
     * Highlight search terms in text
     */
    highlightSearchTerm(text, searchTerm) {
        if (!searchTerm || !text) return text;
        
        // Wildcard highlighting
        if (this.activeFilters.useWildcard && (searchTerm.includes('*') || searchTerm.includes('?'))) {
            try {
                // Convert wildcard to regex for matching
                const wildcardRegex = this.wildcardToRegex(searchTerm);
                const matches = text.match(wildcardRegex);
                if (matches) {
                    // Highlight the entire match
                    return text.replace(wildcardRegex, '<mark>$&</mark>');
                }
            } catch (e) {
                // Fall back to basic highlighting
            }
        }
        
        // Path-based highlighting
        if (this.activeFilters.pathSearch) {
            const searchParts = searchTerm.split('.');
            let highlightedText = text;
            
            searchParts.forEach(part => {
                if (part) {
                    const partRegex = new RegExp(`(${this.escapeRegex(part)})`, this.activeFilters.caseSensitive ? 'g' : 'gi');
                    highlightedText = highlightedText.replace(partRegex, '<mark>$1</mark>');
                }
            });
            
            return highlightedText;
        }
        
        // Regex highlighting
        if (this.activeFilters.useRegex) {
            try {
                const regex = new RegExp(`(${searchTerm})`, this.activeFilters.caseSensitive ? 'g' : 'gi');
                return text.replace(regex, '<mark>$1</mark>');
            } catch (e) {
                // Invalid regex, fall back to regular highlight
            }
        }
        
        // Basic highlighting
        const flags = this.activeFilters.caseSensitive ? 'g' : 'gi';
        const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, flags);
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape regex special characters
     */
    escapeRegex(text) {
        return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Convert wildcard pattern to regex
     */
    wildcardToRegex(pattern) {
        // Escape special regex chars except * and ?
        let regex = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
        // Replace wildcards with regex equivalents
        regex = regex.replace(/\*/g, '.*');
        regex = regex.replace(/\?/g, '.');
        return new RegExp('^' + regex + '$', this.activeFilters.caseSensitive ? '' : 'i');
    }

    /**
     * Get domain depth level
     */
    getDomainDepth(domain) {
        // Remove trailing dot
        const cleanDomain = domain.endsWith('.') ? domain.slice(0, -1) : domain;
        const parts = cleanDomain.split('.');
        return parts.length;
    }

    /**
     * Check if domain matches path search
     */
    matchesPathSearch(domain, searchTerm) {
        // Remove trailing dots
        const cleanDomain = domain.endsWith('.') ? domain.slice(0, -1) : domain;
        const cleanSearch = searchTerm.endsWith('.') ? searchTerm.slice(0, -1) : searchTerm;
        
        // Split into parts
        const domainParts = cleanDomain.split('.');
        const searchParts = cleanSearch.split('.');
        
        // Check if search parts exist in domain in order
        let searchIndex = 0;
        for (let i = 0; i < domainParts.length && searchIndex < searchParts.length; i++) {
            const domainPart = this.activeFilters.caseSensitive ? domainParts[i] : domainParts[i].toLowerCase();
            const searchPart = this.activeFilters.caseSensitive ? searchParts[searchIndex] : searchParts[searchIndex].toLowerCase();
            
            if (domainPart === searchPart || domainPart.includes(searchPart)) {
                searchIndex++;
            }
        }
        
        return searchIndex === searchParts.length;
    }

    /**
     * Perform basic search on zone
     */
    performBasicSearch(zone, searchLower) {
        // Check zone name
        const zoneName = this.activeFilters.caseSensitive ? zone.name : zone.name.toLowerCase();
        if (zoneName.includes(searchLower)) {
            return true;
        }
        
        // Check nameservers
        if (zone.nameservers) {
            const nameserversMatch = zone.nameservers.some(ns => {
                const nsLower = this.activeFilters.caseSensitive ? ns : ns.toLowerCase();
                return nsLower.includes(searchLower);
            });
            if (nameserversMatch) return true;
        }
        
        return false;
    }

    /**
     * Search within zone records (for enhanced search)
     * This would need the full zone data with rrsets
     */
    async searchInZoneRecords(zoneId, searchTerm) {
        try {
            // This would be implemented when we have access to full zone data
            // For now, we'll return false
            return false;
        } catch (error) {
            console.error('Error searching in zone records:', error);
            return false;
        }
    }
}

// Export for use in other modules
window.DNSSearchFilter = DNSSearchFilter;