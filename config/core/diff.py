"""
Configuration Diff Utilities

Deep comparison and diffing of configuration changes between deployments.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

try:
    from deepdiff import DeepDiff
    DEEPDIFF_AVAILABLE = True
except ImportError:
    DEEPDIFF_AVAILABLE = False


def simple_diff(old_config: Dict[str, Any], new_config: Dict[str, Any], path: str = "") -> List[str]:
    """
    Simple configuration diff without external dependencies.
    
    Args:
        old_config: Original configuration
        new_config: New configuration
        path: Current path for nested diffs
        
    Returns:
        List of change descriptions
    """
    changes = []
    
    # Check for added/modified keys
    for key, new_value in new_config.items():
        current_path = f"{path}.{key}" if path else key
        
        if key not in old_config:
            changes.append(f"ADDED: {current_path} = {repr(new_value)}")
        elif old_config[key] != new_value:
            if isinstance(new_value, dict) and isinstance(old_config[key], dict):
                # Recurse into nested dictionaries
                nested_changes = simple_diff(old_config[key], new_value, current_path)
                changes.extend(nested_changes)
            else:
                changes.append(f"CHANGED: {current_path} = {repr(old_config[key])} -> {repr(new_value)}")
    
    # Check for removed keys
    for key in old_config:
        if key not in new_config:
            current_path = f"{path}.{key}" if path else key
            changes.append(f"REMOVED: {current_path} = {repr(old_config[key])}")
    
    return changes


def compute_config_diff(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute detailed configuration diff.
    
    Args:
        old_config: Original configuration dictionary
        new_config: New configuration dictionary
        
    Returns:
        Detailed diff results
    """
    if DEEPDIFF_AVAILABLE:
        # Use DeepDiff for comprehensive comparison
        diff = DeepDiff(
            old_config,
            new_config,
            ignore_order=True,
            report_type='text',
            verbose_level=2
        )
        
        # Convert DeepDiff result to our format
        result = {
            "tool": "deepdiff",
            "has_changes": bool(diff),
            "summary": _summarize_deepdiff(diff),
            "detailed": dict(diff) if diff else {},
            "text_report": str(diff) if diff else "No changes detected"
        }
    else:
        # Use simple diff as fallback
        changes = simple_diff(old_config, new_config)
        
        result = {
            "tool": "simple",
            "has_changes": bool(changes),
            "summary": {
                "total_changes": len(changes),
                "added": len([c for c in changes if c.startswith("ADDED:")]),
                "changed": len([c for c in changes if c.startswith("CHANGED:")]),
                "removed": len([c for c in changes if c.startswith("REMOVED:")])
            },
            "detailed": {"changes": changes},
            "text_report": "\n".join(changes) if changes else "No changes detected"
        }
    
    return result


def _summarize_deepdiff(diff: dict) -> Dict[str, int]:
    """
    Summarize DeepDiff results into counts.
    
    Args:
        diff: DeepDiff result dictionary
        
    Returns:
        Summary statistics
    """
    summary = {
        "total_changes": 0,
        "added": 0,
        "removed": 0,
        "changed": 0,
        "type_changes": 0
    }
    
    # Count different types of changes
    if 'dictionary_item_added' in diff:
        added_count = len(diff['dictionary_item_added'])
        summary["added"] = added_count
        summary["total_changes"] += added_count
    
    if 'dictionary_item_removed' in diff:
        removed_count = len(diff['dictionary_item_removed'])
        summary["removed"] = removed_count
        summary["total_changes"] += removed_count
    
    if 'values_changed' in diff:
        changed_count = len(diff['values_changed'])
        summary["changed"] = changed_count
        summary["total_changes"] += changed_count
    
    if 'type_changes' in diff:
        type_count = len(diff['type_changes'])
        summary["type_changes"] = type_count
        summary["total_changes"] += type_count
    
    return summary


def load_config_from_file(file_path: Path) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        Loaded configuration dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_config_files(old_file: Path, new_file: Path) -> Dict[str, Any]:
    """
    Compare two configuration files.
    
    Args:
        old_file: Path to original configuration file
        new_file: Path to new configuration file
        
    Returns:
        Comparison results
    """
    # Load configurations
    old_config = load_config_from_file(old_file)
    new_config = load_config_from_file(new_file)
    
    # Extract the actual config from snapshots if needed
    if 'config' in old_config and isinstance(old_config['config'], dict):
        old_config = old_config['config']
    
    if 'config' in new_config and isinstance(new_config['config'], dict):
        new_config = new_config['config']
    
    # Compute diff
    diff_result = compute_config_diff(old_config, new_config)
    
    # Add file metadata
    diff_result.update({
        "files": {
            "old": str(old_file),
            "new": str(new_file)
        },
        "comparison_time": datetime.utcnow().isoformat() + "Z"
    })
    
    return diff_result


def format_diff_report(diff_result: Dict[str, Any]) -> str:
    """
    Format diff results into a readable report.
    
    Args:
        diff_result: Results from compute_config_diff or compare_config_files
        
    Returns:
        Formatted diff report
    """
    lines = []
    
    # Header
    lines.append("📋 CONFIGURATION DIFF REPORT")
    lines.append("=" * 60)
    
    # Files being compared (if available)
    if "files" in diff_result:
        lines.append(f"Old: {diff_result['files']['old']}")
        lines.append(f"New: {diff_result['files']['new']}")
        lines.append("")
    
    # Summary
    if diff_result["has_changes"]:
        lines.append("🔄 CHANGES DETECTED")
        summary = diff_result["summary"]
        
        if "total_changes" in summary:
            lines.append(f"Total Changes: {summary['total_changes']}")
        
        if "added" in summary and summary["added"] > 0:
            lines.append(f"Added: {summary['added']}")
        
        if "changed" in summary and summary["changed"] > 0:
            lines.append(f"Changed: {summary['changed']}")
        
        if "removed" in summary and summary["removed"] > 0:
            lines.append(f"Removed: {summary['removed']}")
        
        if "type_changes" in summary and summary["type_changes"] > 0:
            lines.append(f"Type Changes: {summary['type_changes']}")
        
        lines.append("")
        lines.append("DETAILED CHANGES:")
        lines.append("-" * 40)
        lines.append(diff_result["text_report"])
        
    else:
        lines.append("✅ NO CHANGES DETECTED")
        lines.append("The configurations are identical.")
    
    lines.append("")
    lines.append(f"Tool: {diff_result['tool']}")
    
    if "comparison_time" in diff_result:
        lines.append(f"Comparison Time: {diff_result['comparison_time']}")
    
    return "\n".join(lines)


def persist_diff(
    diff_result: Dict[str, Any],
    output_dir: Optional[Path] = None,
    filename_prefix: str = "config_diff"
) -> Path:
    """
    Persist diff results to a file.
    
    Args:
        diff_result: Diff results to persist
        output_dir: Directory to write diff file (defaults to config/snapshots)
        filename_prefix: Prefix for diff filename
        
    Returns:
        Path to written diff file
    """
    if output_dir is None:
        output_dir = Path("config/snapshots")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    file_path = output_dir / filename
    
    # Write diff results
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(diff_result, f, indent=2, sort_keys=True)
    
    # Log the diff
    logger = logging.getLogger(__name__)
    logger.info(f"💾 Configuration diff saved: {file_path}")
    
    if diff_result["has_changes"]:
        summary = diff_result["summary"]
        if "total_changes" in summary:
            logger.info(f"   Total changes: {summary['total_changes']}")
    else:
        logger.info("   No changes detected")
    
    return file_path


# Convenience functions for common operations
def quick_diff(old: Dict[str, Any], new: Dict[str, Any]) -> str:
    """
    Quick diff returning just the text report.
    
    Args:
        old: Original configuration
        new: New configuration
        
    Returns:
        Text diff report
    """
    diff_result = compute_config_diff(old, new)
    return diff_result["text_report"]


def has_significant_changes(diff_result: Dict[str, Any]) -> bool:
    """
    Check if diff contains significant changes (not just metadata).
    
    Args:
        diff_result: Diff results
        
    Returns:
        True if there are significant changes
    """
    if not diff_result["has_changes"]:
        return False
    
    # For simple diff, any change is significant
    if diff_result["tool"] == "simple":
        return diff_result["summary"]["total_changes"] > 0
    
    # For deepdiff, check for meaningful changes
    summary = diff_result["summary"]
    significant_changes = (
        summary.get("added", 0) +
        summary.get("removed", 0) +
        summary.get("changed", 0) +
        summary.get("type_changes", 0)
    )
    
    return significant_changes > 0
