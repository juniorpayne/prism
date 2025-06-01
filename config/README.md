# Configuration Management

The Prism Host Client uses YAML configuration files for all settings.

## Configuration File

Copy `client.example.yaml` to `client.yaml` and modify as needed:

```bash
cp config/client.example.yaml config/client.yaml
```

## Configuration Sections

### Server Configuration
- `host`: Server hostname or IP address
- `port`: Server port number (1-65535)
- `timeout`: Connection timeout in seconds (must be positive)

### Heartbeat Configuration
- `interval`: Heartbeat interval in seconds (must be positive)

### Logging Configuration
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `file`: Log file path (relative or absolute)

## Example Usage

```python
from client.config_manager import ConfigManager

config_manager = ConfigManager()
config = config_manager.load_config('config/client.yaml')

server_config = config_manager.get_server_config(config)
print(f"Connecting to {server_config['host']}:{server_config['port']}")
```

## Validation

The configuration system automatically validates:
- Required fields presence
- Data types (string, integer)
- Value ranges (port numbers, positive values)
- Valid logging levels

Invalid configurations will raise `ConfigValidationError` with descriptive messages.