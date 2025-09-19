"""
Configuration Cache

Thread-safe caching with file modification time guards and reload capability.
Provides process-wide singleton with generation counter for change detection.
"""

import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

from .settings import CoreSettings
from .loader import load_core, collect_file_mtimes


# Global cache state
_state = {
    "core": None,
    "mtimes": {},
    "generation": 0,
    "config_dir": None
}

# Thread safety
_lock = threading.RLock()

logger = logging.getLogger(__name__)


def _load_and_stamp(config_dir: Optional[Path] = None) -> Tuple[CoreSettings, Dict[str, float]]:
    """
    Load configuration and collect file modification times.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Tuple of (CoreSettings, file_mtimes)
    """
    if config_dir is None:
        config_dir = Path("config")
    
    # Load core settings
    core = load_core(config_dir)
    
    # Collect file modification times
    mtimes = collect_file_mtimes(config_dir)
    
    return core, mtimes


def _collect_current_mtimes(config_dir: Optional[Path] = None) -> Dict[str, float]:
    """
    Collect current file modification times.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Dictionary of current file modification times
    """
    if config_dir is None:
        config_dir = Path("config")
    
    return collect_file_mtimes(config_dir)


def get_core(config_dir: Optional[Path] = None) -> CoreSettings:
    """
    Get core configuration settings.
    
    Thread-safe singleton pattern with lazy loading.
    
    Args:
        config_dir: Configuration directory (only used on first load)
        
    Returns:
        CoreSettings instance
    """
    with _lock:
        # First time loading
        if _state["core"] is None:
            logger.info("🔄 Loading core configuration for first time")
            _state["core"], _state["mtimes"] = _load_and_stamp(config_dir)
            _state["config_dir"] = config_dir
            logger.info(f"✅ Core configuration loaded (generation {_state['generation']})")
        
        return _state["core"]


def reload_if_changed(config_dir: Optional[Path] = None) -> bool:
    """
    Reload configuration if any files have changed.
    
    Thread-safe with automatic file modification time checking.
    
    Args:
        config_dir: Configuration directory (uses cached value if None)
        
    Returns:
        True if configuration was reloaded, False if no changes detected
    """
    with _lock:
        # Use cached config_dir if not provided
        if config_dir is None:
            config_dir = _state["config_dir"] or Path("config")
        
        # Collect current modification times
        current_mtimes = _collect_current_mtimes(config_dir)
        
        # Check if any files have changed
        if current_mtimes != _state["mtimes"]:
            logger.info("🔄 Configuration files changed, reloading...")
            
            # Log specific changes
            for file_path, mtime in current_mtimes.items():
                if file_path not in _state["mtimes"]:
                    logger.info(f"   New file: {file_path}")
                elif mtime != _state["mtimes"][file_path]:
                    logger.info(f"   Modified: {file_path}")
            
            for file_path in _state["mtimes"]:
                if file_path not in current_mtimes:
                    logger.info(f"   Removed: {file_path}")
            
            try:
                # Reload configuration
                _state["core"], _state["mtimes"] = _load_and_stamp(config_dir)
                _state["generation"] += 1
                _state["config_dir"] = config_dir
                
                logger.info(f"✅ Configuration reloaded successfully (generation {_state['generation']})")
                logger.info(f"   New contract version: {_state['core'].contract_version}")
                logger.info(f"   New schema checksum: {_state['core'].get_schema_checksum()}")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to reload configuration: {e}")
                logger.error("   Keeping previous configuration")
                # Don't update generation on failure
                return False
        
        return False


def get_generation() -> int:
    """
    Get current configuration generation number.
    
    The generation number increments each time the configuration is reloaded.
    Bots can use this to detect configuration changes.
    
    Returns:
        Current generation number
    """
    with _lock:
        return _state["generation"]


def force_reload(config_dir: Optional[Path] = None) -> bool:
    """
    Force reload configuration regardless of file modification times.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        True if reload succeeded, False otherwise
    """
    with _lock:
        if config_dir is None:
            config_dir = _state["config_dir"] or Path("config")
        
        logger.info("🔄 Force reloading configuration...")
        
        try:
            # Force reload
            _state["core"], _state["mtimes"] = _load_and_stamp(config_dir)
            _state["generation"] += 1
            _state["config_dir"] = config_dir
            
            logger.info(f"✅ Configuration force reloaded (generation {_state['generation']})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to force reload configuration: {e}")
            return False


def clear_cache() -> None:
    """
    Clear the configuration cache.
    
    Next call to get_core() will reload from files.
    """
    with _lock:
        logger.info("🔄 Clearing configuration cache")
        _state["core"] = None
        _state["mtimes"] = {}
        _state["generation"] = 0
        _state["config_dir"] = None


def get_cache_info() -> Dict[str, Any]:
    """
    Get information about the current cache state.
    
    Returns:
        Dictionary with cache information
    """
    with _lock:
        return {
            "loaded": _state["core"] is not None,
            "generation": _state["generation"],
            "config_dir": str(_state["config_dir"]) if _state["config_dir"] else None,
            "tracked_files": list(_state["mtimes"].keys()),
            "contract_version": _state["core"].contract_version if _state["core"] else None,
            "schema_checksum": _state["core"].get_schema_checksum() if _state["core"] else None,
            "loaded_at": _state["core"].loaded_at if _state["core"] else None,
            "config_source": _state["core"].config_source if _state["core"] else None
        }


def is_cache_stale(config_dir: Optional[Path] = None) -> bool:
    """
    Check if cache is stale compared to file system.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        True if cache is stale and needs reload
    """
    with _lock:
        if _state["core"] is None:
            return True
        
        if config_dir is None:
            config_dir = _state["config_dir"] or Path("config")
        
        current_mtimes = _collect_current_mtimes(config_dir)
        return current_mtimes != _state["mtimes"]


# Convenience functions for common operations
def ensure_loaded(config_dir: Optional[Path] = None) -> CoreSettings:
    """
    Ensure configuration is loaded and return it.
    
    Equivalent to get_core() but more explicit about intent.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        CoreSettings instance
    """
    return get_core(config_dir)


def auto_reload_if_stale(config_dir: Optional[Path] = None) -> Tuple[CoreSettings, bool]:
    """
    Automatically reload if cache is stale, then return configuration.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Tuple of (CoreSettings, was_reloaded)
    """
    was_reloaded = reload_if_changed(config_dir)
    core = get_core(config_dir)
    return core, was_reloaded
