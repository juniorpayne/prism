#!/usr/bin/env python3
"""
Test DNS Service Adapter Pattern (SCRUM-122)
Tests for DNS service adapter implementation
"""

import json

import pytest


class TestDNSServiceAdapter:
    """Test DNS service adapter pattern implementation."""

    def test_adapter_files_exist(self):
        """Test that all adapter files are created."""
        import os

        adapter_files = [
            "web/js/dns-service-adapter.js",
            "web/js/dns-adapter-config.js",
            "web/test-dns-adapter.html",
        ]

        for file_path in adapter_files:
            full_path = os.path.join("/app", file_path)
            assert os.path.exists(full_path), f"Missing file: {file_path}"

    def test_adapter_javascript_syntax(self):
        """Test JavaScript files have valid syntax."""
        import subprocess

        js_files = [
            "/app/web/js/dns-service-adapter.js",
            "/app/web/js/dns-adapter-config.js",
        ]

        for js_file in js_files:
            # Use node to check syntax
            result = subprocess.run(["node", "-c", js_file], capture_output=True, text=True)
            assert result.returncode == 0, f"JavaScript syntax error in {js_file}: {result.stderr}"

    def test_adapter_class_structure(self):
        """Test adapter class has required methods."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            content = f.read()

        # Check for DNSServiceAdapter class
        assert "class DNSServiceAdapter" in content
        assert "class DNSRealService" in content
        assert "class DNSServiceFactory" in content

        # Check for required methods
        required_methods = [
            "selectService",
            "executeOperation",
            "getZones",
            "getZone",
            "createZone",
            "updateZone",
            "deleteZone",
            "getRecords",
            "getRecord",
            "createRecord",
            "updateRecord",
            "deleteRecord",
            "searchZones",
            "searchRecords",
            "filterZones",
            "exportZones",
            "importZones",
            "compareServices",
        ]

        for method in required_methods:
            assert f"{method}(" in content, f"Missing method: {method}"

    def test_config_class_structure(self):
        """Test configuration class has required methods."""
        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            content = f.read()

        # Check for DNSAdapterConfig class
        assert "class DNSAdapterConfig" in content

        # Check for required methods
        required_methods = [
            "loadConfig",
            "saveConfig",
            "getConfig",
            "updateConfig",
            "setFeatureFlag",
            "enableCategory",
            "disableCategory",
            "enableAllRealService",
            "disableAllRealService",
            "getMigrationProgress",
        ]

        for method in required_methods:
            assert f"{method}(" in content, f"Missing method: {method}"

    def test_feature_flags_structure(self):
        """Test feature flags have correct structure."""
        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            content = f.read()

        # Check for feature flag categories
        assert "zones: {" in content
        assert "records: {" in content
        assert "search:" in content
        assert "import:" in content
        assert "export:" in content

        # Check for zone operations
        zone_operations = ["list", "get", "create", "update", "delete"]
        for op in zone_operations:
            assert f"{op}:" in content

    def test_mock_service_compatibility(self):
        """Test mock service has adapter-compatible methods."""
        with open("/app/web/js/dns-mock-data-final.js", "r") as f:
            content = f.read()

        # Check for adapter-compatible methods
        required_methods = [
            "async getZones(",
            "async getRecords(",
            "async getRecord(",
            "async createRecord(",
            "async updateRecord(",
            "async deleteRecord(",
            "async searchZones(",
            "async searchRecords(",
            "async filterZones(",
            "async exportZones(",
            "async importZones(",
            "async previewImport(",
        ]

        for method in required_methods:
            assert method in content, f"Missing adapter-compatible method: {method}"

    def test_service_factory_pattern(self):
        """Test service factory implementation."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            content = f.read()

        # Check factory pattern implementation
        assert "static getAdapter(" in content
        assert "static reset(" in content
        assert "static updateConfig(" in content
        assert "static instance = null" in content

    def test_performance_monitoring(self):
        """Test performance monitoring implementation."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            content = f.read()

        # Check performance tracking
        assert "performanceMetrics" in content
        assert "performance.now()" in content
        assert "getPerformanceMetrics(" in content

    def test_health_checking(self):
        """Test health checking implementation."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            content = f.read()

        # Check health checking
        assert "serviceHealth" in content
        assert "checkServiceHealth(" in content
        assert "startHealthChecks(" in content
        assert "stopHealthChecks(" in content

    def test_error_handling_and_fallback(self):
        """Test error handling and fallback mechanisms."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            content = f.read()

        # Check error handling
        assert "try {" in content
        assert "catch (error)" in content
        assert "fallbackToMock" in content
        assert "attempting mock fallback" in content

    def test_migration_utilities(self):
        """Test migration utility methods."""
        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            content = f.read()

        # Check migration utilities
        assert "getMigrationProgress(" in content
        assert "shouldUseRealServiceForUser(" in content
        assert "class DNSMigrationUI" in content

    def test_test_page_structure(self):
        """Test the test page has required elements."""
        with open("/app/web/test-dns-adapter.html", "r") as f:
            content = f.read()

        # Check for required scripts
        assert "dns-service-adapter.js" in content
        assert "dns-adapter-config.js" in content
        assert "dns-mock-data-final.js" in content

        # Check for test functions
        test_functions = [
            "testGetZones",
            "testCreateZone",
            "testSearchZones",
            "testServiceComparison",
            "showFeatureFlags",
            "updateConfiguration",
        ]

        for func in test_functions:
            assert f"{func}(" in content, f"Missing test function: {func}"

    def test_configuration_persistence(self):
        """Test configuration uses localStorage."""
        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            content = f.read()

        # Check localStorage usage
        assert "localStorage.getItem" in content
        assert "localStorage.setItem" in content
        assert "prism-dns-adapter-config" in content

    def test_ab_testing_implementation(self):
        """Test A/B testing functionality."""
        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            content = f.read()

        # Check A/B testing
        assert "abTesting: {" in content
        assert "shouldUseRealServiceForUser(" in content
        assert "hashCode(" in content

    def test_exports_and_globals(self):
        """Test proper exports and global assignments."""
        with open("/app/web/js/dns-service-adapter.js", "r") as f:
            adapter_content = f.read()

        with open("/app/web/js/dns-adapter-config.js", "r") as f:
            config_content = f.read()

        # Check window assignments
        assert "window.DNSServiceAdapter" in adapter_content
        assert "window.DNSRealService" in adapter_content
        assert "window.DNSServiceFactory" in adapter_content
        assert "window.dnsAdapterConfig" in config_content
        assert "window.DNSMigrationUI" in config_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
