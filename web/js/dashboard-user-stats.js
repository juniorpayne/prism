/**
 * Dashboard User Statistics Enhancement
 * Updates dashboard to show user-specific host stats with admin system stats
 */

class DashboardUserStats {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.isAdmin = false;
        this.systemStatsContainer = null;
        
        this.checkUserPermissions();
    }
    
    async checkUserPermissions() {
        try {
            const user = await this.getCurrentUser();
            this.isAdmin = user && user.is_admin;
            
            if (this.isAdmin) {
                this.createSystemStatsSection();
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
    
    createSystemStatsSection() {
        // Find the stats container
        const statsContainer = document.querySelector('.stats-container, .row');
        if (!statsContainer) return;
        
        // Create system stats section
        const systemStatsHtml = `
            <div class="col-12 mt-4">
                <h5 class="text-muted">System Statistics (Admin View)</h5>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">Total System Hosts</h5>
                        <p class="card-text display-4" id="system-total-hosts">-</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">Users with Hosts</h5>
                        <p class="card-text display-4" id="users-with-hosts">-</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">Anonymous Hosts</h5>
                        <p class="card-text display-4" id="anonymous-hosts">-</p>
                    </div>
                </div>
            </div>
        `;
        
        // Create a container for system stats
        this.systemStatsContainer = document.createElement('div');
        this.systemStatsContainer.className = 'row system-stats-section';
        this.systemStatsContainer.innerHTML = systemStatsHtml;
        
        // Add after the main stats
        statsContainer.parentNode.appendChild(this.systemStatsContainer);
    }
    
    async updateStats() {
        try {
            const response = await api.getHostStats();
            const stats = await response.json();
            
            // Update user stats
            this.updateElement('total-hosts', stats.total_hosts);
            this.updateElement('online-hosts', stats.online_hosts);
            this.updateElement('offline-hosts', stats.offline_hosts);
            
            // Update last registration if available
            if (stats.last_registration) {
                const lastRegElement = document.getElementById('last-registration');
                if (lastRegElement) {
                    lastRegElement.textContent = this.formatDateTime(stats.last_registration);
                }
            }
            
            // Update system stats if admin
            if (this.isAdmin && stats.system_stats) {
                this.updateElement('system-total-hosts', stats.system_stats.total_hosts);
                this.updateElement('users-with-hosts', stats.system_stats.users_with_hosts);
                this.updateElement('anonymous-hosts', stats.system_stats.anonymous_hosts);
            }
            
            // Update chart if method exists
            if (this.dashboard && this.dashboard.updateChart) {
                this.dashboard.updateChart(stats);
            }
            
        } catch (error) {
            console.error('Failed to update host stats:', error);
        }
    }
    
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value !== null && value !== undefined ? value : '-';
        }
    }
    
    formatDateTime(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (e) {
            return dateString;
        }
    }
}

// Extend the dashboard loadStats method
if (window.Dashboard) {
    const originalLoadStats = Dashboard.prototype.loadStats;
    
    Dashboard.prototype.loadStats = async function() {
        // Call the new stats endpoint
        try {
            const response = await api.getHostStats();
            const stats = await response.json();
            
            // Use the new stats format
            const formattedStats = {
                total_hosts: stats.total_hosts,
                online_hosts: stats.online_hosts,
                offline_hosts: stats.offline_hosts
            };
            
            // Add system stats if available
            if (stats.system_stats) {
                formattedStats.system_stats = stats.system_stats;
            }
            
            return formattedStats;
        } catch (error) {
            console.error('Failed to load host stats:', error);
            // Fall back to original method if available
            if (originalLoadStats) {
                return originalLoadStats.call(this);
            }
            throw error;
        }
    };
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for dashboard to be initialized
    setTimeout(() => {
        if (window.dashboard) {
            window.dashboardUserStats = new DashboardUserStats(window.dashboard);
            // Trigger initial stats update
            window.dashboardUserStats.updateStats();
        }
    }, 100);
});