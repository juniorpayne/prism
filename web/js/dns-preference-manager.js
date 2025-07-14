/**
 * DNS Preference Manager
 * Manages user preferences for DNS zone view including tree state, view mode, and filters
 */

class DNSPreferenceManager {
    constructor() {
        this.STORAGE_KEY = 'dns-zone-preferences';
        this.preferences = this.loadPreferences();
    }

    /**
     * Default preferences
     */
    getDefaultPreferences() {
        return {
            viewMode: 'tree', // 'tree' or 'flat'
            expandedZones: new Set(), // Set of expanded zone IDs
            expandAll: false, // Expand all preference
            sortColumn: 'name',
            sortDirection: 'asc',
            itemsPerPage: 10,
            activeFilters: {
                search: '',
                status: 'all',
                type: 'all',
                depthLevel: 'all',
                useWildcard: false,
                pathSearch: false,
                useRegex: false,
                caseSensitive: false
            },
            lastModified: new Date().toISOString()
        };
    }

    /**
     * Load preferences from localStorage
     */
    loadPreferences() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Convert expandedZones array back to Set
                if (parsed.expandedZones) {
                    parsed.expandedZones = new Set(parsed.expandedZones);
                }
                return { ...this.getDefaultPreferences(), ...parsed };
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
        return this.getDefaultPreferences();
    }

    /**
     * Save preferences to localStorage
     */
    savePreferences() {
        try {
            // Convert Set to array for storage
            const toStore = {
                ...this.preferences,
                expandedZones: Array.from(this.preferences.expandedZones),
                lastModified: new Date().toISOString()
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(toStore));
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }

    /**
     * Get current view mode
     */
    getViewMode() {
        return this.preferences.viewMode;
    }

    /**
     * Set view mode
     */
    setViewMode(mode) {
        if (mode === 'tree' || mode === 'flat') {
            this.preferences.viewMode = mode;
            this.savePreferences();
        }
    }

    /**
     * Check if a zone is expanded
     */
    isZoneExpanded(zoneId) {
        return this.preferences.expandedZones.has(zoneId);
    }

    /**
     * Toggle zone expansion
     */
    toggleZoneExpansion(zoneId) {
        if (this.preferences.expandedZones.has(zoneId)) {
            this.preferences.expandedZones.delete(zoneId);
        } else {
            this.preferences.expandedZones.add(zoneId);
        }
        this.savePreferences();
    }

    /**
     * Set zone expansion state
     */
    setZoneExpanded(zoneId, expanded) {
        if (expanded) {
            this.preferences.expandedZones.add(zoneId);
        } else {
            this.preferences.expandedZones.delete(zoneId);
        }
        this.savePreferences();
    }

    /**
     * Expand all zones
     */
    expandAllZones(zoneIds) {
        this.preferences.expandedZones = new Set(zoneIds);
        this.preferences.expandAll = true;
        this.savePreferences();
    }

    /**
     * Collapse all zones
     */
    collapseAllZones() {
        this.preferences.expandedZones.clear();
        this.preferences.expandAll = false;
        this.savePreferences();
    }

    /**
     * Get sort preferences
     */
    getSortPreferences() {
        return {
            column: this.preferences.sortColumn,
            direction: this.preferences.sortDirection
        };
    }

    /**
     * Set sort preferences
     */
    setSortPreferences(column, direction) {
        this.preferences.sortColumn = column;
        this.preferences.sortDirection = direction;
        this.savePreferences();
    }

    /**
     * Get items per page
     */
    getItemsPerPage() {
        return this.preferences.itemsPerPage;
    }

    /**
     * Set items per page
     */
    setItemsPerPage(count) {
        this.preferences.itemsPerPage = count;
        this.savePreferences();
    }

    /**
     * Get active filters
     */
    getActiveFilters() {
        return { ...this.preferences.activeFilters };
    }

    /**
     * Update filters
     */
    updateFilters(filters) {
        this.preferences.activeFilters = { ...this.preferences.activeFilters, ...filters };
        this.savePreferences();
    }

    /**
     * Reset all preferences
     */
    resetPreferences() {
        this.preferences = this.getDefaultPreferences();
        this.savePreferences();
    }

    /**
     * Reset only tree state
     */
    resetTreeState() {
        this.preferences.expandedZones.clear();
        this.preferences.expandAll = false;
        this.savePreferences();
    }

    /**
     * Export preferences (for debugging/backup)
     */
    exportPreferences() {
        return JSON.stringify(this.preferences, null, 2);
    }

    /**
     * Import preferences
     */
    importPreferences(json) {
        try {
            const imported = JSON.parse(json);
            if (imported.expandedZones) {
                imported.expandedZones = new Set(imported.expandedZones);
            }
            this.preferences = { ...this.getDefaultPreferences(), ...imported };
            this.savePreferences();
            return true;
        } catch (error) {
            console.error('Error importing preferences:', error);
            return false;
        }
    }
}

// Create singleton instance
window.dnsPreferenceManager = new DNSPreferenceManager();