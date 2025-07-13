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
        return {
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
}