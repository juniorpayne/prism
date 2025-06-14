/**
 * Shared Password Validator Class
 * Reusable password strength checking and validation
 */

class PasswordValidator {
    constructor(options = {}) {
        this.strengthBarId = options.strengthBarId || 'passwordStrength';
        this.strengthTextId = options.strengthTextId || 'strengthText';
        this.requirementsId = options.requirementsId || 'passwordReqs';
        
        this.requirements = {
            length: false,
            uppercase: false,
            lowercase: false,
            number: false,
            special: false
        };
    }
    
    /**
     * Check password strength and update UI
     */
    checkStrength(password) {
        // Update requirements
        this.requirements.length = password.length >= 12;
        this.requirements.uppercase = /[A-Z]/.test(password);
        this.requirements.lowercase = /[a-z]/.test(password);
        this.requirements.number = /[0-9]/.test(password);
        this.requirements.special = /[!@#$%^&*(),.?"{}|<>]/.test(password);
        
        // Update UI
        this.updateUI(password);
        
        return this.requirements;
    }
    
    /**
     * Check if password meets all requirements
     */
    isValid() {
        return Object.values(this.requirements).every(req => req === true);
    }
    
    /**
     * Get the count of met requirements
     */
    getStrengthScore() {
        return Object.values(this.requirements).filter(v => v).length;
    }
    
    /**
     * Update UI elements based on password strength
     */
    updateUI(password = '') {
        // Update requirement indicators
        const requirementsEl = document.getElementById(this.requirementsId);
        if (requirementsEl) {
            // Show requirements when password has content
            if (password.length > 0) {
                requirementsEl.classList.remove('d-none');
            } else {
                requirementsEl.classList.add('d-none');
            }
            
            Object.keys(this.requirements).forEach(req => {
                const element = requirementsEl.querySelector(`[data-req="${req}"]`);
                if (element) {
                    const icon = element.querySelector('i');
                    if (this.requirements[req]) {
                        icon.classList.remove('bi-circle');
                        icon.classList.add('bi-check-circle-fill', 'text-success');
                    } else {
                        icon.classList.remove('bi-check-circle-fill', 'text-success');
                        icon.classList.add('bi-circle');
                    }
                }
            });
        }
        
        // Update strength bar
        const strengthBar = document.getElementById(this.strengthBarId);
        const strengthText = document.getElementById(this.strengthTextId);
        
        if (strengthBar && strengthText) {
            const metRequirements = this.getStrengthScore();
            const strength = (metRequirements / 5) * 100;
            
            strengthBar.style.width = `${strength}%`;
            strengthBar.className = 'progress-bar';
            
            if (password.length === 0) {
                strengthBar.style.width = '0%';
                strengthText.textContent = 'Enter password';
            } else if (strength <= 20) {
                strengthBar.classList.add('bg-danger');
                strengthText.textContent = 'Very weak';
            } else if (strength <= 40) {
                strengthBar.classList.add('bg-warning');
                strengthText.textContent = 'Weak';
            } else if (strength <= 60) {
                strengthBar.classList.add('bg-info');
                strengthText.textContent = 'Fair';
            } else if (strength <= 80) {
                strengthBar.classList.add('bg-primary');
                strengthText.textContent = 'Good';
            } else {
                strengthBar.classList.add('bg-success');
                strengthText.textContent = 'Strong';
            }
        }
    }
    
    /**
     * Reset validator state
     */
    reset() {
        this.requirements = {
            length: false,
            uppercase: false,
            lowercase: false,
            number: false,
            special: false
        };
        this.updateUI();
    }
    
    /**
     * Get human-readable requirement descriptions
     */
    getRequirementDescriptions() {
        return {
            length: 'At least 12 characters',
            uppercase: 'One uppercase letter',
            lowercase: 'One lowercase letter',
            number: 'One number',
            special: 'One special character'
        };
    }
    
    /**
     * Get list of unmet requirements
     */
    getUnmetRequirements() {
        const descriptions = this.getRequirementDescriptions();
        return Object.entries(this.requirements)
            .filter(([key, met]) => !met)
            .map(([key]) => descriptions[key]);
    }
}

// Export for use in other modules
window.PasswordValidator = PasswordValidator;