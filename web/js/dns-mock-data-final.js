/**
 * Mock Data Service for DNS Zone Management - PowerDNS API Compatible
 * This service mimics PowerDNS API responses for frontend development
 */

class DNSMockDataService {
    constructor() {
        this.storageKey = 'prism-dns-zones-v2';
        this.defaultTTL = 3600;
        this.initializeStorage();
    }

    /**
     * Initialize localStorage with PowerDNS-compatible sample data
     */
    initializeStorage() {
        if (!localStorage.getItem(this.storageKey)) {
            const sampleZones = this.generateSampleZones();
            localStorage.setItem(this.storageKey, JSON.stringify(sampleZones));
        }
    }

    /**
     * Generate sample DNS zones in PowerDNS format
     */
    generateSampleZones() {
        const zones = {
            // Add subdomain zones for testing hierarchy
            'api.example.com.': {
                id: 'api.example.com.',
                name: 'api.example.com.',
                kind: 'Native',
                account: '',
                dnssec: false,
                api_rectify: false,
                serial: 2024122001,
                notified_serial: 2024122001,
                edited_serial: 2024122001,
                masters: [],
                nameservers: ['ns1.example.com.', 'ns2.example.com.'],
                rrsets: [
                    {
                        name: 'api.example.com.',
                        type: 'SOA',
                        ttl: 3600,
                        records: [{
                            content: 'ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600',
                            disabled: false
                        }]
                    },
                    {
                        name: 'api.example.com.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '192.168.1.10', disabled: false }]
                    }
                ]
            },
            'dev.api.example.com.': {
                id: 'dev.api.example.com.',
                name: 'dev.api.example.com.',
                kind: 'Native',
                account: '',
                dnssec: false,
                api_rectify: false,
                serial: 2024122001,
                notified_serial: 2024122001,
                edited_serial: 2024122001,
                masters: [],
                nameservers: ['ns1.example.com.', 'ns2.example.com.'],
                rrsets: [
                    {
                        name: 'dev.api.example.com.',
                        type: 'SOA',
                        ttl: 3600,
                        records: [{
                            content: 'ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600',
                            disabled: false
                        }]
                    },
                    {
                        name: 'dev.api.example.com.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '192.168.1.11', disabled: false }]
                    }
                ]
            },
            'example.com.': {
                id: 'example.com.',
                name: 'example.com.',
                kind: 'Native',
                account: '',
                dnssec: false,
                api_rectify: false,
                serial: 2024122001,
                notified_serial: 2024122001,
                edited_serial: 2024122001,
                masters: [],
                nameservers: ['ns1.example.com.', 'ns2.example.com.'],
                rrsets: [
                    {
                        name: 'example.com.',
                        type: 'SOA',
                        ttl: 3600,
                        records: [{
                            content: 'ns1.example.com. admin.example.com. 2024122001 3600 600 86400 3600',
                            disabled: false
                        }],
                        comments: []
                    },
                    {
                        name: 'example.com.',
                        type: 'NS',
                        ttl: 3600,
                        records: [
                            { content: 'ns1.example.com.', disabled: false },
                            { content: 'ns2.example.com.', disabled: false }
                        ],
                        comments: []
                    },
                    {
                        name: 'example.com.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '192.168.1.1', disabled: false }],
                        comments: []
                    },
                    {
                        name: 'www.example.com.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '192.168.1.1', disabled: false }],
                        comments: []
                    },
                    {
                        name: 'example.com.',
                        type: 'MX',
                        ttl: 3600,
                        records: [{ content: '10 mail.example.com.', disabled: false }],
                        comments: []
                    },
                    {
                        name: 'mail.example.com.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '192.168.1.2', disabled: false }],
                        comments: []
                    },
                    {
                        name: 'example.com.',
                        type: 'TXT',
                        ttl: 3600,
                        records: [{ content: '"v=spf1 mx ~all"', disabled: false }],
                        comments: []
                    }
                ]
            },
            'test-domain.org.': {
                id: 'test-domain.org.',
                name: 'test-domain.org.',
                kind: 'Native',
                account: '',
                dnssec: false,
                api_rectify: false,
                serial: 2024113001,
                notified_serial: 2024113001,
                edited_serial: 2024113001,
                masters: [],
                nameservers: ['ns1.test-domain.org.', 'ns2.test-domain.org.'],
                rrsets: [
                    {
                        name: 'test-domain.org.',
                        type: 'SOA',
                        ttl: 3600,
                        records: [{
                            content: 'ns1.test-domain.org. hostmaster.test-domain.org. 2024113001 7200 900 604800 3600',
                            disabled: false
                        }],
                        comments: []
                    },
                    {
                        name: 'test-domain.org.',
                        type: 'NS',
                        ttl: 3600,
                        records: [
                            { content: 'ns1.test-domain.org.', disabled: false },
                            { content: 'ns2.test-domain.org.', disabled: false }
                        ],
                        comments: []
                    },
                    {
                        name: 'test-domain.org.',
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: '10.0.0.1', disabled: false }],
                        comments: []
                    },
                    {
                        name: 'app.test-domain.org.',
                        type: 'CNAME',
                        ttl: 3600,
                        records: [{ content: 'test-domain.org.', disabled: false }],
                        comments: []
                    }
                ]
            }
        };
        
        // Generate additional test zones for performance testing
        for (let i = 1; i <= 20; i++) {
            const domain = `test-zone-${i}.com.`;
            zones[domain] = {
                id: domain,
                name: domain,
                kind: i % 3 === 0 ? 'Slave' : 'Native',
                account: '',
                dnssec: i % 5 === 0,
                api_rectify: false,
                serial: 2024120000 + i,
                notified_serial: 2024120000 + i,
                edited_serial: 2024120000 + i,
                masters: i % 3 === 0 ? ['master1.example.com.', 'master2.example.com.'] : [],
                nameservers: [`ns1.${domain}`, `ns2.${domain}`],
                rrsets: [
                    {
                        name: domain,
                        type: 'SOA',
                        ttl: 3600,
                        records: [{
                            content: `ns1.${domain} admin.${domain} ${2024120000 + i} 3600 600 86400 3600`,
                            disabled: false
                        }],
                        comments: []
                    },
                    {
                        name: domain,
                        type: 'NS',
                        ttl: 3600,
                        records: [
                            { content: `ns1.${domain}`, disabled: false },
                            { content: `ns2.${domain}`, disabled: false }
                        ],
                        comments: []
                    },
                    {
                        name: domain,
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: `192.168.${Math.floor(i/10)}.${i}`, disabled: false }],
                        comments: []
                    },
                    {
                        name: `www.${domain}`,
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: `192.168.${Math.floor(i/10)}.${i}`, disabled: false }],
                        comments: []
                    },
                    {
                        name: `mail.${domain}`,
                        type: 'A',
                        ttl: 3600,
                        records: [{ content: `192.168.${Math.floor(i/10)}.${100 + i}`, disabled: false }],
                        comments: []
                    },
                    {
                        name: domain,
                        type: 'MX',
                        ttl: 3600,
                        records: [{ content: `10 mail.${domain}`, disabled: false }],
                        comments: []
                    }
                ]
            };
        }
        
        return zones;
    }

    /**
     * Simulate network delay
     */
    async simulateDelay() {
        const delay = Math.floor(Math.random() * 300) + 100; // 100-400ms
        await new Promise(resolve => setTimeout(resolve, delay));
    }

    /**
     * Normalize zone name (ensure it ends with dot)
     */
    normalizeZoneName(name) {
        return name.endsWith('.') ? name : name + '.';
    }

    /**
     * Get all zones (simplified format for listing)
     */
    async getAllZones() {
        await this.simulateDelay();
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        
        // Return simplified format for zone listing
        return Object.values(zones).map(zone => ({
            id: zone.id,
            name: zone.name,
            kind: zone.kind,
            serial: zone.serial,
            dnssec: zone.dnssec,
            account: zone.account,
            nameservers: zone.nameservers
        }));
    }

    /**
     * Get a specific zone with full details
     */
    async getZone(zoneId) {
        await this.simulateDelay();
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        const normalizedId = this.normalizeZoneName(zoneId);
        const zone = zones[normalizedId];
        
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        return zone;
    }

    /**
     * Create a new zone
     */
    async createZone(zoneData) {
        await this.simulateDelay();
        
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        const zoneName = this.normalizeZoneName(zoneData.name);
        
        if (zones[zoneName]) {
            throw new Error(`Zone ${zoneName} already exists`);
        }

        const serial = parseInt(new Date().toISOString().slice(0, 10).replace(/-/g, '') + '01');
        
        const newZone = {
            id: zoneName,
            name: zoneName,
            kind: zoneData.kind || 'Native',
            account: zoneData.account || '',
            dnssec: false,
            api_rectify: false,
            serial: serial,
            notified_serial: serial,
            edited_serial: serial,
            masters: zoneData.masters || [],
            nameservers: zoneData.nameservers || [`ns1.${zoneName}`, `ns2.${zoneName}`],
            rrsets: [
                {
                    name: zoneName,
                    type: 'SOA',
                    ttl: 3600,
                    records: [{
                        content: `${zoneData.nameservers?.[0] || 'ns1.' + zoneName} ${zoneData.email || 'hostmaster.' + zoneName} ${serial} 3600 600 86400 3600`,
                        disabled: false
                    }],
                    comments: []
                },
                {
                    name: zoneName,
                    type: 'NS',
                    ttl: 3600,
                    records: (zoneData.nameservers || [`ns1.${zoneName}`, `ns2.${zoneName}`]).map(ns => ({
                        content: this.normalizeZoneName(ns),
                        disabled: false
                    })),
                    comments: []
                }
            ]
        };

        zones[zoneName] = newZone;
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        
        return newZone;
    }

    /**
     * Update zone (PATCH) - PowerDNS style with rrsets changes
     */
    async updateZone(zoneId, changes) {
        await this.simulateDelay();
        
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        const normalizedId = this.normalizeZoneName(zoneId);
        const zone = zones[normalizedId];
        
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }

        // Handle rrsets changes (PowerDNS PATCH format)
        if (changes.rrsets) {
            for (const rrsetChange of changes.rrsets) {
                const changetype = rrsetChange.changetype || 'REPLACE';
                const name = this.normalizeZoneName(rrsetChange.name);
                const type = rrsetChange.type;

                if (changetype === 'DELETE') {
                    // Remove all records of this name and type
                    zone.rrsets = zone.rrsets.filter(rrset => 
                        !(rrset.name === name && rrset.type === type)
                    );
                } else if (changetype === 'REPLACE') {
                    // Remove existing rrset of this name and type
                    zone.rrsets = zone.rrsets.filter(rrset => 
                        !(rrset.name === name && rrset.type === type)
                    );
                    
                    // Add new rrset if records provided
                    if (rrsetChange.records && rrsetChange.records.length > 0) {
                        zone.rrsets.push({
                            name: name,
                            type: type,
                            ttl: rrsetChange.ttl || this.defaultTTL,
                            records: rrsetChange.records,
                            comments: rrsetChange.comments || []
                        });
                    }
                }
            }
            
            // Update serial
            zone.serial = parseInt(new Date().toISOString().slice(0, 10).replace(/-/g, '') + '01');
            zone.edited_serial = zone.serial;
        }

        // Handle direct property updates
        if (changes.nameservers) {
            zone.nameservers = changes.nameservers;
        }

        zones[normalizedId] = zone;
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        
        return zone;
    }

    /**
     * Delete a zone
     */
    async deleteZone(zoneId) {
        await this.simulateDelay();
        
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        const normalizedId = this.normalizeZoneName(zoneId);
        
        if (!zones[normalizedId]) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        delete zones[normalizedId];
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        
        return { success: true, message: `Zone ${zoneId} deleted successfully` };
    }

    /**
     * Get statistics for dashboard
     */
    async getStats() {
        await this.simulateDelay();
        
        const zones = await this.getAllZones();
        let totalRecords = 0;
        
        // Count all records across all zones
        const fullZones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        Object.values(fullZones).forEach(zone => {
            zone.rrsets.forEach(rrset => {
                totalRecords += rrset.records.length;
            });
        });
        
        return {
            totalZones: zones.length,
            activeZones: zones.length,
            totalRecords: totalRecords,
            recentChanges: Math.floor(Math.random() * 10) + 1
        };
    }

    /**
     * Simulate PowerDNS error responses
     */
    simulateError(probability = 0.05) {
        if (Math.random() < probability) {
            const errors = [
                { status: 404, message: 'Not Found' },
                { status: 422, message: 'Unprocessable Entity' },
                { status: 500, message: 'Internal Server Error' }
            ];
            const error = errors[Math.floor(Math.random() * errors.length)];
            throw new Error(`PowerDNS API Error: ${error.status} - ${error.message}`);
        }
    }

    // ==============================================
    // Additional methods for adapter compatibility
    // ==============================================

    /**
     * Get zones with pagination (adapter-compatible version)
     */
    async getZones(page = 1, limit = 50, search = '', filters = {}) {
        await this.simulateDelay();
        
        const allZones = await this.getAllZones();
        let filteredZones = allZones;
        
        // Apply search filter
        if (search) {
            const searchLower = search.toLowerCase();
            filteredZones = filteredZones.filter(zone => 
                zone.name.toLowerCase().includes(searchLower)
            );
        }
        
        // Apply sorting
        if (filters.sort) {
            const reverse = filters.order === 'desc';
            filteredZones.sort((a, b) => {
                const aVal = a[filters.sort] || '';
                const bVal = b[filters.sort] || '';
                return reverse ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            });
        }
        
        // Pagination
        const start = (page - 1) * limit;
        const paginatedZones = filteredZones.slice(start, start + limit);
        
        return {
            zones: paginatedZones,
            pagination: {
                page: page,
                limit: limit,
                total: filteredZones.length,
                pages: Math.ceil(filteredZones.length / limit)
            }
        };
    }

    /**
     * Get records for a zone with pagination
     */
    async getRecords(zoneId, page = 1, limit = 50, filters = {}) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        let records = [];
        
        // Convert rrsets to flat record list
        zone.rrsets.forEach(rrset => {
            rrset.records.forEach(record => {
                records.push({
                    name: rrset.name,
                    type: rrset.type,
                    ttl: rrset.ttl,
                    content: record.content,
                    disabled: record.disabled,
                    zone: zoneId
                });
            });
        });
        
        // Apply filters
        if (filters.recordType) {
            records = records.filter(r => r.type === filters.recordType);
        }
        if (filters.name) {
            records = records.filter(r => r.name.includes(filters.name));
        }
        
        // Pagination
        const start = (page - 1) * limit;
        const paginatedRecords = records.slice(start, start + limit);
        
        return {
            records: paginatedRecords,
            pagination: {
                page: page,
                limit: limit,
                total: records.length,
                pages: Math.ceil(records.length / limit)
            }
        };
    }

    /**
     * Get specific record
     */
    async getRecord(zoneId, name, type) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        // Normalize name
        const fullName = name.endsWith('.') ? name : `${name}.${zoneId}`;
        
        const rrset = zone.rrsets.find(rs => 
            rs.name === fullName && rs.type === type
        );
        
        if (!rrset) {
            throw new Error(`Record ${name}/${type} not found in zone ${zoneId}`);
        }
        
        return rrset;
    }

    /**
     * Create a record
     */
    async createRecord(zoneId, recordData) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        // Normalize name
        let recordName = recordData.name;
        if (!recordName.endsWith('.')) {
            recordName = `${recordName}.${zoneId}`;
        }
        
        // Check if record already exists
        const existing = zone.rrsets.find(rs => 
            rs.name === recordName && rs.type === recordData.type
        );
        
        if (existing) {
            throw new Error(`Record ${recordName}/${recordData.type} already exists`);
        }
        
        // Add new record
        const newRrset = {
            name: recordName,
            type: recordData.type,
            ttl: recordData.ttl || this.defaultTTL,
            records: recordData.records || [],
            comments: []
        };
        
        // Update zone with new record
        await this.updateZone(zoneId, {
            rrsets: [{
                ...newRrset,
                changetype: 'REPLACE'
            }]
        });
        
        return newRrset;
    }

    /**
     * Update a record
     */
    async updateRecord(zoneId, name, type, recordData) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        // Normalize name
        const fullName = name.endsWith('.') ? name : `${name}.${zoneId}`;
        
        // Update via updateZone
        await this.updateZone(zoneId, {
            rrsets: [{
                name: fullName,
                type: type,
                ttl: recordData.ttl || this.defaultTTL,
                records: recordData.records || [],
                changetype: 'REPLACE'
            }]
        });
        
        return await this.getRecord(zoneId, name, type);
    }

    /**
     * Delete a record
     */
    async deleteRecord(zoneId, name, type) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        if (!zone) {
            throw new Error(`Zone ${zoneId} not found`);
        }
        
        // Normalize name
        const fullName = name.endsWith('.') ? name : `${name}.${zoneId}`;
        
        // Delete via updateZone
        await this.updateZone(zoneId, {
            rrsets: [{
                name: fullName,
                type: type,
                changetype: 'DELETE'
            }]
        });
        
        return { success: true, message: `Record ${name}/${type} deleted` };
    }

    /**
     * Search zones
     */
    async searchZones(query, filters = {}) {
        await this.simulateDelay();
        
        const allZones = await this.getAllZones();
        let results = allZones;
        
        // Search by query
        if (query) {
            const queryLower = query.toLowerCase();
            results = results.filter(zone => 
                zone.name.toLowerCase().includes(queryLower) ||
                (zone.account && zone.account.toLowerCase().includes(queryLower))
            );
        }
        
        // Apply filters
        if (filters.zoneType) {
            results = results.filter(zone => zone.kind === filters.zoneType);
        }
        
        if (filters.limit) {
            results = results.slice(0, filters.limit);
        }
        
        return {
            query: query,
            total: results.length,
            zones: results,
            filters: filters
        };
    }

    /**
     * Search records
     */
    async searchRecords(query, filters = {}) {
        await this.simulateDelay();
        
        const allZones = await this.getAllZones();
        let allRecords = [];
        
        // Collect all records from all zones
        for (const zone of allZones) {
            const fullZone = await this.getZone(zone.name);
            fullZone.rrsets.forEach(rrset => {
                rrset.records.forEach(record => {
                    allRecords.push({
                        name: rrset.name,
                        type: rrset.type,
                        ttl: rrset.ttl,
                        content: record.content,
                        disabled: record.disabled,
                        zone: zone.name
                    });
                });
            });
        }
        
        // Search
        if (query) {
            const queryLower = query.toLowerCase();
            allRecords = allRecords.filter(record => {
                if (filters.contentSearch) {
                    return record.content.toLowerCase().includes(queryLower);
                } else {
                    return record.name.toLowerCase().includes(queryLower);
                }
            });
        }
        
        // Apply filters
        if (filters.recordType) {
            allRecords = allRecords.filter(r => r.type === filters.recordType);
        }
        if (filters.zone) {
            allRecords = allRecords.filter(r => r.zone === filters.zone);
        }
        if (filters.limit) {
            allRecords = allRecords.slice(0, filters.limit);
        }
        
        return {
            query: query,
            total: allRecords.length,
            records: allRecords,
            filters: filters
        };
    }

    /**
     * Filter zones with advanced criteria
     */
    async filterZones(filters = {}, sortBy = 'name', sortOrder = 'asc') {
        await this.simulateDelay();
        
        const allZones = await this.getAllZones();
        let results = [];
        
        // Get full zone data for filtering
        for (const zone of allZones) {
            const fullZone = await this.getZone(zone.name);
            fullZone.record_count = fullZone.rrsets.reduce((count, rrset) => 
                count + rrset.records.length, 0
            );
            results.push(fullZone);
        }
        
        // Apply filters
        if (filters.min_records !== undefined) {
            results = results.filter(z => z.record_count >= filters.min_records);
        }
        if (filters.max_records !== undefined) {
            results = results.filter(z => z.record_count <= filters.max_records);
        }
        if (filters.has_dnssec !== undefined) {
            results = results.filter(z => z.dnssec === filters.has_dnssec);
        }
        if (filters.parent_zone) {
            results = results.filter(z => 
                z.name !== filters.parent_zone && 
                z.name.endsWith('.' + filters.parent_zone)
            );
        }
        
        // Sort
        results.sort((a, b) => {
            let aVal = a[sortBy];
            let bVal = b[sortBy];
            
            if (sortBy === 'records') {
                aVal = a.record_count;
                bVal = b.record_count;
            }
            
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
            } else {
                const comparison = String(aVal).localeCompare(String(bVal));
                return sortOrder === 'asc' ? comparison : -comparison;
            }
        });
        
        return {
            total: results.length,
            zones: results,
            filters: filters,
            sort: { by: sortBy, order: sortOrder }
        };
    }

    /**
     * Export zones
     */
    async exportZones(format = 'json', zones = null, includeDnssec = true) {
        await this.simulateDelay();
        
        let exportZones = [];
        
        if (zones && zones.length > 0) {
            // Export specific zones
            for (const zoneName of zones) {
                try {
                    const zone = await this.getZone(zoneName);
                    exportZones.push(zone);
                } catch (error) {
                    console.warn(`Zone ${zoneName} not found for export`);
                }
            }
        } else {
            // Export all zones
            const allZones = await this.getAllZones();
            for (const zone of allZones) {
                exportZones.push(await this.getZone(zone.name));
            }
        }
        
        if (format === 'json') {
            return {
                format: 'json',
                version: '1.0',
                zones: exportZones
            };
        } else {
            // For other formats, return mock data
            return {
                format: format,
                data: `Mock ${format} export data for ${exportZones.length} zones`
            };
        }
    }

    /**
     * Import zones
     */
    async importZones(data, format = 'json', mode = 'merge', dryRun = false) {
        await this.simulateDelay();
        
        const result = {
            status: dryRun ? 'preview' : 'success',
            mode: mode,
            zones_processed: 0,
            zones_created: 0,
            zones_updated: 0,
            zones_skipped: 0,
            records_added: 0,
            errors: []
        };
        
        try {
            let zonesToImport = [];
            
            if (format === 'json') {
                const parsed = JSON.parse(data);
                zonesToImport = parsed.zones || [];
            } else {
                // Mock parsing for other formats
                result.errors.push(`Format ${format} parsing not implemented in mock`);
                return result;
            }
            
            for (const zoneData of zonesToImport) {
                result.zones_processed++;
                
                if (!dryRun) {
                    try {
                        const existing = await this.getZone(zoneData.name).catch(() => null);
                        
                        if (existing) {
                            if (mode === 'skip') {
                                result.zones_skipped++;
                            } else if (mode === 'replace') {
                                await this.deleteZone(zoneData.name);
                                await this.createZone(zoneData);
                                result.zones_updated++;
                            } else { // merge
                                await this.updateZone(zoneData.name, zoneData);
                                result.zones_updated++;
                            }
                        } else {
                            await this.createZone(zoneData);
                            result.zones_created++;
                        }
                        
                        result.records_added += zoneData.rrsets ? zoneData.rrsets.length : 0;
                    } catch (error) {
                        result.errors.push(`Zone ${zoneData.name}: ${error.message}`);
                    }
                } else {
                    // Dry run - just count what would happen
                    const existing = await this.getZone(zoneData.name).catch(() => null);
                    if (existing) {
                        if (mode === 'skip') {
                            result.zones_skipped++;
                        } else {
                            result.zones_updated++;
                        }
                    } else {
                        result.zones_created++;
                    }
                }
            }
        } catch (error) {
            result.status = 'error';
            result.errors.push(error.message);
        }
        
        return result;
    }

    /**
     * Preview import (always dry run)
     */
    async previewImport(data, format = 'json', mode = 'merge') {
        return this.importZones(data, format, mode, true);
    }
}