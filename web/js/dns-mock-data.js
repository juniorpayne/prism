/**
 * Mock Data Service for DNS Zone Management
 * Simulates PowerDNS API responses for frontend development
 */

class DNSMockDataService {
    constructor() {
        this.storageKey = 'prism-dns-zones';
        this.defaultTTL = 3600;
        this.initializeStorage();
    }

    /**
     * Initialize localStorage with sample data if empty
     */
    initializeStorage() {
        if (!localStorage.getItem(this.storageKey)) {
            const sampleZones = this.generateSampleZones();
            localStorage.setItem(this.storageKey, JSON.stringify(sampleZones));
        }
    }

    /**
     * Generate sample DNS zones with realistic data
     */
    generateSampleZones() {
        return {
            'example.com': {
                id: 'example.com',
                name: 'example.com',
                type: 'Master',
                status: 'Active',
                created: '2024-01-15T10:30:00Z',
                modified: '2024-12-20T14:45:00Z',
                soa: {
                    primaryNS: 'ns1.example.com',
                    email: 'admin@example.com',
                    serial: 2024122001,
                    refresh: 3600,
                    retry: 600,
                    expire: 86400,
                    ttl: 3600
                },
                nameservers: ['ns1.example.com', 'ns2.example.com'],
                records: [
                    { name: '@', type: 'A', value: '192.168.1.1', ttl: 3600 },
                    { name: 'www', type: 'A', value: '192.168.1.1', ttl: 3600 },
                    { name: '@', type: 'MX', value: 'mail.example.com', priority: 10, ttl: 3600 },
                    { name: 'mail', type: 'A', value: '192.168.1.2', ttl: 3600 },
                    { name: '@', type: 'TXT', value: 'v=spf1 mx ~all', ttl: 3600 }
                ]
            },
            'test-domain.org': {
                id: 'test-domain.org',
                name: 'test-domain.org',
                type: 'Master',
                status: 'Active',
                created: '2024-02-20T09:15:00Z',
                modified: '2024-11-30T16:20:00Z',
                soa: {
                    primaryNS: 'ns1.test-domain.org',
                    email: 'hostmaster@test-domain.org',
                    serial: 2024113001,
                    refresh: 7200,
                    retry: 900,
                    expire: 604800,
                    ttl: 3600
                },
                nameservers: ['ns1.test-domain.org', 'ns2.test-domain.org'],
                records: [
                    { name: '@', type: 'A', value: '10.0.0.1', ttl: 3600 },
                    { name: 'app', type: 'CNAME', value: 'test-domain.org', ttl: 3600 }
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
     * Get all zones
     */
    async getAllZones() {
        await this.simulateDelay();
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        return Object.values(zones);
    }

    /**
     * Get a specific zone by ID
     */
    async getZone(zoneId) {
        await this.simulateDelay();
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        const zone = zones[zoneId];
        
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
        
        if (zones[zoneData.name]) {
            throw new Error(`Zone ${zoneData.name} already exists`);
        }

        const newZone = {
            id: zoneData.name,
            name: zoneData.name,
            type: zoneData.type || 'Master',
            status: 'Active',
            created: new Date().toISOString(),
            modified: new Date().toISOString(),
            soa: {
                primaryNS: zoneData.primaryNS || `ns1.${zoneData.name}`,
                email: zoneData.email || `admin@${zoneData.name}`,
                serial: parseInt(new Date().toISOString().slice(0,10).replace(/-/g, '') + '01'),
                refresh: zoneData.refresh || 3600,
                retry: zoneData.retry || 600,
                expire: zoneData.expire || 86400,
                ttl: zoneData.ttl || this.defaultTTL
            },
            nameservers: zoneData.nameservers || [`ns1.${zoneData.name}`, `ns2.${zoneData.name}`],
            records: zoneData.records || []
        };

        zones[zoneData.name] = newZone;
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        
        return newZone;
    }

    /**
     * Update a zone
     */
    async updateZone(zoneId, updates) {
        await this.simulateDelay();
        
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        
        if (!zones[zoneId]) {
            throw new Error(`Zone ${zoneId} not found`);
        }

        zones[zoneId] = {
            ...zones[zoneId],
            ...updates,
            modified: new Date().toISOString()
        };
        
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        return zones[zoneId];
    }

    /**
     * Delete a zone
     */
    async deleteZone(zoneId) {
        await this.simulateDelay();
        
        const zones = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
        
        if (!zones[zoneId]) {
            throw new Error(`Zone ${zoneId} not found`);
        }

        delete zones[zoneId];
        localStorage.setItem(this.storageKey, JSON.stringify(zones));
        
        return { success: true, message: `Zone ${zoneId} deleted` };
    }

    /**
     * Add a record to a zone
     */
    async addRecord(zoneId, record) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        
        const newRecord = {
            ...record,
            ttl: record.ttl || this.defaultTTL,
            id: `${record.name}-${record.type}-${Date.now()}`
        };
        
        zone.records.push(newRecord);
        await this.updateZone(zoneId, { records: zone.records });
        
        return newRecord;
    }

    /**
     * Update a record in a zone
     */
    async updateRecord(zoneId, recordId, updates) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        const recordIndex = zone.records.findIndex(r => r.id === recordId);
        
        if (recordIndex === -1) {
            throw new Error(`Record ${recordId} not found in zone ${zoneId}`);
        }
        
        zone.records[recordIndex] = {
            ...zone.records[recordIndex],
            ...updates
        };
        
        await this.updateZone(zoneId, { records: zone.records });
        return zone.records[recordIndex];
    }

    /**
     * Delete a record from a zone
     */
    async deleteRecord(zoneId, recordId) {
        await this.simulateDelay();
        
        const zone = await this.getZone(zoneId);
        zone.records = zone.records.filter(r => r.id !== recordId);
        
        await this.updateZone(zoneId, { records: zone.records });
        return { success: true, message: `Record ${recordId} deleted` };
    }

    /**
     * Get statistics for dashboard
     */
    async getStats() {
        await this.simulateDelay();
        
        const zones = await this.getAllZones();
        const totalRecords = zones.reduce((sum, zone) => sum + zone.records.length, 0);
        
        return {
            totalZones: zones.length,
            activeZones: zones.filter(z => z.status === 'Active').length,
            totalRecords: totalRecords,
            recentChanges: zones.filter(z => {
                const modified = new Date(z.modified);
                const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
                return modified > dayAgo;
            }).length
        };
    }

    /**
     * Clear all data (useful for testing)
     */
    clearAllData() {
        localStorage.removeItem(this.storageKey);
        this.initializeStorage();
    }
}

// Export for use in other modules
window.DNSMockDataService = DNSMockDataService;