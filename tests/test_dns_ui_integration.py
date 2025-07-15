#!/usr/bin/env python3
"""
DNS UI Component Integration Tests (SCRUM-124)
Tests integration between frontend DNS components and the service adapter
"""

import json
import os
from pathlib import Path

import pytest


class TestDNSUIIntegration:
    """Test DNS UI component integration with service adapter."""

    def test_dns_service_adapter_files_structure(self):
        """Test that all DNS service adapter files are properly structured."""
        web_dir = Path("/app/web")

        required_files = [
            "js/dns-service-adapter.js",
            "js/dns-adapter-config.js",
            "js/dns-mock-data-final.js",
            "test-dns-adapter.html",
        ]

        for file_path in required_files:
            full_path = web_dir / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

            # Check file is not empty
            assert full_path.stat().st_size > 0, f"File is empty: {file_path}"

    def test_dns_components_adapter_integration(self):
        """Test that DNS components properly integrate with the service adapter."""

        # Test component file structure
        component_files = [
            "js/dns-zones.js",
            "js/dns-zone-detail.js",
            "js/dns-records-v2.js",
            "js/dns-import-modal.js",
            "js/dns-zone-settings.js",
            "js/dns-subdomain-manager.js",
        ]

        web_dir = Path("/app/web")

        for file_path in component_files:
            full_path = web_dir / file_path
            assert full_path.exists(), f"Component file missing: {file_path}"

            # Read file content and check for adapter usage
            content = full_path.read_text()

            # Should not use mockService directly anymore
            assert (
                "new DNSMockDataService()" not in content
            ), f"{file_path} still creates mock service directly"

            # Should use service adapter
            adapter_patterns = ["DNSServiceFactory.getAdapter()", "this.dnsService", "dnsService"]

            has_adapter_usage = any(pattern in content for pattern in adapter_patterns)
            assert has_adapter_usage, f"{file_path} doesn't use service adapter"

    def test_html_script_loading_order(self):
        """Test that HTML loads scripts in correct order for dependencies."""

        index_html = Path("/app/web/index.html")
        assert index_html.exists(), "index.html not found"

        content = index_html.read_text()

        # Check that adapter files are loaded before components
        adapter_script_pos = content.find("dns-service-adapter.js")
        config_script_pos = content.find("dns-adapter-config.js")
        zones_script_pos = content.find("dns-zones.js")

        assert adapter_script_pos > 0, "dns-service-adapter.js not loaded"
        assert config_script_pos > 0, "dns-adapter-config.js not loaded"
        assert zones_script_pos > 0, "dns-zones.js not loaded"

        # Adapter scripts should be loaded before component scripts
        assert (
            adapter_script_pos < zones_script_pos
        ), "Service adapter should be loaded before components"
        assert (
            config_script_pos < zones_script_pos
        ), "Adapter config should be loaded before components"

    def test_dns_mock_data_adapter_compatibility(self):
        """Test that mock data service has adapter-compatible methods."""

        mock_data_file = Path("/app/web/js/dns-mock-data-final.js")
        assert mock_data_file.exists(), "dns-mock-data-final.js not found"

        content = mock_data_file.read_text()

        # Check for adapter-compatible methods
        required_methods = [
            "async getZones(",
            "async getZone(",
            "async createZone(",
            "async updateZone(",
            "async deleteZone(",
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
            assert method in content, f"Mock service missing adapter-compatible method: {method}"

    def test_service_adapter_class_structure(self):
        """Test service adapter class has all required methods and properties."""

        adapter_file = Path("/app/web/js/dns-service-adapter.js")
        assert adapter_file.exists(), "dns-service-adapter.js not found"

        content = adapter_file.read_text()

        # Check for main classes
        assert "class DNSServiceAdapter" in content
        assert "class DNSRealService" in content
        assert "class DNSServiceFactory" in content

        # Check for required methods in DNSServiceAdapter
        adapter_methods = [
            "selectService(",
            "executeOperation(",
            "getZones(",
            "getZone(",
            "createZone(",
            "updateZone(",
            "deleteZone(",
            "getRecords(",
            "getRecord(",
            "createRecord(",
            "updateRecord(",
            "deleteRecord(",
            "searchZones(",
            "searchRecords(",
            "filterZones(",
            "exportZones(",
            "importZones(",
            "compareServices(",
            "getPerformanceMetrics(",
            "getServiceHealth(",
            "checkServiceHealth(",
            "startHealthChecks(",
            "stopHealthChecks(",
        ]

        for method in adapter_methods:
            assert method in content, f"Service adapter missing method: {method}"

        # Check for factory pattern
        assert "static getAdapter(" in content
        assert "static reset(" in content
        assert "static updateConfig(" in content

    def test_adapter_configuration_structure(self):
        """Test adapter configuration has proper structure."""

        config_file = Path("/app/web/js/dns-adapter-config.js")
        assert config_file.exists(), "dns-adapter-config.js not found"

        content = config_file.read_text()

        # Check for main classes
        assert "class DNSAdapterConfig" in content
        assert "class DNSMigrationUI" in content

        # Check for required configuration methods
        config_methods = [
            "loadConfig(",
            "saveConfig(",
            "getConfig(",
            "updateConfig(",
            "setFeatureFlag(",
            "enableCategory(",
            "disableCategory(",
            "enableAllRealService(",
            "disableAllRealService(",
            "getMigrationProgress(",
            "shouldUseRealServiceForUser(",
            "hashCode(",
        ]

        for method in config_methods:
            assert method in content, f"Config class missing method: {method}"

        # Check for feature flag structure
        assert "featureFlags: {" in content
        assert "zones: {" in content
        assert "records: {" in content
        assert "abTesting: {" in content

    def test_test_page_functionality(self):
        """Test that the DNS adapter test page has all required functionality."""

        test_page = Path("/app/web/test-dns-adapter.html")
        assert test_page.exists(), "test-dns-adapter.html not found"

        content = test_page.read_text()

        # Check for required scripts
        assert "dns-service-adapter.js" in content
        assert "dns-adapter-config.js" in content
        assert "dns-mock-data-final.js" in content

        # Check for test functions
        test_functions = [
            "testGetZones(",
            "testGetZone(",
            "testCreateZone(",
            "testUpdateZone(",
            "testDeleteZone(",
            "testGetRecords(",
            "testCreateRecord(",
            "testUpdateRecord(",
            "testDeleteRecord(",
            "testSearchZones(",
            "testSearchRecords(",
            "testServiceComparison(",
            "showFeatureFlags(",
            "updateConfiguration(",
            "updateABTesting(",
        ]

        for function in test_functions:
            assert function in content, f"Test page missing function: {function}"

    def test_component_loading_state_management(self):
        """Test that components have proper loading state management."""

        components_with_loading = [
            "js/dns-zones.js",
            "js/dns-zone-detail.js",
            "js/dns-records-v2.js",
        ]

        web_dir = Path("/app/web")

        for file_path in components_with_loading:
            full_path = web_dir / file_path
            content = full_path.read_text()

            # Check for loading state methods
            loading_patterns = ["setLoadingState(", "loadingStates", "isLoading"]

            has_loading_management = any(pattern in content for pattern in loading_patterns)
            assert has_loading_management, f"{file_path} missing loading state management"

    def test_error_handling_in_components(self):
        """Test that components have proper error handling."""

        component_files = ["js/dns-zones.js", "js/dns-zone-detail.js", "js/dns-records-v2.js"]

        web_dir = Path("/app/web")

        for file_path in component_files:
            full_path = web_dir / file_path
            content = full_path.read_text()

            # Check for error handling patterns
            error_patterns = ["try {", "catch (", "finally {", "error"]

            error_handling_count = sum(1 for pattern in error_patterns if pattern in content)
            assert error_handling_count >= 2, f"{file_path} has insufficient error handling"

    def test_global_exports_and_accessibility(self):
        """Test that components are properly exported and accessible globally."""

        export_tests = [
            (
                "js/dns-service-adapter.js",
                ["window.DNSServiceAdapter", "window.DNSRealService", "window.DNSServiceFactory"],
            ),
            ("js/dns-adapter-config.js", ["window.dnsAdapterConfig", "window.DNSMigrationUI"]),
            ("js/dns-zones.js", ["DNSZonesManager"]),
            ("js/dns-zone-detail.js", ["DNSZoneDetailManager"]),
            ("js/dns-records-v2.js", ["DNSRecordsManagerV2"]),
        ]

        web_dir = Path("/app/web")

        for file_path, expected_exports in export_tests:
            full_path = web_dir / file_path
            content = full_path.read_text()

            for export in expected_exports:
                assert export in content, f"{file_path} missing export: {export}"

    def test_powerdns_api_compatibility(self):
        """Test that components use PowerDNS-compatible data structures."""

        mock_data_file = Path("/app/web/js/dns-mock-data-final.js")
        content = mock_data_file.read_text()

        # Check for PowerDNS-compatible structure
        powerdns_fields = [
            "rrsets",
            "changetype",
            "kind",
            "serial",
            "nameservers",
            "api_rectify",
            "dnssec",
        ]

        for field in powerdns_fields:
            assert field in content, f"Mock data missing PowerDNS field: {field}"

        # Check for proper zone name format (ending with dot)
        assert "example.com.'" in content or '.": {' in content

        # Check for proper record structure
        assert "records: [" in content
        assert "content:" in content
        assert "disabled:" in content

    def test_feature_flag_implementation(self):
        """Test feature flag implementation for gradual rollout."""

        config_file = Path("/app/web/js/dns-adapter-config.js")
        content = config_file.read_text()

        # Check for granular feature flags
        expected_flags = [
            "zones: {",
            "list:",
            "get:",
            "create:",
            "update:",
            "delete:",
            "records: {",
            "search:",
            "import:",
            "export:",
        ]

        for flag in expected_flags:
            assert flag in content, f"Missing feature flag: {flag}"

    def test_migration_progress_tracking(self):
        """Test migration progress tracking functionality."""

        config_file = Path("/app/web/js/dns-adapter-config.js")
        content = config_file.read_text()

        # Check for migration progress methods
        migration_methods = [
            "getMigrationProgress(",
            "enableAllRealService(",
            "disableAllRealService(",
        ]

        for method in migration_methods:
            assert method in content, f"Missing migration method: {method}"

    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration in UI components."""

        adapter_file = Path("/app/web/js/dns-service-adapter.js")
        content = adapter_file.read_text()

        # Check for performance monitoring
        performance_features = [
            "performanceMetrics",
            "performance.now()",
            "getPerformanceMetrics(",
            "avgResponseTime",
            "errorRate",
        ]

        for feature in performance_features:
            assert feature in content, f"Missing performance monitoring feature: {feature}"

    def test_health_checking_implementation(self):
        """Test health checking implementation for services."""

        adapter_file = Path("/app/web/js/dns-service-adapter.js")
        content = adapter_file.read_text()

        # Check for health checking
        health_features = [
            "serviceHealth",
            "checkServiceHealth(",
            "startHealthChecks(",
            "stopHealthChecks(",
            "healthy:",
        ]

        for feature in health_features:
            assert feature in content, f"Missing health checking feature: {feature}"

    def test_ab_testing_functionality(self):
        """Test A/B testing functionality for gradual rollout."""

        config_file = Path("/app/web/js/dns-adapter-config.js")
        content = config_file.read_text()

        # Check for A/B testing features
        ab_testing_features = [
            "abTesting: {",
            "enabled:",
            "percentage:",
            "shouldUseRealServiceForUser(",
            "hashCode(",
        ]

        for feature in ab_testing_features:
            assert feature in content, f"Missing A/B testing feature: {feature}"

    def test_fallback_mechanism_implementation(self):
        """Test fallback mechanism from real service to mock service."""

        adapter_file = Path("/app/web/js/dns-service-adapter.js")
        content = adapter_file.read_text()

        # Check for fallback mechanisms
        fallback_features = ["fallbackToMock", "try {", "catch (", "attempting mock fallback"]

        for feature in fallback_features:
            assert feature in content, f"Missing fallback feature: {feature}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
