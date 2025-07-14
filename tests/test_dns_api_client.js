#!/usr/bin/env node
/**
 * Test DNS API Client Methods (SCRUM-121)
 * Unit tests for DNS methods in the frontend API client
 */

// Mock fetch for testing
global.fetch = jest.fn();
global.setTimeout = jest.fn((fn) => fn());
global.clearTimeout = jest.fn();

// Import the API client
const { PrismAPI, APIError } = require('../web/js/api.js');

describe('DNS API Client Methods', () => {
    let api;
    
    beforeEach(() => {
        api = new PrismAPI('/api');
        api.tokenManager = {
            getAccessToken: () => 'test-token',
            shouldRefreshToken: () => false,
            refreshAccessToken: jest.fn()
        };
        fetch.mockClear();
    });

    describe('Zone Management', () => {
        test('getZones - should fetch zones with pagination', async () => {
            const mockResponse = {
                zones: [{ name: 'example.com.', kind: 'Native' }],
                pagination: { page: 1, limit: 50, total: 1 }
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await api.getZones(1, 50, 'example');
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/zones?page=1&limit=50&search=example', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer test-token'
                },
                signal: expect.any(AbortSignal),
                timeout: 10000
            });
            
            expect(result).toEqual(mockResponse);
        });

        test('getZone - should fetch specific zone', async () => {
            const mockZone = { name: 'example.com.', kind: 'Native', rrsets: [] };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockZone
            });

            const result = await api.getZone('example.com.');
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/zones/example.com.', expect.any(Object));
            expect(result).toEqual(mockZone);
        });

        test('createZone - should create new zone', async () => {
            const zoneData = {
                name: 'test.com.',
                kind: 'Native',
                nameservers: ['ns1.test.com.', 'ns2.test.com.']
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ...zoneData, id: 'test.com.' })
            });

            const result = await api.createZone(zoneData);
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/zones', expect.objectContaining({
                method: 'POST',
                body: JSON.stringify(zoneData)
            }));
        });

        test('updateZone - should update zone', async () => {
            const updates = { kind: 'Master' };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ name: 'test.com.', ...updates })
            });

            await api.updateZone('test.com.', updates);
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/zones/test.com.', expect.objectContaining({
                method: 'PUT',
                body: JSON.stringify(updates)
            }));
        });

        test('deleteZone - should delete zone', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ deleted: true })
            });

            await api.deleteZone('test.com.');
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/zones/test.com.', expect.objectContaining({
                method: 'DELETE'
            }));
        });
    });

    describe('Record Management', () => {
        test('getRecords - should fetch records with filters', async () => {
            const mockResponse = {
                records: [{ name: 'www.example.com.', type: 'A', ttl: 300 }],
                pagination: { page: 1, limit: 50, total: 1 }
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await api.getRecords('example.com.', 1, 50, {
                recordType: 'A',
                name: 'www'
            });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/example.com./records?page=1&limit=50&record_type=A&name=www',
                expect.any(Object)
            );
            expect(result).toEqual(mockResponse);
        });

        test('getRecord - should fetch specific record', async () => {
            const mockRecord = {
                name: 'www.example.com.',
                type: 'A',
                ttl: 300,
                records: [{ content: '192.168.1.1' }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockRecord
            });

            const result = await api.getRecord('example.com.', 'www', 'A');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/example.com./records/www/A',
                expect.any(Object)
            );
            expect(result).toEqual(mockRecord);
        });

        test('createRecord - should create new record', async () => {
            const recordData = {
                name: 'www',
                type: 'A',
                ttl: 300,
                records: [{ content: '192.168.1.1' }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ...recordData, name: 'www.example.com.' })
            });

            await api.createRecord('example.com.', recordData);
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/example.com./records',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify(recordData)
                })
            );
        });

        test('updateRecord - should update record', async () => {
            const updates = {
                ttl: 600,
                records: [{ content: '192.168.1.2' }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ name: 'www.example.com.', type: 'A', ...updates })
            });

            await api.updateRecord('example.com.', 'www', 'A', updates);
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/example.com./records/www/A',
                expect.objectContaining({
                    method: 'PUT',
                    body: JSON.stringify(updates)
                })
            );
        });

        test('deleteRecord - should delete record', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ deleted: true })
            });

            await api.deleteRecord('example.com.', 'www', 'A');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/example.com./records/www/A',
                expect.objectContaining({
                    method: 'DELETE'
                })
            );
        });
    });

    describe('Search and Filter', () => {
        test('searchZones - should search zones', async () => {
            const mockResults = {
                query: 'example',
                total: 2,
                zones: [
                    { name: 'example.com.', kind: 'Native' },
                    { name: 'example.org.', kind: 'Native' }
                ]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResults
            });

            const result = await api.searchZones('example', {
                zoneType: 'Native',
                hierarchyLevel: 0,
                limit: 100
            });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/search?q=example&zone_type=Native&hierarchy_level=0&limit=100',
                expect.any(Object)
            );
            expect(result).toEqual(mockResults);
        });

        test('searchRecords - should search records', async () => {
            const mockResults = {
                query: 'www',
                total: 1,
                records: [{ name: 'www.example.com.', type: 'A', zone: 'example.com.' }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResults
            });

            const result = await api.searchRecords('www', {
                recordType: 'A',
                zone: 'example.com.',
                contentSearch: true
            });
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/records/search?q=www&record_type=A&zone=example.com.&content=true',
                expect.any(Object)
            );
            expect(result).toEqual(mockResults);
        });

        test('filterZones - should filter zones', async () => {
            const filters = {
                min_records: 5,
                max_records: 100,
                has_dnssec: true
            };
            
            const mockResults = {
                total: 1,
                zones: [{ name: 'secure.com.', dnssec: true }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResults
            });

            const result = await api.filterZones(filters, 'name', 'desc');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/zones/filter?sort_by=name&sort_order=desc',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify(filters)
                })
            );
            expect(result).toEqual(mockResults);
        });
    });

    describe('Import/Export', () => {
        test('exportZones - JSON format', async () => {
            const mockExport = {
                format: 'json',
                version: '1.0',
                zones: [{ name: 'example.com.' }]
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockExport
            });

            const result = await api.exportZones('json', ['example.com.'], true);
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/export/zones?format=json&include_dnssec=true&zones=example.com.',
                expect.any(Object)
            );
            expect(result).toEqual(mockExport);
        });

        test('exportZones - BIND format', async () => {
            const mockBlob = new Blob(['zone data'], { type: 'text/plain' });
            
            fetch.mockResolvedValueOnce({
                ok: true,
                blob: async () => mockBlob
            });

            const result = await api.exportZones('bind', null, false);
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/export/zones?format=bind&include_dnssec=false',
                expect.any(Object)
            );
            expect(result).toBeInstanceOf(Blob);
        });

        test('importZones - should import zones', async () => {
            const importData = JSON.stringify({
                zones: [{ name: 'imported.com.', kind: 'Native' }]
            });
            
            const mockResult = {
                status: 'success',
                zones_processed: 1,
                zones_created: 1
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResult
            });

            const result = await api.importZones(importData, 'json', 'merge', false);
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/import/zones',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({
                        data: importData,
                        format: 'json',
                        mode: 'merge',
                        dry_run: false
                    })
                })
            );
            expect(result).toEqual(mockResult);
        });

        test('previewImport - should preview import', async () => {
            const importData = 'zone data';
            
            const mockPreview = {
                status: 'preview',
                zones_processed: 1,
                changes: []
            };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockPreview
            });

            const result = await api.previewImport(importData, 'bind', 'replace');
            
            expect(fetch).toHaveBeenCalledWith(
                '/api/dns/import/preview',
                expect.objectContaining({
                    method: 'POST',
                    body: JSON.stringify({
                        data: importData,
                        format: 'bind',
                        mode: 'replace'
                    })
                })
            );
            expect(result).toEqual(mockPreview);
        });
    });

    describe('Error Handling', () => {
        test('should handle 404 errors', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found'
            });

            await expect(api.getZone('nonexistent.com.')).rejects.toThrow(APIError);
            await expect(api.getZone('nonexistent.com.')).rejects.toMatchObject({
                status: 404,
                message: expect.stringContaining('not found')
            });
        });

        test('should retry on server errors', async () => {
            fetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({ name: 'example.com.' })
                });

            const result = await api.getZone('example.com.');
            
            expect(fetch).toHaveBeenCalledTimes(3);
            expect(result).toEqual({ name: 'example.com.' });
        });

        test('should handle authentication errors', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: 'Unauthorized'
            });
            
            api.tokenManager.refreshAccessToken.mockResolvedValueOnce('new-token');
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ name: 'example.com.' })
            });

            await api.getZone('example.com.');
            
            expect(api.tokenManager.refreshAccessToken).toHaveBeenCalled();
            expect(fetch).toHaveBeenCalledTimes(2);
        });
    });

    describe('Utility Methods', () => {
        test('getDnsHealth - should check DNS service health', async () => {
            const mockHealth = { status: 'healthy', powerdns: 'connected' };
            
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockHealth
            });

            const result = await api.getDnsHealth();
            
            expect(fetch).toHaveBeenCalledWith('/api/dns/health', expect.any(Object));
            expect(result).toEqual(mockHealth);
        });
    });
});

// Export for Jest
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PrismAPI, APIError };
}