/**
 * Navigation Component for Prism DNS
 * Handles navigation bar functionality, user menu, and session display
 */

class Navigation {
    constructor() {
        this.navbar = document.querySelector('.navbar');
        this.userDropdown = document.getElementById('userDropdown');
        this.userName = document.getElementById('userName');
        this.userEmail = document.getElementById('userEmail');
        this.userInitials = document.getElementById('userInitials');
        this.logoutLink = document.getElementById('logoutLink');
        this.navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        
        this.init();
    }
    
    init() {
        // Set up logout handler
        this.logoutLink?.addEventListener('click', (e) => {
            e.preventDefault();
            this.handleLogout();
        });
        
        // Update active nav item based on current path
        this.updateActiveNavItem();
        
        // Update user info
        this.updateUserInfo();
        
        // Listen for user info updates
        window.addEventListener('userInfoUpdated', () => {
            this.updateUserInfo();
        });
        
        // Handle route changes
        window.addEventListener('popstate', () => {
            this.updateActiveNavItem();
        });
    }
    
    updateUserInfo() {
        const user = window.api?.tokenManager?.getCurrentUser();
        
        if (user) {
            // Update user name
            const displayName = user.full_name || user.username;
            this.userName.textContent = displayName;
            
            // Update email
            this.userEmail.textContent = user.email;
            
            // Generate initials
            const initials = this.generateInitials(displayName);
            this.userInitials.textContent = initials;
        }
    }
    
    generateInitials(name) {
        if (!name) return '??';
        
        const parts = name.trim().split(' ');
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }
    
    updateActiveNavItem() {
        const currentPath = window.location.pathname;
        
        // Remove active class from all nav items
        this.navLinks.forEach(link => {
            link.classList.remove('active');
            link.setAttribute('aria-current', 'false');
        });
        
        // Add active class to current page
        this.navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
                link.classList.add('active');
                link.setAttribute('aria-current', 'page');
            }
        });
        
        // Special case for dashboard (root path)
        if (currentPath === '/' || currentPath === '/dashboard') {
            const dashboardLink = document.getElementById('nav-dashboard');
            if (dashboardLink) {
                dashboardLink.classList.add('active');
                dashboardLink.setAttribute('aria-current', 'page');
            }
        }
    }
    
    async handleLogout() {
        try {
            // Show loading state
            this.logoutLink.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Logging out...';
            this.logoutLink.classList.add('disabled');
            
            // Call logout API
            await window.api.logout();
            
            // Show success message
            showToast('Logged out successfully', 'success');
            
            // Navigate to login page
            window.router.navigate('/login');
        } catch (error) {
            console.error('Logout error:', error);
            showToast('Logout failed', 'danger');
            
            // Reset link state
            this.logoutLink.innerHTML = '<i class="bi bi-box-arrow-right me-2"></i>Logout';
            this.logoutLink.classList.remove('disabled');
        }
    }
    
    show() {
        this.navbar?.classList.remove('d-none');
    }
    
    hide() {
        this.navbar?.classList.add('d-none');
    }
}

// Export for use in other modules
window.Navigation = Navigation;