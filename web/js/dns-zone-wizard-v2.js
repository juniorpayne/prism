/**
 * DNS Zone Creation Wizard V2 - Simplified Implementation
 * 
 * Design principles:
 * 1. All steps are rendered in the DOM at once
 * 2. Show/hide steps using CSS classes
 * 3. Direct event handling without complex delegation
 * 4. Simple state management
 */

class DNSZoneWizardV2 {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 5;
        this.modal = null;
        
        // Wizard data
        this.data = {
            domainName: '',
            zoneType: 'master',
            template: 'basic',
            nameservers: ['ns1.example.com', 'ns2.example.com'],
            useOrgDefaults: true,
            primaryNs: '',
            adminEmail: '',
            ttl: 3600,
            refresh: 3600,
            retry: 600,
            expire: 86400,
            minimumTtl: 3600,
            initialRecords: [],
            skipRecords: false
        };
        
        // Validation patterns
        this.patterns = {
            domain: /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i,
            email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        };
    }
    
    /**
     * Show the wizard
     */
    show() {
        this.createModal();
        this.attachEventListeners();
        this.showStep(1);
        
        // Show modal
        this.modal = new bootstrap.Modal(document.getElementById('dnsZoneWizardV2'));
        this.modal.show();
    }
    
    /**
     * Create the modal with all steps
     */
    createModal() {
        // Remove any existing modal
        const existing = document.getElementById('dnsZoneWizardV2');
        if (existing) existing.remove();
        
        const modalHTML = `
            <div class="modal fade" id="dnsZoneWizardV2" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-magic me-2"></i>Create New DNS Zone
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Progress Bar -->
                            <div class="progress mb-3" style="height: 30px;">
                                <div class="progress-bar" id="wizardProgress" role="progressbar" style="width: 20%">
                                    Step 1 of 5
                                </div>
                            </div>
                            
                            <!-- All Steps (hidden by default) -->
                            <div id="wizardSteps">
                                ${this.renderAllSteps()}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-outline-primary" id="btnBack" style="display: none;">
                                <i class="fas fa-arrow-left me-2"></i>Back
                            </button>
                            <button type="button" class="btn btn-primary" id="btnNext">
                                Next<i class="fas fa-arrow-right ms-2"></i>
                            </button>
                            <button type="button" class="btn btn-success" id="btnCreate" style="display: none;">
                                <i class="fas fa-check me-2"></i>Create Zone
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
    
    /**
     * Render all steps at once
     */
    renderAllSteps() {
        return `
            <!-- Step 1: Basic Information -->
            <div class="wizard-step" data-step="1">
                <h6 class="mb-3">Step 1: Basic Information</h6>
                
                <div class="mb-3">
                    <label for="domainName" class="form-label">Domain Name <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" id="domainName" placeholder="example.com">
                    <div class="invalid-feedback">Please enter a valid domain name</div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Zone Type</label>
                    <div class="btn-group d-flex" role="group">
                        <input type="radio" class="btn-check" name="zoneType" id="typeMaster" value="master" checked>
                        <label class="btn btn-outline-primary" for="typeMaster">
                            <i class="fas fa-crown me-2"></i>Master
                        </label>
                        <input type="radio" class="btn-check" name="zoneType" id="typeSlave" value="slave">
                        <label class="btn btn-outline-primary" for="typeSlave">
                            <i class="fas fa-link me-2"></i>Slave
                        </label>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Template</label>
                    <div class="row">
                        <div class="col-md-6 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="template" id="templateBasic" value="basic" checked>
                                <label class="form-check-label" for="templateBasic">
                                    <strong>Basic</strong><br>
                                    <small class="text-muted">Simple zone with default settings</small>
                                </label>
                            </div>
                        </div>
                        <div class="col-md-6 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="template" id="templateWeb" value="webhosting">
                                <label class="form-check-label" for="templateWeb">
                                    <strong>Web Hosting</strong><br>
                                    <small class="text-muted">Optimized for web hosting</small>
                                </label>
                            </div>
                        </div>
                        <div class="col-md-6 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="template" id="templateEmail" value="email">
                                <label class="form-check-label" for="templateEmail">
                                    <strong>Email Service</strong><br>
                                    <small class="text-muted">Pre-configured for email</small>
                                </label>
                            </div>
                        </div>
                        <div class="col-md-6 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="template" id="templateCustom" value="custom">
                                <label class="form-check-label" for="templateCustom">
                                    <strong>Custom</strong><br>
                                    <small class="text-muted">Start with empty zone</small>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Step 2: Name Servers -->
            <div class="wizard-step" data-step="2" style="display: none;">
                <h6 class="mb-3">Step 2: Name Servers</h6>
                
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="useOrgDefaults" checked>
                    <label class="form-check-label" for="useOrgDefaults">
                        Use organization default name servers
                    </label>
                </div>
                
                <div id="nameserverInputs">
                    <div class="mb-2">
                        <div class="input-group">
                            <span class="input-group-text">NS 1</span>
                            <input type="text" class="form-control nameserver-input" value="ns1.example.com" readonly>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="input-group">
                            <span class="input-group-text">NS 2</span>
                            <input type="text" class="form-control nameserver-input" value="ns2.example.com" readonly>
                        </div>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    At least 2 name servers are required for DNS redundancy
                </div>
            </div>
            
            <!-- Step 3: SOA Settings -->
            <div class="wizard-step" data-step="3" style="display: none;">
                <h6 class="mb-3">Step 3: SOA Settings</h6>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="primaryNs" class="form-label">Primary Name Server</label>
                        <input type="text" class="form-control" id="primaryNs" value="ns1.example.com" readonly>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="adminEmail" class="form-label">Administrator Email <span class="text-danger">*</span></label>
                        <input type="email" class="form-control" id="adminEmail" placeholder="admin@example.com">
                        <div class="invalid-feedback">Please enter a valid email address</div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="ttl" class="form-label">Default TTL (seconds)</label>
                        <input type="number" class="form-control" id="ttl" value="3600" min="60" max="86400">
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="minimumTtl" class="form-label">Minimum TTL (seconds)</label>
                        <input type="number" class="form-control" id="minimumTtl" value="3600" min="60" max="86400">
                    </div>
                </div>
            </div>
            
            <!-- Step 4: Initial Records -->
            <div class="wizard-step" data-step="4" style="display: none;">
                <h6 class="mb-3">Step 4: Initial Records (Optional)</h6>
                
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="skipRecords">
                    <label class="form-check-label" for="skipRecords">
                        Skip this step - I'll add records later
                    </label>
                </div>
                
                <div id="recordsSection">
                    <p class="text-muted">Record management will be available after zone creation.</p>
                </div>
            </div>
            
            <!-- Step 5: Review -->
            <div class="wizard-step" data-step="5" style="display: none;">
                <h6 class="mb-3">Step 5: Review & Create</h6>
                
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-title">Zone Configuration Summary</h6>
                        <dl class="row mb-0">
                            <dt class="col-sm-3">Domain Name</dt>
                            <dd class="col-sm-9" id="reviewDomain">-</dd>
                            
                            <dt class="col-sm-3">Zone Type</dt>
                            <dd class="col-sm-9" id="reviewType">-</dd>
                            
                            <dt class="col-sm-3">Template</dt>
                            <dd class="col-sm-9" id="reviewTemplate">-</dd>
                            
                            <dt class="col-sm-3">Name Servers</dt>
                            <dd class="col-sm-9" id="reviewNameservers">-</dd>
                            
                            <dt class="col-sm-3">Admin Email</dt>
                            <dd class="col-sm-9" id="reviewEmail">-</dd>
                        </dl>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Attach all event listeners
     */
    attachEventListeners() {
        // Navigation buttons
        document.getElementById('btnNext').addEventListener('click', () => this.nextStep());
        document.getElementById('btnBack').addEventListener('click', () => this.previousStep());
        document.getElementById('btnCreate').addEventListener('click', () => this.createZone());
        
        // Form inputs for validation
        document.getElementById('domainName').addEventListener('input', () => this.validateCurrentStep());
        document.getElementById('adminEmail').addEventListener('input', () => this.validateCurrentStep());
        
        // Checkbox handlers
        document.getElementById('useOrgDefaults').addEventListener('change', (e) => {
            const inputs = document.querySelectorAll('.nameserver-input');
            inputs.forEach(input => {
                input.readOnly = e.target.checked;
            });
        });
        
        // Modal cleanup
        document.getElementById('dnsZoneWizardV2').addEventListener('hidden.bs.modal', () => {
            this.cleanup();
        });
    }
    
    /**
     * Show specific step
     */
    showStep(step) {
        // Hide all steps
        document.querySelectorAll('.wizard-step').forEach(el => {
            el.style.display = 'none';
        });
        
        // Show current step
        const currentStepEl = document.querySelector(`[data-step="${step}"]`);
        if (currentStepEl) {
            currentStepEl.style.display = 'block';
        }
        
        // Update progress
        const progress = (step / this.totalSteps) * 100;
        const progressBar = document.getElementById('wizardProgress');
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `Step ${step} of ${this.totalSteps}`;
        
        // Update buttons
        document.getElementById('btnBack').style.display = step > 1 ? 'inline-block' : 'none';
        document.getElementById('btnNext').style.display = step < this.totalSteps ? 'inline-block' : 'none';
        document.getElementById('btnCreate').style.display = step === this.totalSteps ? 'inline-block' : 'none';
        
        // Validate to set button states
        this.validateCurrentStep();
        
        // Update review if on last step
        if (step === 5) {
            this.updateReview();
        }
    }
    
    /**
     * Go to next step
     */
    nextStep() {
        if (this.validateCurrentStep() && this.currentStep < this.totalSteps) {
            this.saveStepData();
            this.currentStep++;
            this.showStep(this.currentStep);
        }
    }
    
    /**
     * Go to previous step
     */
    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.showStep(this.currentStep);
        }
    }
    
    /**
     * Validate current step
     */
    validateCurrentStep() {
        let isValid = true;
        const nextBtn = document.getElementById('btnNext');
        
        switch (this.currentStep) {
            case 1:
                const domain = document.getElementById('domainName').value.trim();
                isValid = this.patterns.domain.test(domain);
                
                const domainInput = document.getElementById('domainName');
                if (domain) {
                    domainInput.classList.toggle('is-invalid', !isValid);
                    domainInput.classList.toggle('is-valid', isValid);
                } else {
                    domainInput.classList.remove('is-invalid', 'is-valid');
                }
                break;
                
            case 3:
                const email = document.getElementById('adminEmail').value.trim();
                isValid = this.patterns.email.test(email);
                
                const emailInput = document.getElementById('adminEmail');
                if (email) {
                    emailInput.classList.toggle('is-invalid', !isValid);
                    emailInput.classList.toggle('is-valid', isValid);
                } else {
                    emailInput.classList.remove('is-invalid', 'is-valid');
                }
                break;
        }
        
        if (nextBtn) {
            nextBtn.disabled = !isValid;
        }
        
        return isValid;
    }
    
    /**
     * Save current step data
     */
    saveStepData() {
        switch (this.currentStep) {
            case 1:
                this.data.domainName = document.getElementById('domainName').value.trim();
                this.data.zoneType = document.querySelector('input[name="zoneType"]:checked').value;
                this.data.template = document.querySelector('input[name="template"]:checked').value;
                break;
                
            case 2:
                this.data.useOrgDefaults = document.getElementById('useOrgDefaults').checked;
                this.data.nameservers = Array.from(document.querySelectorAll('.nameserver-input'))
                    .map(input => input.value.trim())
                    .filter(ns => ns);
                this.data.primaryNs = this.data.nameservers[0] || '';
                break;
                
            case 3:
                this.data.adminEmail = document.getElementById('adminEmail').value.trim();
                this.data.ttl = parseInt(document.getElementById('ttl').value);
                this.data.minimumTtl = parseInt(document.getElementById('minimumTtl').value);
                break;
                
            case 4:
                this.data.skipRecords = document.getElementById('skipRecords').checked;
                break;
        }
    }
    
    /**
     * Update review step
     */
    updateReview() {
        document.getElementById('reviewDomain').textContent = this.data.domainName || '-';
        document.getElementById('reviewType').textContent = this.data.zoneType || '-';
        document.getElementById('reviewTemplate').textContent = this.data.template || '-';
        document.getElementById('reviewNameservers').textContent = this.data.nameservers.join(', ') || '-';
        document.getElementById('reviewEmail').textContent = this.data.adminEmail || '-';
    }
    
    /**
     * Create the zone
     */
    async createZone() {
        const btn = document.getElementById('btnCreate');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating...';
        
        try {
            // Simulate API call - replace with actual implementation
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // For now, just show success
            alert(`Zone ${this.data.domainName} created successfully!`);
            
            // Close modal
            this.modal.hide();
            
            // Refresh zones list if available
            if (window.dnsZonesManager) {
                window.dnsZonesManager.loadZones();
            }
        } catch (error) {
            alert('Error creating zone: ' + error.message);
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-check me-2"></i>Create Zone';
        }
    }
    
    /**
     * Cleanup
     */
    cleanup() {
        // Reset form
        this.currentStep = 1;
        this.data = {
            domainName: '',
            zoneType: 'master',
            template: 'basic',
            nameservers: ['ns1.example.com', 'ns2.example.com'],
            useOrgDefaults: true,
            primaryNs: '',
            adminEmail: '',
            ttl: 3600,
            refresh: 3600,
            retry: 600,
            expire: 86400,
            minimumTtl: 3600,
            initialRecords: [],
            skipRecords: false
        };
    }
}

// Export for use
window.DNSZoneWizardV2 = DNSZoneWizardV2;