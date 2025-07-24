/**
 * Profile Page for Prism DNS
 * Handles user profile viewing and editing
 */

class ProfilePage {
    constructor() {
        this.viewMode = document.getElementById('profileViewMode');
        this.editMode = document.getElementById('profileEditMode');
        this.editBtn = document.getElementById('editProfileBtn');
        this.cancelBtn = document.getElementById('cancelEditBtn');
        this.form = document.getElementById('editProfileForm');
        this.bioTextarea = document.getElementById('editBio');
        this.bioCharCount = document.getElementById('bioCharCount');
        this.saveBtn = document.getElementById('saveProfileBtn');
        this.saveSpinner = document.getElementById('saveProfileSpinner');
        
        this.userData = null;
        this.originalData = null;
        this.isDestroyed = false;
        
        this.init();
    }
    
    init() {
        if (!this.form) {
            console.error('Profile form not found');
            return;
        }
        
        this.setupEventListeners();
        this.loadUserProfile();
    }
    
    setupEventListeners() {
        // Edit/Cancel buttons
        this.editBtn?.addEventListener('click', () => this.enterEditMode());
        this.cancelBtn?.addEventListener('click', () => this.exitEditMode());
        
        // Form submission
        this.form?.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Character counting for bio
        this.bioTextarea?.addEventListener('input', () => this.updateCharCount());
        
        // Real-time validation
        const fullNameInput = document.getElementById('editFullName');
        if (fullNameInput) {
            fullNameInput.addEventListener('blur', () => this.validateFullName());
            fullNameInput.addEventListener('input', () => {
                if (fullNameInput.classList.contains('is-invalid')) {
                    this.validateFullName();
                }
            });
        }
    }
    
    async loadUserProfile() {
        try {
            const response = await window.api.get('/users/me');
            this.userData = response;
            this.displayProfile(response);
        } catch (error) {
            console.error('Failed to load profile:', error);
            this.showError('Failed to load profile. Please try again.');
        }
    }
    
    displayProfile(data) {
        // Display name (full name or username)
        const displayName = data.full_name || data.username || 'User';
        document.getElementById('profileDisplayName').textContent = displayName;
        
        // Email and username
        document.getElementById('profileEmail').textContent = data.email || '';
        document.getElementById('profileUsername').textContent = `@${data.username || 'user'}`;
        
        // Member since
        if (data.created_at) {
            const date = new Date(data.created_at);
            document.getElementById('profileCreatedAt').textContent = date.toLocaleDateString();
        }
        
        // Profile information
        document.getElementById('profileFullName').textContent = data.full_name || 'Not provided';
        document.getElementById('profileBio').textContent = data.bio || 'No bio added yet';
        
        // Email verification status
        const emailVerifiedBadge = document.getElementById('profileEmailVerified');
        if (emailVerifiedBadge) {
            if (data.email_verified) {
                emailVerifiedBadge.textContent = 'Verified';
                emailVerifiedBadge.className = 'badge bg-success';
            } else {
                emailVerifiedBadge.textContent = 'Not Verified';
                emailVerifiedBadge.className = 'badge bg-warning';
            }
        }
        
        // Update avatar with initials
        const avatar = document.getElementById('profileAvatar');
        if (avatar && displayName) {
            const initials = this.getInitials(displayName);
            avatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(initials)}&background=0d6efd&color=fff&size=150`;
        }
        
        // Update navbar user info if navigation exists
        if (window.app?.navigation) {
            window.app.navigation.updateUserInfo();
        }
    }
    
    getInitials(name) {
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) {
            return parts[0][0] + parts[parts.length - 1][0];
        }
        return name.substring(0, 2);
    }
    
    enterEditMode() {
        if (!this.userData) return;
        
        // Store original data for cancel functionality
        this.originalData = {
            full_name: this.userData.full_name || '',
            bio: this.userData.bio || ''
        };
        
        // Populate form with current data
        document.getElementById('editFullName').value = this.originalData.full_name;
        document.getElementById('editBio').value = this.originalData.bio;
        
        // Update character count
        this.updateCharCount();
        
        // Switch views
        this.viewMode.style.display = 'none';
        this.editMode.style.display = 'block';
        this.editBtn.style.display = 'none';
        
        // Focus on first field
        document.getElementById('editFullName').focus();
    }
    
    exitEditMode() {
        // Switch views
        this.viewMode.style.display = 'block';
        this.editMode.style.display = 'none';
        this.editBtn.style.display = 'inline-block';
        
        // Reset form validation
        this.form.classList.remove('was-validated');
        this.clearValidation();
        this.clearErrors();
    }
    
    updateCharCount() {
        const count = this.bioTextarea.value.length;
        this.bioCharCount.textContent = count;
        
        // Update color based on count
        if (count > 450) {
            this.bioCharCount.classList.add('text-warning');
            this.bioCharCount.classList.remove('text-danger');
        } else if (count >= 500) {
            this.bioCharCount.classList.add('text-danger');
            this.bioCharCount.classList.remove('text-warning');
        } else {
            this.bioCharCount.classList.remove('text-warning', 'text-danger');
        }
    }
    
    validateFullName() {
        const input = document.getElementById('editFullName');
        const value = input.value.trim();
        
        // Allow empty (optional field)
        if (!value) {
            input.classList.remove('is-invalid', 'is-valid');
            return true;
        }
        
        // Validate format: letters, spaces, hyphens, apostrophes
        const isValid = /^[a-zA-Z\s'-]{1,255}$/.test(value);
        
        if (isValid) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
        }
        
        return isValid;
    }
    
    async handleSubmit(event) {
        event.preventDefault();
        event.stopPropagation();
        
        // Clear any existing errors
        this.clearErrors();
        
        // Validate form
        if (!this.validateFullName()) {
            this.form.classList.add('was-validated');
            return;
        }
        
        // Get form data
        const fullName = document.getElementById('editFullName').value.trim();
        const bio = document.getElementById('editBio').value.trim();
        
        // Check if anything changed
        if (fullName === this.originalData.full_name && bio === this.originalData.bio) {
            this.showInfo('No changes to save.');
            this.exitEditMode();
            return;
        }
        
        // Show loading state
        this.saveBtn.disabled = true;
        this.saveSpinner.classList.remove('d-none');
        
        try {
            const updates = {
                full_name: fullName,
                bio: bio
            };
            
            const response = await window.api.put('/users/me', updates);
            
            // Update local data
            this.userData = { ...this.userData, ...response };
            this.displayProfile(this.userData);
            
            // Show success and exit edit mode
            this.showSuccess('Profile updated successfully!');
            this.exitEditMode();
            
        } catch (error) {
            console.error('Failed to update profile:', error);
            this.showError(error.message || 'Failed to update profile. Please try again.');
        } finally {
            this.saveBtn.disabled = false;
            this.saveSpinner.classList.add('d-none');
        }
    }
    
    clearValidation() {
        const inputs = this.form.querySelectorAll('.is-valid, .is-invalid');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success', this.viewMode);
    }
    
    showError(message) {
        const container = this.editMode.style.display === 'none' ? this.viewMode : this.editMode;
        this.showAlert(message, 'danger', container);
    }
    
    showInfo(message) {
        const container = this.editMode.style.display === 'none' ? this.viewMode : this.editMode;
        this.showAlert(message, 'info', container);
    }
    
    showAlert(message, type, container) {
        // Remove any existing alerts
        this.clearErrors();
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.insertBefore(alert, container.firstChild);
        
        // Auto-remove after delay
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, type === 'danger' ? 10000 : 5000);
    }
    
    clearErrors() {
        const alerts = document.querySelectorAll('#profileViewMode .alert, #profileEditMode .alert');
        alerts.forEach(alert => alert.remove());
    }
    
    /**
     * Clean up event listeners and resources
     */
    destroy() {
        this.isDestroyed = true;
        this.clearErrors();
        // Event listeners are automatically cleaned up when elements are removed from DOM
    }
}

// Export for use in other modules
window.ProfilePage = ProfilePage;