/**
 * Route Guard for Prism DNS
 * Monitors authentication state and protects routes
 */

class RouteGuard {
    constructor(router) {
        this.router = router;
        this.isInitialized = false;
        this.lastAuthState = null;
        
        // Bind methods
        this.checkAuthState = this.checkAuthState.bind(this);
        this.handleAuthStateChange = this.handleAuthStateChange.bind(this);
        
        this.init();
    }
    
    /**
     * Initialize route guard
     */
    init() {
        if (this.isInitialized) {
            console.warn('RouteGuard already initialized');
            return;
        }
        
        // Register route handlers
        this.registerRouteHandlers();
        
        // Monitor auth state changes
        this.monitorAuthState();
        
        // Check initial auth state
        this.checkAuthState();
        
        this.isInitialized = true;
        console.log('RouteGuard initialized');
    }
    
    /**
     * Register before/after route handlers
     */
    registerRouteHandlers() {
        // Before route handler - check auth requirements
        this.router.beforeRoute(async (route, path) => {
            // Allow router's built-in auth check to handle this
            // We just monitor for logging/analytics
            console.log(`Navigating to ${path}`, {
                protected: route.protected,
                public: route.public,
                authOnly: route.authOnly
            });
            
            return true; // Continue navigation
        });
        
        // After route handler - update UI state
        this.router.afterRoute(async (route, path) => {
            // Update any UI elements that depend on current route
            this.updateUIForRoute(route, path);
        });
    }
    
    /**
     * Monitor authentication state changes
     */
    monitorAuthState() {
        // Listen for token updates
        window.addEventListener('tokenUpdate', this.handleAuthStateChange);
        window.addEventListener('tokenClear', this.handleAuthStateChange);
        window.addEventListener('authStateChanged', this.handleAuthStateChange);
        
        // Also check periodically for external changes
        setInterval(() => {
            this.checkAuthState();
        }, 5000); // Every 5 seconds
    }
    
    /**
     * Check current authentication state
     */
    checkAuthState() {
        const isAuthenticated = this.router.isAuthenticated();
        
        // If state changed, handle it
        if (this.lastAuthState !== null && this.lastAuthState !== isAuthenticated) {
            this.handleAuthStateChange();
        }
        
        this.lastAuthState = isAuthenticated;
    }
    
    /**
     * Handle authentication state changes
     */
    handleAuthStateChange() {
        const isAuthenticated = this.router.isAuthenticated();
        const currentRoute = this.router.getCurrentRoute();
        
        console.log('Auth state changed:', {
            authenticated: isAuthenticated,
            currentPath: currentRoute.path,
            protected: currentRoute.isProtected
        });
        
        // If user logged out and on protected route
        if (!isAuthenticated && currentRoute.isProtected) {
            console.log('User logged out, redirecting to login');
            showToast('Please login to continue', 'warning');
            this.router.navigate('/login');
        }
        
        // If user logged in and on auth-only route (login/register)
        if (isAuthenticated && currentRoute.route?.authOnly) {
            console.log('User logged in, redirecting to dashboard');
            this.router.redirectAfterLogin();
        }
        
        // Update UI elements
        this.updateAuthUI(isAuthenticated);
    }
    
    /**
     * Update UI elements based on route
     */
    updateUIForRoute(route, path) {
        // Update body classes for route-specific styling
        document.body.className = document.body.className
            .replace(/\broute-\S+/g, '') // Remove existing route classes
            .trim();
        
        // Add new route class
        const routeClass = `route-${route.component || 'unknown'}`;
        document.body.classList.add(routeClass);
        
        // Add auth state class
        if (this.router.isAuthenticated()) {
            document.body.classList.add('authenticated');
        } else {
            document.body.classList.remove('authenticated');
        }
        
        // Special handling for auth pages
        if (route.authOnly || route.public) {
            document.body.classList.add('auth-page');
        } else {
            document.body.classList.remove('auth-page');
        }
    }
    
    /**
     * Update UI elements based on auth state
     */
    updateAuthUI(isAuthenticated) {
        // This is handled by Navigation component, but we can add
        // additional UI updates here if needed
        
        // Update any auth-dependent elements
        document.querySelectorAll('[data-auth-required]').forEach(el => {
            el.style.display = isAuthenticated ? '' : 'none';
        });
        
        document.querySelectorAll('[data-guest-only]').forEach(el => {
            el.style.display = !isAuthenticated ? '' : 'none';
        });
    }
    
    /**
     * Check if user can access a specific route
     */
    canAccessRoute(path) {
        const route = this.router.routes[path];
        if (!route) return true; // Unknown routes are allowed (will 404)
        
        const isAuthenticated = this.router.isAuthenticated();
        
        // Public routes are always accessible
        if (route.public) return true;
        
        // Protected routes need authentication
        if (route.protected && !isAuthenticated) return false;
        
        return true;
    }
    
    /**
     * Get redirect path for unauthorized access
     */
    getUnauthorizedRedirect(path) {
        const route = this.router.routes[path];
        
        // For protected routes, redirect to login
        if (route?.protected) {
            return '/login';
        }
        
        // Default to home
        return '/';
    }
    
    /**
     * Clean up event listeners
     */
    destroy() {
        window.removeEventListener('tokenUpdate', this.handleAuthStateChange);
        window.removeEventListener('tokenClear', this.handleAuthStateChange);
        window.removeEventListener('authStateChanged', this.handleAuthStateChange);
        
        this.isInitialized = false;
    }
}

// Export for use in other modules
window.RouteGuard = RouteGuard;