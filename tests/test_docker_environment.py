#!/usr/bin/env python3
"""
Tests for Docker Development Environment (SCRUM-12)
Test-driven development for Docker setup and functionality.
"""

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


class TestDockerEnvironment(unittest.TestCase):
    """Test Docker development environment setup and functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent
        self.dockerfile_path = self.project_root / "Dockerfile"
        self.compose_path = self.project_root / "docker-compose.yml"
        self.requirements_path = self.project_root / "server" / "requirements.txt"

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists in project root."""
        self.assertTrue(self.dockerfile_path.exists(), "Dockerfile should exist in project root")

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        self.assertTrue(
            self.compose_path.exists(), "docker-compose.yml should exist in project root"
        )

    def test_server_requirements_exists(self):
        """Test that server requirements.txt exists."""
        self.assertTrue(self.requirements_path.exists(), "server/requirements.txt should exist")

    def test_dockerfile_contains_python_base(self):
        """Test that Dockerfile uses Python 3.8+ base image."""
        if not self.dockerfile_path.exists():
            self.skipTest("Dockerfile not yet created")

        with open(self.dockerfile_path, "r") as f:
            content = f.read()

        self.assertIn("FROM python:", content, "Dockerfile should use Python base image")
        # Check for Python 3.8 or higher
        python_versions = ["3.8", "3.9", "3.10", "3.11", "3.12"]
        has_valid_python = any(version in content for version in python_versions)
        self.assertTrue(has_valid_python, "Dockerfile should use Python 3.8+")

    def test_dockerfile_installs_requirements(self):
        """Test that Dockerfile installs Python requirements."""
        if not self.dockerfile_path.exists():
            self.skipTest("Dockerfile not yet created")

        with open(self.dockerfile_path, "r") as f:
            content = f.read()

        self.assertIn("pip install", content, "Dockerfile should install requirements")
        self.assertIn("requirements.txt", content, "Dockerfile should reference requirements.txt")

    def test_dockerfile_exposes_ports(self):
        """Test that Dockerfile exposes required ports."""
        if not self.dockerfile_path.exists():
            self.skipTest("Dockerfile not yet created")

        with open(self.dockerfile_path, "r") as f:
            content = f.read()

        # Should expose TCP server port (8080) and API port (8081)
        self.assertIn("EXPOSE", content, "Dockerfile should expose ports")
        self.assertTrue(
            "8080" in content or "8081" in content, "Dockerfile should expose server ports"
        )

    def test_compose_defines_services(self):
        """Test that docker-compose defines required services."""
        if not self.compose_path.exists():
            self.skipTest("docker-compose.yml not yet created")

        import yaml

        with open(self.compose_path, "r") as f:
            compose_config = yaml.safe_load(f)

        self.assertIn("services", compose_config, "Compose should define services")
        services = compose_config["services"]

        # Should have at least a server service
        service_names = list(services.keys())
        self.assertTrue(
            any("server" in name for name in service_names),
            "Compose should define a server service",
        )

    def test_compose_has_port_mapping(self):
        """Test that docker-compose maps ports to host."""
        if not self.compose_path.exists():
            self.skipTest("docker-compose.yml not yet created")

        import yaml

        with open(self.compose_path, "r") as f:
            compose_config = yaml.safe_load(f)

        services = compose_config["services"]

        # At least one service should have port mapping
        has_ports = False
        for service_name, service_config in services.items():
            if "ports" in service_config:
                has_ports = True
                break

        self.assertTrue(has_ports, "At least one service should map ports")

    def test_compose_has_volume_mount(self):
        """Test that docker-compose mounts volumes for development."""
        if not self.compose_path.exists():
            self.skipTest("docker-compose.yml not yet created")

        import yaml

        with open(self.compose_path, "r") as f:
            compose_config = yaml.safe_load(f)

        services = compose_config["services"]

        # At least one service should have volume mounts for development
        has_volumes = False
        for service_name, service_config in services.items():
            if "volumes" in service_config:
                has_volumes = True
                break

        self.assertTrue(has_volumes, "Services should mount volumes for development")

    def test_development_script_exists(self):
        """Test that development helper script exists."""
        script_path = self.project_root / "scripts" / "docker-dev.sh"
        self.assertTrue(script_path.exists(), "Development helper script should exist")

    def test_development_script_executable(self):
        """Test that development script is executable."""
        script_path = self.project_root / "scripts" / "docker-dev.sh"
        if not script_path.exists():
            self.skipTest("Development script not yet created")

        # Check if file has execute permissions
        import stat

        file_stat = script_path.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IEXEC)
        self.assertTrue(is_executable, "Development script should be executable")

    def test_server_requirements_has_dependencies(self):
        """Test that server requirements includes necessary dependencies."""
        if not self.requirements_path.exists():
            self.skipTest("server/requirements.txt not yet created")

        with open(self.requirements_path, "r") as f:
            content = f.read().lower()

        # Should include FastAPI for REST API
        self.assertIn("fastapi", content, "Should include FastAPI")

        # Should include SQLAlchemy for database operations
        self.assertIn("sqlalchemy", content, "Should include SQLAlchemy")

        # Should include testing dependencies
        self.assertIn("pytest", content, "Should include pytest")

    def test_docker_ignore_exists(self):
        """Test that .dockerignore exists to optimize builds."""
        dockerignore_path = self.project_root / ".dockerignore"
        self.assertTrue(dockerignore_path.exists(), ".dockerignore should exist to optimize builds")

    def test_docker_ignore_excludes_unnecessary_files(self):
        """Test that .dockerignore excludes development files."""
        dockerignore_path = self.project_root / ".dockerignore"
        if not dockerignore_path.exists():
            self.skipTest(".dockerignore not yet created")

        with open(dockerignore_path, "r") as f:
            content = f.read()

        # Should exclude common development files
        exclusions = [".git", "__pycache__", "*.pyc", ".pytest_cache", "venv"]
        for exclusion in exclusions:
            self.assertIn(exclusion, content, f"Should exclude {exclusion}")


class TestDockerFunctionality(unittest.TestCase):
    """Integration tests for Docker functionality (requires Docker)."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(__file__).parent.parent

        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True, timeout=10)
            self.docker_available = True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.docker_available = False

    def test_docker_build_succeeds(self):
        """Test that Docker image builds successfully."""
        if not self.docker_available:
            self.skipTest("Docker not available for testing")

        dockerfile_path = self.project_root / "Dockerfile"
        if not dockerfile_path.exists():
            self.skipTest("Dockerfile not yet created")

        # Build Docker image
        result = subprocess.run(
            ["docker", "build", "-t", "prism-server-test", "."],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout for build
        )

        self.assertEqual(
            result.returncode, 0, f"Docker build should succeed. Error: {result.stderr}"
        )

    def test_compose_services_start(self):
        """Test that docker-compose services start successfully."""
        if not self.docker_available:
            self.skipTest("Docker not available for testing")

        compose_path = self.project_root / "docker-compose.yml"
        if not compose_path.exists():
            self.skipTest("docker-compose.yml not yet created")

        try:
            # Start services in detached mode
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            self.assertEqual(
                result.returncode, 0, f"docker compose up should succeed. Error: {result.stderr}"
            )

            # Give services time to start
            time.sleep(5)

            # Check service status
            status_result = subprocess.run(
                ["docker", "compose", "ps"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(status_result.returncode, 0, "Should be able to check service status")

        finally:
            # Cleanup - stop services
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=self.project_root,
                capture_output=True,
                timeout=60,
            )

    def test_development_script_works(self):
        """Test that development script executes without errors."""
        script_path = self.project_root / "scripts" / "docker-dev.sh"
        if not script_path.exists():
            self.skipTest("Development script not yet created")

        # Test script help or version command
        result = subprocess.run(
            [str(script_path), "--help"], capture_output=True, text=True, timeout=30
        )

        # Script should either succeed or fail gracefully
        self.assertIn(
            result.returncode, [0, 1, 2], "Development script should execute without crashing"
        )


if __name__ == "__main__":
    unittest.main()
