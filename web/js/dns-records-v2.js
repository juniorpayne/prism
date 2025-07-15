/**
 * DNS Records Manager V2 - PowerDNS rrsets format
 * Manages DNS records within a zone using PowerDNS API structure
 */

class DNSRecordsManagerV2 {
    constructor(zoneDetailManager) {
        this.zoneDetailManager = zoneDetailManager;
        // Use service adapter instead of direct mock service
        this.dnsService = zoneDetailManager.dnsService || DNSServiceFactory.getAdapter();
        this.searchFilter = new DNSSearchFilter();
        this.currentZone = null;
        this.filteredRrsets = [];
        this.searchTerm = '';
        this.selectedType = 'all';
        this.loadingStates = new Map(); // Track loading states for different operations
    }

    /**
     * Initialize records tab for a zone
     */
    initialize(zone) {
        this.currentZone = zone;
        this.filterRrsets();
        this.render();
        this.bindEvents();
    }

    /**
     * Filter rrsets based on search and type
     */
    filterRrsets() {
        let rrsets = this.currentZone.rrsets || [];
        
        // Exclude SOA and NS records from the list
        rrsets = rrsets.filter(rrset => rrset.type !== 'SOA' && rrset.type !== 'NS');
        
        // Apply type filter
        if (this.selectedType !== 'all') {
            rrsets = rrsets.filter(rrset => rrset.type === this.selectedType);
        }
        
        // Apply search filter
        if (this.searchTerm) {
            const searchLower = this.searchTerm.toLowerCase();
            rrsets = rrsets.filter(rrset => 
                rrset.name.toLowerCase().includes(searchLower) ||
                rrset.type.toLowerCase().includes(searchLower) ||
                rrset.records.some(record => 
                    record.content.toLowerCase().includes(searchLower)
                )
            );
        }
        
        this.filteredRrsets = rrsets;
    }

    /**
     * Render the records tab content
     */
    render() {
        const container = document.getElementById('records');
        if (!container) return;

        container.innerHTML = `
            <div class="records-container">
                <!-- Header with Add button and search -->
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <button class="btn btn-primary" id="add-record-btn">
                        <i class="bi bi-plus-circle"></i> Add Record
                    </button>
                    <div class="d-flex gap-2">
                        <select class="form-select" id="record-type-filter" style="width: 150px;">
                            <option value="all">All Types</option>
                            <option value="A">A</option>
                            <option value="AAAA">AAAA</option>
                            <option value="CNAME">CNAME</option>
                            <option value="MX">MX</option>
                            <option value="TXT">TXT</option>
                            <option value="SRV">SRV</option>
                            <option value="PTR">PTR</option>
                        </select>
                        <input type="text" class="form-control" id="record-search" 
                               placeholder="Search records..." style="width: 250px;">
                    </div>
                </div>

                <!-- Records table -->
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>TTL</th>
                                <th>Records</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="records-tbody">
                            ${this.renderRecordsRows()}
                        </tbody>
                    </table>
                </div>

                <!-- Empty state -->
                ${this.filteredRrsets.length === 0 ? this.renderEmptyState() : ''}
            </div>
        `;
    }

    /**
     * Render table rows for rrsets
     */
    renderRecordsRows() {
        if (this.filteredRrsets.length === 0) return '';

        return this.filteredRrsets.map(rrset => {
            // Get simplified name (remove zone suffix)
            const simpleName = this.getSimpleName(rrset.name);
            
            return `
                <tr>
                    <td>${this.searchFilter.highlightSearchTerm(this.escapeHtml(simpleName), this.searchTerm)}</td>
                    <td><span class="badge bg-secondary">${this.searchFilter.highlightSearchTerm(rrset.type, this.searchTerm)}</span></td>
                    <td>${rrset.ttl || 'Default'}</td>
                    <td>
                        ${rrset.records.map(record => {
                            const formattedContent = this.formatRecordContent(rrset.type, record.content);
                            const highlightedContent = this.searchFilter.highlightSearchTerm(formattedContent, this.searchTerm);
                            return `
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="text-break">${highlightedContent}</span>
                                <span class="ms-2">
                                    ${record.disabled ? '<span class="badge bg-warning">Disabled</span>' : ''}
                                </span>
                            </div>
                        `}).join('')}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary edit-rrset" 
                                data-rrset-name="${rrset.name}" data-rrset-type="${rrset.type}" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-rrset" 
                                data-rrset-name="${rrset.name}" data-rrset-type="${rrset.type}" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    /**
     * Get simplified name (remove zone suffix for display)
     */
    getSimpleName(name) {
        if (name === this.currentZone.name) {
            return '@';
        }
        return name.replace(`.${this.currentZone.name}`, '');
    }

    /**
     * Format record content for display
     */
    formatRecordContent(type, content) {
        if (type === 'MX') {
            // Extract priority and target from MX content
            const parts = content.split(' ');
            if (parts.length >= 2) {
                return `<span class="badge bg-info me-1">${parts[0]}</span> ${parts.slice(1).join(' ')}`;
            }
        } else if (type === 'TXT') {
            // Remove quotes from TXT records for display
            return content.replace(/^"|"$/g, '');
        }
        return this.escapeHtml(content);
    }

    /**
     * Render empty state
     */
    renderEmptyState() {
        return `
            <div class="text-center py-5">
                <i class="bi bi-inbox fs-1 text-muted"></i>
                <p class="mt-2 text-muted">
                    ${this.searchTerm || this.selectedType !== 'all' 
                        ? 'No records match your filter' 
                        : 'No DNS records found'}
                </p>
                ${!this.searchTerm && this.selectedType === 'all' ? `
                    <button class="btn btn-primary mt-2" onclick="dnsRecordsManager.showAddRecord()">
                        <i class="bi bi-plus-circle"></i> Add Your First Record
                    </button>
                ` : ''}
            </div>
        `;
    }

    /**
     * Bind events
     */
    bindEvents() {
        // Add record button
        const addBtn = document.getElementById('add-record-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddRecord());
        }

        // Search input
        const searchInput = document.getElementById('record-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.filterRrsets();
                this.updateTable();
            });
        }

        // Type filter
        const typeFilter = document.getElementById('record-type-filter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                this.selectedType = e.target.value;
                this.filterRrsets();
                this.updateTable();
            });
        }

        // Edit/Delete buttons (using event delegation)
        const tbody = document.getElementById('records-tbody');
        if (tbody) {
            tbody.addEventListener('click', (e) => {
                const editBtn = e.target.closest('.edit-rrset');
                const deleteBtn = e.target.closest('.delete-rrset');

                if (editBtn) {
                    const name = editBtn.dataset.rrsetName;
                    const type = editBtn.dataset.rrsetType;
                    this.showEditRrset(name, type);
                } else if (deleteBtn) {
                    const name = deleteBtn.dataset.rrsetName;
                    const type = deleteBtn.dataset.rrsetType;
                    this.deleteRrset(name, type);
                }
            });
        }
    }

    /**
     * Update just the table body
     */
    updateTable() {
        const tbody = document.getElementById('records-tbody');
        if (tbody) {
            tbody.innerHTML = this.renderRecordsRows();
        }

        // Update empty state
        const container = document.querySelector('.records-container');
        const emptyState = container.querySelector('.text-center.py-5');
        
        if (this.filteredRrsets.length === 0) {
            if (!emptyState) {
                const table = container.querySelector('.table-responsive');
                table.insertAdjacentHTML('afterend', this.renderEmptyState());
            }
        } else if (emptyState) {
            emptyState.remove();
        }
    }

    /**
     * Show add record modal
     */
    showAddRecord() {
        const modal = this.createRecordModal();
        modal.show();
    }

    /**
     * Show edit rrset modal
     */
    showEditRrset(name, type) {
        const rrset = this.currentZone.rrsets.find(r => r.name === name && r.type === type);
        if (!rrset) return;

        const modal = this.createRecordModal(rrset);
        modal.show();
    }

    /**
     * Create record modal (for add/edit)
     */
    createRecordModal(rrset = null) {
        const isEdit = !!rrset;
        const modalId = 'dnsRecordModal';

        // Remove existing modal if any
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        // Get simplified name for display
        const simpleName = isEdit ? this.getSimpleName(rrset.name) : '';

        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${isEdit ? 'Edit' : 'Add'} DNS Record</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="record-form">
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label">Record Type</label>
                                        <select class="form-select" id="record-type" ${isEdit ? 'disabled' : ''}>
                                            <option value="A" ${rrset?.type === 'A' ? 'selected' : ''}>A - IPv4 Address</option>
                                            <option value="AAAA" ${rrset?.type === 'AAAA' ? 'selected' : ''}>AAAA - IPv6 Address</option>
                                            <option value="CNAME" ${rrset?.type === 'CNAME' ? 'selected' : ''}>CNAME - Canonical Name</option>
                                            <option value="MX" ${rrset?.type === 'MX' ? 'selected' : ''}>MX - Mail Exchange</option>
                                            <option value="TXT" ${rrset?.type === 'TXT' ? 'selected' : ''}>TXT - Text</option>
                                            <option value="SRV" ${rrset?.type === 'SRV' ? 'selected' : ''}>SRV - Service</option>
                                        </select>
                                    </div>
                                    
                                    <div class="col-md-6 mb-3">
                                        <label class="form-label">Name</label>
                                        <div class="input-group">
                                            <input type="text" class="form-control" id="record-name" 
                                                   value="${simpleName}" ${isEdit ? 'disabled' : ''} placeholder="subdomain or @">
                                            <span class="input-group-text">.${this.currentZone.name}</span>
                                        </div>
                                        <small class="text-muted">Use @ for the root domain</small>
                                    </div>
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">TTL (seconds)</label>
                                    <input type="number" class="form-control" id="record-ttl" 
                                           value="${rrset?.ttl || 3600}" min="60" max="86400">
                                    <small class="text-muted">Time to live (60 - 86400 seconds)</small>
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">Records</label>
                                    <div id="records-list">
                                        ${isEdit ? this.renderEditableRecords(rrset) : this.renderNewRecordInput(rrset?.type || 'A')}
                                    </div>
                                    <button type="button" class="btn btn-sm btn-outline-primary mt-2" id="add-record-value">
                                        <i class="bi bi-plus"></i> Add Another Value
                                    </button>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="save-record-btn">
                                ${isEdit ? 'Update' : 'Add'} Record
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Get modal instance
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);

        // Bind events
        this.bindModalEvents(modalElement, rrset);

        const saveBtn = document.getElementById('save-record-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const success = await this.saveRecord(rrset);
                if (success) {
                    modal.hide();
                    modalElement.addEventListener('hidden.bs.modal', () => modalElement.remove());
                }
            });
        }

        return modal;
    }

    /**
     * Render editable records for edit mode
     */
    renderEditableRecords(rrset) {
        return rrset.records.map((record, index) => 
            this.renderRecordInput(rrset.type, record, index)
        ).join('');
    }

    /**
     * Render new record input
     */
    renderNewRecordInput(type) {
        return this.renderRecordInput(type, null, 0);
    }

    /**
     * Render a single record input
     */
    renderRecordInput(type, record = null, index = 0) {
        const content = record ? this.extractRecordValue(type, record.content) : '';
        const priority = type === 'MX' && record ? this.extractMXPriority(record.content) : '';
        
        return `
            <div class="record-input-group mb-2" data-index="${index}">
                <div class="row">
                    ${type === 'MX' ? `
                        <div class="col-3">
                            <input type="number" class="form-control record-priority" 
                                   placeholder="Priority" value="${priority}" min="0" max="65535">
                        </div>
                        <div class="col-7">
                    ` : '<div class="col-10">'}
                        <input type="text" class="form-control record-value" 
                               placeholder="${this.getValuePlaceholder(type)}" 
                               value="${this.escapeHtml(content)}">
                        <small class="text-muted">${this.getValueHelp(type)}</small>
                    </div>
                    <div class="col-2">
                        <button type="button" class="btn btn-sm btn-outline-danger remove-record-value" 
                                ${index === 0 && !record ? 'disabled' : ''}>
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Extract MX priority from content
     */
    extractMXPriority(content) {
        const parts = content.split(' ');
        return parts.length > 0 ? parts[0] : '';
    }

    /**
     * Extract record value without priority
     */
    extractRecordValue(type, content) {
        if (type === 'MX') {
            const parts = content.split(' ');
            return parts.slice(1).join(' ');
        } else if (type === 'TXT') {
            // Remove quotes from TXT records
            return content.replace(/^"|"$/g, '');
        }
        return content;
    }

    /**
     * Bind modal events
     */
    bindModalEvents(modalElement, rrset) {
        // Type change
        const typeSelect = document.getElementById('record-type');
        if (typeSelect && !rrset) {
            typeSelect.addEventListener('change', (e) => {
                const type = e.target.value;
                document.getElementById('records-list').innerHTML = this.renderNewRecordInput(type);
                this.bindRecordInputEvents();
            });
        }

        // Add record value button
        const addValueBtn = document.getElementById('add-record-value');
        if (addValueBtn) {
            addValueBtn.addEventListener('click', () => {
                const type = document.getElementById('record-type').value;
                const recordsList = document.getElementById('records-list');
                const index = recordsList.children.length;
                recordsList.insertAdjacentHTML('beforeend', this.renderRecordInput(type, null, index));
                this.bindRecordInputEvents();
            });
        }

        this.bindRecordInputEvents();
    }

    /**
     * Bind events for record input fields
     */
    bindRecordInputEvents() {
        // Remove buttons
        document.querySelectorAll('.remove-record-value').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const group = e.target.closest('.record-input-group');
                if (group && document.querySelectorAll('.record-input-group').length > 1) {
                    group.remove();
                }
            });
        });
    }

    /**
     * Save record (add or update)
     */
    async saveRecord(existingRrset = null) {
        const type = document.getElementById('record-type').value;
        const name = document.getElementById('record-name').value.trim();
        const ttl = parseInt(document.getElementById('record-ttl').value) || 3600;

        // Collect all record values
        const records = [];
        document.querySelectorAll('.record-input-group').forEach(group => {
            const value = group.querySelector('.record-value').value.trim();
            if (!value) return;

            let content = value;
            
            // Format content based on type
            if (type === 'MX') {
                const priority = group.querySelector('.record-priority').value || '10';
                content = `${priority} ${value}`;
            } else if (type === 'TXT') {
                // Add quotes if not present
                if (!content.startsWith('"')) {
                    content = `"${content}"`;
                }
            }

            // Add trailing dot for domain names
            if ((type === 'CNAME' || type === 'MX' || type === 'NS') && !content.endsWith('.')) {
                const lastPart = type === 'MX' ? content.split(' ').pop() : content;
                if (lastPart && !lastPart.endsWith('.')) {
                    content = type === 'MX' 
                        ? content.replace(/ ([^ ]+)$/, ' $1.')
                        : content + '.';
                }
            }

            records.push({
                content: content,
                disabled: false
            });
        });

        // Validation
        if (!name) {
            alert('Please enter a record name');
            return false;
        }

        if (records.length === 0) {
            alert('Please enter at least one record value');
            return false;
        }

        // Validate record values
        for (const record of records) {
            if (!this.validateRecord(type, record.content)) {
                return false;
            }
        }

        // Prepare rrset change
        const fullName = name === '@' 
            ? this.currentZone.name 
            : `${name}.${this.currentZone.name}`;

        const recordData = {
            name: simpleName,  // Use simple name, API will convert to FQDN
            type: type,
            ttl: ttl,
            records: records
        };

        this.setLoadingState('save-record', true);
        try {
            // Check if record exists to determine create vs update
            const existingRecords = this.getRecordsByNameAndType(fullName, type);
            
            if (existingRecords.length > 0) {
                // Update existing record
                await this.dnsService.updateRecord(this.currentZone.id, simpleName, type, recordData);
            } else {
                // Create new record
                await this.dnsService.createRecord(this.currentZone.id, recordData);
            }

            // Reload zone data and refresh display
            await this.zoneDetailManager.loadZone(this.currentZone.id);
            this.initialize(this.zoneDetailManager.currentZone);

            return true;
        } catch (error) {
            console.error('Error saving record:', error);
            alert('Failed to save record: ' + error.message);
            return false;
        } finally {
            this.setLoadingState('save-record', false);
        }
    }

    /**
     * Delete rrset
     */
    async deleteRrset(name, type) {
        const simpleName = this.getSimpleName(name);
        const confirmed = confirm(`Are you sure you want to delete all ${type} records for ${simpleName}?`);

        if (!confirmed) return;

        this.setLoadingState('delete-record', true);
        try {
            // Use the deleteRecord method from the DNS service
            await this.dnsService.deleteRecord(this.currentZone.id, simpleName, type);
            
            // Reload zone data and refresh display
            await this.zoneDetailManager.loadZone(this.currentZone.id);
            this.initialize(this.zoneDetailManager.currentZone);

        } catch (error) {
            console.error('Error deleting rrset:', error);
            alert('Failed to delete record: ' + error.message);
        } finally {
            this.setLoadingState('delete-record', false);
        }
    }

    /**
     * Validate record based on type
     */
    validateRecord(type, content) {
        // Remove priority from MX content for validation
        let value = content;
        if (type === 'MX') {
            const parts = content.split(' ');
            value = parts.slice(1).join(' ');
        }

        switch (type) {
            case 'A':
                // IPv4 validation
                const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
                const testValue = value.replace(/\.$/, ''); // Remove trailing dot for IP check
                if (!ipv4Regex.test(testValue)) {
                    alert('Please enter a valid IPv4 address (e.g., 192.168.1.1)');
                    return false;
                }
                const parts = testValue.split('.');
                if (parts.some(part => parseInt(part) > 255)) {
                    alert('Invalid IPv4 address: each octet must be 0-255');
                    return false;
                }
                break;

            case 'AAAA':
                // Basic IPv6 validation
                const ipv6Regex = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;
                if (!ipv6Regex.test(value) && value !== '::1') {
                    alert('Please enter a valid IPv6 address');
                    return false;
                }
                break;

            case 'CNAME':
            case 'NS':
            case 'MX':
                // Domain name validation (must end with dot)
                if (!value.endsWith('.')) {
                    alert(`${type} records must be fully qualified domain names ending with a dot (e.g., example.com.)`);
                    return false;
                }
                break;

            case 'TXT':
                // TXT records are already quoted, just check length
                if (value.length > 255) {
                    alert('TXT record value cannot exceed 255 characters');
                    return false;
                }
                break;
        }

        return true;
    }

    /**
     * Helper functions
     */
    getValuePlaceholder(type) {
        switch (type) {
            case 'A': return '192.168.1.1';
            case 'AAAA': return '2001:db8::1';
            case 'CNAME': return 'target.example.com.';
            case 'MX': return 'mail.example.com.';
            case 'TXT': return 'v=spf1 include:_spf.example.com ~all';
            case 'NS': return 'ns1.example.com.';
            case 'SRV': return '10 5060 sipserver.example.com.';
            default: return '';
        }
    }

    getValueHelp(type) {
        switch (type) {
            case 'A': return 'Enter an IPv4 address';
            case 'AAAA': return 'Enter an IPv6 address';
            case 'CNAME': return 'Enter the target domain name (must end with .)';
            case 'MX': return 'Enter the mail server hostname (must end with .)';
            case 'TXT': return 'Enter any text value';
            case 'NS': return 'Enter the name server hostname (must end with .)';
            case 'SRV': return 'Enter weight, port, and target';
            default: return '';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Set loading state for an operation
     * @param {string} operation - Operation identifier
     * @param {boolean} isLoading - Loading state
     */
    setLoadingState(operation, isLoading) {
        this.loadingStates.set(operation, isLoading);
        
        // Update UI loading indicators based on operation
        if (operation === 'save-record') {
            const saveBtn = document.querySelector('#recordModal .btn-primary');
            if (saveBtn) {
                saveBtn.disabled = isLoading;
                if (isLoading) {
                    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
                } else {
                    saveBtn.innerHTML = 'Save Record';
                }
            }
        } else if (operation === 'delete-record') {
            // Find all delete buttons and disable them during delete operations
            const deleteButtons = document.querySelectorAll('.delete-rrset-btn');
            deleteButtons.forEach(btn => {
                btn.disabled = isLoading;
                if (isLoading) {
                    const originalText = btn.innerHTML;
                    btn.dataset.originalText = originalText;
                    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Deleting...';
                } else if (btn.dataset.originalText) {
                    btn.innerHTML = btn.dataset.originalText;
                    delete btn.dataset.originalText;
                }
            });
        }
    }
}

// Replace the old class
class DNSRecordsManager extends DNSRecordsManagerV2 {}

// Create global instance
let dnsRecordsManager = null;