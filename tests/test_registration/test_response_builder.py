#!/usr/bin/env python3
"""
Tests for Response Builder (SCRUM-15)
Test-driven development for registration response message creation.
"""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch


class TestResponseBuilder(unittest.TestCase):
    """Test response builder functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.builder_config = {
            "response": {
                "include_server_info": True,
                "include_statistics": False,
                "message_format": "detailed",
            }
        }

    def test_response_builder_class_exists(self):
        """Test that ResponseBuilder class exists."""
        try:
            from server.response_builder import ResponseBuilder

            self.assertTrue(callable(ResponseBuilder))
        except ImportError:
            self.fail("ResponseBuilder should be importable from server.response_builder")

    def test_response_builder_initialization(self):
        """Test response builder initialization."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        self.assertIsNotNone(builder)
        self.assertTrue(hasattr(builder, "config"))

    def test_build_success_response_new_registration(self):
        """Test building success response for new registration."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="New host registered successfully",
        )

        self.assertEqual(response["version"], "1.0")
        self.assertEqual(response["type"], "response")
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result_type"], "new_registration")
        self.assertEqual(response["hostname"], "test-host")
        self.assertEqual(response["ip_address"], "192.168.1.100")
        self.assertEqual(response["message"], "New host registered successfully")
        self.assertIn("timestamp", response)

    def test_build_success_response_ip_change(self):
        """Test building success response for IP change."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="ip_change",
            hostname="test-host",
            ip_address="192.168.1.200",
            message="IP address updated",
            previous_ip="192.168.1.100",
        )

        self.assertEqual(response["result_type"], "ip_change")
        self.assertEqual(response["ip_address"], "192.168.1.200")
        self.assertEqual(response["previous_ip"], "192.168.1.100")

    def test_build_success_response_heartbeat(self):
        """Test building success response for heartbeat update."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="heartbeat_update",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Heartbeat updated",
        )

        self.assertEqual(response["result_type"], "heartbeat_update")
        self.assertEqual(response["message"], "Heartbeat updated")

    def test_build_success_response_reconnection(self):
        """Test building success response for host reconnection."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="reconnection",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Host reconnected",
            previous_status="offline",
        )

        self.assertEqual(response["result_type"], "reconnection")
        self.assertEqual(response["previous_status"], "offline")

    def test_build_error_response_validation_error(self):
        """Test building error response for validation errors."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_error_response(
            error_type="validation_error",
            message="Invalid hostname format",
            hostname="invalid..hostname",
        )

        self.assertEqual(response["version"], "1.0")
        self.assertEqual(response["type"], "response")
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_type"], "validation_error")
        self.assertEqual(response["message"], "Invalid hostname format")
        self.assertEqual(response["hostname"], "invalid..hostname")
        self.assertIn("timestamp", response)

    def test_build_error_response_database_error(self):
        """Test building error response for database errors."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_error_response(
            error_type="database_error", message="Database connection failed", hostname="test-host"
        )

        self.assertEqual(response["error_type"], "database_error")
        self.assertEqual(response["message"], "Database connection failed")

    def test_build_error_response_rate_limit(self):
        """Test building error response for rate limiting."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_error_response(
            error_type="rate_limit_exceeded",
            message="Too many registrations",
            hostname="test-host",
            retry_after=60,
        )

        self.assertEqual(response["error_type"], "rate_limit_exceeded")
        self.assertEqual(response["retry_after"], 60)

    def test_build_response_with_server_info(self):
        """Test building response with server information."""
        from server.response_builder import ResponseBuilder

        config = self.builder_config.copy()
        config["response"]["include_server_info"] = True

        builder = ResponseBuilder(config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        self.assertIn("server_info", response)
        self.assertIsInstance(response["server_info"], dict)

    def test_build_response_without_server_info(self):
        """Test building response without server information."""
        from server.response_builder import ResponseBuilder

        config = self.builder_config.copy()
        config["response"]["include_server_info"] = False

        builder = ResponseBuilder(config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        self.assertNotIn("server_info", response)

    def test_build_response_with_statistics(self):
        """Test building response with statistics."""
        from server.response_builder import ResponseBuilder

        config = self.builder_config.copy()
        config["response"]["include_statistics"] = True

        builder = ResponseBuilder(config)

        # Mock statistics
        mock_stats = {"total_hosts": 100, "online_hosts": 85, "registrations_today": 50}

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
            statistics=mock_stats,
        )

        self.assertIn("statistics", response)
        self.assertEqual(response["statistics"], mock_stats)

    def test_build_minimal_response(self):
        """Test building minimal response format."""
        from server.response_builder import ResponseBuilder

        config = self.builder_config.copy()
        config["response"]["message_format"] = "minimal"

        builder = ResponseBuilder(config)

        response = builder.build_success_response(
            result_type="heartbeat_update",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        # Minimal format should have fewer fields
        required_fields = {"version", "type", "status", "message", "timestamp"}
        response_fields = set(response.keys())

        self.assertTrue(required_fields.issubset(response_fields))

    def test_build_detailed_response(self):
        """Test building detailed response format."""
        from server.response_builder import ResponseBuilder

        config = self.builder_config.copy()
        config["response"]["message_format"] = "detailed"

        builder = ResponseBuilder(config)

        response = builder.build_success_response(
            result_type="ip_change",
            hostname="test-host",
            ip_address="192.168.1.200",
            message="IP changed",
            previous_ip="192.168.1.100",
        )

        # Detailed format should have more fields
        expected_fields = {
            "version",
            "type",
            "status",
            "result_type",
            "hostname",
            "ip_address",
            "previous_ip",
            "message",
            "timestamp",
        }
        response_fields = set(response.keys())

        self.assertTrue(expected_fields.issubset(response_fields))

    def test_response_json_serialization(self):
        """Test that responses can be JSON serialized."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        # Should be JSON serializable
        json_str = json.dumps(response)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["hostname"], "test-host")
        self.assertEqual(parsed["status"], "success")

    def test_response_timestamp_format(self):
        """Test response timestamp format."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        # Timestamp should be ISO format
        timestamp = response["timestamp"]
        self.assertIsInstance(timestamp, str)

        # Should be parseable as ISO datetime
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        self.assertIsInstance(parsed_time, datetime)

    def test_build_response_with_custom_fields(self):
        """Test building response with custom fields."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        custom_fields = {
            "request_id": "req-12345",
            "processing_time_ms": 15,
            "server_node": "node-1",
        }

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
            **custom_fields,
        )

        for field, value in custom_fields.items():
            self.assertEqual(response[field], value)

    def test_validate_response_structure(self):
        """Test response structure validation."""
        from server.response_builder import ResponseBuilder

        builder = ResponseBuilder(self.builder_config)

        response = builder.build_success_response(
            result_type="new_registration",
            hostname="test-host",
            ip_address="192.168.1.100",
            message="Success",
        )

        # Validate response has required fields
        is_valid = builder.validate_response(response)
        self.assertTrue(is_valid)

        # Test with invalid response
        invalid_response = {"invalid": "response"}
        is_valid = builder.validate_response(invalid_response)
        self.assertFalse(is_valid)


class TestResponseBuilderConfig(unittest.TestCase):
    """Test response builder configuration."""

    def test_response_builder_config_class_exists(self):
        """Test that ResponseBuilderConfig class exists."""
        try:
            from server.response_builder import ResponseBuilderConfig

            self.assertTrue(callable(ResponseBuilderConfig))
        except ImportError:
            self.fail("ResponseBuilderConfig should be importable from server.response_builder")

    def test_response_builder_config_initialization(self):
        """Test response builder config initialization."""
        from server.response_builder import ResponseBuilderConfig

        config_dict = {
            "response": {
                "include_server_info": True,
                "include_statistics": False,
                "message_format": "detailed",
            }
        }

        config = ResponseBuilderConfig(config_dict)

        self.assertTrue(config.include_server_info)
        self.assertFalse(config.include_statistics)
        self.assertEqual(config.message_format, "detailed")

    def test_response_builder_config_defaults(self):
        """Test response builder config default values."""
        from server.response_builder import ResponseBuilderConfig

        config = ResponseBuilderConfig({})

        # Should have reasonable defaults
        self.assertIsInstance(config.include_server_info, bool)
        self.assertIsInstance(config.include_statistics, bool)
        self.assertIsInstance(config.message_format, str)

    def test_response_builder_config_validation(self):
        """Test response builder config validation."""
        from server.response_builder import ResponseBuilderConfig, ResponseBuilderConfigError

        # Invalid message format
        invalid_config = {"response": {"message_format": "invalid_format"}}

        with self.assertRaises(ResponseBuilderConfigError):
            ResponseBuilderConfig(invalid_config)


class TestResponseTemplate(unittest.TestCase):
    """Test response template functionality."""

    def test_response_template_class_exists(self):
        """Test that ResponseTemplate class exists."""
        try:
            from server.response_builder import ResponseTemplate

            self.assertTrue(callable(ResponseTemplate))
        except ImportError:
            self.fail("ResponseTemplate should be importable from server.response_builder")

    def test_create_response_template(self):
        """Test creating response templates."""
        from server.response_builder import ResponseTemplate

        template = ResponseTemplate(
            template_type="success",
            required_fields=["hostname", "ip_address"],
            optional_fields=["previous_ip", "statistics"],
        )

        self.assertEqual(template.template_type, "success")
        self.assertEqual(len(template.required_fields), 2)
        self.assertEqual(len(template.optional_fields), 2)

    def test_apply_response_template(self):
        """Test applying response template."""
        from server.response_builder import ResponseTemplate

        template = ResponseTemplate(
            template_type="success",
            required_fields=["hostname", "ip_address"],
            optional_fields=["previous_ip"],
        )

        data = {
            "hostname": "test-host",
            "ip_address": "192.168.1.100",
            "previous_ip": "192.168.1.50",
        }

        response = template.apply(data)

        self.assertIn("hostname", response)
        self.assertIn("ip_address", response)
        self.assertIn("previous_ip", response)

    def test_response_template_validation(self):
        """Test response template validation."""
        from server.response_builder import ResponseTemplate

        template = ResponseTemplate(
            template_type="success", required_fields=["hostname", "ip_address"], optional_fields=[]
        )

        # Valid data
        valid_data = {"hostname": "test-host", "ip_address": "192.168.1.100"}

        is_valid = template.validate(valid_data)
        self.assertTrue(is_valid)

        # Invalid data (missing required field)
        invalid_data = {
            "hostname": "test-host"
            # Missing ip_address
        }

        is_valid = template.validate(invalid_data)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
