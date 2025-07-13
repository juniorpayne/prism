/**
 * DNS Zone Creation Wizard
 * Multi-step wizard for creating new DNS zones with validation and templates
 */

class DNSZoneWizard {
    constructor() {
        this.mockService = new DNSMockDataService();
        this.modal = null;
        this.currentStep = 1;
        this.totalSteps = 5;
        
        // Wizard state
        this.wizardData = {
            // Step 1: Basic Information
            domainName: '',
            zoneType: 'master',
            template: 'basic',
            
            // Step 2: Name Servers
            nameservers: ['ns1.example.com', 'ns2.example.com'],
            useOrgDefaults: true,
            
            // Step 3: SOA Settings
            primaryNs: '',
            adminEmail: '',
            ttl: 3600,
            refresh: 3600,
            retry: 600,
            expire: 86400,
            minimumTtl: 3600,
            
            // Step 4: Initial Records
            initialRecords: [],
            skipRecords: false,
            
            // Step 5: Review (no data, just display)
        };

        // Templates configuration
        this.templates = {
            basic: {
                name: 'Basic',
                description: 'Simple zone with default settings',
                nameservers: ['ns1.example.com', 'ns2.example.com'],
                records: []
            },
            webhosting: {
                name: 'Web Hosting',
                description: 'Optimized for web hosting with www and mail records',
                nameservers: ['ns1.example.com', 'ns2.example.com'],
                records: [
                    { type: 'A', name: '@', content: '192.0.2.1', ttl: 3600 },
                    { type: 'A', name: 'www', content: '192.0.2.1', ttl: 3600 },
                    { type: 'MX', name: '@', content: 'mail.example.com', priority: 10, ttl: 3600 }
                ]
            },
            email: {
                name: 'Email Service',
                description: 'Pre-configured for email hosting',
                nameservers: ['ns1.example.com', 'ns2.example.com'],
                records: [
                    { type: 'MX', name: '@', content: 'mx1.example.com', priority: 10, ttl: 3600 },
                    { type: 'MX', name: '@', content: 'mx2.example.com', priority: 20, ttl: 3600 },
                    { type: 'TXT', name: '@', content: 'v=spf1 mx ~all', ttl: 3600 }
                ]
            },
            custom: {
                name: 'Custom',
                description: 'Start with empty zone and configure manually',
                nameservers: ['ns1.example.com', 'ns2.example.com'],
                records: []
            }
        };

        // Validation rules
        this.validationRules = {
            domainName: /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i,
            email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            nameserver: /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i,
            ipv4: /^(\d{1,3}\.){3}\d{1,3}$/,
            ipv6: /^([\da-f]{1,4}:){7}[\da-f]{1,4}$/i
        };
    }

    /**
     * Show the create zone wizard
     */
    showWizard() {
        this.resetWizardData();
        this.currentStep = 1;
        this.createModal();
        this.bindEvents();
        // Update navigation buttons after modal is created
        this.updateNavigationButtons();
        
        // Focus on first input after modal is shown
        const modalElement = document.getElementById('dnsZoneWizardModal');
        modalElement.addEventListener('shown.bs.modal', () => {
            const firstInput = document.querySelector('#wizardContent input:not([type="hidden"])');
            if (firstInput) firstInput.focus();
        }, { once: true });
    }

    /**
     * Reset wizard data to defaults
     */
    resetWizardData() {
        this.wizardData = {
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

    /**
     * Create and display the wizard modal
     */
    createModal() {
        // Remove existing modal if any
        const existingModal = document.getElementById('dnsZoneWizardModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="dnsZoneWizardModal" tabindex="-1" aria-labelledby="wizardModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="wizardModalLabel">
                                <i class="fas fa-magic me-2"></i>Create New DNS Zone
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ${this.renderProgressBar()}
                            <div id="wizardContent" class="mt-4">
                                ${this.renderStep(1)}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cancel
                            </button>
                            <button type="button" class="btn btn-outline-primary" id="wizardBackBtn" onclick="dnsZoneWizard.previousStep()">
                                <i class="fas fa-arrow-left me-2"></i>Back
                            </button>
                            <button type="button" class="btn btn-primary" id="wizardNextBtn" onclick="dnsZoneWizard.nextStep()" 
                                    title="Complete all required fields to continue">
                                Next<i class="fas fa-arrow-right ms-2"></i>
                            </button>
                            <button type="button" class="btn btn-success" id="wizardCreateBtn" onclick="dnsZoneWizard.createZone()" style="display: none;">
                                <i class="fas fa-check me-2"></i>Create Zone
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Initialize Bootstrap modal
        this.modal = new bootstrap.Modal(document.getElementById('dnsZoneWizardModal'));
        this.modal.show();
    }

    /**
     * Render progress bar
     */
    renderProgressBar() {
        const steps = [
            'Basic Info',
            'Name Servers',
            'SOA Settings',
            'Initial Records',
            'Review'
        ];

        return `
            <div class="wizard-progress">
                <div class="progress" style="height: 30px;">
                    <div class="progress-bar" role="progressbar" 
                         style="width: ${(this.currentStep / this.totalSteps) * 100}%"
                         aria-valuenow="${this.currentStep}" 
                         aria-valuemin="1" 
                         aria-valuemax="${this.totalSteps}">
                        Step ${this.currentStep} of ${this.totalSteps}
                    </div>
                </div>
                <div class="step-indicators d-flex justify-content-between mt-2">
                    ${steps.map((step, index) => `
                        <div class="step-indicator text-center ${index + 1 === this.currentStep ? 'active' : ''} ${index + 1 < this.currentStep ? 'completed' : ''}">
                            <div class="step-number">${index + 1}</div>
                            <div class="step-label small">${step}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Show specific step
     */
    showStep(stepNumber) {
        this.currentStep = stepNumber;
        
        const modalBody = document.querySelector('.modal-body');
        if (!modalBody) {
            console.error('Modal body not found!');
            return;
        }
        
        // Update progress bar and content
        modalBody.innerHTML = 
            this.renderProgressBar() + 
            '<div id="wizardContent" class="mt-4">' + 
            this.renderStep(stepNumber) + 
            '</div>';
        
        // Update navigation buttons
        this.updateNavigationButtons();
        
        // Fix modal height calculation issue - force Bootstrap to recalculate dimensions
        setTimeout(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('dnsZoneWizardModal'));
            if (modal) {
                modal.handleUpdate(); // Force Bootstrap to recalculate dimensions
            }
            
            // Focus first input after modal update
            const firstInput = document.querySelector('#wizardContent input:not([type="hidden"])');
            if (firstInput) firstInput.focus();
        }, 100);
    }

    /**
     * Render specific step content
     */
    renderStep(stepNumber) {
        switch (stepNumber) {
            case 1: return this.renderStep1();
            case 2: return this.renderStep2();
            case 3: return this.renderStep3();
            case 4: return this.renderStep4();
            case 5: return this.renderStep5();
            default: return '';
        }
    }

    /**
     * Step 1: Basic Information
     */
    renderStep1() {
        return `
            <div class="step-content">
                <h6 class="mb-3">Step 1: Basic Information</h6>
                
                <div class="mb-3">
                    <label for="domainName" class="form-label">Domain Name <span class="text-danger">*</span></label>
                    <input type="text" class="form-control" id="domainName" 
                           placeholder="example.com" value="${this.wizardData.domainName}"
                           onkeyup="dnsZoneWizard.validateStep1()">
                    <div class="invalid-feedback">
                        Please enter a valid domain name (e.g., example.com)
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label">Zone Type</label>
                    <div class="btn-group d-flex" role="group">
                        <input type="radio" class="btn-check" name="zoneType" id="typeMaster" 
                               value="master" ${this.wizardData.zoneType === 'master' ? 'checked' : ''}>
                        <label class="btn btn-outline-primary" for="typeMaster">
                            <i class="fas fa-crown me-2"></i>Master
                        </label>
                        
                        <input type="radio" class="btn-check" name="zoneType" id="typeSlave" 
                               value="slave" ${this.wizardData.zoneType === 'slave' ? 'checked' : ''}>
                        <label class="btn btn-outline-primary" for="typeSlave">
                            <i class="fas fa-link me-2"></i>Slave
                        </label>
                    </div>
                    <small class="text-muted">Master zones are authoritative, Slave zones replicate from a master</small>
                </div>

                <div class="mb-3">
                    <label class="form-label">Template</label>
                    <div class="row">
                        ${Object.entries(this.templates).map(([key, template]) => `
                            <div class="col-md-6 mb-2">
                                <div class="form-check template-option p-3 border rounded 
                                     ${this.wizardData.template === key ? 'border-primary bg-light' : ''}">
                                    <input class="form-check-input" type="radio" name="template" 
                                           id="template${key}" value="${key}"
                                           ${this.wizardData.template === key ? 'checked' : ''}
                                           onchange="dnsZoneWizard.selectTemplate('${key}')">
                                    <label class="form-check-label" for="template${key}">
                                        <strong>${template.name}</strong><br>
                                        <small class="text-muted">${template.description}</small>
                                    </label>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Step 2: Name Servers
     */
    renderStep2() {
        return `
            <div class="step-content">
                <h6 class="mb-3">Step 2: Name Servers</h6>
                
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="useOrgDefaults" 
                           ${this.wizardData.useOrgDefaults ? 'checked' : ''}
                           onchange="dnsZoneWizard.toggleOrgDefaults()">
                    <label class="form-check-label" for="useOrgDefaults">
                        Use organization default name servers
                    </label>
                </div>

                <div id="nameserversList">
                    ${this.wizardData.nameservers.map((ns, index) => `
                        <div class="input-group mb-2" id="ns-row-${index}">
                            <span class="input-group-text">NS ${index + 1}</span>
                            <input type="text" class="form-control nameserver-input" 
                                   value="${ns}" placeholder="ns${index + 1}.example.com"
                                   onkeyup="dnsZoneWizard.validateNameserver(${index})"
                                   ${this.wizardData.useOrgDefaults ? 'readonly' : ''}>
                            <button class="btn btn-outline-danger" type="button" 
                                    onclick="dnsZoneWizard.removeNameserver(${index})"
                                    ${this.wizardData.useOrgDefaults || this.wizardData.nameservers.length <= 2 ? 'disabled' : ''}>
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `).join('')}
                </div>

                <button type="button" class="btn btn-sm btn-outline-primary" 
                        onclick="dnsZoneWizard.addNameserver()"
                        ${this.wizardData.useOrgDefaults ? 'disabled' : ''}>
                    <i class="fas fa-plus me-2"></i>Add Name Server
                </button>

                <div class="alert alert-info mt-3">
                    <i class="fas fa-info-circle me-2"></i>
                    At least 2 name servers are required for DNS redundancy
                </div>
            </div>
        `;
    }

    /**
     * Step 3: SOA Settings
     */
    renderStep3() {
        // Auto-fill primary NS from step 2 if not set
        if (!this.wizardData.primaryNs && this.wizardData.nameservers.length > 0) {
            this.wizardData.primaryNs = this.wizardData.nameservers[0];
        }

        return `
            <div class="step-content">
                <h6 class="mb-3">Step 3: SOA (Start of Authority) Settings</h6>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="primaryNs" class="form-label">Primary Name Server</label>
                        <input type="text" class="form-control" id="primaryNs" 
                               value="${this.wizardData.primaryNs}" readonly>
                        <small class="text-muted">Auto-filled from name servers</small>
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="adminEmail" class="form-label">Administrator Email <span class="text-danger">*</span></label>
                        <input type="email" class="form-control" id="adminEmail" 
                               placeholder="admin@example.com" 
                               value="${this.wizardData.adminEmail}"
                               onkeyup="dnsZoneWizard.validateEmail()">
                        <div class="invalid-feedback">
                            Please enter a valid email address
                        </div>
                    </div>
                </div>

                <h6 class="mt-3 mb-2">TTL Values (seconds)</h6>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="ttl" class="form-label">Default TTL</label>
                        <input type="number" class="form-control" id="ttl" 
                               value="${this.wizardData.ttl}" min="60" max="86400"
                               onchange="dnsZoneWizard.updateWizardData()">
                    </div>
                    
                    <div class="col-md-6 mb-3">
                        <label for="minimumTtl" class="form-label">Minimum TTL</label>
                        <input type="number" class="form-control" id="minimumTtl" 
                               value="${this.wizardData.minimumTtl}" min="60" max="86400"
                               onchange="dnsZoneWizard.updateWizardData()">
                    </div>
                </div>

                <div class="accordion" id="advancedSettings">
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" 
                                    data-bs-toggle="collapse" data-bs-target="#advancedSOA">
                                <i class="fas fa-cog me-2"></i>Advanced SOA Settings
                            </button>
                        </h2>
                        <div id="advancedSOA" class="accordion-collapse collapse" 
                             data-bs-parent="#advancedSettings">
                            <div class="accordion-body">
                                <div class="row">
                                    <div class="col-md-4 mb-3">
                                        <label for="refresh" class="form-label">Refresh</label>
                                        <input type="number" class="form-control" id="refresh" 
                                               value="${this.wizardData.refresh}" min="60"
                                               onchange="dnsZoneWizard.updateWizardData()">
                                    </div>
                                    
                                    <div class="col-md-4 mb-3">
                                        <label for="retry" class="form-label">Retry</label>
                                        <input type="number" class="form-control" id="retry" 
                                               value="${this.wizardData.retry}" min="60"
                                               onchange="dnsZoneWizard.updateWizardData()">
                                    </div>
                                    
                                    <div class="col-md-4 mb-3">
                                        <label for="expire" class="form-label">Expire</label>
                                        <input type="number" class="form-control" id="expire" 
                                               value="${this.wizardData.expire}" min="3600"
                                               onchange="dnsZoneWizard.updateWizardData()">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Step 4: Initial Records
     */
    renderStep4() {
        return `
            <div class="step-content">
                <h6 class="mb-3">Step 4: Initial Records (Optional)</h6>
                
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="skipRecords" 
                           ${this.wizardData.skipRecords ? 'checked' : ''}
                           onchange="dnsZoneWizard.toggleSkipRecords()">
                    <label class="form-check-label" for="skipRecords">
                        Skip this step - I'll add records later
                    </label>
                </div>

                <div id="recordsSection" ${this.wizardData.skipRecords ? 'style="display:none;"' : ''}>
                    <div class="mb-3">
                        <h6>Quick Add Common Records</h6>
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-sm btn-outline-primary" 
                                    onclick="dnsZoneWizard.quickAddRecord('A')">
                                <i class="fas fa-plus me-1"></i>A Record
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-primary" 
                                    onclick="dnsZoneWizard.quickAddRecord('AAAA')">
                                <i class="fas fa-plus me-1"></i>AAAA Record
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-primary" 
                                    onclick="dnsZoneWizard.quickAddRecord('CNAME')">
                                <i class="fas fa-plus me-1"></i>CNAME
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-primary" 
                                    onclick="dnsZoneWizard.quickAddRecord('MX')">
                                <i class="fas fa-plus me-1"></i>MX Record
                            </button>
                        </div>
                    </div>

                    <div id="recordsList">
                        ${this.wizardData.initialRecords.length === 0 ? 
                            '<p class="text-muted">No records added yet. Use the buttons above to add records.</p>' :
                            this.renderRecordsList()
                        }
                    </div>

                    <div class="alert alert-info mt-3">
                        <i class="fas fa-lightbulb me-2"></i>
                        <strong>Tip:</strong> You can add more records after creating the zone
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render records list
     */
    renderRecordsList() {
        return `
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Name</th>
                        <th>Content</th>
                        <th>TTL</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${this.wizardData.initialRecords.map((record, index) => `
                        <tr>
                            <td><span class="badge bg-secondary">${record.type}</span></td>
                            <td>${record.name}</td>
                            <td>${record.content}${record.priority ? ` (Priority: ${record.priority})` : ''}</td>
                            <td>${record.ttl}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" 
                                        onclick="dnsZoneWizard.removeRecord(${index})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    /**
     * Step 5: Review & Create
     */
    renderStep5() {
        return `
            <div class="step-content">
                <h6 class="mb-3">Step 5: Review & Create</h6>
                
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Please review your zone configuration before creating
                </div>

                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Basic Information</h6>
                        <button class="btn btn-sm btn-link" onclick="dnsZoneWizard.showStep(1)">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                    <div class="card-body">
                        <dl class="row mb-0">
                            <dt class="col-sm-3">Domain Name</dt>
                            <dd class="col-sm-9">${this.wizardData.domainName}</dd>
                            
                            <dt class="col-sm-3">Zone Type</dt>
                            <dd class="col-sm-9"><span class="badge bg-primary">${this.wizardData.zoneType}</span></dd>
                            
                            <dt class="col-sm-3">Template</dt>
                            <dd class="col-sm-9">${this.templates[this.wizardData.template].name}</dd>
                        </dl>
                    </div>
                </div>

                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Name Servers</h6>
                        <button class="btn btn-sm btn-link" onclick="dnsZoneWizard.showStep(2)">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                    <div class="card-body">
                        <ul class="mb-0">
                            ${this.wizardData.nameservers.map(ns => `<li>${ns}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">SOA Settings</h6>
                        <button class="btn btn-sm btn-link" onclick="dnsZoneWizard.showStep(3)">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                    <div class="card-body">
                        <dl class="row mb-0">
                            <dt class="col-sm-3">Primary NS</dt>
                            <dd class="col-sm-9">${this.wizardData.primaryNs}</dd>
                            
                            <dt class="col-sm-3">Admin Email</dt>
                            <dd class="col-sm-9">${this.wizardData.adminEmail}</dd>
                            
                            <dt class="col-sm-3">Default TTL</dt>
                            <dd class="col-sm-9">${this.wizardData.ttl} seconds</dd>
                        </dl>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Initial Records</h6>
                        <button class="btn btn-sm btn-link" onclick="dnsZoneWizard.showStep(4)">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                    </div>
                    <div class="card-body">
                        ${this.wizardData.skipRecords ? 
                            '<p class="text-muted mb-0">No initial records (will add later)</p>' :
                            `<p class="mb-0">${this.wizardData.initialRecords.length} records will be created</p>`
                        }
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Update navigation buttons based on current step
     */
    updateNavigationButtons() {
        const backBtn = document.getElementById('wizardBackBtn');
        const nextBtn = document.getElementById('wizardNextBtn');
        const createBtn = document.getElementById('wizardCreateBtn');
        
        // Back button
        backBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-block';
        
        // Next/Create buttons
        if (this.currentStep === this.totalSteps) {
            nextBtn.style.display = 'none';
            createBtn.style.display = 'inline-block';
        } else {
            nextBtn.style.display = 'inline-block';
            createBtn.style.display = 'none';
        }
        
        // Validate current step to enable/disable next button
        this.validateCurrentStep();
    }

    /**
     * Navigate to previous step
     */
    previousStep() {
        if (this.currentStep > 1) {
            this.showStep(this.currentStep - 1);
        }
    }

    /**
     * Navigate to next step
     */
    nextStep() {
        if (this.validateCurrentStep()) {
            this.saveCurrentStepData();
            if (this.currentStep < this.totalSteps) {
                this.showStep(this.currentStep + 1);
            }
        }
    }

    /**
     * Validate current step
     */
    validateCurrentStep() {
        const nextBtn = document.getElementById('wizardNextBtn');
        let isValid = false;
        
        switch (this.currentStep) {
            case 1:
                isValid = this.validateStep1();
                break;
            case 2:
                isValid = this.validateStep2();
                break;
            case 3:
                isValid = this.validateStep3();
                break;
            case 4:
                isValid = true; // Optional step
                break;
            case 5:
                isValid = true; // Review step
                break;
        }
        
        if (nextBtn) {
            nextBtn.disabled = !isValid;
        }
        
        return isValid;
    }

    /**
     * Validate Step 1
     */
    validateStep1() {
        const domainInput = document.getElementById('domainName');
        if (!domainInput) return false;
        
        const domain = domainInput.value.trim();
        const isValid = this.validationRules.domainName.test(domain);
        
        if (isValid) {
            domainInput.classList.remove('is-invalid');
            domainInput.classList.add('is-valid');
        } else {
            domainInput.classList.remove('is-valid');
            if (domain.length > 0) {
                domainInput.classList.add('is-invalid');
            }
        }
        
        return isValid;
    }

    /**
     * Validate Step 2
     */
    validateStep2() {
        const nameservers = document.querySelectorAll('.nameserver-input');
        let allValid = true;
        
        nameservers.forEach(input => {
            const value = input.value.trim();
            if (!value || !this.validationRules.nameserver.test(value)) {
                allValid = false;
            }
        });
        
        return allValid && nameservers.length >= 2;
    }

    /**
     * Validate Step 3
     */
    validateStep3() {
        return this.validateEmail();
    }

    /**
     * Validate email field
     */
    validateEmail() {
        const emailInput = document.getElementById('adminEmail');
        if (!emailInput) return false;
        
        const email = emailInput.value.trim();
        const isValid = this.validationRules.email.test(email);
        
        if (isValid) {
            emailInput.classList.remove('is-invalid');
            emailInput.classList.add('is-valid');
        } else {
            emailInput.classList.remove('is-valid');
            if (email.length > 0) {
                emailInput.classList.add('is-invalid');
            }
        }
        
        return isValid;
    }

    /**
     * Save current step data
     */
    saveCurrentStepData() {
        switch (this.currentStep) {
            case 1:
                this.wizardData.domainName = document.getElementById('domainName').value.trim();
                this.wizardData.zoneType = document.querySelector('input[name="zoneType"]:checked').value;
                this.wizardData.template = document.querySelector('input[name="template"]:checked').value;
                break;
            case 2:
                this.wizardData.nameservers = Array.from(document.querySelectorAll('.nameserver-input'))
                    .map(input => input.value.trim())
                    .filter(ns => ns.length > 0);
                this.wizardData.useOrgDefaults = document.getElementById('useOrgDefaults').checked;
                break;
            case 3:
                this.wizardData.primaryNs = document.getElementById('primaryNs').value;
                this.wizardData.adminEmail = document.getElementById('adminEmail').value;
                this.wizardData.ttl = parseInt(document.getElementById('ttl').value);
                this.wizardData.minimumTtl = parseInt(document.getElementById('minimumTtl').value);
                this.wizardData.refresh = parseInt(document.getElementById('refresh').value);
                this.wizardData.retry = parseInt(document.getElementById('retry').value);
                this.wizardData.expire = parseInt(document.getElementById('expire').value);
                break;
            case 4:
                this.wizardData.skipRecords = document.getElementById('skipRecords').checked;
                break;
        }
    }

    /**
     * Handle template selection
     */
    selectTemplate(templateKey) {
        this.wizardData.template = templateKey;
        
        // Update UI
        document.querySelectorAll('.template-option').forEach(option => {
            option.classList.remove('border-primary', 'bg-light');
        });
        document.querySelector(`#template${templateKey}`).closest('.template-option')
            .classList.add('border-primary', 'bg-light');
        
        // Apply template defaults in step 4
        if (templateKey !== 'custom') {
            this.wizardData.initialRecords = [...this.templates[templateKey].records];
        }
    }

    /**
     * Toggle organization defaults
     */
    toggleOrgDefaults() {
        const useDefaults = document.getElementById('useOrgDefaults').checked;
        this.wizardData.useOrgDefaults = useDefaults;
        
        // Enable/disable nameserver inputs
        document.querySelectorAll('.nameserver-input').forEach(input => {
            input.readOnly = useDefaults;
        });
        
        // Enable/disable add/remove buttons
        document.querySelectorAll('#nameserversList button').forEach(btn => {
            btn.disabled = useDefaults || 
                (btn.classList.contains('btn-outline-danger') && this.wizardData.nameservers.length <= 2);
        });
    }

    /**
     * Add nameserver field
     */
    addNameserver() {
        this.wizardData.nameservers.push('');
        this.showStep(2); // Re-render step
    }

    /**
     * Remove nameserver field
     */
    removeNameserver(index) {
        if (this.wizardData.nameservers.length > 2) {
            this.wizardData.nameservers.splice(index, 1);
            this.showStep(2); // Re-render step
        }
    }

    /**
     * Validate nameserver field
     */
    validateNameserver(index) {
        const input = document.querySelectorAll('.nameserver-input')[index];
        if (!input) return;
        
        const value = input.value.trim();
        const isValid = this.validationRules.nameserver.test(value);
        
        if (isValid || value.length === 0) {
            input.classList.remove('is-invalid');
        } else {
            input.classList.add('is-invalid');
        }
    }

    /**
     * Toggle skip records checkbox
     */
    toggleSkipRecords() {
        const skip = document.getElementById('skipRecords').checked;
        this.wizardData.skipRecords = skip;
        document.getElementById('recordsSection').style.display = skip ? 'none' : 'block';
    }

    /**
     * Quick add record
     */
    quickAddRecord(type) {
        // Show a simple modal or inline form for adding the record
        const recordData = this.showRecordForm(type);
        if (recordData) {
            this.wizardData.initialRecords.push(recordData);
            this.showStep(4); // Re-render step
        }
    }

    /**
     * Show record form (simplified for now)
     */
    showRecordForm(type) {
        // For now, add a default record based on type
        const record = {
            type: type,
            name: '@',
            ttl: 3600
        };
        
        switch (type) {
            case 'A':
                record.content = prompt('Enter IPv4 address:', '192.0.2.1');
                break;
            case 'AAAA':
                record.content = prompt('Enter IPv6 address:', '2001:db8::1');
                break;
            case 'CNAME':
                record.name = prompt('Enter subdomain:', 'www');
                record.content = prompt('Enter target:', this.wizardData.domainName);
                break;
            case 'MX':
                record.content = prompt('Enter mail server:', 'mail.' + this.wizardData.domainName);
                record.priority = parseInt(prompt('Enter priority (10, 20, etc):', '10'));
                break;
        }
        
        return record.content ? record : null;
    }

    /**
     * Remove record
     */
    removeRecord(index) {
        this.wizardData.initialRecords.splice(index, 1);
        this.showStep(4); // Re-render step
    }

    /**
     * Update wizard data from form inputs
     */
    updateWizardData() {
        // Called by onchange events to save data as user types
        this.saveCurrentStepData();
    }

    /**
     * Handle cancel
     */
    handleCancel() {
        if (confirm('Are you sure you want to cancel? All entered data will be lost.')) {
            this.modal.hide();
            this.cleanup();
        }
    }

    /**
     * Create zone
     */
    async createZone() {
        const createBtn = document.getElementById('wizardCreateBtn');
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating...';
        
        try {
            // Prepare zone data
            const zoneData = {
                name: this.wizardData.domainName,
                type: this.wizardData.zoneType,
                nameservers: this.wizardData.nameservers,
                soa: {
                    primaryNs: this.wizardData.primaryNs,
                    email: this.wizardData.adminEmail,
                    serial: new Date().toISOString().replace(/\D/g, '').substring(0, 10),
                    refresh: this.wizardData.refresh,
                    retry: this.wizardData.retry,
                    expire: this.wizardData.expire,
                    ttl: this.wizardData.minimumTtl
                },
                records: this.wizardData.initialRecords,
                status: 'active'
            };
            
            // Create zone using mock service
            const newZone = await this.mockService.createZone(zoneData);
            
            // Show success message
            this.showSuccess(newZone);
            
        } catch (error) {
            console.error('Error creating zone:', error);
            this.showError('Failed to create zone: ' + error.message);
            
            // Re-enable button
            createBtn.disabled = false;
            createBtn.innerHTML = '<i class="fas fa-check me-2"></i>Create Zone';
        }
    }

    /**
     * Show success message
     */
    showSuccess(zone) {
        const modalBody = document.querySelector('.modal-body');
        modalBody.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-check-circle text-success" style="font-size: 4rem;"></i>
                <h4 class="mt-3">Zone Created Successfully!</h4>
                <p class="text-muted">Your DNS zone <strong>${zone.name}</strong> has been created.</p>
                <div class="mt-4">
                    <button class="btn btn-primary" onclick="dnsZoneWizard.viewZone('${zone.id}')">
                        <i class="fas fa-eye me-2"></i>View Zone Details
                    </button>
                    <button class="btn btn-outline-primary ms-2" onclick="dnsZoneWizard.createAnother()">
                        <i class="fas fa-plus me-2"></i>Create Another Zone
                    </button>
                </div>
            </div>
        `;
        
        // Hide footer buttons
        document.querySelector('.modal-footer').style.display = 'none';
        
        // Refresh zones list
        if (window.dnsZonesManager) {
            window.dnsZonesManager.loadZones();
        }
    }

    /**
     * View created zone
     */
    viewZone(zoneId) {
        this.modal.hide();
        this.cleanup();
        
        // Open zone detail modal
        if (window.dnsZonesManager) {
            window.dnsZonesManager.showZoneDetail(zoneId);
        }
    }

    /**
     * Create another zone
     */
    createAnother() {
        this.modal.hide();
        this.cleanup();
        
        // Show new wizard
        setTimeout(() => {
            this.showWizard();
        }, 300);
    }

    /**
     * Show error message
     */
    showError(message) {
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, 'error');
        } else {
            alert(message);
        }
    }

    /**
     * Bind events
     */
    bindEvents() {
        const modalElement = document.getElementById('dnsZoneWizardModal');
        
        // Handle modal close
        modalElement.addEventListener('hidden.bs.modal', () => {
            this.cleanup();
        });
        
        // Handle keyboard navigation
        modalElement.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                if (this.currentStep < this.totalSteps) {
                    this.nextStep();
                } else if (this.currentStep === this.totalSteps) {
                    this.createZone();
                }
            }
        });
    }

    /**
     * Cleanup on modal close
     */
    cleanup() {
        this.resetWizardData();
        this.currentStep = 1;
    }
}

// Export for use in other modules
window.DNSZoneWizard = DNSZoneWizard;

// Create global instance
window.dnsZoneWizard = new DNSZoneWizard();