/**
 * Session Manager for Prism DNS
 * Handles session timeout, activity monitoring, and auto-logout
 */

class SessionManager {
    constructor(config = {}) {
        // Configuration with defaults
        this.config = {
            inactivityTimeout: config.inactivityTimeout || 30 * 60 * 1000, // 30 minutes
            warningTime: config.warningTime || 5 * 60 * 1000, // 5 minutes before timeout
            checkInterval: config.checkInterval || 60 * 1000, // Check every minute
            enableSessionTimer: config.enableSessionTimer !== false, // Default true
            enableWarningModal: config.enableWarningModal !== false, // Default true
            crossTabSync: config.crossTabSync !== false // Default true
        };
        
        // State
        this.lastActivity = Date.now();
        this.warningShown = false;
        this.activityTimer = null;
        this.warningTimer = null;
        this.isRunning = false;
        
        // Storage key for cross-tab communication
        this.storageKey = 'prism_last_activity';
        
        // Bind methods
        this.updateActivity = this.updateActivity.bind(this);
        this.handleStorageChange = this.handleStorageChange.bind(this);
    }
    
    /**
     * Initialize session management
     */
    init() {
        // Check if user is logged in
        if (!window.api || !window.api.tokenManager || !window.api.tokenManager.isAuthenticated()) {
            console.log('Session manager: User not authenticated, skipping initialization');
            return;
        }
        
        if (this.isRunning) {
            console.warn('Session manager already running');
            return;
        }
        
        this.isRunning = true;
        
        // Set up activity listeners
        this.setupActivityListeners();
        
        // Start monitoring
        this.startMonitoring();
        
        // Listen for storage events (cross-tab activity)
        if (this.config.crossTabSync) {
            window.addEventListener('storage', this.handleStorageChange);
        }
        
        // Intercept API calls
        this.interceptApiCalls();
        
        // Update initial activity
        this.updateActivity();
        
        console.log('Session manager initialized');
    }
    
    /**
     * Set up activity event listeners
     */
    setupActivityListeners() {
        const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, this.updateActivity, { passive: true });
        });
        
        // Also track focus
        window.addEventListener('focus', this.updateActivity);
    }
    
    /**
     * Update last activity timestamp
     */
    updateActivity() {
        this.lastActivity = Date.now();
        this.warningShown = false;
        
        // Update storage for other tabs
        if (this.config.crossTabSync) {
            try {
                localStorage.setItem(this.storageKey, this.lastActivity.toString());
            } catch (e) {
                console.warn('Failed to update activity in localStorage:', e);
            }
        }
        
        // Hide warning if shown
        this.hideWarning();
    }
    
    /**
     * Handle storage changes from other tabs
     */
    handleStorageChange(e) {
        if (e.key === this.storageKey && e.newValue) {
            const newActivity = parseInt(e.newValue);
            if (!isNaN(newActivity)) {
                this.lastActivity = newActivity;
                this.warningShown = false;
                this.hideWarning();
            }
        }
    }
    
    /**
     * Intercept API calls to update activity
     */
    interceptApiCalls() {
        // Store original fetch
        const originalFetch = window.fetch;
        
        // Override fetch
        window.fetch = (...args) => {
            // Update activity on API calls (except for auth endpoints)
            const url = args[0];
            if (typeof url === 'string' && !url.includes('/auth/')) {
                this.updateActivity();
            }
            
            return originalFetch.apply(window, args);
        };
    }
    
    /**
     * Start monitoring session activity
     */
    startMonitoring() {
        // Check every interval
        this.activityTimer = setInterval(() => {
            this.checkInactivity();
        }, this.config.checkInterval);
        
        // Initial check
        this.checkInactivity();
    }
    
    /**
     * Check for inactivity and handle timeout
     */
    checkInactivity() {
        const now = Date.now();
        const timeSinceActivity = now - this.lastActivity;
        const timeUntilTimeout = this.config.inactivityTimeout - timeSinceActivity;
        
        if (timeUntilTimeout <= 0) {
            // Time's up - logout
            this.performAutoLogout();
        } else if (timeUntilTimeout <= this.config.warningTime && !this.warningShown && this.config.enableWarningModal) {
            // Show warning
            this.showWarning(timeUntilTimeout);
        }
        
        // Update session timer display if enabled
        if (this.config.enableSessionTimer) {
            this.updateSessionTimer(timeUntilTimeout);
        }
    }
    
    /**
     * Show session expiry warning modal
     */
    showWarning(timeRemaining) {
        this.warningShown = true;
        
        // Check if modal already exists
        if (document.getElementById('sessionWarningModal')) {
            return;
        }
        
        // Create warning modal
        const modal = document.createElement('div');
        modal.id = 'sessionWarningModal';
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-clock-history text-warning me-2"></i>
                            Session Expiring Soon
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>Your session will expire in <strong id="sessionCountdown" class="text-danger"></strong> due to inactivity.</p>
                        <p class="mb-0">Would you like to continue working?</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="logoutNowBtn">
                            <i class="bi bi-box-arrow-right me-1"></i> Logout Now
                        </button>
                        <button type="button" class="btn btn-primary" id="continueSessionBtn">
                            <i class="bi bi-arrow-clockwise me-1"></i> Continue Session
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade show';
        backdrop.id = 'sessionWarningBackdrop';
        
        document.body.appendChild(backdrop);
        document.body.appendChild(modal);
        document.body.classList.add('modal-open');
        
        // Start countdown
        this.startCountdown(timeRemaining);
        
        // Event listeners
        document.getElementById('continueSessionBtn').addEventListener('click', () => {
            this.updateActivity();
            this.hideWarning();
        });
        
        document.getElementById('logoutNowBtn').addEventListener('click', () => {
            this.performLogout();
        });
        
        // Focus on continue button
        setTimeout(() => {
            document.getElementById('continueSessionBtn')?.focus();
        }, 100);
    }
    
    /**
     * Start countdown timer in warning modal
     */
    startCountdown(timeRemaining) {
        const countdownEl = document.getElementById('sessionCountdown');
        if (!countdownEl) return;
        
        let seconds = Math.floor(timeRemaining / 1000);
        
        const updateCountdown = () => {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            
            if (countdownEl) {
                countdownEl.textContent = `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
            }
            
            seconds--;
            
            if (seconds < 0) {
                clearInterval(this.warningTimer);
                this.performAutoLogout();
            }
        };
        
        updateCountdown();
        this.warningTimer = setInterval(updateCountdown, 1000);
    }
    
    /**
     * Hide warning modal
     */
    hideWarning() {
        const modal = document.getElementById('sessionWarningModal');
        const backdrop = document.getElementById('sessionWarningBackdrop');
        
        if (modal) {
            modal.remove();
        }
        
        if (backdrop) {
            backdrop.remove();
        }
        
        document.body.classList.remove('modal-open');
        
        if (this.warningTimer) {
            clearInterval(this.warningTimer);
            this.warningTimer = null;
        }
        
        this.warningShown = false;
    }
    
    /**
     * Update session timer in navbar
     */
    updateSessionTimer(timeRemaining) {
        const timerEl = document.getElementById('sessionTime');
        const timerContainer = document.getElementById('sessionTimerContainer');
        const sessionTimerEl = document.getElementById('sessionTimer');
        
        if (!timerEl || !timerContainer) return;
        
        // Show timer container when authenticated
        if (timerContainer.classList.contains('d-none')) {
            timerContainer.classList.remove('d-none');
        }
        
        if (timeRemaining <= 0) {
            timerEl.textContent = 'Expired';
            sessionTimerEl.className = 'text-danger';
            return;
        }
        
        const minutes = Math.floor(timeRemaining / 60000);
        const seconds = Math.floor((timeRemaining % 60000) / 1000);
        
        // Update styling based on time remaining
        sessionTimerEl.className = 'text-white-50';
        if (minutes < 5) {
            sessionTimerEl.className = 'text-danger';
        } else if (minutes < 10) {
            sessionTimerEl.className = 'text-warning';
        }
        
        timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
    
    /**
     * Perform auto-logout due to inactivity
     */
    async performAutoLogout() {
        // Show notification
        this.showAutoLogoutNotification();
        
        // Wait a moment for user to see notification
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Perform logout
        this.performLogout();
    }
    
    /**
     * Show auto-logout notification
     */
    showAutoLogoutNotification() {
        // Remove any existing notification
        const existing = document.getElementById('autoLogoutNotification');
        if (existing) {
            existing.remove();
        }
        
        const notification = document.createElement('div');
        notification.id = 'autoLogoutNotification';
        notification.className = 'alert alert-warning position-fixed top-0 start-50 translate-middle-x mt-3 shadow';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-clock-history me-2 fs-4"></i>
                <div>
                    <strong>Session Expired</strong><br>
                    You have been logged out due to inactivity.
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after delay
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    /**
     * Perform logout
     */
    async performLogout() {
        // Clean up timers
        this.cleanup();
        
        // Call logout API
        try {
            if (window.api && window.api.logout) {
                await window.api.logout();
            }
        } catch (error) {
            console.error('Logout API error:', error);
        }
        
        // Clear tokens
        if (window.api && window.api.tokenManager) {
            window.api.tokenManager.clearTokens();
        }
        
        // Clear activity storage
        if (this.config.crossTabSync) {
            localStorage.removeItem(this.storageKey);
        }
        
        // Navigate to login
        if (window.router) {
            window.router.navigate('/login');
        } else {
            window.location.href = '/login';
        }
    }
    
    /**
     * Clean up timers and listeners
     */
    cleanup() {
        this.isRunning = false;
        
        if (this.activityTimer) {
            clearInterval(this.activityTimer);
            this.activityTimer = null;
        }
        
        if (this.warningTimer) {
            clearInterval(this.warningTimer);
            this.warningTimer = null;
        }
        
        // Remove event listeners
        const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
        events.forEach(event => {
            document.removeEventListener(event, this.updateActivity);
        });
        
        window.removeEventListener('focus', this.updateActivity);
        
        if (this.config.crossTabSync) {
            window.removeEventListener('storage', this.handleStorageChange);
        }
        
        this.hideWarning();
    }
    
    /**
     * Get time until session expires
     */
    getTimeUntilExpiry() {
        const now = Date.now();
        const timeSinceActivity = now - this.lastActivity;
        return Math.max(0, this.config.inactivityTimeout - timeSinceActivity);
    }
    
    /**
     * Check if session is active
     */
    isSessionActive() {
        return this.getTimeUntilExpiry() > 0;
    }
    
    /**
     * Extend session (reset activity)
     */
    extendSession() {
        this.updateActivity();
    }
}

// Export for use in other modules
window.SessionManager = SessionManager;