/**
 * Main Application for Prism DNS Web Interface
 * Handles navigation, initialization, and global app state
 */

class PrismApp {
    constructor() {
        this.router = null;
        this.sessionManager = null;
        this.isInitialized = false;
        this.connectionStatus = 'unknown';
        this.lastUpdate = null;
        
        this.initializeApp();
    }

    async initializeApp() {
        try {
            // Initialize router first
            this.router = new Router();
            
            // Initialize components
            this.initializeStatusBar();
            
            // Create component instances
            console.log('Creating dashboard component...');
            window.dashboard = new Dashboard();
            console.log('Creating hostManager component...');
            window.hostManager = new HostManager();
            console.log('Components created successfully');
            
            // Check API connectivity (non-blocking)
            this.checkApiConnection();
            
            // Start periodic connection checks
            this.startConnectionMonitoring();
            
            // Setup router handlers
            this.setupRouterHandlers();
            
            // Initialize session manager after token manager is ready
            this.initializeSessionManager();
            
            this.isInitialized = true;
            this.updateStatusBar('Ready', 'success');
            
            console.log('Prism DNS Web Interface initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.updateStatusBar('Initialization failed', 'danger');
            showToast('Failed to initialize application', 'danger');
        }
    }

    initializeSessionManager() {
        if (!window.SessionManager) {
            console.warn('SessionManager not available');
            return;
        }
        
        // Create session manager with configuration
        this.sessionManager = new SessionManager({
            inactivityTimeout: 30 * 60 * 1000, // 30 minutes
            warningTime: 5 * 60 * 1000, // 5 minutes warning
            checkInterval: 60 * 1000, // Check every minute
            enableSessionTimer: true,
            enableWarningModal: true,
            crossTabSync: true
        });
        
        // Listen for authentication state changes
        window.addEventListener('tokenUpdate', () => {
            this.handleAuthStateChange();
        });
        
        window.addEventListener('tokenClear', () => {
            this.handleAuthStateChange();
        });
        
        // Check initial auth state
        this.handleAuthStateChange();
    }
    
    handleAuthStateChange() {
        const isAuthenticated = window.api && window.api.tokenManager && window.api.tokenManager.isAuthenticated();
        
        if (isAuthenticated) {
            // Show session timer
            const timerContainer = document.getElementById('sessionTimerContainer');
            if (timerContainer) {
                timerContainer.classList.remove('d-none');
            }
            
            // Initialize session manager if not running
            if (this.sessionManager && !this.sessionManager.isRunning) {
                this.sessionManager.init();
            }
        } else {
            // Hide session timer
            const timerContainer = document.getElementById('sessionTimerContainer');
            if (timerContainer) {
                timerContainer.classList.add('d-none');
            }
            
            // Cleanup session manager
            if (this.sessionManager && this.sessionManager.isRunning) {
                this.sessionManager.cleanup();
            }
        }
    }

    setupRouterHandlers() {
        // Setup router after route handlers
        this.router.afterRoute(async (route, path) => {
            // Handle loading data for specific routes
            if (route.component === 'dashboard' || route.component === 'hosts') {
                await this.loadViewData(route.component);
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Alt+D for dashboard
            if (e.altKey && e.key === 'd') {
                e.preventDefault();
                this.router.navigate('/dashboard');
            }
            // Alt+H for hosts
            else if (e.altKey && e.key === 'h') {
                e.preventDefault();
                this.router.navigate('/hosts');
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

    showView(viewName) {
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
        
        // Router handles navigation now
        if (this.router) {
            const path = viewName === 'dashboard' ? '/' : `/${viewName}`;
            this.router.navigate(path);
            return;
        }
        
        // Load view data immediately - components are already initialized
        console.log(`Loading data for view: ${viewName}`);
        this.loadViewData(viewName);
        
        // Update page title
        document.title = `Prism DNS - ${viewName.charAt(0).toUpperCase() + viewName.slice(1)}`;
    }

    async loadViewData(viewName) {
        try {
            switch (viewName) {
                case 'dashboard':
                    if (window.dashboard) {
                        await window.dashboard.loadDashboard();
                        window.dashboard.startAutoRefresh();
                    } else {
                        console.warn('Dashboard component not available');
                    }
                    if (window.hostManager) {
                        window.hostManager.stopAutoRefresh();
                    }
                    break;
                    
                case 'hosts':
                    if (window.hostManager) {
                        await window.hostManager.loadHosts();
                        window.hostManager.startAutoRefresh();
                    } else {
                        console.warn('HostManager component not available');
                    }
                    if (window.dashboard) {
                        window.dashboard.stopAutoRefresh();
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
            const currentRoute = this.router.getCurrentRoute();
            if (currentRoute.component) {
                await this.loadViewData(currentRoute.component);
                this.updateStatusBar('Refreshed', 'success');
                showToast('Data refreshed', 'success', 2000);
            }
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
        this.router.navigate('/hosts');
        // Wait for view to load, then show host detail
        setTimeout(() => {
            if (window.hostManager) {
                window.hostManager.showHostDetail(hostname);
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
        const currentRoute = this.router ? this.router.getCurrentRoute() : {};
        return {
            version: '1.0.0',
            currentView: currentRoute.component || 'unknown',
            currentPath: currentRoute.path || '/',
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