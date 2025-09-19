"""
Configuration Manager CLI

Operational CLI tool for configuration management with report, health, print, diff, and reload commands.
"""

import sys
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .core import (
    get_core, reload_if_changed, get_generation, get_cache_info,
    run_health_checks, format_health_report, validate_startup,
    write_snapshot, get_provenance, compare_config_files, format_diff_report
)
from .profiles import get_bot_profile, ProfileManager
from .secrets import load_keypair, validate_keypair_file


def setup_logging(level: str = "INFO") -> None:
    """Setup logging for CLI"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def cmd_report(args) -> int:
    """Generate comprehensive configuration report"""
    try:
        print("🔍 GENERATING CONFIGURATION REPORT")
        print("=" * 60)
        
        # Load core configuration
        core = get_core(args.config_dir)
        
        # Run startup validation
        validation_results = await validate_startup(core, "CLI Report")
        
        # Print validation report (already formatted)
        print()
        
        # Profile information
        if args.bot_type:
            print("\n📋 BOT PROFILE INFORMATION")
            print("-" * 40)
            try:
                profile = get_bot_profile(args.bot_type, args.profile, args.config_dir)
                summary = profile.to_summary()
                
                for key, value in summary.items():
                    print(f"{key}: {value}")
                    
            except Exception as e:
                print(f"❌ Failed to load profile: {e}")
        
        # Cache information
        print("\n💾 CACHE INFORMATION")
        print("-" * 40)
        cache_info = get_cache_info()
        for key, value in cache_info.items():
            print(f"{key}: {value}")
        
        return 0 if validation_results["valid"] else 1
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return 1


async def cmd_health(args) -> int:
    """Run health checks"""
    try:
        print("🏥 RUNNING HEALTH CHECKS")
        print("=" * 60)
        
        # Load core configuration for health check parameters
        core = get_core(args.config_dir)
        
        # Run health checks
        health_results = await run_health_checks(
            rpc_url=core.rpc.primary_url,
            swift_url=core.swift.base_url if core.swift.enabled else None,
            wallet_path=args.wallet_path,
            mock_mode=args.mock
        )
        
        # Format and print report
        report = format_health_report(health_results)
        print(report)
        
        # Return appropriate exit code
        return 0 if health_results["should_proceed"] else 1
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1


def cmd_print(args) -> int:
    """Print configuration in various formats"""
    try:
        print("📄 CONFIGURATION CONTENT")
        print("=" * 60)
        
        # Load core configuration
        core = get_core(args.config_dir)
        
        if args.format == "json":
            # JSON format
            config_dict = core.model_dump()
            print(json.dumps(config_dict, indent=2, sort_keys=True))
            
        elif args.format == "summary":
            # Summary format
            print(f"Contract Version: {core.contract_version}")
            print(f"Schema Checksum: {core.get_schema_checksum()}")
            print(f"Network: {core.network}")
            print(f"Environment: {core.environment}")
            print(f"Config Source: {core.config_source}")
            print(f"Loaded At: {core.loaded_at}")
            print()
            
            # Feature flags
            print("Feature Flags:")
            for flag, enabled in core.feature_flags.model_dump().items():
                status = "✅" if enabled else "❌"
                print(f"  {status} {flag}")
            print()
            
            # Kill switches
            print("Kill Switches:")
            active_kills = []
            for switch, active in core.kill_switches.model_dump().items():
                if active:
                    active_kills.append(switch)
                    print(f"  🚨 {switch}: ACTIVE")
            
            if not active_kills:
                print("  ✅ No active kill switches")
            print()
            
            # Markets
            print(f"Default Markets ({len(core.default_markets.primary_markets)}):")
            for market in core.default_markets.primary_markets:
                print(f"  • {market}")
                
        elif args.format == "yaml":
            # YAML-like format
            import yaml
            config_dict = core.model_dump()
            print(yaml.dump(config_dict, default_flow_style=False, sort_keys=True))
            
        else:
            print(f"❌ Unknown format: {args.format}")
            return 1
        
        # Profile information if requested
        if args.bot_type:
            print(f"\n🤖 {args.bot_type.upper()} PROFILE")
            print("-" * 40)
            try:
                profile = get_bot_profile(args.bot_type, args.profile, args.config_dir)
                
                if args.format == "json":
                    print(json.dumps(profile.model_dump(), indent=2, sort_keys=True))
                else:
                    summary = profile.to_summary()
                    for key, value in summary.items():
                        print(f"{key}: {value}")
                        
            except Exception as e:
                print(f"❌ Failed to load profile: {e}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Print failed: {e}")
        return 1


def cmd_diff(args) -> int:
    """Compare two configuration files"""
    try:
        print("📊 CONFIGURATION DIFF")
        print("=" * 60)
        
        from_file = Path(args.from_file)
        to_file = Path(args.to_file)
        
        if not from_file.exists():
            print(f"❌ Source file not found: {from_file}")
            return 1
            
        if not to_file.exists():
            print(f"❌ Target file not found: {to_file}")
            return 1
        
        # Compare configurations
        diff_result = compare_config_files(from_file, to_file)
        
        # Format and print report
        report = format_diff_report(diff_result)
        print(report)
        
        # Save diff if requested
        if args.save:
            from .core.diff import persist_diff
            saved_path = persist_diff(diff_result)
            print(f"\n💾 Diff saved to: {saved_path}")
        
        return 0 if not diff_result["has_changes"] else 1
        
    except Exception as e:
        print(f"❌ Diff failed: {e}")
        return 1


def cmd_snapshot(args) -> int:
    """Create configuration snapshot"""
    try:
        print("📸 CREATING CONFIGURATION SNAPSHOT")
        print("=" * 60)
        
        # Load core configuration
        core = get_core(args.config_dir)
        
        # Create snapshot
        snapshot_path = write_snapshot(core, args.output_dir, args.config_dir)
        
        print(f"✅ Snapshot created: {snapshot_path}")
        print(f"   Contract version: {core.contract_version}")
        print(f"   Schema checksum: {core.get_schema_checksum()}")
        
        # Print provenance information
        provenance = get_provenance()
        if provenance["git"]["sha"]:
            dirty = " (dirty)" if provenance["git"]["dirty"] else ""
            print(f"   Git: {provenance['git']['branch']} @ {provenance['git']['sha'][:8]}{dirty}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Snapshot creation failed: {e}")
        return 1


def cmd_reload(args) -> int:
    """Reload configuration from files"""
    try:
        print("🔄 RELOADING CONFIGURATION")
        print("=" * 60)
        
        # Get current generation
        old_generation = get_generation()
        print(f"Current generation: {old_generation}")
        
        # Attempt reload
        was_reloaded = reload_if_changed(args.config_dir)
        
        if was_reloaded:
            new_generation = get_generation()
            print(f"✅ Configuration reloaded successfully")
            print(f"New generation: {new_generation}")
            
            # Show what changed
            core = get_core(args.config_dir)
            print(f"Contract version: {core.contract_version}")
            print(f"Schema checksum: {core.get_schema_checksum()}")
            
        else:
            print("ℹ️  No changes detected - configuration not reloaded")
        
        return 0
        
    except Exception as e:
        print(f"❌ Reload failed: {e}")
        return 1


def cmd_validate(args) -> int:
    """Validate configuration and profiles"""
    try:
        print("✅ VALIDATING CONFIGURATION")
        print("=" * 60)
        
        errors_found = False
        
        # Validate core configuration
        print("Core Configuration:")
        try:
            core = get_core(args.config_dir)
            print(f"  ✅ Core config valid (v{core.contract_version})")
            print(f"     Schema checksum: {core.get_schema_checksum()}")
        except Exception as e:
            print(f"  ❌ Core config invalid: {e}")
            errors_found = True
        
        # Validate profiles
        print("\nBot Profiles:")
        manager = ProfileManager(args.config_dir)
        profile_results = manager.validate_all_profiles()
        
        for bot_type, result in profile_results.items():
            if result["valid"]:
                print(f"  ✅ {bot_type} profile valid (v{result['profile_version']})")
            else:
                print(f"  ❌ {bot_type} profile invalid:")
                for error in result["errors"]:
                    print(f"     • {error}")
                errors_found = True
        
        # Validate wallet if path provided
        if args.wallet_path:
            print("\nWallet File:")
            try:
                validation = validate_keypair_file(args.wallet_path)
                if validation["format_valid"] and validation["permissions_ok"]:
                    print(f"  ✅ Wallet valid: {validation['public_key']}")
                else:
                    print(f"  ❌ Wallet invalid:")
                    for error in validation["errors"]:
                        print(f"     • {error}")
                    errors_found = True
            except Exception as e:
                print(f"  ❌ Wallet validation failed: {e}")
                errors_found = True
        
        if not errors_found:
            print("\n🎉 All validations passed!")
        
        return 0 if not errors_found else 1
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all subcommands"""
    parser = argparse.ArgumentParser(
        description="Configuration Manager CLI",
        epilog="Use 'config-manager <command> --help' for command-specific help"
    )
    
    # Global options
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Configuration directory (default: ./config)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate comprehensive configuration report")
    report_parser.add_argument("--bot-type", choices=["jit", "hedge", "trend"], help="Include bot profile information")
    report_parser.add_argument("--profile", help="Specific profile name")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Run health checks")
    health_parser.add_argument("--wallet-path", type=Path, help="Specific wallet file to check")
    health_parser.add_argument("--mock", action="store_true", help="Use mock responses for testing")
    
    # Print command
    print_parser = subparsers.add_parser("print", help="Print configuration")
    print_parser.add_argument("--format", choices=["json", "yaml", "summary"], default="summary", help="Output format")
    print_parser.add_argument("--bot-type", choices=["jit", "hedge", "trend"], help="Include bot profile")
    print_parser.add_argument("--profile", help="Specific profile name")
    
    # Diff command
    diff_parser = subparsers.add_parser("diff", help="Compare two configuration files")
    diff_parser.add_argument("--from", dest="from_file", required=True, help="Source configuration file")
    diff_parser.add_argument("--to", dest="to_file", required=True, help="Target configuration file")
    diff_parser.add_argument("--save", action="store_true", help="Save diff results to file")
    
    # Snapshot command
    snapshot_parser = subparsers.add_parser("snapshot", help="Create configuration snapshot")
    snapshot_parser.add_argument("--output-dir", type=Path, help="Output directory for snapshot")
    
    # Reload command
    reload_parser = subparsers.add_parser("reload", help="Reload configuration from files")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration and profiles")
    validate_parser.add_argument("--wallet-path", type=Path, help="Wallet file to validate")
    
    return parser


async def main() -> int:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Print schema checksum and contract version for debugging
    try:
        core = get_core(args.config_dir)
        print(f"Config Contract v{core.contract_version} | Schema {core.get_schema_checksum()}")
        print()
    except Exception:
        pass  # Ignore errors for commands that might not need core config
    
    # Execute command
    command_map = {
        "report": cmd_report,
        "health": cmd_health,
        "print": cmd_print,
        "diff": cmd_diff,
        "snapshot": cmd_snapshot,
        "reload": cmd_reload,
        "validate": cmd_validate
    }
    
    command_func = command_map.get(args.command)
    if not command_func:
        print(f"❌ Unknown command: {args.command}")
        return 1
    
    # Run command (async if needed)
    if asyncio.iscoroutinefunction(command_func):
        return await command_func(args)
    else:
        return command_func(args)


def cli_main() -> None:
    """Entry point for CLI script"""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
