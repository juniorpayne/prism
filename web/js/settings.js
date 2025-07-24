/**
 * Settings Page for Prism DNS
 * Handles all account settings and preferences
 */

class SettingsPage {
    constructor() {
        this.currentSection = 'general';
        this.navLinks = document.querySelectorAll('[data-section]');
        this.sections = document.querySelectorAll('.settings-section');
        this.generalForm = document.getElementById('generalSettingsForm');
        this.notificationForm = document.getElementById('notificationSettingsForm');
        this.changePasswordBtn = document.getElementById('changePasswordBtn');
        this.deleteAccountBtn = document.getElementById('deleteAccountBtn');
        this.exportDataBtn = document.getElementById('exportDataBtn');
        this.viewActivityBtn = document.getElementById('viewActivityBtn');
        
        this.isDestroyed = false;
        this.settings = {};
        
        this.init();
    }
    
    init() {
        if (!this.generalForm) {
            console.error('Settings forms not found');
            return;
        }
        
        this.setupEventListeners();
        this.loadSettings();
        this.handleRouteChange();
    }
    
    setupEventListeners() {
        // Navigation
        this.navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                window.location.hash = `settings/${section}`;
            });
        });
        
        // Forms
        this.generalForm?.addEventListener('submit', (e) => this.handleGeneralSubmit(e));
        this.notificationForm?.addEventListener('submit', (e) => this.handleNotificationSubmit(e));
        
        // Buttons
        this.changePasswordBtn?.addEventListener('click', () => {
            window.location.hash = 'password-change';
        });
        
        this.deleteAccountBtn?.addEventListener('click', () => {
            this.confirmAccountDeletion();
        });
        
        this.exportDataBtn?.addEventListener('click', () => this.exportData());
        
        this.viewActivityBtn?.addEventListener('click', () => {
            window.location.hash = 'activity';
        });
        
        // Route changes
        window.addEventListener('hashchange', () => this.handleRouteChange());
    }
    
    handleRouteChange() {
        const hash = window.location.hash;
        const match = hash.match(/#settings\/([\w-]+)/);
        
        if (match) {
            this.showSection(match[1]);
        } else if (hash === '#settings') {
            this.showSection('general');
        }
    }
    
    showSection(section) {
        // Update navigation
        this.navLinks.forEach(link => {
            if (link.dataset.section === section) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
        
        // Show section
        this.sections.forEach(sec => {
            const secId = sec.id.replace('settings', '').toLowerCase();
            // Convert section name to match ID format (e.g., 'api-tokens' -> 'apitokens')
            const sectionNormalized = section.replace(/-/g, '').toLowerCase();
            if (secId === sectionNormalized) {
                sec.style.display = 'block';
            } else {
                sec.style.display = 'none';
            }
        });
        
        this.currentSection = section;
        
        // Load API tokens when navigating to that section
        if (section === 'api-tokens' && window.tokenManagement) {
            console.log('[Settings] Loading API tokens section...');
            window.tokenManagement.loadTokens();
            // Re-setup the generate button event listener after section is visible
            setTimeout(() => {
                window.tokenManagement.setupGenerateButton();
            }, 100);
        }
        
        // Load section-specific data
        if (section === 'security') {
            this.loadActiveSessions();
        }
    }
    
    async loadSettings() {
        try {
            // Load general settings
            const settings = await window.api.get('/users/me/settings');
            this.settings = settings;
            
            // Apply general settings
            if (settings.language) {
                document.getElementById('settingsLanguage').value = settings.language;
            }
            if (settings.timezone) {
                document.getElementById('settingsTimezone').value = settings.timezone;
            }
            if (settings.date_format) {
                document.getElementById('settingsDateFormat').value = settings.date_format;
            }
            
            // Load notification preferences separately (might not exist yet)
            try {
                const notifications = await window.api.get('/users/me/settings');
                if (notifications.notifications) {
                    document.getElementById('notifyHostDown').checked = notifications.notifications.host_down !== false;
                    document.getElementById('notifyHostUp').checked = notifications.notifications.host_up !== false;
                    document.getElementById('notifyWeeklyReport').checked = notifications.notifications.weekly_report === true;
                    document.getElementById('notifySecurityAlerts').checked = notifications.notifications.security_alerts !== false;
                }
            } catch (error) {
                console.log('No notification preferences found, using defaults');
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
            // If settings endpoint doesn't exist yet, use defaults
            if (error.status === 404) {
                console.log('Settings endpoint not found, using defaults');
            } else {
                this.showError('Failed to load settings. Please refresh the page.');
            }
        }
    }
    
    async handleGeneralSubmit(event) {
        event.preventDefault();
        
        const spinner = document.getElementById('generalSaveSpinner');
        const button = event.target.querySelector('button[type="submit"]');
        
        button.disabled = true;
        spinner.classList.remove('d-none');
        
        try {
            const settings = {
                ...this.settings,
                language: document.getElementById('settingsLanguage').value,
                timezone: document.getElementById('settingsTimezone').value,
                date_format: document.getElementById('settingsDateFormat').value
            };
            
            await window.api.put('/users/me/settings', settings);
            this.settings = settings;
            this.showSuccess('General settings updated successfully!');
            
        } catch (error) {
            console.error('Failed to update settings:', error);
            // If endpoint doesn't exist, store locally for now
            if (error.status === 404) {
                localStorage.setItem('userSettings', JSON.stringify(settings));
                this.showSuccess('Settings saved locally.');
            } else {
                this.showError('Failed to update settings. Please try again.');
            }
        } finally {
            button.disabled = false;
            spinner.classList.add('d-none');
        }
    }
    
    async handleNotificationSubmit(event) {
        event.preventDefault();
        
        const spinner = document.getElementById('notificationSaveSpinner');
        const button = event.target.querySelector('button[type="submit"]');
        
        button.disabled = true;
        spinner.classList.remove('d-none');
        
        try {
            const notifications = {
                host_down: document.getElementById('notifyHostDown').checked,
                host_up: document.getElementById('notifyHostUp').checked,
                weekly_report: document.getElementById('notifyWeeklyReport').checked,
                security_alerts: document.getElementById('notifySecurityAlerts').checked
            };
            
            const settings = {
                ...this.settings,
                notifications: notifications
            };
            
            await window.api.put('/users/me/settings', settings);
            this.settings = settings;
            this.showSuccess('Notification preferences updated!');
            
        } catch (error) {
            console.error('Failed to update notifications:', error);
            // If endpoint doesn't exist, store locally for now
            if (error.status === 404) {
                localStorage.setItem('notificationPrefs', JSON.stringify(notifications));
                this.showSuccess('Preferences saved locally.');
            } else {
                this.showError('Failed to update preferences. Please try again.');
            }
        } finally {
            button.disabled = false;
            spinner.classList.add('d-none');
        }
    }
    
    async loadActiveSessions() {
        const container = document.getElementById('activeSessions');
        container.innerHTML = '<div class="text-center"><div class="spinner-border"></div></div>';
        
        try {
            // Get current session info
            const currentSession = {
                device: this.getBrowserInfo(),
                ip: 'Current Device',
                location: 'Current Session',
                last_active: new Date().toISOString(),
                current: true
            };
            
            // For now, just show current session
            const sessions = [currentSession];
            
            container.innerHTML = sessions.map(session => `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">
                                ${session.device}
                                ${session.current ? '<span class="badge bg-success ms-2">Current</span>' : ''}
                            </h6>
                            <p class="mb-1 text-muted">
                                <small>
                                    ${session.ip} • ${session.location}<br>
                                    Last active: ${new Date(session.last_active).toLocaleString()}
                                </small>
                            </p>
                        </div>
                        ${!session.current ? `
                            <button class="btn btn-sm btn-outline-danger"
                                    onclick="settingsPage.revokeSession('${session.id}')">
                                Revoke
                            </button>
                        ` : ''}
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            container.innerHTML = '<div class="alert alert-danger">Failed to load sessions</div>';
        }
    }
    
    getBrowserInfo() {
        const ua = navigator.userAgent;
        let browser = "Unknown Browser";
        let os = "Unknown OS";
        
        // Detect browser
        if (ua.indexOf("Chrome") > -1 && ua.indexOf("Edg") === -1) {
            browser = "Chrome";
        } else if (ua.indexOf("Safari") > -1 && ua.indexOf("Chrome") === -1) {
            browser = "Safari";
        } else if (ua.indexOf("Firefox") > -1) {
            browser = "Firefox";
        } else if (ua.indexOf("Edg") > -1) {
            browser = "Edge";
        }
        
        // Detect OS
        if (ua.indexOf("Windows") > -1) {
            os = "Windows";
        } else if (ua.indexOf("Mac") > -1) {
            os = "macOS";
        } else if (ua.indexOf("Linux") > -1) {
            os = "Linux";
        } else if (ua.indexOf("Android") > -1) {
            os = "Android";
        } else if (ua.indexOf("iOS") > -1) {
            os = "iOS";
        }
        
        return `${browser} on ${os}`;
    }
    
    async exportData() {
        const button = this.exportDataBtn;
        const originalText = button.innerHTML;
        
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Preparing...';
        
        try {
            // For now, export local data
            const exportData = {
                profile: {
                    email: localStorage.getItem('userEmail'),
                    settings: this.settings
                },
                preferences: {
                    notifications: this.settings.notifications || {}
                },
                exported_at: new Date().toISOString()
            };
            
            // Create download
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `prism-dns-export-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            this.showSuccess('Data exported successfully!');
            
        } catch (error) {
            console.error('Failed to export data:', error);
            this.showError('Failed to export data. Please try again.');
        } finally {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
    
    confirmAccountDeletion() {
        // Navigate to the dedicated delete account page
        if (window.router) {
            window.router.navigate('/delete-account');
        } else {
            window.location.href = '/delete-account';
        }
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show mb-3`;
        alert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const section = this.sections[Array.from(this.sections).findIndex(s => 
            s.style.display !== 'none'
        )];
        
        if (section) {
            const cardBody = section.querySelector('.card-body');
            if (cardBody) {
                cardBody.insertBefore(alert, cardBody.firstChild);
                
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 5000);
            }
        }
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
window.SettingsPage = SettingsPage;
