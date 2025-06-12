# Contribution Guidelines

## Overview

Thank you for considering contributing to Prism DNS! This guide explains our development process, coding standards, and how to submit contributions.

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, discrimination, or hate speech
- Personal attacks or trolling
- Publishing private information
- Inappropriate sexual content
- Other unprofessional conduct

## Getting Started

### 1. Find an Issue

```bash
# Good first issues for newcomers
https://github.com/yourorg/prism-dns/labels/good%20first%20issue

# Help wanted
https://github.com/yourorg/prism-dns/labels/help%20wanted

# Or create a new issue
https://github.com/yourorg/prism-dns/issues/new
```

### 2. Fork and Clone

```bash
# Fork via GitHub UI, then:
git clone git@github.com:yourusername/prism-dns.git
cd prism-dns

# Add upstream remote
git remote add upstream git@github.com:yourorg/prism-dns.git

# Verify remotes
git remote -v
```

### 3. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bugs
git checkout -b fix/issue-description
```

## Development Process

### 1. Make Changes

Follow these guidelines:
- Write clean, readable code
- Add tests for new functionality
- Update documentation
- Follow existing patterns

### 2. Test Your Changes

```bash
# Run tests locally
pytest

# Check code style
black --check .
flake8 .

# Run type checking
mypy server/

# Test in Docker
docker-compose up --build
```

### 3. Commit Your Changes

#### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Test additions or changes
- **chore**: Build process or auxiliary tool changes

#### Examples

```bash
# Feature
git commit -m "feat(api): Add batch host registration endpoint

- Support registering multiple hosts in one request
- Add validation for batch size limits
- Include transaction support for atomicity

Closes #123"

# Bug fix
git commit -m "fix(dns): Resolve timeout on zone transfers

Zone transfers were timing out due to incorrect socket timeout.
Increased timeout from 5s to 30s for large zones.

Fixes #456"

# Documentation
git commit -m "docs(api): Update REST API documentation

- Add examples for new endpoints
- Fix typos in authentication section
- Add rate limiting information"
```

### 4. Push Changes

```bash
# Push to your fork
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Go to GitHub and create PR from your branch
2. Fill out the PR template completely
3. Link related issues
4. Request reviews from maintainers

## Pull Request Guidelines

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests covering my changes
- [ ] All new and existing tests pass

## Related Issues
Closes #(issue number)

## Screenshots (if applicable)
```

### PR Best Practices

1. **Keep PRs Small**
   - Single feature or fix per PR
   - Easier to review and merge
   - Less chance of conflicts

2. **Write Good Descriptions**
   - Explain what and why
   - Include examples
   - Reference issues

3. **Respond to Feedback**
   - Address all comments
   - Ask questions if unclear
   - Update PR based on feedback

## Code Standards

### Python Style Guide

We follow PEP 8 with some modifications:

```python
# Good: Clear, descriptive names
def calculate_dns_response_time(query: DNSQuery) -> float:
    """Calculate response time for DNS query."""
    start_time = time.time()
    response = await execute_query(query)
    return time.time() - start_time

# Bad: Unclear names, no type hints
def calc(q):
    t = time.time()
    r = execute(q)
    return time.time() - t
```

### Import Organization

```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import aiohttp
import pytest
from sqlalchemy import Column, Integer, String

# Local imports
from server.config import Config
from server.models import Host
from server.utils import validate_hostname
```

### Function Documentation

```python
def process_registration(
    hostname: str,
    ip_address: str,
    metadata: Optional[Dict[str, Any]] = None
) -> RegistrationResult:
    """
    Process a new host registration.
    
    Args:
        hostname: The hostname to register
        ip_address: The IP address of the host
        metadata: Optional metadata dictionary
        
    Returns:
        RegistrationResult containing status and details
        
    Raises:
        ValidationError: If hostname or IP is invalid
        DatabaseError: If database operation fails
        
    Example:
        >>> result = process_registration("web-01", "192.168.1.100")
        >>> print(result.status)
        'success'
    """
    # Implementation
```

### Error Handling

```python
# Good: Specific error handling
try:
    result = await dns_client.create_record(hostname, ip)
except DNSConnectionError as e:
    logger.error(f"DNS connection failed: {e}")
    # Retry or fallback logic
except DNSValidationError as e:
    logger.warning(f"Invalid DNS record: {e}")
    return ErrorResponse(400, str(e))
except Exception as e:
    logger.exception("Unexpected error in DNS operation")
    raise

# Bad: Catch-all with no handling
try:
    result = dns_client.create_record(hostname, ip)
except:
    pass
```

### Testing Standards

```python
# Good: Descriptive test with proper setup
class TestHostRegistration:
    """Test host registration functionality."""
    
    @pytest.fixture
    def mock_dns_client(self):
        """Provide mock DNS client."""
        client = Mock(spec=DNSClient)
        client.create_record.return_value = {"status": "success"}
        return client
    
    async def test_successful_registration(self, mock_dns_client):
        """Test that valid registration succeeds."""
        # Arrange
        hostname = "test-host"
        ip_address = "192.168.1.100"
        
        # Act
        result = await register_host(hostname, ip_address, mock_dns_client)
        
        # Assert
        assert result.status == "success"
        mock_dns_client.create_record.assert_called_once_with(hostname, ip_address)
    
    async def test_registration_with_invalid_hostname(self):
        """Test that invalid hostname is rejected."""
        # Arrange
        invalid_hostname = "host with spaces"
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await register_host(invalid_hostname, "192.168.1.100")
        
        assert "Invalid hostname format" in str(exc_info.value)
```

## Documentation Standards

### Code Comments

```python
# Good: Explains why, not what
# Use exponential backoff to avoid overwhelming the server
# during temporary failures
retry_delay = min(base_delay * (2 ** attempt), max_delay)

# Bad: Redundant comment
# Increment counter by 1
counter += 1
```

### API Documentation

```python
@app.route('/api/hosts/<hostname>', methods=['GET'])
async def get_host(hostname: str):
    """
    Get host information by hostname.
    
    **Example Request:**
    ```
    GET /api/hosts/web-01
    Accept: application/json
    Authorization: Bearer <token>
    ```
    
    **Example Response:**
    ```json
    {
        "hostname": "web-01",
        "ip_address": "192.168.1.100",
        "status": "online",
        "last_seen": "2024-01-15T10:30:00Z"
    }
    ```
    
    **Error Responses:**
    - 404: Host not found
    - 401: Unauthorized
    - 500: Internal server error
    """
    # Implementation
```

## Review Process

### For Contributors

1. **Self Review**
   - Check diff carefully
   - Run tests locally
   - Verify documentation

2. **Address Feedback**
   - Respond to all comments
   - Make requested changes
   - Re-request review

3. **Be Patient**
   - Reviews take time
   - Ping if no response in 3 days
   - Be respectful of reviewer time

### For Reviewers

1. **Review Checklist**
   - [ ] Code follows style guide
   - [ ] Tests are adequate
   - [ ] Documentation updated
   - [ ] No security issues
   - [ ] Performance acceptable

2. **Provide Constructive Feedback**
   ```markdown
   # Good feedback
   "Consider using `asyncio.gather()` here for concurrent execution.
   This would improve performance when handling multiple hosts.
   See: [link to example]"
   
   # Less helpful
   "This is wrong."
   ```

3. **Approve or Request Changes**
   - Approve: Ready to merge
   - Comment: Minor suggestions
   - Request changes: Must fix issues

## Release Process

### Version Numbering

We use Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped
- [ ] Release notes drafted
- [ ] Security scan completed

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **Slack**: `#prism-dns` for discussions
- **Email**: dev@prism-dns.org for security issues

### Getting Help

1. **Check Documentation**
   - README.md
   - docs/ directory
   - API documentation

2. **Search Issues**
   - Existing issues
   - Closed issues
   - Pull requests

3. **Ask Questions**
   - GitHub Discussions
   - Slack channel
   - Stack Overflow tag

## Recognition

### Contributors

We maintain a CONTRIBUTORS.md file recognizing all contributors:
- Code contributions
- Documentation improvements
- Bug reports
- Feature suggestions
- Community support

### Becoming a Maintainer

Active contributors may be invited to become maintainers:
- Consistent quality contributions
- Helpful in reviews and discussions
- Understanding of project goals
- Commitment to project values

## Legal

### License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

### Developer Certificate of Origin

By making a contribution, you certify that:
1. The contribution was created by you
2. You have the right to submit it under the license
3. You understand it will be public and may be redistributed

---

*Thank you for contributing to Prism DNS! Your efforts help make this project better for everyone.*