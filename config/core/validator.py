"""
Startup Validator

Comprehensive startup validation and "who am I" reporting for trading bots.
"""

import os
import platform
import socket
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .settings import CoreSettings
from .health import run_health_checks, format_health_report
from ..secrets import load_keypair


async def validate_startup(core: CoreSettings, bot_name: str = "unknown") -> Dict[str, Any]:
    """
    Comprehensive startup validation with detailed reporting.
    
    Args:
        core: Core settings to validate
        bot_name: Name of the bot for identification
        
    Returns:
        Validation results dictionary
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()
    
    logger.info("🚀 Starting comprehensive startup validation...")
    
    # System information
    system_info = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "timestamp": start_time.isoformat() + "Z"
    }
    
    # Bot identification
    bot_info = {
        "name": bot_name,
        "config_version": core.contract_version,
        "network": core.network,
        "environment": core.environment,
        "is_production": core.is_production(),
        "schema_checksum": core.get_schema_checksum()
    }
    
    # Health checks
    health_results = await run_health_checks(
        rpc_url=core.rpc.primary_url,
        swift_url=core.swift.base_url if core.swift.enabled else None
    )
    
    # Configuration validation
    config_validation = validate_configuration(core)
    
    # Environment validation  
    env_validation = validate_environment()
    
    # Overall validation status
    overall_valid = (
        health_results["healthy"] and
        config_validation["valid"] and
        env_validation["valid"]
    )
    
    validation_results = {
        "valid": overall_valid,
        "timestamp": start_time.isoformat() + "Z",
        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        "system": system_info,
        "bot": bot_info,
        "health": health_results,
        "config": config_validation,
        "environment": env_validation
    }
    
    # Generate and log report
    report = generate_startup_report(validation_results)
    logger.info("📋 STARTUP VALIDATION REPORT:")
    for line in report.split('\n'):
        logger.info(line)
    
    return validation_results


def validate_configuration(core: CoreSettings) -> Dict[str, Any]:
    """
    Validate core configuration settings.
    
    Args:
        core: Core settings to validate
        
    Returns:
        Configuration validation results
    """
    errors = []
    warnings = []
    
    # Check required settings
    if not core.rpc.primary_url:
        errors.append("RPC primary URL not configured")
    
    if not core.rpc.backup_urls:
        warnings.append("No RPC backup URLs configured")
    
    # Check timeouts are reasonable
    if core.rpc.timeout_seconds < 5:
        warnings.append(f"RPC timeout very low: {core.rpc.timeout_seconds}s")
    elif core.rpc.timeout_seconds > 120:
        warnings.append(f"RPC timeout very high: {core.rpc.timeout_seconds}s")
    
    # Check Swift configuration if enabled
    if core.swift.enabled:
        if not core.swift.base_url:
            errors.append("Swift enabled but base URL not configured")
        
        if core.swift.timeout_seconds > 30:
            warnings.append(f"Swift timeout very high: {core.swift.timeout_seconds}s")
    
    # Check logging configuration
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if core.logging.level not in valid_log_levels:
        errors.append(f"Invalid log level: {core.logging.level}")
    
    # Check kill switches
    active_kills = [name for name, value in core.kill_switches.model_dump().items() if value]
    if active_kills:
        warnings.append(f"Active kill switches: {', '.join(active_kills)}")
    
    # Check production vs development settings
    if core.is_production():
        if core.logging.level == "DEBUG":
            warnings.append("DEBUG logging enabled in production")
        
        if core.swift.enabled and "localhost" in core.swift.base_url:
            warnings.append("Swift pointing to localhost in production")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_issues": len(errors) + len(warnings)
    }


def validate_environment() -> Dict[str, Any]:
    """
    Validate environment setup and dependencies.
    
    Returns:
        Environment validation results
    """
    errors = []
    warnings = []
    environment_info = {}
    
    # Check critical environment variables
    critical_env_vars = ["NETWORK"]
    optional_env_vars = ["KEYPAIR_PATH", "TAKER_SECRET_KEY_BASE58"]
    
    for var in critical_env_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Critical environment variable not set: {var}")
        else:
            environment_info[var] = value
    
    for var in optional_env_vars:
        value = os.getenv(var)
        if value:
            environment_info[var] = "***SET***"  # Don't log sensitive values
        else:
            environment_info[var] = "NOT_SET"
    
    # Check wallet configuration
    try:
        keypair_info = load_keypair()
        environment_info["wallet_source"] = keypair_info.source
        environment_info["wallet_public_key"] = keypair_info.public_key
        
        if not keypair_info.permissions_ok:
            warnings.append("Wallet file has insecure permissions")
            
    except Exception as e:
        errors.append(f"Wallet validation failed: {e}")
    
    # Check Python packages (basic imports)
    required_packages = [
        ("aiohttp", "aiohttp"),
        ("yaml", "pyyaml"), 
        ("pydantic", "pydantic"),
        ("base58", "base58")
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        errors.append(f"Missing required packages: {', '.join(missing_packages)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "environment_vars": environment_info,
        "missing_packages": missing_packages,
        "total_issues": len(errors) + len(warnings)
    }


def generate_startup_report(validation_results: Dict[str, Any]) -> str:
    """
    Generate a comprehensive "who am I" startup report.
    
    Args:
        validation_results: Results from validate_startup
        
    Returns:
        Formatted startup report
    """
    lines = []
    
    # Header
    lines.append("🤖 BOT STARTUP REPORT")
    lines.append("=" * 80)
    
    # Bot identity
    bot = validation_results["bot"]
    lines.append(f"Bot Name: {bot['name']}")
    lines.append(f"Config Version: {bot['config_version']}")
    lines.append(f"Network: {bot['network']}")
    lines.append(f"Environment: {bot['environment']} {'🚨 PRODUCTION' if bot['is_production'] else '🧪 DEVELOPMENT'}")
    lines.append(f"Schema Checksum: {bot['schema_checksum']}")
    lines.append("")
    
    # System information
    system = validation_results["system"]
    lines.append("💻 SYSTEM INFORMATION")
    lines.append(f"Hostname: {system['hostname']}")
    lines.append(f"Platform: {system['platform']}")
    lines.append(f"Python: {system['python_version']}")
    lines.append(f"Architecture: {system['architecture']}")
    lines.append(f"Startup Time: {system['timestamp']}")
    lines.append("")
    
    # Environment details
    env = validation_results["environment"]
    lines.append("🌍 ENVIRONMENT")
    for var, value in env["environment_vars"].items():
        lines.append(f"{var}: {value}")
    lines.append("")
    
    # Health check summary
    health = validation_results["health"]
    status_icon = "✅" if health["healthy"] else "❌"
    lines.append(f"🏥 HEALTH CHECKS {status_icon}")
    lines.append(f"Total: {health['total_checks']}, Passed: {health['passed_checks']}")
    lines.append(f"Critical Failures: {health['critical_failures']}")
    lines.append(f"Warning Failures: {health['warning_failures']}")
    lines.append("")
    
    # Individual health checks
    for check in health["checks"]:
        check_icon = "✅" if check.passed else ("❌" if check.severity == "critical" else "⚠️")
        lines.append(f"  {check_icon} {check.name}: {check.message}")
    lines.append("")
    
    # Configuration validation
    config = validation_results["config"]
    config_icon = "✅" if config["valid"] else "❌"
    lines.append(f"⚙️  CONFIGURATION {config_icon}")
    
    if config["errors"]:
        lines.append("ERRORS:")
        for error in config["errors"]:
            lines.append(f"  ❌ {error}")
    
    if config["warnings"]:
        lines.append("WARNINGS:")
        for warning in config["warnings"]:
            lines.append(f"  ⚠️  {warning}")
    
    if not config["errors"] and not config["warnings"]:
        lines.append("  All configuration checks passed")
    lines.append("")
    
    # Environment validation
    env_icon = "✅" if env["valid"] else "❌"
    lines.append(f"🔧 ENVIRONMENT SETUP {env_icon}")
    
    if env["errors"]:
        lines.append("ERRORS:")
        for error in env["errors"]:
            lines.append(f"  ❌ {error}")
    
    if env["warnings"]:
        lines.append("WARNINGS:")
        for warning in env["warnings"]:
            lines.append(f"  ⚠️  {warning}")
    
    if not env["errors"] and not env["warnings"]:
        lines.append("  All environment checks passed")
    lines.append("")
    
    # Overall status
    overall_icon = "✅" if validation_results["valid"] else "❌"
    lines.append(f"🎯 OVERALL STATUS {overall_icon}")
    
    if validation_results["valid"]:
        lines.append("✅ All validations passed - Bot ready for trading!")
    else:
        lines.append("❌ Validation failures detected - Review issues above")
        
        # Count total issues
        total_errors = config["errors"] + env["errors"]
        total_warnings = config["warnings"] + env["warnings"]
        
        if total_errors:
            lines.append(f"   Critical issues: {len(total_errors)}")
        if total_warnings:
            lines.append(f"   Warnings: {len(total_warnings)}")
    
    lines.append("")
    lines.append(f"⏱️  Total validation time: {validation_results['duration_ms']:.1f}ms")
    lines.append("=" * 80)
    
    return "\n".join(lines)
