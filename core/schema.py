"""
Core Schema Validation - JSON Schema + Checksum protection for core settings.

This module provides schema validation and checksum protection to prevent
accidental changes to the core settings structure.
"""

from __future__ import annotations
import json
import hashlib
from typing import Dict, Any
from pathlib import Path
import logging

from core.settings import (
    CoreSettings, RpcSettings, SwiftSettings, JitoSettings,
    WalletSettings, FeatureFlags, Observability
)

logger = logging.getLogger(__name__)

# ============================================================================
# Schema Generation
# ============================================================================

def core_schema() -> Dict[str, Any]:
    """
    Generate JSON schema for core settings.

    This function creates a comprehensive JSON schema that validates
    the structure and types of core settings.

    Returns:
        Dict containing the JSON schema
    """
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "Core Settings Schema",
        "description": "Schema for validating core bot settings",
        "properties": {
            "network": {
                "type": "string",
                "enum": ["mainnet-beta", "devnet", "localnet"],
                "description": "Solana network to connect to"
            },
            "default_markets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Default markets available for trading"
            },
            "rpc": {
                "type": "object",
                "properties": {
                    "http": {"type": "string", "format": "uri"},
                    "websocket": {"type": "string", "format": "uri"},
                    "commitment": {
                        "type": "string",
                        "enum": ["processed", "confirmed", "finalized"]
                    }
                },
                "required": ["http", "websocket"]
            },
            "wallet": {
                "type": "object",
                "properties": {
                    "keypair_path": {"type": "string"},
                    "taker_authority": {"type": "string"}
                },
                "required": ["keypair_path"]
            },
            "swift": {
                "type": "object",
                "properties": {
                    "orders_base": {"type": "string", "format": "uri"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300}
                },
                "required": ["orders_base"]
            },
            "jito": {
                "type": "object",
                "properties": {
                    "enable": {"type": "boolean"},
                    "tip": {"type": "integer", "minimum": 0}
                }
            },
            "features": {
                "type": "object",
                "properties": {
                    "crash_v2": {"type": "boolean"},
                    "cxlrep_v2": {"type": "boolean"},
                    "obi": {"type": "boolean"}
                }
            },
            "observability": {
                "type": "object",
                "properties": {
                    "prom_port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    "log_level": {
                        "type": "string",
                        "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                    }
                }
            }
        },
        "required": ["network", "rpc", "wallet", "swift"]
    }

    return schema

def schema_checksum() -> str:
    """
    Generate checksum of the core schema.

    This checksum serves as a guard against accidental schema changes.
    If the schema changes, the checksum will change and tests will fail,
    alerting developers to review the change intentionally.

    Returns:
        SHA256 checksum of the schema
    """
    schema = core_schema()
    schema_str = json.dumps(schema, sort_keys=True, separators=(',', ':'))
    checksum = hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
    return checksum

# ============================================================================
# Schema Validation
# ============================================================================

def validate_against_schema(data: Dict[str, Any]) -> bool:
    """
    Validate configuration data against the core schema.

    Args:
        data: Configuration data to validate

    Returns:
        bool: True if valid, False otherwise

    Note:
        This is a basic validation. For production, consider using
        a full JSON Schema validator library like 'jsonschema'
    """
    try:
        # Basic validation without external dependencies
        return _validate_core_structure(data)
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False

def _validate_core_structure(data: Dict[str, Any]) -> bool:
    """
    Validate core structure without external JSON Schema library.

    Args:
        data: Configuration data to validate

    Returns:
        bool: True if structure is valid
    """
    # Check required top-level fields
    required_fields = ['network', 'rpc', 'wallet', 'swift']
    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return False

    # Validate network
    if data['network'] not in ['mainnet-beta', 'devnet', 'localnet']:
        logger.error(f"Invalid network: {data['network']}")
        return False

    # Validate RPC structure
    rpc = data.get('rpc', {})
    if not isinstance(rpc, dict) or 'http' not in rpc or 'websocket' not in rpc:
        logger.error("Invalid RPC configuration structure")
        return False

    # Validate wallet structure
    wallet = data.get('wallet', {})
    if not isinstance(wallet, dict) or 'keypair_path' not in wallet:
        logger.error("Invalid wallet configuration structure")
        return False

    # Validate Swift structure
    swift = data.get('swift', {})
    if not isinstance(swift, dict) or 'orders_base' not in swift:
        logger.error("Invalid Swift configuration structure")
        return False

    # Validate default_markets
    markets = data.get('default_markets', [])
    if not isinstance(markets, list):
        logger.error("default_markets must be a list")
        return False

    # Validate optional structures
    if 'jito' in data and not isinstance(data['jito'], dict):
        logger.error("jito configuration must be a dictionary")
        return False

    if 'features' in data and not isinstance(data['features'], dict):
        logger.error("features configuration must be a dictionary")
        return False

    if 'observability' in data and not isinstance(data['observability'], dict):
        logger.error("observability configuration must be a dictionary")
        return False

    return True

# ============================================================================
# Schema Export and Documentation
# ============================================================================

def export_schema_to_file(output_path: str) -> None:
    """
    Export the core schema to a JSON file for documentation and sharing.

    Args:
        output_path: Path to save the schema file
    """
    schema = core_schema()

    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2, sort_keys=True)

    logger.info(f"✅ Exported core schema to: {output_path}")

def export_schema_documentation(output_path: str) -> None:
    """
    Export human-readable schema documentation.

    Args:
        output_path: Path to save documentation
    """
    schema = core_schema()
    checksum = schema_checksum()

    docs = f"""# Core Settings Schema Documentation

## Overview
This document describes the JSON schema for core bot settings validation.

## Schema Checksum
**Current Checksum:** `{checksum}`

*This checksum is used in automated tests to detect accidental schema changes.*

## Required Fields

### Top Level
- `network` (string): Solana network (`mainnet-beta`, `devnet`, `localnet`)
- `rpc` (object): RPC configuration
- `wallet` (object): Wallet configuration
- `swift` (object): Swift integration settings

### RPC Configuration
- `http` (string): HTTP RPC endpoint URL
- `websocket` (string): WebSocket RPC endpoint URL
- `commitment` (string): Commitment level (`processed`, `confirmed`, `finalized`)

### Wallet Configuration
- `keypair_path` (string): Path to keypair file
- `taker_authority` (string, optional): Taker authority address

### Swift Configuration
- `orders_base` (string): Swift orders API base URL
- `timeout_seconds` (integer, optional): Request timeout (1-300 seconds)

## Optional Fields

### JIT Configuration
- `enable` (boolean): Enable JITO integration
- `tip` (integer): JITO tip amount in lamports

### Feature Flags
- `crash_v2` (boolean): Enable Crash v2 features
- `cxlrep_v2` (boolean): Enable Cancel/Replace v2 features
- `obi` (boolean): Enable Order Book Intelligence

### Observability
- `prom_port` (integer): Prometheus metrics port (1024-65535)
- `log_level` (string): Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)

### Default Markets
- `default_markets` (array): List of default market symbols

## Usage in Code

```python
from core.schema import validate_against_schema, schema_checksum

# Validate configuration
config = load_config_from_yaml()
if not validate_against_schema(config):
    raise ValueError("Invalid configuration")

# Check schema hasn't changed (in tests)
expected_checksum = "b9de1e2a3e..."  # Update when schema changes intentionally
assert schema_checksum() == expected_checksum
```

## Schema Versioning

When making intentional changes to the core settings structure:

1. Update this schema file
2. Update the checksum in tests
3. Update this documentation
4. Notify all team members of the breaking change

## Validation Rules

The schema enforces:
- Type safety for all configuration values
- Required vs optional field validation
- Enum validation for specific values
- URI format validation for URLs
- Range validation for numeric values

This ensures configuration consistency across all bots and environments.
"""

    with open(output_path, 'w') as f:
        f.write(docs)

    logger.info(f"✅ Exported schema documentation to: {output_path}")

# ============================================================================
# Utility Functions
# ============================================================================

def create_expected_checksum_file(output_path: str) -> None:
    """
    Create a file with the current schema checksum for use in tests.

    Args:
        output_path: Path to save the checksum file
    """
    checksum = schema_checksum()

    content = f'''"""
Expected schema checksum for core settings validation.

This file contains the expected checksum for the core settings schema.
Update this value when making intentional changes to the schema.

Generated: {checksum}
"""

EXPECTED_SCHEMA_CHECKSUM = "{checksum}"
'''

    with open(output_path, 'w') as f:
        f.write(content)

    logger.info(f"✅ Created expected checksum file: {output_path}")
    logger.info(f"   Checksum: {checksum}")

if __name__ == "__main__":
    # Export schema and documentation when run directly
    export_schema_to_file("docs/core_schema.json")
    export_schema_documentation("docs/core_schema.md")
    create_expected_checksum_file("tests/core/expected_checksum.py")
    print(f"Current schema checksum: {schema_checksum()}")
