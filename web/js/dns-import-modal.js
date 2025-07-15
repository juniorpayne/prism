/**
 * DNS Import Modal Component
 * Handles the UI for importing DNS zone files
 */

class DNSImportModal {
    constructor() {
        this.importExport = new DNSImportExport();
        this.modal = null;
        this.fileContent = null;
        this.detectedFormat = null;
        this.parsedZones = null;
        this.validationResults = null;
        this.selectedZones = new Set();
    }

    /**
     * Show the import modal
     */
    show() {
        this.createModal();
        this.attachEventHandlers();
        this.modal = new bootstrap.Modal(document.getElementById('dnsImportModal'));
        this.modal.show();
    }

    /**
     * Create the modal HTML
     */
    createModal() {
        // Remove existing modal if any
        const existing = document.getElementById('dnsImportModal');
        if (existing) existing.remove();

        const modalHTML = `
            <div class="modal fade" id="dnsImportModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-upload me-2"></i>Import DNS Zones
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Step 1: File Upload -->
                            <div id="importStep1" class="import-step">
                                <h6 class="mb-3">Step 1: Select Zone File</h6>
                                
                                <!-- Drag and Drop Area -->
                                <div id="dropZone" class="border-2 border-dashed rounded p-5 text-center mb-3">
                                    <i class="bi bi-cloud-upload fs-1 text-muted"></i>
                                    <p class="mt-3 mb-1">Drag and drop your zone file here</p>
                                    <p class="text-muted small">or</p>
                                    <button type="button" class="btn btn-primary" id="browseButton">
                                        <i class="bi bi-folder-open me-2"></i>Browse Files
                                    </button>
                                    <input type="file" id="fileInput" class="d-none" 
                                           accept=".zone,.txt,.json,.csv">
                                    <p class="text-muted small mt-3 mb-0">
                                        Supported formats: BIND zone files, JSON, CSV
                                    </p>
                                </div>

                                <!-- File Info -->
                                <div id="fileInfo" class="alert alert-info d-none">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div>
                                            <i class="bi bi-file-text me-2"></i>
                                            <strong id="fileName">filename.zone</strong>
                                            <span class="text-muted ms-2" id="fileSize">(0 KB)</span>
                                        </div>
                                        <button type="button" class="btn btn-sm btn-outline-danger" id="removeFile">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>
                                </div>

                                <!-- Format Selection -->
                                <div class="row mt-3">
                                    <div class="col-md-6">
                                        <label class="form-label">File Format</label>
                                        <select class="form-select" id="formatSelect">
                                            <option value="auto">Auto-detect</option>
                                            <option value="bind">BIND Zone File</option>
                                            <option value="json">JSON</option>
                                            <option value="csv">CSV</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Import Options</label>
                                        <div class="form-check">
                                            <input class="form-check-input" type="checkbox" id="validateOnly">
                                            <label class="form-check-label" for="validateOnly">
                                                Validate only (don't import)
                                            </label>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 2: Preview -->
                            <div id="importStep2" class="import-step d-none">
                                <h6 class="mb-3">Step 2: Preview Import</h6>
                                
                                <!-- Summary -->
                                <div class="alert alert-info" id="importSummary">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <span id="summaryText">Analyzing file...</span>
                                </div>

                                <!-- Validation Errors/Warnings -->
                                <div id="validationMessages"></div>

                                <!-- Preview Table -->
                                <div class="table-responsive mt-3">
                                    <table class="table table-sm" id="previewTable">
                                        <thead>
                                            <tr>
                                                <th style="width: 40px;">
                                                    <input type="checkbox" id="selectAllZones" checked>
                                                </th>
                                                <th>Zone Name</th>
                                                <th>Type</th>
                                                <th>Records</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody id="previewTableBody">
                                            <!-- Preview rows will be inserted here -->
                                        </tbody>
                                    </table>
                                </div>

                                <!-- Conflict Resolution -->
                                <div class="mt-3" id="conflictOptions">
                                    <label class="form-label">For existing zones:</label>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="conflictResolution" 
                                               id="skipExisting" value="skip" checked>
                                        <label class="form-check-label" for="skipExisting">
                                            Skip existing zones
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="conflictResolution" 
                                               id="overwriteExisting" value="overwrite">
                                        <label class="form-check-label" for="overwriteExisting">
                                            Overwrite existing zones
                                        </label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="conflictResolution" 
                                               id="mergeRecords" value="merge">
                                        <label class="form-check-label" for="mergeRecords">
                                            Merge records (add new records only)
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 3: Import Progress -->
                            <div id="importStep3" class="import-step d-none">
                                <h6 class="mb-3">Step 3: Importing Zones</h6>
                                
                                <div class="progress mb-3" style="height: 25px;">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                                         id="importProgress" role="progressbar" style="width: 0%">
                                        0%
                                    </div>
                                </div>

                                <div id="importLog" class="border rounded p-3" 
                                     style="height: 300px; overflow-y: auto; font-family: monospace; font-size: 0.875rem;">
                                    <!-- Import log messages will appear here -->
                                </div>
                            </div>

                            <!-- Step 4: Results -->
                            <div id="importStep4" class="import-step d-none">
                                <h6 class="mb-3">Import Complete</h6>
                                
                                <div class="alert alert-success" id="importSuccess">
                                    <i class="bi bi-check-circle me-2"></i>
                                    <strong>Success!</strong> <span id="successMessage"></span>
                                </div>

                                <div class="alert alert-danger d-none" id="importError">
                                    <i class="bi bi-exclamation-triangle me-2"></i>
                                    <strong>Error!</strong> <span id="errorMessage"></span>
                                </div>

                                <div id="importResults">
                                    <!-- Results summary will be shown here -->
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" id="parseButton" disabled>
                                <i class="bi bi-search me-2"></i>Parse File
                            </button>
                            <button type="button" class="btn btn-primary d-none" id="importButton">
                                <i class="bi bi-upload me-2"></i>Import Selected
                            </button>
                            <button type="button" class="btn btn-success d-none" id="doneButton" data-bs-dismiss="modal">
                                <i class="bi bi-check me-2"></i>Done
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Attach event handlers
     */
    attachEventHandlers() {
        // File upload
        const fileInput = document.getElementById('fileInput');
        const browseButton = document.getElementById('browseButton');
        const dropZone = document.getElementById('dropZone');
        
        browseButton.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e.target.files[0]));
        
        // Drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-primary', 'bg-light');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('border-primary', 'bg-light');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-primary', 'bg-light');
            const file = e.dataTransfer.files[0];
            if (file) {
                this.handleFileSelect(file);
            }
        });

        // Remove file
        document.getElementById('removeFile').addEventListener('click', () => {
            this.clearFile();
        });

        // Parse button
        document.getElementById('parseButton').addEventListener('click', () => {
            this.parseFile();
        });

        // Import button
        document.getElementById('importButton').addEventListener('click', () => {
            this.importZones();
        });

        // Select all checkbox
        document.getElementById('selectAllZones').addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.zone-checkbox');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            this.updateSelectedZones();
        });

        // Modal cleanup
        document.getElementById('dnsImportModal').addEventListener('hidden.bs.modal', () => {
            this.cleanup();
        });
    }

    /**
     * Handle file selection
     */
    handleFileSelect(file) {
        if (!file) return;

        // Update UI
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
        document.getElementById('fileInfo').classList.remove('d-none');
        document.getElementById('dropZone').classList.add('d-none');
        document.getElementById('parseButton').disabled = false;

        // Read file content
        const reader = new FileReader();
        reader.onload = (e) => {
            this.fileContent = e.target.result;
            
            // Auto-detect format
            const formatSelect = document.getElementById('formatSelect');
            if (formatSelect.value === 'auto') {
                this.detectedFormat = this.importExport.detectFormat(this.fileContent);
                console.log('Detected format:', this.detectedFormat);
            }
        };
        reader.readAsText(file);
    }

    /**
     * Clear selected file
     */
    clearFile() {
        this.fileContent = null;
        this.detectedFormat = null;
        document.getElementById('fileInput').value = '';
        document.getElementById('fileInfo').classList.add('d-none');
        document.getElementById('dropZone').classList.remove('d-none');
        document.getElementById('parseButton').disabled = true;
    }

    /**
     * Parse the uploaded file
     */
    async parseFile() {
        try {
            // Show loading
            const parseButton = document.getElementById('parseButton');
            parseButton.disabled = true;
            parseButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Parsing...';

            // Get format
            const formatSelect = document.getElementById('formatSelect');
            const format = formatSelect.value === 'auto' ? this.detectedFormat : formatSelect.value;

            // Parse file
            const result = await this.importExport.importZones(this.fileContent, format);
            this.parsedZones = result.zones;
            this.validationResults = result.validationResults;

            // Show preview
            this.showPreview();

            // Update UI
            document.getElementById('importStep1').classList.add('d-none');
            document.getElementById('importStep2').classList.remove('d-none');
            parseButton.classList.add('d-none');
            document.getElementById('importButton').classList.remove('d-none');

        } catch (error) {
            console.error('Parse error:', error);
            this.showError(`Failed to parse file: ${error.message}`);
        } finally {
            const parseButton = document.getElementById('parseButton');
            parseButton.disabled = false;
            parseButton.innerHTML = '<i class="bi bi-search me-2"></i>Parse File';
        }
    }

    /**
     * Show preview of parsed zones
     */
    showPreview() {
        // Update summary
        const totalZones = this.parsedZones.length;
        const errorCount = this.validationResults.filter(r => r.errors.length > 0).length;
        const warningCount = this.validationResults.filter(r => r.warnings.length > 0).length;
        
        document.getElementById('summaryText').textContent = 
            `Found ${totalZones} zone(s). ${errorCount} error(s), ${warningCount} warning(s).`;

        // Show validation messages
        this.showValidationMessages();

        // Populate preview table
        const tbody = document.getElementById('previewTableBody');
        tbody.innerHTML = '';

        const previewData = this.importExport.createImportPreview(this.parsedZones, this.validationResults);
        
        previewData.forEach((item, index) => {
            const zone = item.zone;
            const validation = item.validation;
            
            // Check if zone exists
            const exists = this.checkZoneExists(zone.name);
            
            const row = document.createElement('tr');
            if (item.hasErrors) {
                row.classList.add('table-danger');
            } else if (item.hasWarnings) {
                row.classList.add('table-warning');
            }

            row.innerHTML = `
                <td>
                    <input type="checkbox" class="zone-checkbox" data-index="${index}" 
                           ${!item.hasErrors ? 'checked' : ''} ${item.hasErrors ? 'disabled' : ''}>
                </td>
                <td>${this.escapeHtml(zone.name)}</td>
                <td>${zone.kind || 'Native'}</td>
                <td><span class="badge bg-info">${item.recordCount}</span></td>
                <td>
                    ${item.hasErrors ? '<span class="badge bg-danger">Errors</span>' : ''}
                    ${item.hasWarnings ? '<span class="badge bg-warning">Warnings</span>' : ''}
                    ${exists ? '<span class="badge bg-secondary">Exists</span>' : ''}
                    ${!item.hasErrors && !exists ? '<span class="badge bg-success">Ready</span>' : ''}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="dnsImportModal.viewZoneDetails(${index})">
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            `;

            tbody.appendChild(row);
        });

        // Add checkbox event handlers
        document.querySelectorAll('.zone-checkbox').forEach(cb => {
            cb.addEventListener('change', () => this.updateSelectedZones());
        });

        this.updateSelectedZones();
    }

    /**
     * Show validation messages
     */
    showValidationMessages() {
        const container = document.getElementById('validationMessages');
        container.innerHTML = '';

        let hasErrors = false;
        let hasWarnings = false;

        this.validationResults.forEach((result, index) => {
            if (result.errors.length > 0) {
                hasErrors = true;
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger alert-sm mb-2';
                alert.innerHTML = `
                    <strong>Zone ${index + 1}:</strong> ${result.errors.join(', ')}
                `;
                container.appendChild(alert);
            }
            
            if (result.warnings.length > 0) {
                hasWarnings = true;
                const alert = document.createElement('div');
                alert.className = 'alert alert-warning alert-sm mb-2';
                alert.innerHTML = `
                    <strong>Zone ${index + 1}:</strong> ${result.warnings.join(', ')}
                `;
                container.appendChild(alert);
            }
        });

        if (!hasErrors && !hasWarnings) {
            container.innerHTML = '<div class="alert alert-success">All zones validated successfully!</div>';
        }
    }

    /**
     * Check if zone already exists
     */
    checkZoneExists(zoneName) {
        // This would check against the actual zones list
        // For now, we'll return false
        return false;
    }

    /**
     * Update selected zones count
     */
    updateSelectedZones() {
        this.selectedZones.clear();
        document.querySelectorAll('.zone-checkbox:checked').forEach(cb => {
            this.selectedZones.add(parseInt(cb.dataset.index));
        });

        const importButton = document.getElementById('importButton');
        if (this.selectedZones.size > 0) {
            importButton.textContent = `Import ${this.selectedZones.size} Zone(s)`;
            importButton.disabled = false;
        } else {
            importButton.textContent = 'Import Selected';
            importButton.disabled = true;
        }
    }

    /**
     * View zone details
     */
    viewZoneDetails(index) {
        const zone = this.parsedZones[index];
        const validation = this.validationResults[index];
        
        // Create a modal to show zone details
        const detailsHtml = `
            <div class="modal fade" id="zoneDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Zone Details: ${zone.name}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <h6>Zone Information</h6>
                            <dl class="row">
                                <dt class="col-sm-3">Name</dt>
                                <dd class="col-sm-9">${zone.name}</dd>
                                <dt class="col-sm-3">Type</dt>
                                <dd class="col-sm-9">${zone.kind || 'Native'}</dd>
                                <dt class="col-sm-3">Nameservers</dt>
                                <dd class="col-sm-9">${zone.nameservers?.join(', ') || 'None'}</dd>
                            </dl>
                            
                            <h6>Records</h6>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Name</th>
                                            <th>Type</th>
                                            <th>TTL</th>
                                            <th>Content</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${zone.rrsets?.map(rrset => 
                                            rrset.records.map(record => `
                                                <tr>
                                                    <td>${rrset.name}</td>
                                                    <td>${rrset.type}</td>
                                                    <td>${rrset.ttl || 'Default'}</td>
                                                    <td>${this.escapeHtml(record.content)}</td>
                                                </tr>
                                            `).join('')
                                        ).join('') || '<tr><td colspan="4">No records</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                            
                            ${validation.errors.length > 0 ? `
                                <div class="alert alert-danger">
                                    <h6>Errors</h6>
                                    <ul class="mb-0">
                                        ${validation.errors.map(e => `<li>${e}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                            
                            ${validation.warnings.length > 0 ? `
                                <div class="alert alert-warning">
                                    <h6>Warnings</h6>
                                    <ul class="mb-0">
                                        ${validation.warnings.map(w => `<li>${w}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing details modal
        const existing = document.getElementById('zoneDetailsModal');
        if (existing) existing.remove();

        document.body.insertAdjacentHTML('beforeend', detailsHtml);
        const detailsModal = new bootstrap.Modal(document.getElementById('zoneDetailsModal'));
        detailsModal.show();
    }

    /**
     * Import selected zones
     */
    async importZones() {
        // Show progress
        document.getElementById('importStep2').classList.add('d-none');
        document.getElementById('importStep3').classList.remove('d-none');
        document.getElementById('importButton').classList.add('d-none');

        const progressBar = document.getElementById('importProgress');
        const importLog = document.getElementById('importLog');
        
        // Get conflict resolution option
        const conflictResolution = document.querySelector('input[name="conflictResolution"]:checked').value;
        
        let successCount = 0;
        let errorCount = 0;
        const totalZones = this.selectedZones.size;
        let current = 0;

        for (const index of this.selectedZones) {
            current++;
            const zone = this.parsedZones[index];
            
            // Update progress
            const progress = (current / totalZones) * 100;
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
            
            // Log
            this.addLogMessage(`Importing zone ${zone.name}...`);
            
            try {
                // Import zone
                await this.importZone(zone, conflictResolution);
                successCount++;
                this.addLogMessage(`✓ Successfully imported ${zone.name}`, 'success');
            } catch (error) {
                errorCount++;
                this.addLogMessage(`✗ Failed to import ${zone.name}: ${error.message}`, 'error');
            }
            
            // Small delay for UI updates
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        // Show results
        this.showImportResults(successCount, errorCount);
    }

    /**
     * Import a single zone
     */
    async importZone(zone, conflictResolution) {
        const dnsService = DNSServiceFactory.getAdapter();
        
        // Check if zone exists
        try {
            const existingZone = await dnsService.getZone(zone.name);
            if (existingZone && conflictResolution === 'skip') {
                throw new Error('Zone already exists (skipped)');
            }
            
            if (existingZone && conflictResolution === 'overwrite') {
                // Delete existing zone first
                await dnsService.deleteZone(zone.name);
            }
            
            if (existingZone && conflictResolution === 'merge') {
                // Merge records - not implemented in this version
                throw new Error('Merge not implemented');
            }
        } catch (error) {
            if (!error.message.includes('not found')) {
                throw error;
            }
        }

        // Create the zone
        await dnsService.createZone(zone);
        
        // Update zone with rrsets if needed
        if (zone.rrsets && zone.rrsets.length > 0) {
            // Filter out SOA and NS records that were auto-created
            const rrsetsToAdd = zone.rrsets.filter(rrset => 
                rrset.type !== 'SOA' && rrset.type !== 'NS'
            );
            
            if (rrsetsToAdd.length > 0) {
                await dnsService.updateZone(zone.name, {
                    rrsets: rrsetsToAdd.map(rrset => ({
                        ...rrset,
                        changetype: 'REPLACE'
                    }))
                });
            }
        }
    }

    /**
     * Add message to import log
     */
    addLogMessage(message, type = 'info') {
        const importLog = document.getElementById('importLog');
        const timestamp = new Date().toLocaleTimeString();
        const colorClass = type === 'success' ? 'text-success' : 
                          type === 'error' ? 'text-danger' : 'text-muted';
        
        const logEntry = document.createElement('div');
        logEntry.className = colorClass;
        logEntry.textContent = `[${timestamp}] ${message}`;
        importLog.appendChild(logEntry);
        
        // Scroll to bottom
        importLog.scrollTop = importLog.scrollHeight;
    }

    /**
     * Show import results
     */
    showImportResults(successCount, errorCount) {
        document.getElementById('importStep3').classList.add('d-none');
        document.getElementById('importStep4').classList.remove('d-none');
        document.getElementById('doneButton').classList.remove('d-none');

        const total = successCount + errorCount;
        
        if (errorCount === 0) {
            document.getElementById('successMessage').textContent = 
                `All ${successCount} zone(s) imported successfully!`;
            document.getElementById('importSuccess').classList.remove('d-none');
        } else {
            document.getElementById('errorMessage').textContent = 
                `${errorCount} out of ${total} zones failed to import.`;
            document.getElementById('importError').classList.remove('d-none');
            
            if (successCount > 0) {
                document.getElementById('successMessage').textContent = 
                    `${successCount} zone(s) imported successfully.`;
                document.getElementById('importSuccess').classList.remove('d-none');
            }
        }

        // Refresh zones list if available
        if (window.dnsZonesManager) {
            window.dnsZonesManager.loadZones();
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('#importStep1') || document.querySelector('.modal-body');
        container.insertBefore(alert, container.firstChild);
    }

    /**
     * Escape HTML
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
        this.fileContent = null;
        this.detectedFormat = null;
        this.parsedZones = null;
        this.validationResults = null;
        this.selectedZones.clear();
    }
}

// Create global instance
window.dnsImportModal = new DNSImportModal();