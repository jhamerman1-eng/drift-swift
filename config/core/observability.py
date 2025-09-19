"""
Observability and Provenance Tracking

Comprehensive tracking of configuration snapshots, git provenance, and operational history.
"""

import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import hashlib
import os
import logging

from .settings import CoreSettings


def get_git_sha() -> Optional[str]:
    """
    Get current git commit SHA.
    
    Returns:
        Git SHA or None if not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None


def get_git_branch() -> Optional[str]:
    """
    Get current git branch name.
    
    Returns:
        Git branch name or None if not in a git repository
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None


def get_git_status() -> Dict[str, Any]:
    """
    Get git repository status information.
    
    Returns:
        Dictionary with git status details
    """
    status = {
        "sha": get_git_sha(),
        "branch": get_git_branch(),
        "dirty": False,
        "ahead": 0,
        "behind": 0
    }
    
    try:
        # Check if working directory is dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            status["dirty"] = bool(result.stdout.strip())
        
        # Check ahead/behind status
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                status["ahead"] = int(parts[0])
                status["behind"] = int(parts[1])
                
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return status


def get_environment_hash() -> str:
    """
    Get a hash of relevant environment variable names (not values for security).
    
    Returns:
        SHA256 hash of environment variable names
    """
    # Get relevant environment variable names
    relevant_vars = []
    for key in os.environ.keys():
        if any(key.startswith(prefix) for prefix in [
            "CORE_", "DRIFT_", "SWIFT_", "RPC_", "WS_", "JITO_", 
            "LOG_", "METRICS_", "NETWORK", "KEYPAIR_"
        ]):
            relevant_vars.append(key)
    
    # Sort for consistency
    relevant_vars.sort()
    
    # Create hash
    env_string = ",".join(relevant_vars)
    return hashlib.sha256(env_string.encode()).hexdigest()[:16]


def collect_file_mtimes(config_dir: Path) -> Dict[str, float]:
    """
    Collect modification times of all configuration files.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Dictionary mapping file paths to modification times
    """
    mtimes = {}
    
    # Configuration files
    config_patterns = [
        "data/defaults/*.yaml",
        "data/environments/*.yaml",
        "core/*.py",
        "profiles/*.py",
        "secrets/*.py"
    ]
    
    for pattern in config_patterns:
        for file_path in config_dir.glob(pattern):
            if file_path.is_file():
                mtimes[str(file_path.relative_to(config_dir))] = file_path.stat().st_mtime
    
    return mtimes


def get_system_info() -> Dict[str, Any]:
    """
    Get system information for provenance tracking.
    
    Returns:
        System information dictionary
    """
    import platform
    
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "architecture": platform.architecture(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version()
    }


def create_snapshot(core: CoreSettings, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Create a comprehensive configuration snapshot with provenance.
    
    Args:
        core: Core settings to snapshot
        config_dir: Configuration directory
        
    Returns:
        Complete snapshot dictionary
    """
    if config_dir is None:
        config_dir = Path("config")
    
    timestamp = datetime.now(timezone.utc)
    
    snapshot = {
        # Metadata
        "snapshot_version": "1.0.0",
        "timestamp": timestamp.isoformat(),
        "snapshot_id": hashlib.sha256(f"{timestamp.isoformat()}{socket.gethostname()}".encode()).hexdigest()[:16],
        
        # Configuration
        "contract_version": core.contract_version,
        "schema_checksum": core.get_schema_checksum(),
        "config": core.model_dump(),
        "config_source": core.config_source,
        "loaded_at": core.loaded_at,
        
        # Git provenance
        "git": get_git_status(),
        
        # Environment
        "environment": {
            "hash": get_environment_hash(),
            "network": core.network,
            "deployment_env": core.environment
        },
        
        # System
        "system": get_system_info(),
        
        # File tracking
        "files": collect_file_mtimes(config_dir),
        
        # Runtime info
        "process": {
            "pid": os.getpid(),
            "working_directory": str(Path.cwd()),
            "command_line": " ".join(os.sys.argv) if hasattr(os, 'sys') else "unknown"
        }
    }
    
    return snapshot


def write_snapshot(core: CoreSettings, snapshots_dir: Optional[Path] = None, config_dir: Optional[Path] = None) -> Path:
    """
    Write configuration snapshot to file.
    
    Args:
        core: Core settings to snapshot
        snapshots_dir: Directory to write snapshots (defaults to config/snapshots)
        config_dir: Configuration directory for file tracking
        
    Returns:
        Path to written snapshot file
    """
    if snapshots_dir is None:
        snapshots_dir = Path("config/snapshots")
    
    if config_dir is None:
        config_dir = Path("config")
    
    # Ensure snapshots directory exists
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    # Create snapshot
    snapshot = create_snapshot(core, config_dir)
    
    # Generate filename
    timestamp = datetime.now(timezone.utc)
    filename = f"core_{timestamp.strftime('%Y%m%d_%H%M%S')}_{snapshot['snapshot_id']}.json"
    file_path = snapshots_dir / filename
    
    # Write snapshot
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
    
    # Log the snapshot
    logger = logging.getLogger(__name__)
    logger.info(f"📸 Configuration snapshot written: {file_path}")
    logger.info(f"   Snapshot ID: {snapshot['snapshot_id']}")
    logger.info(f"   Contract version: {snapshot['contract_version']}")
    logger.info(f"   Schema checksum: {snapshot['schema_checksum']}")
    
    git_info = snapshot['git']
    if git_info['sha']:
        dirty_marker = " (dirty)" if git_info['dirty'] else ""
        logger.info(f"   Git: {git_info['branch']} @ {git_info['sha'][:8]}{dirty_marker}")
    
    return file_path


def cleanup_old_snapshots(snapshots_dir: Optional[Path] = None, keep_count: int = 50) -> List[Path]:
    """
    Clean up old snapshot files, keeping only the most recent ones.
    
    Args:
        snapshots_dir: Directory containing snapshots
        keep_count: Number of snapshots to keep
        
    Returns:
        List of deleted snapshot files
    """
    if snapshots_dir is None:
        snapshots_dir = Path("config/snapshots")
    
    if not snapshots_dir.exists():
        return []
    
    # Find all snapshot files
    snapshot_files = list(snapshots_dir.glob("core_*.json"))
    
    # Sort by modification time (newest first)
    snapshot_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # Delete old files
    deleted_files = []
    for file_path in snapshot_files[keep_count:]:
        try:
            file_path.unlink()
            deleted_files.append(file_path)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to delete old snapshot {file_path}: {e}")
    
    if deleted_files:
        logger = logging.getLogger(__name__)
        logger.info(f"🧹 Cleaned up {len(deleted_files)} old configuration snapshots")
    
    return deleted_files


def load_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    """
    Load a configuration snapshot from file.
    
    Args:
        snapshot_path: Path to snapshot file
        
    Returns:
        Loaded snapshot data
        
    Raises:
        FileNotFoundError: If snapshot file doesn't exist
        json.JSONDecodeError: If snapshot file is invalid JSON
    """
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_snapshots(snapshot_a: Dict[str, Any], snapshot_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two configuration snapshots and identify differences.
    
    Args:
        snapshot_a: First snapshot (baseline)
        snapshot_b: Second snapshot (comparison)
        
    Returns:
        Dictionary with comparison results
    """
    from deepdiff import DeepDiff
    
    # Compare the configuration sections
    config_diff = DeepDiff(
        snapshot_a.get('config', {}),
        snapshot_b.get('config', {}),
        ignore_order=True
    )
    
    # Compare metadata
    metadata_changes = {}
    
    if snapshot_a.get('contract_version') != snapshot_b.get('contract_version'):
        metadata_changes['contract_version'] = {
            'old': snapshot_a.get('contract_version'),
            'new': snapshot_b.get('contract_version')
        }
    
    if snapshot_a.get('schema_checksum') != snapshot_b.get('schema_checksum'):
        metadata_changes['schema_checksum'] = {
            'old': snapshot_a.get('schema_checksum'),
            'new': snapshot_b.get('schema_checksum')
        }
    
    # Compare git status
    git_changes = {}
    git_a = snapshot_a.get('git', {})
    git_b = snapshot_b.get('git', {})
    
    if git_a.get('sha') != git_b.get('sha'):
        git_changes['commit'] = {
            'old': git_a.get('sha', 'unknown')[:8],
            'new': git_b.get('sha', 'unknown')[:8]
        }
    
    if git_a.get('branch') != git_b.get('branch'):
        git_changes['branch'] = {
            'old': git_a.get('branch'),
            'new': git_b.get('branch')
        }
    
    return {
        "snapshots": {
            "a": {
                "id": snapshot_a.get('snapshot_id'),
                "timestamp": snapshot_a.get('timestamp')
            },
            "b": {
                "id": snapshot_b.get('snapshot_id'),
                "timestamp": snapshot_b.get('timestamp')
            }
        },
        "config_changes": config_diff,
        "metadata_changes": metadata_changes,
        "git_changes": git_changes,
        "has_changes": bool(config_diff) or bool(metadata_changes) or bool(git_changes)
    }


def get_provenance() -> Dict[str, Any]:
    """
    Get current provenance information without creating a full snapshot.
    
    Returns:
        Provenance information dictionary
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": get_git_status(),
        "environment_hash": get_environment_hash(),
        "system": get_system_info(),
        "process": {
            "pid": os.getpid(),
            "working_directory": str(Path.cwd())
        }
    }
