/**
 * Client-side Router for Prism DNS
 * Handles navigation, protected routes, and JWT authentication
 */

class Router {
    constructor() {
        // Route configuration with enhanced metadata
        this.routes = {
            '/': { component: 'dashboard', protected: true, title: 'Dashboard' },
            '/dashboard': { component: 'dashboard', protected: true, title: 'Dashboard' },
            '/login': { component: 'login', public: true, authOnly: true, title: 'Login' },
            '/register': { component: 'register', public: true, authOnly: true, title: 'Register' },
            '/forgot-password': { component: 'forgot-password', public: true, title: 'Forgot Password' },
            '/reset-password': { component: 'reset-password', public: true, title: 'Reset Password' },
            '/verify-email': { component: 'verify-email', public: true, title: 'Verify Email' },
            '/profile': { component: 'profile', protected: true, title: 'My Profile' },
            '/settings': { component: 'settings', protected: true, title: 'Settings' },
            '/activity': { component: 'activity', protected: true, title: 'Activity Log' },
            '/zones': { component: 'zones', protected: true, title: 'DNS Zones' },
            '/clients': { component: 'clients', protected: true, title: 'Clients' },
            '/hosts': { component: 'hosts', protected: true, title: 'Hosts' },
            '/404': { component: '404', public: true, title: 'Page Not Found' }
        };
        
        this.currentRoute = null;
        this.currentComponent = null;
        this.beforeRouteHandlers = [];
        this.afterRouteHandlers = [];
        this.authCheckInProgress = false;
        
        // Initialize router
        this.init();
    }
    
    init() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', () => this.handleRoute());
        
        // Intercept all link clicks
        document.addEventListener('click', (e) => {
            // Check if clicked element or parent is a link
            const link = e.target.closest('a');
            if (!link) return;
            
            const href = link.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('http') || 
                href.startsWith('mailto:') || link.hasAttribute('download')) {
                return; // Let browser handle external links, anchors, downloads
            }
            
            // Prevent default navigation for internal links
            if (href.startsWith('/')) {
                e.preventDefault();
                this.navigate(href);
            }
        });
        
        // Load initial route
        this.handleRoute();
    }
    
    /**
     * Navigate to a new route
     * @param {string} path - The path to navigate to
     * @param {Object} state - Optional state to pass to the route
     */
    navigate(path, state = {}) {
        // Don't navigate if already on the same path
        if (window.location.pathname === path) {
            return;
        }
        
        window.history.pushState(state, '', path);
        this.handleRoute();
    }
    
    /**
     * Replace current route without adding to history
     * @param {string} path - The path to replace with
     * @param {Object} state - Optional state to pass to the route
     */
    replace(path, state = {}) {
        window.history.replaceState(state, '', path);
        this.handleRoute();
    }
    
    /**
     * Go back in history
     */
    back() {
        window.history.back();
    }
    
    /**
     * Handle route changes
     */
    async handleRoute() {
        const path = window.location.pathname;
        let route = this.routes[path];
        
        // If route not found, check for dynamic routes
        if (!route) {
            route = this.findMatchingRoute(path) || this.routes['/404'];
        }
        
        // Show loading state
        this.showLoadingState();
        
        try {
            // Run before route handlers
            for (const handler of this.beforeRouteHandlers) {
                const shouldContinue = await handler(route, path);
                if (!shouldContinue) {
                    this.hideLoadingState();
                    return;
                }
            }
            
            // Check authentication
            const authCheckResult = await this.checkAuthentication(route, path);
            if (!authCheckResult) {
                this.hideLoadingState();
                return; // Navigation was handled by checkAuthentication
            }
            
            // Update current route
            this.currentRoute = route;
            
            // Load the component
            await this.loadComponent(route.component);
            
            // Run after route handlers
            for (const handler of this.afterRouteHandlers) {
                await handler(route, path);
            }
            
            // Update page title
            this.updatePageTitle(route.title || route.component);
            
        } catch (error) {
            console.error('Failed to load route:', error);
            this.navigate('/404');
        } finally {
            this.hideLoadingState();
        }
    }
    
    /**
     * Check authentication for route
     */
    async checkAuthentication(route, path) {
        const isAuthenticated = this.isAuthenticated();
        
        // If route is public, allow access
        if (route.public) {
            // If authenticated and trying to access auth-only routes, redirect to dashboard
            if (isAuthenticated && route.authOnly) {
                this.navigate('/dashboard');
                return false;
            }
            return true;
        }
        
        // If route is protected and user is not authenticated
        if (route.protected && !isAuthenticated) {
            // Save intended destination
            if (path !== '/login' && path !== '/') {
                localStorage.setItem('redirectAfterLogin', path);
            }
            
            // Show notification
            showToast('Please login to access this page', 'warning');
            
            // Redirect to login
            this.navigate('/login');
            return false;
        }
        
        // Check if token needs refresh
        if (isAuthenticated && window.api?.tokenManager?.shouldRefreshToken()) {
            try {
                await window.api.tokenManager.refreshAccessToken();
            } catch (error) {
                console.error('Token refresh failed:', error);
                // Token refresh failed, redirect to login
                this.navigate('/login');
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Check if user is authenticated
     * @returns {boolean} True if user has valid JWT token
     */
    isAuthenticated() {
        // Use TokenManager if available
        if (window.api && window.api.tokenManager) {
            return window.api.tokenManager.isAuthenticated();
        }
        
        // Fallback to direct localStorage check
        const token = localStorage.getItem('accessToken');
        return token && !this.isTokenExpired(token);
    }
    
    /**
     * Check if JWT token is expired
     * @param {string} token - JWT token to check
     * @returns {boolean} True if token is expired
     */
    isTokenExpired(token) {
        if (!token) return true;
        
        try {
            // JWT structure: header.payload.signature
            const parts = token.split('.');
            if (parts.length !== 3) return true;
            
            // Decode payload (base64 URL encoded)
            const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
            
            // Check expiration
            if (!payload.exp) return false; // No expiration
            
            // exp is in seconds, Date.now() is in milliseconds
            return payload.exp * 1000 < Date.now();
            
        } catch (error) {
            console.error('Error parsing token:', error);
            return true; // Consider invalid tokens as expired
        }
    }
    
    /**
     * Load a component based on route
     * @param {string} componentName - Name of the component to load
     */
    async loadComponent(componentName) {
        // Hide all views
        document.querySelectorAll('.view').forEach(view => {
            view.style.display = 'none';
        });
        
        // Update navigation active state
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Special handling for existing views
        const existingViews = ['dashboard', 'hosts', 'login', 'register', 'verify-email-sent', 'verify-email', 'forgot-password', 'reset-password'];
        if (existingViews.includes(componentName)) {
            const viewElement = document.getElementById(`${componentName}-view`);
            const navElement = document.getElementById(`nav-${componentName}`);
            
            if (viewElement) {
                viewElement.style.display = 'block';
                viewElement.classList.add('fade-in');
            }
            
            if (navElement) {
                navElement.classList.add('active');
            }
            
            // Handle page-specific initialization
            if (componentName === 'login') {
                // Clean up any existing login page instance
                if (window.currentLoginPage) {
                    window.currentLoginPage.destroy();
                }
                // Create new login page instance
                window.currentLoginPage = new window.LoginPage();
                
                // Check for verification success message
                if (sessionStorage.getItem('verificationSuccess') === 'true') {
                    sessionStorage.removeItem('verificationSuccess');
                    showToast('Email verified successfully! You can now login.', 'success');
                }
            } else if (componentName === 'register') {
                // Clean up any existing register page instance
                if (window.currentRegisterPage) {
                    window.currentRegisterPage.destroy();
                }
                // Create new register page instance
                window.currentRegisterPage = new window.RegisterPage();
            } else if (componentName === 'verify-email-sent') {
                // Clean up any existing email sent page instance
                if (window.currentEmailSentPage) {
                    window.currentEmailSentPage.destroy();
                }
                // Create new email sent page instance
                window.currentEmailSentPage = new window.EmailSentPage();
            } else if (componentName === 'verify-email') {
                // Clean up any existing verification page instance
                if (window.currentEmailVerificationPage) {
                    window.currentEmailVerificationPage.destroy();
                }
                // Create new verification page instance
                window.currentEmailVerificationPage = new window.EmailVerificationPage();
            } else if (componentName === 'forgot-password') {
                // Clean up any existing forgot password page instance
                if (window.currentForgotPasswordPage) {
                    window.currentForgotPasswordPage.destroy();
                }
                // Create new forgot password page instance
                window.currentForgotPasswordPage = new window.ForgotPasswordPage();
            } else if (componentName === 'reset-password') {
                // Clean up any existing reset password page instance
                if (window.currentResetPasswordPage) {
                    window.currentResetPasswordPage.destroy();
                }
                // Create new reset password page instance
                window.currentResetPasswordPage = new window.ResetPasswordPage();
            } else if (window.app) {
                // Use existing app logic to load data for dashboard/hosts
                await window.app.loadViewData(componentName);
            }
            
            this.currentComponent = componentName;
            return;
        }
        
        // For new components, we'll need to create view containers
        // This will be implemented as we add login, register, etc.
        console.log(`Loading component: ${componentName}`);
        
        // Show placeholder for now
        this.showPlaceholder(componentName);
    }
    
    /**
     * Show placeholder for components not yet implemented
     * @param {string} componentName - Name of the component
     */
    showPlaceholder(componentName) {
        // Check if placeholder view exists
        let placeholderView = document.getElementById('placeholder-view');
        if (!placeholderView) {
            // Create placeholder view
            placeholderView = document.createElement('div');
            placeholderView.id = 'placeholder-view';
            placeholderView.className = 'view container mt-4';
            document.querySelector('.container-fluid').appendChild(placeholderView);
        }
        
        // Update placeholder content
        placeholderView.innerHTML = `
            <div class="row">
                <div class="col-12">
                    <div class="card">
                        <div class="card-body text-center py-5">
                            <h2>${componentName.charAt(0).toUpperCase() + componentName.slice(1)}</h2>
                            <p class="text-muted">This page is coming soon!</p>
                            <a href="/" class="btn btn-primary">Back to Dashboard</a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        placeholderView.style.display = 'block';
        this.currentComponent = componentName;
    }
    
    /**
     * Update page title based on component
     * @param {string} componentName - Name of the current component
     */
    updatePageTitle(componentName) {
        const titles = {
            'dashboard': 'Dashboard',
            'hosts': 'Hosts',
            'login': 'Login',
            'register': 'Register',
            'profile': 'Profile',
            'zones': 'DNS Zones',
            'clients': 'Clients',
            'forgot-password': 'Forgot Password',
            'reset-password': 'Reset Password',
            'verify-email': 'Verify Email',
            '404': 'Page Not Found'
        };
        
        const title = titles[componentName] || componentName;
        document.title = `Prism DNS - ${title}`;
    }
    
    /**
     * Register a before route handler
     * @param {Function} handler - Function to run before route changes
     */
    beforeRoute(handler) {
        this.beforeRouteHandlers.push(handler);
    }
    
    /**
     * Register an after route handler
     * @param {Function} handler - Function to run after route changes
     */
    afterRoute(handler) {
        this.afterRouteHandlers.push(handler);
    }
    
    /**
     * Get current route info
     * @returns {Object} Current route information
     */
    getCurrentRoute() {
        return {
            path: window.location.pathname,
            route: this.currentRoute,
            component: this.currentComponent,
            isProtected: this.currentRoute?.protected || false
        };
    }
    
    /**
     * Redirect to originally requested page after login
     */
    redirectAfterLogin() {
        const redirectPath = localStorage.getItem('redirectAfterLogin');
        localStorage.removeItem('redirectAfterLogin');
        
        if (redirectPath && redirectPath !== '/login') {
            this.navigate(redirectPath);
        } else {
            this.navigate('/');
        }
    }
    
    /**
     * Show loading state
     */
    showLoadingState() {
        document.body.classList.add('route-loading');
    }
    
    /**
     * Hide loading state
     */
    hideLoadingState() {
        document.body.classList.remove('route-loading');
    }
    
    /**
     * Find matching route for dynamic paths
     */
    findMatchingRoute(path) {
        // For now, we don't have dynamic routes
        // This is a placeholder for future dynamic route support
        return null;
    }
}

// Export for use in other modules
window.Router = Router;