/**
 * DNS Records Manager - Simple implementation for managing DNS records within a zone
 */

class DNSRecordsManager {
    constructor(zoneDetailManager) {
        this.zoneDetailManager = zoneDetailManager;
        this.mockService = zoneDetailManager.mockService;
        this.currentZone = null;
        this.filteredRecords = [];
        this.searchTerm = '';
        this.selectedType = 'all';
    }

    /**
     * Initialize records tab for a zone
     */
    initialize(zone) {
        this.currentZone = zone;
        this.filteredRecords = [...zone.records];
        this.render();
        this.bindEvents();
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
                            <option value="NS">NS</option>
                            <option value="SRV">SRV</option>
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
                                <th>Value</th>
                                <th>TTL</th>
                                <th>Priority</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="records-tbody">
                            ${this.renderRecordsRows()}
                        </tbody>
                    </table>
                </div>

                <!-- Empty state -->
                ${this.filteredRecords.length === 0 ? this.renderEmptyState() : ''}
            </div>
        `;
    }

    /**
     * Render table rows
     */
    renderRecordsRows() {
        if (this.filteredRecords.length === 0) return '';

        return this.filteredRecords.map(record => `
            <tr data-record-id="${record.id}">
                <td>${this.escapeHtml(record.name)}</td>
                <td><span class="badge bg-secondary">${record.type}</span></td>
                <td class="text-break">${this.escapeHtml(record.content)}</td>
                <td>${record.ttl || 'Default'}</td>
                <td>${record.priority || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-record" 
                            data-record-id="${record.id}" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-record" 
                            data-record-id="${record.id}" title="Delete">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
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
                this.filterRecords();
            });
        }

        // Type filter
        const typeFilter = document.getElementById('record-type-filter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                this.selectedType = e.target.value;
                this.filterRecords();
            });
        }

        // Edit/Delete buttons (using event delegation)
        const tbody = document.getElementById('records-tbody');
        if (tbody) {
            tbody.addEventListener('click', (e) => {
                const editBtn = e.target.closest('.edit-record');
                const deleteBtn = e.target.closest('.delete-record');

                if (editBtn) {
                    const recordId = editBtn.dataset.recordId;
                    this.showEditRecord(recordId);
                } else if (deleteBtn) {
                    const recordId = deleteBtn.dataset.recordId;
                    this.deleteRecord(recordId);
                }
            });
        }
    }

    /**
     * Filter records based on search and type
     */
    filterRecords() {
        this.filteredRecords = this.currentZone.records.filter(record => {
            // Type filter
            if (this.selectedType !== 'all' && record.type !== this.selectedType) {
                return false;
            }

            // Search filter
            if (this.searchTerm) {
                const searchLower = this.searchTerm.toLowerCase();
                return record.name.toLowerCase().includes(searchLower) ||
                       record.content.toLowerCase().includes(searchLower) ||
                       record.type.toLowerCase().includes(searchLower);
            }

            return true;
        });

        // Re-render table body
        const tbody = document.getElementById('records-tbody');
        if (tbody) {
            tbody.innerHTML = this.renderRecordsRows();
            
            // Show/hide empty state
            const container = document.querySelector('.records-container');
            const emptyState = container.querySelector('.text-center.py-5');
            
            if (this.filteredRecords.length === 0) {
                if (!emptyState) {
                    const table = container.querySelector('.table-responsive');
                    table.insertAdjacentHTML('afterend', this.renderEmptyState());
                }
            } else if (emptyState) {
                emptyState.remove();
            }
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
     * Show edit record modal
     */
    showEditRecord(recordId) {
        const record = this.currentZone.records.find(r => r.id === recordId);
        if (!record) return;

        const modal = this.createRecordModal(record);
        modal.show();
    }

    /**
     * Create record modal (for add/edit)
     */
    createRecordModal(record = null) {
        const isEdit = !!record;
        const modalId = 'dnsRecordModal';

        // Remove existing modal if any
        const existingModal = document.getElementById(modalId);
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${isEdit ? 'Edit' : 'Add'} DNS Record</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="record-form">
                                <div class="mb-3">
                                    <label class="form-label">Record Type</label>
                                    <select class="form-select" id="record-type" ${isEdit ? 'disabled' : ''}>
                                        <option value="A" ${record?.type === 'A' ? 'selected' : ''}>A - IPv4 Address</option>
                                        <option value="AAAA" ${record?.type === 'AAAA' ? 'selected' : ''}>AAAA - IPv6 Address</option>
                                        <option value="CNAME" ${record?.type === 'CNAME' ? 'selected' : ''}>CNAME - Canonical Name</option>
                                        <option value="MX" ${record?.type === 'MX' ? 'selected' : ''}>MX - Mail Exchange</option>
                                        <option value="TXT" ${record?.type === 'TXT' ? 'selected' : ''}>TXT - Text</option>
                                        <option value="NS" ${record?.type === 'NS' ? 'selected' : ''}>NS - Name Server</option>
                                        <option value="SRV" ${record?.type === 'SRV' ? 'selected' : ''}>SRV - Service</option>
                                    </select>
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">Name</label>
                                    <div class="input-group">
                                        <input type="text" class="form-control" id="record-name" 
                                               value="${record?.name || ''}" placeholder="subdomain or @">
                                        <span class="input-group-text">.${this.currentZone.name}</span>
                                    </div>
                                    <small class="text-muted">Use @ for the root domain</small>
                                </div>

                                <div class="mb-3" id="priority-group" style="${this.shouldShowPriority(record?.type) ? '' : 'display:none'}">
                                    <label class="form-label">Priority</label>
                                    <input type="number" class="form-control" id="record-priority" 
                                           value="${record?.priority || ''}" min="0" max="65535">
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">Value</label>
                                    <input type="text" class="form-control" id="record-value" 
                                           value="${record?.content || ''}" 
                                           placeholder="${this.getValuePlaceholder(record?.type || 'A')}">
                                    <small class="text-muted" id="value-help">${this.getValueHelp(record?.type || 'A')}</small>
                                </div>

                                <div class="mb-3">
                                    <label class="form-label">TTL (seconds)</label>
                                    <input type="number" class="form-control" id="record-ttl" 
                                           value="${record?.ttl || 3600}" min="60" max="86400">
                                    <small class="text-muted">Time to live (60 - 86400 seconds)</small>
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
        const typeSelect = document.getElementById('record-type');
        if (typeSelect) {
            typeSelect.addEventListener('change', (e) => {
                const type = e.target.value;
                document.getElementById('priority-group').style.display = 
                    this.shouldShowPriority(type) ? '' : 'none';
                document.getElementById('record-value').placeholder = this.getValuePlaceholder(type);
                document.getElementById('value-help').textContent = this.getValueHelp(type);
            });
        }

        const saveBtn = document.getElementById('save-record-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const success = await this.saveRecord(record?.id);
                if (success) {
                    modal.hide();
                    modalElement.addEventListener('hidden.bs.modal', () => modalElement.remove());
                }
            });
        }

        return modal;
    }

    /**
     * Save record (add or update)
     */
    async saveRecord(recordId = null) {
        const type = document.getElementById('record-type').value;
        const name = document.getElementById('record-name').value.trim();
        const value = document.getElementById('record-value').value.trim();
        const ttl = parseInt(document.getElementById('record-ttl').value) || 3600;
        const priority = document.getElementById('record-priority').value;

        // Basic validation
        if (!name) {
            alert('Please enter a record name');
            return false;
        }

        if (!value) {
            alert('Please enter a record value');
            return false;
        }

        // Type-specific validation
        if (!this.validateRecord(type, value)) {
            return false;
        }

        // Create record object
        const recordData = {
            name: name === '@' ? this.currentZone.name : name,
            type,
            content: value,
            ttl
        };

        if (this.shouldShowPriority(type) && priority) {
            recordData.priority = parseInt(priority);
        }

        try {
            if (recordId) {
                // Update existing record
                await this.mockService.updateRecord(this.currentZone.id, recordId, recordData);
            } else {
                // Add new record
                await this.mockService.addRecord(this.currentZone.id, recordData);
            }

            // Reload zone data and refresh display
            await this.zoneDetailManager.loadZone(this.currentZone.id);
            this.initialize(this.zoneDetailManager.currentZone);

            return true;
        } catch (error) {
            console.error('Error saving record:', error);
            alert('Failed to save record: ' + error.message);
            return false;
        }
    }

    /**
     * Delete record
     */
    async deleteRecord(recordId) {
        const record = this.currentZone.records.find(r => r.id === recordId);
        if (!record) return;

        const confirmed = confirm(`Are you sure you want to delete this ${record.type} record?\n\n` +
                                 `Name: ${record.name}\n` +
                                 `Value: ${record.content}`);

        if (!confirmed) return;

        try {
            await this.mockService.deleteRecord(this.currentZone.id, recordId);
            
            // Reload zone data and refresh display
            await this.zoneDetailManager.loadZone(this.currentZone.id);
            this.initialize(this.zoneDetailManager.currentZone);

        } catch (error) {
            console.error('Error deleting record:', error);
            alert('Failed to delete record: ' + error.message);
        }
    }

    /**
     * Validate record based on type
     */
    validateRecord(type, value) {
        switch (type) {
            case 'A':
                // IPv4 validation
                const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
                if (!ipv4Regex.test(value)) {
                    alert('Please enter a valid IPv4 address (e.g., 192.168.1.1)');
                    return false;
                }
                const parts = value.split('.');
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
                // Domain name validation
                if (!value.match(/^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i) && value !== '@') {
                    alert('Please enter a valid domain name');
                    return false;
                }
                break;

            case 'MX':
                // Mail server validation
                if (!value.match(/^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$/i)) {
                    alert('Please enter a valid mail server domain');
                    return false;
                }
                break;

            case 'TXT':
                // TXT records can contain anything
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
    shouldShowPriority(type) {
        return type === 'MX' || type === 'SRV';
    }

    getValuePlaceholder(type) {
        switch (type) {
            case 'A': return '192.168.1.1';
            case 'AAAA': return '2001:db8::1';
            case 'CNAME': return 'target.example.com';
            case 'MX': return 'mail.example.com';
            case 'TXT': return 'v=spf1 include:_spf.example.com ~all';
            case 'NS': return 'ns1.example.com';
            case 'SRV': return '10 5060 sipserver.example.com';
            default: return '';
        }
    }

    getValueHelp(type) {
        switch (type) {
            case 'A': return 'Enter an IPv4 address';
            case 'AAAA': return 'Enter an IPv6 address';
            case 'CNAME': return 'Enter the target domain name';
            case 'MX': return 'Enter the mail server hostname';
            case 'TXT': return 'Enter any text value (max 255 characters)';
            case 'NS': return 'Enter the name server hostname';
            case 'SRV': return 'Enter weight, port, and target (e.g., 10 5060 sip.example.com)';
            default: return '';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Create global instance
let dnsRecordsManager = null;