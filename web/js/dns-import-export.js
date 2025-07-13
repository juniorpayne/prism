/**
 * DNS Import/Export Module
 * Handles importing and exporting DNS zones in various formats
 */

class DNSImportExport {
    constructor() {
        this.mockService = new DNSMockDataService();
        this.supportedFormats = {
            bind: 'BIND Zone File',
            json: 'JSON Format',
            csv: 'CSV Format (Records Only)'
        };
    }

    /**
     * Export a single zone in the specified format
     */
    async exportZone(zoneId, format = 'bind', options = {}) {
        try {
            const zone = await this.mockService.getZone(zoneId);
            if (!zone) {
                throw new Error(`Zone ${zoneId} not found`);
            }

            let content;
            let filename;
            let mimeType;

            switch (format) {
                case 'bind':
                    content = this.exportToBind(zone, options);
                    filename = `${zone.name.replace(/\.$/, '')}.zone`;
                    mimeType = 'text/plain';
                    break;
                case 'json':
                    content = this.exportToJson(zone, options);
                    filename = `${zone.name.replace(/\.$/, '')}.json`;
                    mimeType = 'application/json';
                    break;
                case 'csv':
                    content = this.exportToCsv(zone, options);
                    filename = `${zone.name.replace(/\.$/, '')}.csv`;
                    mimeType = 'text/csv';
                    break;
                default:
                    throw new Error(`Unsupported format: ${format}`);
            }

            this.downloadFile(content, filename, mimeType);
            return { success: true, filename };
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        }
    }

    /**
     * Export multiple zones
     */
    async exportMultipleZones(zoneIds, format = 'bind', options = {}) {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const zipFilename = `dns-zones-export-${timestamp}.zip`;
            
            // For now, we'll export them individually
            // In a real implementation, we'd create a zip file
            const results = [];
            for (const zoneId of zoneIds) {
                try {
                    const result = await this.exportZone(zoneId, format, options);
                    results.push(result);
                } catch (error) {
                    results.push({ success: false, zoneId, error: error.message });
                }
            }
            
            return results;
        } catch (error) {
            console.error('Bulk export error:', error);
            throw error;
        }
    }

    /**
     * Export zone to BIND format
     */
    exportToBind(zone, options = {}) {
        const lines = [];
        const includeComments = options.includeComments !== false;
        
        // Header comment
        if (includeComments) {
            lines.push(`; Zone file for ${zone.name}`);
            lines.push(`; Exported from Prism DNS on ${new Date().toISOString()}`);
            lines.push('');
        }

        // $ORIGIN directive
        lines.push(`$ORIGIN ${zone.name}`);
        lines.push('');

        // Default TTL
        const defaultTTL = zone.rrsets.find(r => r.ttl)?.ttl || 3600;
        lines.push(`$TTL ${defaultTTL}`);
        lines.push('');

        // Process rrsets
        zone.rrsets.forEach(rrset => {
            if (options.excludeSOA && rrset.type === 'SOA') return;
            if (options.excludeNS && rrset.type === 'NS') return;

            rrset.records.forEach(record => {
                if (record.disabled && !options.includeDisabled) return;

                // Format the name
                let name = rrset.name;
                if (name === zone.name) {
                    name = '@';
                } else {
                    // Remove zone suffix for relative names
                    name = name.replace(new RegExp(`\\.${zone.name.replace('.', '\\.')}$`), '');
                }

                // Format the record
                const ttl = rrset.ttl !== defaultTTL ? `${rrset.ttl}` : '';
                const line = `${name.padEnd(30)} ${ttl.padEnd(8)} IN  ${rrset.type.padEnd(6)} ${record.content}`;
                
                if (record.disabled && options.includeDisabled) {
                    lines.push(`; DISABLED: ${line}`);
                } else {
                    lines.push(line);
                }
            });
            
            lines.push(''); // Empty line between record types
        });

        return lines.join('\n');
    }

    /**
     * Export zone to JSON format
     */
    exportToJson(zone, options = {}) {
        const exportData = {
            name: zone.name,
            kind: zone.kind,
            dnssec: zone.dnssec,
            serial: zone.serial,
            nameservers: zone.nameservers,
            exported: new Date().toISOString(),
            exportedBy: 'Prism DNS'
        };

        // Filter rrsets based on options
        exportData.rrsets = zone.rrsets.filter(rrset => {
            if (options.excludeSOA && rrset.type === 'SOA') return false;
            if (options.excludeNS && rrset.type === 'NS') return false;
            return true;
        });

        // Remove disabled records if requested
        if (!options.includeDisabled) {
            exportData.rrsets = exportData.rrsets.map(rrset => ({
                ...rrset,
                records: rrset.records.filter(record => !record.disabled)
            })).filter(rrset => rrset.records.length > 0);
        }

        return JSON.stringify(exportData, null, 2);
    }

    /**
     * Export zone records to CSV format
     */
    exportToCsv(zone, options = {}) {
        const rows = [];
        
        // Header row
        rows.push(['Zone', 'Name', 'Type', 'TTL', 'Priority', 'Content', 'Disabled'].join(','));

        // Data rows
        zone.rrsets.forEach(rrset => {
            if (options.excludeSOA && rrset.type === 'SOA') return;
            if (options.excludeNS && rrset.type === 'NS') return;

            rrset.records.forEach(record => {
                if (record.disabled && !options.includeDisabled) return;

                // Extract priority from MX/SRV records
                let priority = '';
                let content = record.content;
                
                if (rrset.type === 'MX') {
                    const parts = content.split(' ');
                    if (parts.length >= 2) {
                        priority = parts[0];
                        content = parts.slice(1).join(' ');
                    }
                }

                const row = [
                    zone.name,
                    rrset.name,
                    rrset.type,
                    rrset.ttl || '',
                    priority,
                    `"${content.replace(/"/g, '""')}"`, // Escape quotes in content
                    record.disabled ? 'Yes' : 'No'
                ];

                rows.push(row.join(','));
            });
        });

        return rows.join('\n');
    }

    /**
     * Import zones from file content
     */
    async importZones(fileContent, format, options = {}) {
        try {
            let zones;
            
            switch (format) {
                case 'bind':
                    zones = this.parseBindZoneFile(fileContent, options);
                    break;
                case 'json':
                    zones = this.parseJsonZoneFile(fileContent, options);
                    break;
                case 'csv':
                    zones = this.parseCsvZoneFile(fileContent, options);
                    break;
                default:
                    throw new Error(`Unsupported format: ${format}`);
            }

            // Validate zones
            const validationResults = zones.map(zone => this.validateZone(zone));
            
            return {
                zones,
                validationResults,
                hasErrors: validationResults.some(r => r.errors.length > 0)
            };
        } catch (error) {
            console.error('Import error:', error);
            throw error;
        }
    }

    /**
     * Parse BIND zone file
     */
    parseBindZoneFile(content, options = {}) {
        const lines = content.split('\n');
        const zones = [];
        let currentZone = null;
        let origin = options.zoneName || null;
        let defaultTTL = 3600;
        let lineNumber = 0;

        const parseErrors = [];

        for (const line of lines) {
            lineNumber++;
            const trimmed = line.trim();
            
            // Skip empty lines and comments
            if (!trimmed || trimmed.startsWith(';')) continue;

            // Handle directives
            if (trimmed.startsWith('$ORIGIN')) {
                origin = trimmed.split(/\s+/)[1];
                if (!origin.endsWith('.')) {
                    origin += '.';
                }
                continue;
            }

            if (trimmed.startsWith('$TTL')) {
                defaultTTL = parseInt(trimmed.split(/\s+/)[1]);
                continue;
            }

            // Parse record line
            try {
                const record = this.parseBindRecord(trimmed, origin, defaultTTL);
                if (record) {
                    if (!currentZone) {
                        currentZone = {
                            name: origin,
                            kind: 'Native',
                            nameservers: [],
                            rrsets: []
                        };
                        zones.push(currentZone);
                    }

                    // Add to appropriate rrset
                    let rrset = currentZone.rrsets.find(r => 
                        r.name === record.name && r.type === record.type
                    );
                    
                    if (!rrset) {
                        rrset = {
                            name: record.name,
                            type: record.type,
                            ttl: record.ttl,
                            records: []
                        };
                        currentZone.rrsets.push(rrset);
                    }

                    rrset.records.push({
                        content: record.content,
                        disabled: false
                    });
                }
            } catch (error) {
                parseErrors.push({
                    line: lineNumber,
                    content: trimmed,
                    error: error.message
                });
            }
        }

        if (parseErrors.length > 0 && options.strict) {
            throw new Error(`Parse errors found: ${parseErrors.length} errors`);
        }

        return zones;
    }

    /**
     * Parse a single BIND record line
     */
    parseBindRecord(line, origin, defaultTTL) {
        // Simple regex for basic record parsing
        const parts = line.split(/\s+/);
        if (parts.length < 4) return null;

        let index = 0;
        let name = parts[index++];
        
        // Handle @ symbol
        if (name === '@') {
            name = origin;
        } else if (!name.endsWith('.')) {
            name = `${name}.${origin}`;
        }

        // Check if next part is TTL (number)
        let ttl = defaultTTL;
        if (/^\d+$/.test(parts[index])) {
            ttl = parseInt(parts[index++]);
        }

        // Skip class (IN)
        if (parts[index] === 'IN') {
            index++;
        }

        // Record type
        const type = parts[index++];
        
        // Rest is content
        const content = parts.slice(index).join(' ');

        return {
            name,
            type,
            ttl,
            content
        };
    }

    /**
     * Parse JSON zone file
     */
    parseJsonZoneFile(content, options = {}) {
        try {
            const data = JSON.parse(content);
            const zones = [];

            // Handle single zone or array of zones
            const zoneData = Array.isArray(data) ? data : [data];

            for (const zone of zoneData) {
                // Ensure zone name ends with dot
                if (zone.name && !zone.name.endsWith('.')) {
                    zone.name += '.';
                }

                // Ensure all rrset names end with dot
                if (zone.rrsets) {
                    zone.rrsets.forEach(rrset => {
                        if (!rrset.name.endsWith('.')) {
                            rrset.name += '.';
                        }
                    });
                }

                zones.push(zone);
            }

            return zones;
        } catch (error) {
            throw new Error(`Invalid JSON format: ${error.message}`);
        }
    }

    /**
     * Parse CSV zone file
     */
    parseCsvZoneFile(content, options = {}) {
        const lines = content.split('\n');
        const zones = {};
        
        // Skip header row
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            const values = this.parseCsvLine(line);
            if (values.length < 6) continue;

            const [zoneName, name, type, ttl, priority, content, disabled] = values;
            
            // Ensure zone exists
            if (!zones[zoneName]) {
                zones[zoneName] = {
                    name: zoneName.endsWith('.') ? zoneName : zoneName + '.',
                    kind: 'Native',
                    nameservers: [],
                    rrsets: []
                };
            }

            const zone = zones[zoneName];
            
            // Find or create rrset
            let rrset = zone.rrsets.find(r => r.name === name && r.type === type);
            if (!rrset) {
                rrset = {
                    name: name.endsWith('.') ? name : name + '.',
                    type,
                    ttl: parseInt(ttl) || 3600,
                    records: []
                };
                zone.rrsets.push(rrset);
            }

            // Add record
            let recordContent = content;
            if (type === 'MX' && priority) {
                recordContent = `${priority} ${content}`;
            }

            rrset.records.push({
                content: recordContent,
                disabled: disabled === 'Yes'
            });
        }

        return Object.values(zones);
    }

    /**
     * Parse CSV line handling quoted values
     */
    parseCsvLine(line) {
        const values = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            const nextChar = line[i + 1];

            if (char === '"') {
                if (inQuotes && nextChar === '"') {
                    current += '"';
                    i++; // Skip next quote
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                values.push(current);
                current = '';
            } else {
                current += char;
            }
        }

        values.push(current);
        return values;
    }

    /**
     * Validate zone data
     */
    validateZone(zone) {
        const errors = [];
        const warnings = [];

        // Check zone name
        if (!zone.name) {
            errors.push('Zone name is required');
        } else if (!zone.name.endsWith('.')) {
            warnings.push('Zone name should end with a dot');
        }

        // Check for SOA record
        const hasSOA = zone.rrsets?.some(r => r.type === 'SOA');
        if (!hasSOA) {
            warnings.push('No SOA record found');
        }

        // Check for NS records
        const nsRecords = zone.rrsets?.filter(r => r.type === 'NS') || [];
        if (nsRecords.length === 0) {
            warnings.push('No NS records found');
        }

        // Validate each rrset
        zone.rrsets?.forEach(rrset => {
            // Check record content based on type
            rrset.records.forEach(record => {
                const contentError = this.validateRecordContent(rrset.type, record.content);
                if (contentError) {
                    errors.push(`Invalid ${rrset.type} record: ${contentError}`);
                }
            });
        });

        return { errors, warnings };
    }

    /**
     * Validate record content based on type
     */
    validateRecordContent(type, content) {
        switch (type) {
            case 'A':
                // Simple IPv4 validation
                if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(content)) {
                    return 'Invalid IPv4 address';
                }
                break;
            case 'AAAA':
                // Simple IPv6 validation
                if (!/^[0-9a-fA-F:]+$/.test(content)) {
                    return 'Invalid IPv6 address';
                }
                break;
            case 'MX':
                if (!/^\d+ /.test(content)) {
                    return 'MX record must start with priority';
                }
                break;
            case 'CNAME':
                if (!content || content.trim() === '') {
                    return 'CNAME target is required';
                }
                break;
        }
        return null;
    }

    /**
     * Auto-detect file format
     */
    detectFormat(content) {
        // Try JSON first
        try {
            JSON.parse(content);
            return 'json';
        } catch (e) {
            // Not JSON
        }

        // Check for CSV headers
        const firstLine = content.split('\n')[0];
        if (firstLine && firstLine.includes(',') && 
            firstLine.toLowerCase().includes('zone') && 
            firstLine.toLowerCase().includes('type')) {
            return 'csv';
        }

        // Default to BIND format
        return 'bind';
    }

    /**
     * Download file to user's computer
     */
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Create import preview data
     */
    createImportPreview(zones, validationResults) {
        return zones.map((zone, index) => ({
            zone,
            validation: validationResults[index],
            recordCount: zone.rrsets?.reduce((sum, rrset) => sum + rrset.records.length, 0) || 0,
            hasErrors: validationResults[index].errors.length > 0,
            hasWarnings: validationResults[index].warnings.length > 0
        }));
    }
}

// Export for use in other modules
window.DNSImportExport = DNSImportExport;