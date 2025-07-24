/**
 * Host User Filtering Enhancement for Prism DNS Web Interface
 * Adds support for user-specific host views and admin toggles
 */

class HostUserFiltering {
    constructor(hostManager) {
        this.hostManager = hostManager;
        this.showAllHosts = false;
        this.isAdmin = false;
        
        this.initializeElements();
        this.checkUserPermissions();
    }
    
    initializeElements() {
        // Create admin controls container
        const hostsHeader = document.querySelector('.hosts-header') || 
                           document.querySelector('.card-header') ||
                           document.querySelector('h2');
                           
        if (hostsHeader && this.isAdmin) {
            this.createAdminToggle(hostsHeader);
        }
    }
    
    async checkUserPermissions() {
        try {
            const user = await this.getCurrentUser();
            this.isAdmin = user && user.is_admin;
            
            if (this.isAdmin) {
                this.createAdminToggle();
            }
        } catch (error) {
            console.error('Failed to check user permissions:', error);
        }
    }
    
    async getCurrentUser() {
        try {
            const response = await api.get('/auth/me');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to get current user:', error);
        }
        return null;
    }
    
    createAdminToggle(container) {
        // Don't create if already exists
        if (document.getElementById('admin-host-controls')) {
            return;
        }
        
        const adminControls = document.createElement('div');
        adminControls.id = 'admin-host-controls';
        adminControls.className = 'admin-controls mt-3';
        adminControls.innerHTML = `
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="show-all-hosts" 
                       ${this.showAllHosts ? 'checked' : ''}>
                <label class="form-check-label" for="show-all-hosts">
                    Show all users' hosts
                </label>
            </div>
        `;
        
        // Find appropriate container or create one
        if (!container) {
            const mainContent = document.querySelector('.card-body') || 
                              document.querySelector('.container');
            if (mainContent) {
                container = mainContent;
            }
        }
        
        if (container) {
            // Insert after the header
            const headerElement = container.querySelector('h2, h3, .card-header');
            if (headerElement && headerElement.nextSibling) {
                headerElement.parentNode.insertBefore(adminControls, headerElement.nextSibling);
            } else {
                container.prepend(adminControls);
            }
        }
        
        // Bind toggle event
        const toggle = document.getElementById('show-all-hosts');
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                this.showAllHosts = e.target.checked;
                this.updateHostDisplay();
            });
        }
    }
    
    async updateHostDisplay() {
        // Update the API call in the host manager
        const originalGetHosts = api.getHosts.bind(api);
        
        // Override the getHosts method temporarily
        api.getHosts = async (params = {}) => {
            if (this.showAllHosts && this.isAdmin) {
                params.all = true;
            }
            return originalGetHosts(params);
        };
        
        // Reload hosts with new parameters
        if (this.hostManager && this.hostManager.loadHosts) {
            await this.hostManager.loadHosts();
        }
        
        // Update table headers if showing all hosts
        this.updateTableHeaders();
    }
    
    updateTableHeaders() {
        const table = document.querySelector('#hosts-table, .hosts-table, table');
        if (!table) return;
        
        const headerRow = table.querySelector('thead tr');
        if (!headerRow) return;
        
        const ownerHeader = headerRow.querySelector('th.owner-column');
        
        if (this.showAllHosts && !ownerHeader) {
            // Add owner column header
            const lastHeader = headerRow.lastElementChild;
            const newHeader = document.createElement('th');
            newHeader.className = 'owner-column';
            newHeader.textContent = 'Owner';
            headerRow.insertBefore(newHeader, lastHeader);
        } else if (!this.showAllHosts && ownerHeader) {
            // Remove owner column header
            ownerHeader.remove();
        }
    }
    
    // Enhance the renderHosts method to include owner info
    enhanceHostRow(row, host) {
        if (this.showAllHosts && this.isAdmin && host.owner) {
            // Add owner cell before the last cell (actions)
            const ownerCell = document.createElement('td');
            ownerCell.className = 'owner-cell';
            ownerCell.textContent = host.owner_username || host.owner || 'Unknown';
            
            const lastCell = row.lastElementChild;
            row.insertBefore(ownerCell, lastCell);
        }
    }
}

// Extend the API client to support the new parameters
if (window.PrismAPI) {
    // Add getHosts method if it doesn't exist
    PrismAPI.prototype.getHosts = async function(params = {}) {
        let endpoint = '/api/v1/hosts';
        const queryParams = new URLSearchParams();
        
        if (params.page) queryParams.append('page', params.page);
        if (params.per_page) queryParams.append('per_page', params.per_page);
        if (params.status) queryParams.append('status', params.status);
        if (params.search) queryParams.append('search', params.search);
        if (params.all) queryParams.append('all', 'true');
        
        const queryString = queryParams.toString();
        if (queryString) {
            endpoint += '?' + queryString;
        }
        
        return this.get(endpoint);
    };
    
    // Add getHostStats method
    PrismAPI.prototype.getHostStats = async function() {
        return this.get('/api/v1/hosts/stats/summary');
    };
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for host manager to be initialized
    setTimeout(() => {
        if (window.hostManager) {
            window.hostUserFiltering = new HostUserFiltering(window.hostManager);
        }
    }, 100);
});