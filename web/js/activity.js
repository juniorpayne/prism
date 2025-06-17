/**
 * Activity Page for Prism DNS
 * Shows user activity history with filtering and pagination
 */

class ActivityPage {
    constructor() {
        this.activityList = document.getElementById('activityList');
        this.pagination = document.getElementById('activityPagination');
        this.typeFilter = document.getElementById('activityType');
        this.startDate = document.getElementById('startDate');
        this.endDate = document.getElementById('endDate');
        this.applyBtn = document.getElementById('applyFilters');
        this.clearBtn = document.getElementById('clearFilters');
        this.template = document.getElementById('activityItemTemplate');
        
        this.currentPage = 1;
        this.pageSize = 20;
        this.totalPages = 1;
        this.filters = {};
        
        this.eventIcons = {
            login: 'bi-box-arrow-in-right text-success',
            logout: 'bi-box-arrow-right text-secondary',
            profile_updated: 'bi-person-circle text-info',
            password_changed: 'bi-shield-lock text-warning',
            security: 'bi-exclamation-triangle text-danger',
            settings: 'bi-gear text-primary',
            failed_login: 'bi-x-circle text-danger',
            two_factor_enabled: 'bi-shield-check text-success',
            api_key_created: 'bi-key text-info',
            email_verified: 'bi-envelope-check text-success',
            account_created: 'bi-person-plus text-success'
        };
        
        this.eventTitles = {
            login: 'Logged In',
            logout: 'Logged Out',
            profile_updated: 'Profile Updated',
            password_changed: 'Password Changed',
            security: 'Security Event',
            settings: 'Settings Changed',
            failed_login: 'Failed Login Attempt',
            two_factor_enabled: '2FA Enabled',
            api_key_created: 'API Key Created',
            email_verified: 'Email Verified',
            account_created: 'Account Created'
        };
        
        this.isDestroyed = false;
        this.init();
    }
    
    init() {
        if (!this.activityList) {
            console.error('Activity list element not found');
            return;
        }
        
        this.setupEventListeners();
        this.setDefaultDates();
        this.loadActivity();
    }
    
    setupEventListeners() {
        this.applyBtn?.addEventListener('click', () => {
            this.applyFilters();
        });
        
        this.clearBtn?.addEventListener('click', () => {
            this.clearFilters();
        });
        
        // Enter key in date fields
        [this.startDate, this.endDate].forEach(input => {
            input?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });
        
        // Auto-apply filter on type change
        this.typeFilter?.addEventListener('change', () => {
            this.applyFilters();
        });
    }
    
    setDefaultDates() {
        // Default to last 30 days
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 30);
        
        if (this.startDate) this.startDate.value = start.toISOString().split('T')[0];
        if (this.endDate) this.endDate.value = end.toISOString().split('T')[0];
    }
    
    applyFilters() {
        this.filters = {
            type: this.typeFilter?.value || '',
            start_date: this.startDate?.value || '',
            end_date: this.endDate?.value || ''
        };
        
        this.currentPage = 1;
        this.loadActivity();
    }
    
    clearFilters() {
        if (this.typeFilter) this.typeFilter.value = '';
        this.setDefaultDates();
        this.filters = {};
        this.currentPage = 1;
        this.loadActivity();
    }
    
    async loadActivity() {
        if (this.isDestroyed) return;
        
        this.showLoading();
        
        try {
            // For now, use mock data since the API endpoint might not exist
            const mockData = this.getMockActivityData();
            
            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Apply filters to mock data
            let filtered = this.filterMockData(mockData, this.filters);
            
            // Apply pagination
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            const items = filtered.slice(start, end);
            
            this.displayActivity(items);
            this.updatePagination(Math.ceil(filtered.length / this.pageSize), this.currentPage);
            
        } catch (error) {
            console.error('Failed to load activity:', error);
            this.showError('Failed to load activity history.');
        }
    }
    
    getMockActivityData() {
        const now = new Date();
        const activities = [];
        
        // Generate mock activities for the last 30 days
        for (let i = 0; i < 50; i++) {
            const date = new Date(now);
            date.setDate(date.getDate() - Math.floor(Math.random() * 30));
            date.setHours(Math.floor(Math.random() * 24));
            date.setMinutes(Math.floor(Math.random() * 60));
            
            const types = ['login', 'logout', 'profile_updated', 'password_changed', 'settings'];
            const eventType = types[Math.floor(Math.random() * types.length)];
            
            activities.push({
                id: i + 1,
                event_type: eventType,
                created_at: date.toISOString(),
                ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
                device: this.getRandomDevice(),
                status: Math.random() > 0.9 ? 'failed' : 'success',
                details: this.getEventDetails(eventType)
            });
        }
        
        // Sort by date descending
        return activities.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    }
    
    getRandomDevice() {
        const devices = [
            'Chrome on Windows',
            'Safari on macOS',
            'Firefox on Linux',
            'Chrome on Android',
            'Safari on iOS'
        ];
        return devices[Math.floor(Math.random() * devices.length)];
    }
    
    getEventDetails(eventType) {
        switch (eventType) {
            case 'profile_updated':
                const fields = ['full_name', 'bio', 'email'];
                return { fields: [fields[Math.floor(Math.random() * fields.length)]] };
            case 'settings':
                const settings = ['language', 'timezone', 'notifications'];
                return { setting: settings[Math.floor(Math.random() * settings.length)] };
            default:
                return {};
        }
    }
    
    filterMockData(data, filters) {
        let filtered = [...data];
        
        // Filter by type
        if (filters.type) {
            filtered = filtered.filter(item => item.event_type === filters.type);
        }
        
        // Filter by date range
        if (filters.start_date) {
            const startDate = new Date(filters.start_date);
            startDate.setHours(0, 0, 0, 0);
            filtered = filtered.filter(item => new Date(item.created_at) >= startDate);
        }
        
        if (filters.end_date) {
            const endDate = new Date(filters.end_date);
            endDate.setHours(23, 59, 59, 999);
            filtered = filtered.filter(item => new Date(item.created_at) <= endDate);
        }
        
        return filtered;
    }
    
    displayActivity(activities) {
        if (activities.length === 0) {
            this.activityList.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                    <p class="mt-2">No activity found for the selected period.</p>
                </div>
            `;
            return;
        }
        
        this.activityList.innerHTML = '';
        
        activities.forEach(activity => {
            const item = this.createActivityItem(activity);
            this.activityList.appendChild(item);
        });
    }
    
    createActivityItem(activity) {
        const clone = this.template.content.cloneNode(true);
        const item = clone.querySelector('.activity-item');
        
        // Set icon
        const icon = item.querySelector('.activity-icon i');
        icon.className = `bi ${this.eventIcons[activity.event_type] || 'bi-circle'}`;
        
        // Set title
        const title = item.querySelector('.activity-title');
        title.textContent = this.eventTitles[activity.event_type] || activity.event_type;
        
        // Set details
        const details = item.querySelector('.activity-details');
        details.textContent = this.formatDetails(activity);
        
        // Set time
        const time = item.querySelector('.activity-time');
        time.textContent = this.formatTime(activity.created_at);
        
        // Set location
        const location = item.querySelector('.activity-location');
        location.textContent = activity.ip_address || 'Unknown';
        
        // Set badge for status
        const badge = item.querySelector('.activity-badge');
        if (activity.status === 'failed') {
            badge.className = 'badge bg-danger';
            badge.textContent = 'Failed';
        } else if (activity.status === 'suspicious') {
            badge.className = 'badge bg-warning';
            badge.textContent = 'Suspicious';
        } else {
            badge.remove();
        }
        
        return item;
    }
    
    formatDetails(activity) {
        switch (activity.event_type) {
            case 'login':
                return `Logged in from ${activity.device || 'Unknown device'}`;
            case 'logout':
                return 'Session ended';
            case 'profile_updated':
                return this.formatProfileChanges(activity.details);
            case 'password_changed':
                return 'Password was successfully changed';
            case 'failed_login':
                return `Failed login attempt`;
            case 'settings':
                return this.formatSettingsChanges(activity.details);
            case 'email_verified':
                return 'Email address verified';
            case 'account_created':
                return 'Account created';
            default:
                return activity.description || 'Activity recorded';
        }
    }
    
    formatProfileChanges(details) {
        if (!details || !details.fields) return 'Profile information updated';
        
        const fields = details.fields;
        const changes = [];
        
        if (fields.includes('full_name')) {
            changes.push('name');
        }
        if (fields.includes('email')) {
            changes.push('email');
        }
        if (fields.includes('bio')) {
            changes.push('bio');
        }
        
        return changes.length > 0 
            ? `Updated ${changes.join(', ')}`
            : 'Profile information updated';
    }
    
    formatSettingsChanges(details) {
        if (!details || !details.setting) return 'Settings updated';
        
        const settingNames = {
            language: 'language preference',
            timezone: 'timezone',
            notifications: 'notification preferences',
            date_format: 'date format'
        };
        
        return `Changed ${settingNames[details.setting] || details.setting}`;
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        // Less than 1 minute
        if (diff < 60000) {
            return 'Just now';
        }
        
        // Less than 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        }
        
        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }
        
        // Less than 7 days
        if (diff < 604800000) {
            const days = Math.floor(diff / 86400000);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        }
        
        // Default to full date
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    
    updatePagination(totalPages, currentPage) {
        this.totalPages = totalPages;
        this.currentPage = currentPage;
        
        this.pagination.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `
            <a class="page-link" href="#" aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
            </a>
        `;
        if (currentPage > 1) {
            prevLi.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPage(currentPage - 1);
            });
        }
        this.pagination.appendChild(prevLi);
        
        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, startPage + 4);
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#">${i}</a>`;
            
            if (i !== currentPage) {
                pageLi.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(i);
                });
            }
            
            this.pagination.appendChild(pageLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `
            <a class="page-link" href="#" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        `;
        if (currentPage < totalPages) {
            nextLi.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPage(currentPage + 1);
            });
        }
        this.pagination.appendChild(nextLi);
    }
    
    goToPage(page) {
        this.currentPage = page;
        this.loadActivity();
        
        // Scroll to top of activity list
        this.activityList.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    showLoading() {
        this.activityList.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }
    
    showError(message) {
        this.activityList.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-circle"></i> ${message}
            </div>
        `;
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        this.isDestroyed = true;
        // Event listeners are automatically cleaned up when elements are removed from DOM
    }
}

// Export for use in other modules
window.ActivityPage = ActivityPage;