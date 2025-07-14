/**
 * DNS Breadcrumb Navigation Component
 * Provides hierarchical navigation for DNS zones showing current path and allowing quick navigation to parent levels
 */

class DNSBreadcrumbNav {
    constructor(zonesManager) {
        this.zonesManager = zonesManager;
        this.currentPath = []; // Array of zone objects representing the path
        this.containerId = 'dns-breadcrumb-container';
    }

    /**
     * Set the current navigation path
     * @param {Array<Object>} path - Array of zone objects from root to current
     */
    setPath(path = []) {
        this.currentPath = path;
        this.render();
    }

    /**
     * Add a zone to the current path
     * @param {Object} zone - Zone object to add to path
     */
    addToPath(zone) {
        // Remove any existing occurrence of this zone (avoid duplicates)
        this.currentPath = this.currentPath.filter(z => z.id !== zone.id);
        this.currentPath.push(zone);
        this.render();
    }

    /**
     * Navigate to a specific zone in the path
     * @param {number} index - Index in the path to navigate to
     */
    navigateToIndex(index) {
        if (index >= 0 && index < this.currentPath.length) {
            // Truncate path to the selected index
            this.currentPath = this.currentPath.slice(0, index + 1);
            
            // If navigating to a zone, show its details
            if (index < this.currentPath.length - 1 || this.currentPath.length === 1) {
                const targetZone = this.currentPath[index];
                if (targetZone) {
                    this.zonesManager.showZoneDetail(targetZone.id);
                }
            }
            
            this.render();
        }
    }

    /**
     * Navigate to root (all zones)
     */
    navigateToRoot() {
        this.currentPath = [];
        this.render();
        // Close any open zone details and refresh zones view
        if (this.zonesManager) {
            this.zonesManager.loadZones();
        }
    }

    /**
     * Get the container element for the breadcrumb
     */
    getContainer() {
        let container = document.getElementById(this.containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = this.containerId;
            container.className = 'dns-breadcrumb-wrapper mb-3';
        }
        return container;
    }

    /**
     * Render the breadcrumb navigation
     */
    render() {
        const container = this.getContainer();
        
        if (this.currentPath.length === 0) {
            // Hide breadcrumb when at root level
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        
        // Build breadcrumb items
        const breadcrumbItems = [];
        
        // Always start with "All Zones" as root
        breadcrumbItems.push(`
            <li class="breadcrumb-item">
                <a href="#" class="text-decoration-none" onclick="dnsBreadcrumbNav.navigateToRoot(); return false;">
                    <i class="bi bi-house-door me-1"></i>All Zones
                </a>
            </li>
        `);

        // Add each zone in the path
        this.currentPath.forEach((zone, index) => {
            const isLast = index === this.currentPath.length - 1;
            const zoneName = zone.name.replace(/\.$/, ''); // Remove trailing dot for display
            
            if (isLast) {
                // Current zone - no link
                breadcrumbItems.push(`
                    <li class="breadcrumb-item active" aria-current="page">
                        <i class="bi bi-${zone.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                        ${this.escapeHtml(zoneName)}
                    </li>
                `);
            } else {
                // Parent zones - clickable
                breadcrumbItems.push(`
                    <li class="breadcrumb-item">
                        <a href="#" class="text-decoration-none" onclick="dnsBreadcrumbNav.navigateToIndex(${index}); return false;">
                            <i class="bi bi-${zone.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                            ${this.escapeHtml(zoneName)}
                        </a>
                    </li>
                `);
            }
        });

        // Render the complete breadcrumb
        container.innerHTML = `
            <nav aria-label="DNS zone navigation">
                <ol class="breadcrumb mb-0 bg-light p-3 rounded">
                    ${breadcrumbItems.join('')}
                </ol>
            </nav>
        `;
    }

    /**
     * Build path for a given zone by walking up the hierarchy
     * @param {Object} zone - Zone to build path for
     * @returns {Array<Object>} Path from root to zone
     */
    buildPathForZone(zone) {
        const path = [];
        let currentZone = zone;
        
        // Walk up the hierarchy
        while (currentZone) {
            path.unshift(currentZone); // Add to beginning
            
            // Find parent zone
            if (currentZone.parentZone) {
                currentZone = this.zonesManager.zones.find(z => z.name === currentZone.parentZone);
            } else {
                break;
            }
        }
        
        return path;
    }

    /**
     * Set path based on a zone (builds full hierarchy path)
     * @param {Object} zone - Zone to set as current
     */
    setPathForZone(zone) {
        const path = this.buildPathForZone(zone);
        this.setPath(path);
    }

    /**
     * Get mobile-friendly breadcrumb (collapsed view)
     */
    getMobileBreadcrumb() {
        if (this.currentPath.length <= 2) {
            return this.render(); // Show full breadcrumb for short paths
        }

        // For mobile, show: All Zones > ... > Parent > Current
        const first = this.currentPath[0];
        const last = this.currentPath[this.currentPath.length - 1];
        const secondLast = this.currentPath.length > 1 ? this.currentPath[this.currentPath.length - 2] : null;

        const breadcrumbItems = [];
        
        // All Zones
        breadcrumbItems.push(`
            <li class="breadcrumb-item">
                <a href="#" onclick="dnsBreadcrumbNav.navigateToRoot(); return false;">
                    <i class="bi bi-house-door"></i>
                </a>
            </li>
        `);

        // Ellipsis if path is long
        if (this.currentPath.length > 3) {
            breadcrumbItems.push(`
                <li class="breadcrumb-item">
                    <span class="text-muted">...</span>
                </li>
            `);
        }

        // Parent (if exists)
        if (secondLast) {
            const parentName = secondLast.name.replace(/\.$/, '');
            breadcrumbItems.push(`
                <li class="breadcrumb-item">
                    <a href="#" onclick="dnsBreadcrumbNav.navigateToIndex(${this.currentPath.length - 2}); return false;">
                        ${this.escapeHtml(parentName)}
                    </a>
                </li>
            `);
        }

        // Current zone
        const currentName = last.name.replace(/\.$/, '');
        breadcrumbItems.push(`
            <li class="breadcrumb-item active" aria-current="page">
                ${this.escapeHtml(currentName)}
            </li>
        `);

        return breadcrumbItems.join('');
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Insert breadcrumb into the DOM at the appropriate location
     */
    insertIntoDOM() {
        // Find the zones table container
        const zonesView = document.getElementById('dns-zones-view');
        if (!zonesView) return;

        // Look for the search/filter section
        const searchSection = zonesView.querySelector('.row:has(.form-control)');
        const container = this.getContainer();

        if (searchSection) {
            // Insert after search section
            searchSection.parentNode.insertBefore(container, searchSection.nextSibling);
        } else {
            // Fallback: insert at beginning of zones view
            zonesView.insertBefore(container, zonesView.firstChild);
        }
    }

    /**
     * Initialize the breadcrumb navigation
     */
    initialize() {
        this.insertIntoDOM();
        this.render();
    }

    /**
     * Show breadcrumb for zone detail modal
     * @param {Object} zone - Zone being viewed in detail
     */
    showInModal(zone) {
        const path = this.buildPathForZone(zone);
        
        // Create modal breadcrumb (simpler version)
        const breadcrumbItems = [];
        
        breadcrumbItems.push(`
            <li class="breadcrumb-item">
                <a href="#" class="text-decoration-none" onclick="dnsBreadcrumbNav.navigateToRoot(); return false;">
                    <i class="bi bi-house-door me-1"></i>All Zones
                </a>
            </li>
        `);

        path.forEach((z, index) => {
            const isLast = index === path.length - 1;
            const zoneName = z.name.replace(/\.$/, '');
            
            if (isLast) {
                breadcrumbItems.push(`
                    <li class="breadcrumb-item active" aria-current="page">
                        <i class="bi bi-${z.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                        ${this.escapeHtml(zoneName)}
                    </li>
                `);
            } else {
                breadcrumbItems.push(`
                    <li class="breadcrumb-item">
                        <a href="#" class="text-decoration-none" onclick="dnsBreadcrumbNav.navigateToIndex(${index}); return false;">
                            <i class="bi bi-${z.isSubdomain ? 'folder' : 'globe2'} me-1"></i>
                            ${this.escapeHtml(zoneName)}
                        </a>
                    </li>
                `);
            }
        });

        return `
            <nav aria-label="DNS zone navigation" class="mb-3">
                <ol class="breadcrumb mb-0 bg-light p-2 rounded">
                    ${breadcrumbItems.join('')}
                </ol>
            </nav>
        `;
    }
}

// Export for use in other modules
window.DNSBreadcrumbNav = DNSBreadcrumbNav;