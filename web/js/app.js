/**
 * Main Application for Prism DNS Web Interface
 * Handles navigation, initialization, and global app state
 */

class PrismApp {
    constructor() {
        this.currentView = 'dashboard';
        this.isInitialized = false;
        this.connectionStatus = 'unknown';
        this.lastUpdate = null;
        
        this.initializeApp();
    }

    async initializeApp() {
        try {
            // Initialize components
            this.initializeNavigation();
            this.initializeStatusBar();
            
            // Create component instances
            window.dashboard = new Dashboard();
            window.hostManager = new HostManager();
            
            // Check API connectivity
            await this.checkApiConnection();
            
            // Load initial view
            this.showView(this.currentView);
            
            // Start periodic connection checks
            this.startConnectionMonitoring();
            
            // Handle browser navigation
            this.initializeRouting();
            
            this.isInitialized = true;
            this.updateStatusBar('Ready', 'success');
            
            console.log('Prism DNS Web Interface initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.updateStatusBar('Initialization failed', 'danger');
            showToast('Failed to initialize application', 'danger');
        }
    }

    initializeNavigation() {
        // Navigation click handlers
        document.getElementById('nav-dashboard')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.showView('dashboard');
        });
        
        document.getElementById('nav-hosts')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.showView('hosts');
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Alt+D for dashboard
            if (e.altKey && e.key === 'd') {
                e.preventDefault();
                this.showView('dashboard');
            }
            // Alt+H for hosts
            else if (e.altKey && e.key === 'h') {
                e.preventDefault();
                this.showView('hosts');
            }
            // F5 or Ctrl+R for refresh
            else if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshCurrentView();
            }
        });
    }

    initializeStatusBar() {
        // Make status bar dismissible but auto-show important messages
        const statusBar = document.getElementById('status-bar');
        if (statusBar) {
            statusBar.addEventListener('closed.bs.alert', () => {
                // Auto-show again after 30 seconds for important status updates
                setTimeout(() => {
                    if (this.connectionStatus === 'error') {
                        statusBar.style.display = 'block';
                        statusBar.classList.add('show');
                    }
                }, 30000);
            });
        }
    }

    initializeRouting() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', (e) => {
            const view = this.getViewFromUrl();
            this.showView(view, false); // Don't update URL again
        });
        
        // Load view from URL on page load
        const initialView = this.getViewFromUrl();
        if (initialView !== this.currentView) {
            this.showView(initialView);
        }
    }

    getViewFromUrl() {
        const hash = window.location.hash.substring(1);
        return ['dashboard', 'hosts'].includes(hash) ? hash : 'dashboard';
    }

    showView(viewName, updateUrl = true) {
        // Hide all views
        document.querySelectorAll('.view').forEach(view => {
            view.style.display = 'none';
        });
        
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Show selected view
        const viewElement = document.getElementById(`${viewName}-view`);
        const navElement = document.getElementById(`nav-${viewName}`);
        
        if (viewElement) {
            viewElement.style.display = 'block';
            viewElement.classList.add('fade-in');
        }
        
        if (navElement) {
            navElement.classList.add('active');
        }
        
        // Update URL
        if (updateUrl) {
            window.history.pushState({}, '', `#${viewName}`);
        }
        
        this.currentView = viewName;
        
        // Load view data after a short delay to ensure DOM is ready
        setTimeout(() => {
            this.loadViewData(viewName);
        }, 50);
        
        // Update page title
        document.title = `Prism DNS - ${viewName.charAt(0).toUpperCase() + viewName.slice(1)}`;
    }

    async loadViewData(viewName) {
        try {
            switch (viewName) {
                case 'dashboard':
                    if (dashboard) {
                        await dashboard.loadDashboard();
                        dashboard.startAutoRefresh();
                    }
                    if (hostManager) {
                        hostManager.stopAutoRefresh();
                    }
                    break;
                    
                case 'hosts':
                    if (hostManager) {
                        await hostManager.loadHosts();
                        hostManager.startAutoRefresh();
                    }
                    if (dashboard) {
                        dashboard.stopAutoRefresh();
                    }
                    break;
            }
            
            this.lastUpdate = new Date();
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error(`Failed to load ${viewName} data:`, error);
            this.updateStatusBar(`Failed to load ${viewName}`, 'danger');
        }
    }

    async refreshCurrentView() {
        this.updateStatusBar('Refreshing...', 'info');
        
        try {
            await this.loadViewData(this.currentView);
            this.updateStatusBar('Refreshed', 'success');
            showToast('Data refreshed', 'success', 2000);
        } catch (error) {
            this.updateStatusBar('Refresh failed', 'danger');
            showToast('Failed to refresh data', 'danger');
        }
    }

    async checkApiConnection() {
        try {
            const isConnected = await api.ping();
            
            if (isConnected) {
                this.connectionStatus = 'connected';
                this.updateStatusBar('Connected to server', 'success');
            } else {
                this.connectionStatus = 'error';
                this.updateStatusBar('Cannot connect to server', 'danger');
            }
            
        } catch (error) {
            this.connectionStatus = 'error';
            this.updateStatusBar('Server connection failed', 'danger');
            console.error('API connection check failed:', error);
        }
    }

    startConnectionMonitoring() {
        // Check connection every 60 seconds
        setInterval(async () => {
            await this.checkApiConnection();
        }, 60000);
    }

    updateStatusBar(message, type = 'info') {
        const statusBar = document.getElementById('status-bar');
        const statusMessage = document.getElementById('status-message');
        
        if (!statusBar || !statusMessage) return;
        
        // Update message
        statusMessage.textContent = message;
        
        // Update class
        statusBar.className = `alert alert-${type} alert-dismissible fade show mb-0`;
        
        // Update icon
        const icon = statusBar.querySelector('i');
        if (icon) {
            icon.className = this.getStatusIcon(type);
        }
        
        // Update last update time
        this.updateLastUpdateTime();
        
        // Auto-hide success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                statusBar.style.display = 'none';
            }, 5000);
        } else {
            statusBar.style.display = 'block';
        }
    }

    updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement && this.lastUpdate) {
            lastUpdateElement.textContent = `Last updated: ${formatTimestamp(this.lastUpdate)}`;
        }
    }

    getStatusIcon(type) {
        switch (type) {
            case 'success':
                return 'bi bi-check-circle';
            case 'danger':
                return 'bi bi-exclamation-triangle';
            case 'warning':
                return 'bi bi-exclamation-circle';
            default:
                return 'bi bi-info-circle';
        }
    }

    // Public methods for other components to use

    showHost(hostname) {
        this.showView('hosts');
        // Wait for view to load, then show host detail
        setTimeout(() => {
            if (hostManager) {
                hostManager.showHostDetail(hostname);
            }
        }, 100);
    }

    getConnectionStatus() {
        return this.connectionStatus;
    }

    isReady() {
        return this.isInitialized;
    }

    // Settings and configuration

    updateApiConfig(config) {
        if (api) {
            api.updateConfig(config);
            this.checkApiConnection();
        }
    }

    getAppInfo() {
        return {
            version: '1.0.0',
            currentView: this.currentView,
            connectionStatus: this.connectionStatus,
            lastUpdate: this.lastUpdate,
            isInitialized: this.isInitialized,
            apiConfig: api ? api.getConfig() : null,
            browser: getBrowserInfo()
        };
    }

    // Error handling

    handleGlobalError(error) {
        console.error('Global error:', error);
        
        if (error instanceof APIError) {
            this.updateStatusBar(error.getUserMessage(), 'danger');
        } else {
            this.updateStatusBar('An unexpected error occurred', 'danger');
        }
        
        // Report error for debugging
        this.reportError(error);
    }

    reportError(error) {
        // In a real application, this would send error reports to a logging service
        const errorReport = {
            message: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            appInfo: this.getAppInfo()
        };
        
        console.log('Error report:', errorReport);
        
        // Store in localStorage for debugging
        const errorLog = storage.get('errorLog', []);
        errorLog.push(errorReport);
        
        // Keep only last 10 errors
        if (errorLog.length > 10) {
            errorLog.shift();
        }
        
        storage.set('errorLog', errorLog);
    }
}

// Global error handler
window.addEventListener('error', (e) => {
    if (window.app) {
        app.handleGlobalError(e.error);
    }
});

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', (e) => {
    if (window.app) {
        app.handleGlobalError(e.reason);
    }
});

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new PrismApp();
});

// Update last update time every minute
setInterval(() => {
    if (window.app) {
        app.updateLastUpdateTime();
    }
}, 60000);