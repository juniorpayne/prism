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
     * @param {Object} options - Optional wizard configuration
     * @param {string} options.parentZone - Parent zone name for subdomain creation
     * @param {string} options.suggestedName - Suggested domain name
     */
    show(options = {}) {
        // Store options for parent detection
        this.options = options;
        
        // Store zones if provided for parent detection
        if (options.zones) {
            this.availableZones = options.zones;
        }
        
        // Pre-fill data if parent zone is provided
        if (options.parentZone) {
            this.data.parentZone = options.parentZone;
            this.data.isSubdomain = true;
        }
        
        if (options.suggestedName) {
            this.data.domainName = options.suggestedName;
        }
        
        this.createModal();
        this.attachEventListeners();
        this.showStep(1);
        
        // Show modal
        this.modal = new bootstrap.Modal(document.getElementById('dnsZoneWizardV2'));
        this.modal.show();
        
        // Apply parent detection enhancements after modal is shown
        setTimeout(() => {
            this.enhanceWithParentDetection();
        }, 100);
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
        
        // Apply inheritance settings when moving to nameserver or SOA steps
        if (step === 2 || step === 3) {
            this.applyInheritanceSettings();
        }
        
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
            // Use DNS service adapter to support both mock and real PowerDNS
            const dnsService = DNSServiceFactory.getAdapter();
            
            // Prepare zone data for PowerDNS format
            // Ensure domain name ends with a dot for PowerDNS
            const domainName = this.data.domainName.endsWith('.') 
                ? this.data.domainName 
                : this.data.domainName + '.';
            
            // Ensure nameservers end with dots
            const nameservers = this.data.nameservers.map(ns => 
                ns.endsWith('.') ? ns : ns + '.'
            );
                
            const zoneData = {
                name: domainName,
                kind: this.data.zoneType === 'master' ? 'Native' : 'Slave',
                nameservers: nameservers,
                email: this.data.adminEmail || `hostmaster.${domainName}`
            };
            
            await dnsService.createZone(zoneData);
            
            // Show success
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
     * Enhance the wizard with parent detection capabilities
     */
    enhanceWithParentDetection() {
        const domainInput = document.getElementById('domainName');
        if (!domainInput) return;
        
        // Pre-fill the domain name if provided
        if (this.options.suggestedName) {
            domainInput.value = this.options.suggestedName.replace(/\.$/, ''); // Remove trailing dot
        }
        
        // Add real-time parent detection on input
        domainInput.addEventListener('input', (e) => {
            this.detectParentDomain(e.target.value);
        });
        
        // If we already have a parent zone, show inheritance options
        if (this.options.parentZone) {
            this.showInheritanceOptions(this.options.parentZone);
        }
        
        console.log('Parent detection enhancement completed');
    }
    
    /**
     * Detect if the entered domain has a parent zone in the system
     */
    async detectParentDomain(domainName) {
        if (!domainName || domainName.length < 3) {
            this.hideParentDetection();
            return;
        }
        
        try {
            // Clean domain name
            const cleanDomain = domainName.replace(/\.$/, '');
            const parts = cleanDomain.split('.');
            
            if (parts.length <= 2) {
                // Not a subdomain
                this.hideParentDetection();
                return;
            }
            
            // Check for parent domains by removing parts from the beginning
            // This finds the closest existing parent zone
            for (let i = 1; i < parts.length - 1; i++) {
                const potentialParent = parts.slice(i).join('.') + '.';
                
                // Check if this parent exists in our zones
                // Try available zones first, then window contexts
                const zones = this.availableZones || 
                             window.dnsZonesManager?.zones || 
                             window.parent?.dnsZonesManager?.zones;
                             
                if (zones) {
                    const parentZone = zones.find(z => z.name === potentialParent);
                    if (parentZone) {
                        this.showParentDetection(parentZone, cleanDomain);
                        return;
                    }
                }
            }
            
            // No parent found
            this.hideParentDetection();
            
        } catch (error) {
            console.error('Error detecting parent domain:', error);
            this.hideParentDetection();
        }
    }
    
    /**
     * Show parent domain detection UI
     */
    showParentDetection(parentZone, childDomain) {
        // Remove existing parent detection UI
        this.hideParentDetection();
        
        const step1 = document.querySelector('[data-step="1"]');
        if (!step1) return;
        
        const parentDetectionHtml = `
            <div id="parentDetectionAlert" class="alert alert-info border-primary" style="border-left: 4px solid var(--bs-primary);">
                <div class="d-flex align-items-start">
                    <i class="bi bi-lightbulb text-primary me-3 fs-5"></i>
                    <div class="flex-grow-1">
                        <h6 class="mb-2">
                            <i class="bi bi-diagram-3 me-1"></i>
                            Parent Zone Detected!
                        </h6>
                        <p class="mb-3">
                            We found that <strong>${parentZone.name.replace(/\.$/, '')}</strong> already exists. 
                            Would you like to create <strong>${childDomain}</strong> as a subdomain?
                        </p>
                        
                        <div class="d-flex gap-2 mb-3">
                            <button type="button" class="btn btn-primary btn-sm" onclick="window.dnsZoneWizardV2Instance.acceptParentSuggestion('${parentZone.name}')">
                                <i class="bi bi-check-circle me-1"></i>Yes, create as subdomain
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="window.dnsZoneWizardV2Instance.rejectParentSuggestion()">
                                <i class="bi bi-x-circle me-1"></i>No, create as independent zone
                            </button>
                        </div>
                        
                        <div id="inheritancePreview" style="display: none;">
                            <h6 class="text-primary"><i class="bi bi-arrow-down-circle me-1"></i>Inheritance Options</h6>
                            <div class="row">
                                <div class="col-md-4">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="inheritNameservers" checked>
                                        <label class="form-check-label" for="inheritNameservers">
                                            <strong>Name Servers</strong><br>
                                            <small class="text-muted">Use parent's name servers</small>
                                        </label>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="inheritSOA" checked>
                                        <label class="form-check-label" for="inheritSOA">
                                            <strong>SOA Settings</strong><br>
                                            <small class="text-muted">Use parent's SOA configuration</small>
                                        </label>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="inheritTTL" checked>
                                        <label class="form-check-label" for="inheritTTL">
                                            <strong>Default TTL</strong><br>
                                            <small class="text-muted">Use parent's default TTL</small>
                                        </label>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Preview of inherited values -->
                            <div id="inheritedValuesPreview" class="mt-3 p-3 bg-light rounded" style="display: none;">
                                <h6 class="text-secondary mb-2"><i class="bi bi-eye me-1"></i>Preview of Inherited Values</h6>
                                <div class="row small">
                                    <div class="col-md-6">
                                        <div id="nameserversPreview" style="display: none;">
                                            <strong>Name Servers:</strong>
                                            <ul class="mb-2" id="nameserversList"></ul>
                                        </div>
                                        <div id="ttlPreview" style="display: none;">
                                            <strong>Default TTL:</strong> <span id="ttlValue"></span>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div id="soaPreview" style="display: none;">
                                            <strong>SOA Settings:</strong>
                                            <ul class="mb-0" id="soaList"></ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="mt-2">
                                <small class="text-muted">
                                    <i class="bi bi-info-circle me-1"></i>
                                    Inherited settings can be customized later in the wizard.
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert after the domain name input
        const domainGroup = step1.querySelector('.mb-3');
        if (domainGroup) {
            domainGroup.insertAdjacentHTML('afterend', parentDetectionHtml);
        }
        
        // Store reference to wizard instance
        window.dnsZoneWizardV2Instance = this;
    }
    
    /**
     * Hide parent domain detection UI
     */
    hideParentDetection() {
        const existingAlert = document.getElementById('parentDetectionAlert');
        if (existingAlert) {
            existingAlert.remove();
        }
    }
    
    /**
     * Accept parent domain suggestion
     */
    async acceptParentSuggestion(parentZoneName) {
        try {
            // Store parent zone information
            this.data.parentZone = parentZoneName;
            this.data.isSubdomain = true;
            
            // Show inheritance preview
            const inheritancePreview = document.getElementById('inheritancePreview');
            if (inheritancePreview) {
                inheritancePreview.style.display = 'block';
            }
            
            // Load parent zone data for inheritance
            await this.loadParentZoneData(parentZoneName);
            
            // Show preview of inherited values
            this.showInheritedValuesPreview();
            
            // Update the alert to show accepted state
            const alert = document.getElementById('parentDetectionAlert');
            if (alert) {
                alert.classList.remove('alert-info');
                alert.classList.add('alert-success');
                const icon = alert.querySelector('.bi-lightbulb');
                if (icon) {
                    icon.className = 'bi bi-check-circle text-success me-3 fs-5';
                }
            }
            
            console.log('Parent suggestion accepted:', parentZoneName);
            
        } catch (error) {
            console.error('Error accepting parent suggestion:', error);
        }
    }
    
    /**
     * Reject parent domain suggestion
     */
    rejectParentSuggestion() {
        // Clear parent zone data
        this.data.parentZone = null;
        this.data.isSubdomain = false;
        
        // Hide the parent detection UI
        this.hideParentDetection();
        
        console.log('Parent suggestion rejected');
    }
    
    /**
     * Load parent zone data for inheritance
     */
    async loadParentZoneData(parentZoneName) {
        const zones = this.availableZones || 
                     window.dnsZonesManager?.zones || 
                     window.parent?.dnsZonesManager?.zones;
                     
        if (!zones) return;
        
        try {
            // Find parent zone
            const parentZone = zones.find(z => z.name === parentZoneName);
            if (!parentZone) return;
            
            // Get full parent zone data
            const mockService = new DNSMockDataService();
            const fullParentZone = await mockService.getZone(parentZone.id);
            
            if (fullParentZone) {
                // Store parent zone data for inheritance
                this.data.parentZoneData = fullParentZone;
                
                // Pre-fill inheritance settings
                if (fullParentZone.nameservers) {
                    this.data.inheritedNameservers = [...fullParentZone.nameservers];
                }
                
                // Extract SOA settings if available
                if (fullParentZone.rrsets) {
                    const soaRecord = fullParentZone.rrsets.find(r => r.type === 'SOA');
                    if (soaRecord && soaRecord.records.length > 0) {
                        const soaContent = soaRecord.records[0].content;
                        const soaParts = soaContent.split(' ');
                        if (soaParts.length >= 7) {
                            this.data.inheritedSOA = {
                                primaryNs: soaParts[0],
                                adminEmail: soaParts[1],
                                refresh: parseInt(soaParts[3]),
                                retry: parseInt(soaParts[4]),
                                expire: parseInt(soaParts[5]),
                                minimumTtl: parseInt(soaParts[6])
                            };
                        }
                    }
                    
                    // Also check for default TTL (if SOA record has TTL)
                    if (soaRecord && soaRecord.ttl) {
                        this.data.inheritedTTL = soaRecord.ttl;
                    }
                }
                
                console.log('Parent zone data loaded for inheritance:', this.data.parentZoneData.name);
            }
            
        } catch (error) {
            console.error('Error loading parent zone data:', error);
        }
    }
    
    /**
     * Show inheritance options (called when wizard is opened with parent pre-selected)
     */
    showInheritanceOptions(parentZoneName) {
        setTimeout(() => {
            this.showParentDetection({ name: parentZoneName }, '');
            this.acceptParentSuggestion(parentZoneName);
        }, 200);
    }
    
    /**
     * Show preview of inherited values
     */
    showInheritedValuesPreview() {
        const previewContainer = document.getElementById('inheritedValuesPreview');
        if (!previewContainer) return;
        
        previewContainer.style.display = 'block';
        
        // Show nameservers preview
        if (this.data.inheritedNameservers && this.data.inheritedNameservers.length > 0) {
            const nameserversPreview = document.getElementById('nameserversPreview');
            const nameserversList = document.getElementById('nameserversList');
            if (nameserversPreview && nameserversList) {
                nameserversPreview.style.display = 'block';
                nameserversList.innerHTML = this.data.inheritedNameservers
                    .map(ns => `<li>${this.escapeHtml(ns)}</li>`)
                    .join('');
            }
        }
        
        // Show TTL preview
        if (this.data.inheritedTTL) {
            const ttlPreview = document.getElementById('ttlPreview');
            const ttlValue = document.getElementById('ttlValue');
            if (ttlPreview && ttlValue) {
                ttlPreview.style.display = 'block';
                ttlValue.textContent = `${this.data.inheritedTTL} seconds`;
            }
        }
        
        // Show SOA preview
        if (this.data.inheritedSOA) {
            const soaPreview = document.getElementById('soaPreview');
            const soaList = document.getElementById('soaList');
            if (soaPreview && soaList) {
                soaPreview.style.display = 'block';
                soaList.innerHTML = `
                    <li>Primary NS: ${this.escapeHtml(this.data.inheritedSOA.primaryNs)}</li>
                    <li>Admin Email: ${this.escapeHtml(this.data.inheritedSOA.adminEmail)}</li>
                    <li>Refresh: ${this.data.inheritedSOA.refresh}s</li>
                    <li>Retry: ${this.data.inheritedSOA.retry}s</li>
                    <li>Expire: ${this.data.inheritedSOA.expire}s</li>
                    <li>Minimum TTL: ${this.data.inheritedSOA.minimumTtl}s</li>
                `;
            }
        }
    }
    
    /**
     * Apply inheritance settings in later steps
     */
    applyInheritanceSettings() {
        if (!this.data.isSubdomain || !this.data.parentZoneData) return;
        
        // Apply nameserver inheritance
        const inheritNameservers = document.getElementById('inheritNameservers');
        if (inheritNameservers && inheritNameservers.checked && this.data.inheritedNameservers) {
            this.data.nameservers = [...this.data.inheritedNameservers];
            this.data.primaryNs = this.data.inheritedNameservers[0] || '';
            
            // Update nameserver inputs
            const nameserverInputs = document.querySelectorAll('.nameserver-input');
            nameserverInputs.forEach((input, index) => {
                if (this.data.inheritedNameservers[index]) {
                    input.value = this.data.inheritedNameservers[index];
                }
            });
        }
        
        // Apply SOA inheritance
        const inheritSOA = document.getElementById('inheritSOA');
        if (inheritSOA && inheritSOA.checked && this.data.inheritedSOA) {
            this.data.primaryNs = this.data.inheritedSOA.primaryNs;
            this.data.adminEmail = this.data.inheritedSOA.adminEmail;
            this.data.refresh = this.data.inheritedSOA.refresh;
            this.data.retry = this.data.inheritedSOA.retry;
            this.data.expire = this.data.inheritedSOA.expire;
            this.data.minimumTtl = this.data.inheritedSOA.minimumTtl;
            
            // Update SOA inputs
            const primaryNsInput = document.getElementById('primaryNs');
            const adminEmailInput = document.getElementById('adminEmail');
            const minimumTtlInput = document.getElementById('minimumTtl');
            
            if (primaryNsInput) primaryNsInput.value = this.data.primaryNs;
            if (adminEmailInput) adminEmailInput.value = this.data.adminEmail;
            if (minimumTtlInput) minimumTtlInput.value = this.data.minimumTtl;
        }
        
        // Apply TTL inheritance
        const inheritTTL = document.getElementById('inheritTTL');
        if (inheritTTL && inheritTTL.checked && this.data.inheritedTTL) {
            this.data.ttl = this.data.inheritedTTL;
            
            // Update TTL input
            const ttlInput = document.getElementById('ttl');
            if (ttlInput) ttlInput.value = this.data.ttl;
        }
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
            skipRecords: false,
            // Parent detection fields
            parentZone: null,
            isSubdomain: false,
            parentZoneData: null,
            inheritedNameservers: null,
            inheritedSOA: null,
            inheritedTTL: null
        };
        
        // Clean up global reference
        if (window.dnsZoneWizardV2Instance === this) {
            delete window.dnsZoneWizardV2Instance;
        }
    }
}

// Export for use
window.DNSZoneWizardV2 = DNSZoneWizardV2;