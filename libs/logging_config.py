#!/usr/bin/env python3
"""
Centralized logging configuration for Drift Trading Bots
Provides consistent logging setup across all applications with proper file rotation and formatting
"""

import json
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DEFAULT_LOG_FORMAT_VERBOSE = "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"

# Log file configuration
LOG_DIR = Path("logs")
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5
LOG_RETENTION_DAYS = 7

# Critical application loggers
CRITICAL_LOGGERS = [
    "jit-mm-swift",           # Main MM bot
    "hedge-bot",              # Hedge bot
    "trend-bot",              # Trend bot
    "drift-client",           # Drift client
    "rpc-manager",            # RPC management
    "order-management",       # Order management
    "risk-manager",           # Risk management
    "swift-client",           # Swift client
    "orchestrator",           # Bot orchestrator
]

# Non-critical application loggers (utilities, tests, etc.)
NON_CRITICAL_LOGGERS = [
    "test",                   # Test modules
    "utils",                  # Utility modules
    "setup",                  # Setup scripts
    "debug",                  # Debug scripts
]

def ensure_log_directory():
    """Ensure the logs directory exists"""
    LOG_DIR.mkdir(exist_ok=True)
    return LOG_DIR

def get_log_level(level_name: Optional[str] = None) -> int:
    """Get log level from string or environment variable"""
    if level_name:
        return getattr(logging, level_name.upper(), DEFAULT_LOG_LEVEL)
    
    # Check environment variable
    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        return getattr(logging, env_level)
    
    return DEFAULT_LOG_LEVEL

def create_rotating_file_handler(
    filename: str,
    max_bytes: int = MAX_LOG_SIZE,
    backup_count: int = BACKUP_COUNT,
    encoding: str = "utf-8"
) -> logging.handlers.RotatingFileHandler:
    """Create a rotating file handler with proper configuration"""
    ensure_log_directory()
    log_path = LOG_DIR / filename
    
    handler = logging.handlers.RotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )
    
    # Set formatter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    handler.setFormatter(formatter)
    
    return handler

def create_timed_rotating_file_handler(
    filename: str,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = BACKUP_COUNT,
    encoding: str = "utf-8"
) -> logging.handlers.TimedRotatingFileHandler:
    """Create a timed rotating file handler for daily logs"""
    ensure_log_directory()
    log_path = LOG_DIR / filename
    
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding=encoding
    )
    
    # Set formatter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    handler.setFormatter(formatter)
    
    return handler

def setup_console_handler(level: int = DEFAULT_LOG_LEVEL) -> logging.StreamHandler:
    """Create a console handler with proper formatting"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Use verbose format for console
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT_VERBOSE)
    handler.setFormatter(formatter)
    
    return handler

def setup_critical_logging(
    app_name: str,
    log_level: Optional[str] = None,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    log_format: str = "default"
) -> logging.Logger:
    """
    Setup logging for critical applications with file rotation and console output
    
    Args:
        app_name: Name of the application (used for log filename)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging
        enable_console_logging: Whether to enable console logging
        log_format: Log format ("default" or "verbose")
    
    Returns:
        Configured logger instance
    """
    # Get logger
    logger = logging.getLogger(app_name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    level = get_log_level(log_level)
    logger.setLevel(level)
    
    # Choose format
    if log_format == "verbose":
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT_VERBOSE)
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    
    # File handler (rotating)
    if enable_file_logging:
        file_handler = create_rotating_file_handler(f"{app_name}.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if enable_console_logging:
        console_handler = setup_console_handler(level)
        logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def setup_utility_logging(
    app_name: str,
    log_level: Optional[str] = None,
    enable_file_logging: bool = False,
    enable_console_logging: bool = True
) -> logging.Logger:
    """
    Setup logging for utility/non-critical applications
    
    Args:
        app_name: Name of the application
        log_level: Log level
        enable_file_logging: Whether to enable file logging
        enable_console_logging: Whether to enable console logging
    
    Returns:
        Configured logger instance
    """
    return setup_critical_logging(
        app_name=app_name,
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        enable_console_logging=enable_console_logging
    )

def setup_test_logging(
    test_name: str,
    log_level: str = "INFO",
    enable_file_logging: bool = False
) -> logging.Logger:
    """
    Setup logging for test modules
    
    Args:
        test_name: Name of the test
        log_level: Log level
        enable_file_logging: Whether to enable file logging
    
    Returns:
        Configured logger instance
    """
    return setup_utility_logging(
        app_name=f"test.{test_name}",
        log_level=log_level,
        enable_file_logging=enable_file_logging,
        enable_console_logging=True
    )

def get_existing_logger(app_name: str) -> logging.Logger:
    """Get an existing logger or create a new one with default settings"""
    logger = logging.getLogger(app_name)
    
    if not logger.handlers:
        # Setup with default configuration
        if app_name in CRITICAL_LOGGERS:
            setup_critical_logging(app_name)
        elif app_name in NON_CRITICAL_LOGGERS:
            setup_utility_logging(app_name)
        else:
            # Default to utility logging
            setup_utility_logging(app_name)
    
    return logger

def cleanup_old_logs():
    """Clean up old log files based on retention policy"""
    try:
        ensure_log_directory()
        
        # Get all log files
        log_files = list(LOG_DIR.glob("*.log*"))
        current_time = time.time()
        
        for log_file in log_files:
            # Check if file is older than retention period
            if log_file.stat().st_mtime < (current_time - (LOG_RETENTION_DAYS * 24 * 60 * 60)):
                try:
                    log_file.unlink()
                    print(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    print(f"Failed to clean up {log_file}: {e}")
    
    except Exception as e:
        print(f"Error during log cleanup: {e}")

def log_system_info(logger: logging.Logger):
    """Log system information for debugging"""
    import platform
    import sys
    
    logger.info("=" * 60)
    logger.info("SYSTEM INFORMATION")
    logger.info("=" * 60)
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Python Executable: {sys.executable}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info(f"Log Directory: {LOG_DIR.absolute()}")
    logger.info(f"Log Level: {logging.getLevelName(logger.level)}")
    logger.info("=" * 60)

# Convenience functions for common use cases
def get_mm_bot_logger() -> logging.Logger:
    """Get logger for market maker bot"""
    return get_existing_logger("jit-mm-swift")

def get_hedge_bot_logger() -> logging.Logger:
    """Get logger for hedge bot"""
    return get_existing_logger("hedge-bot")

def get_trend_bot_logger() -> logging.Logger:
    """Get logger for trend bot"""
    return get_existing_logger("trend-bot")

def get_drift_client_logger() -> logging.Logger:
    """Get logger for drift client"""
    return get_existing_logger("drift-client")

def get_rpc_manager_logger() -> logging.Logger:
    """Get logger for RPC manager"""
    return get_existing_logger("rpc-manager")

def get_order_management_logger() -> logging.Logger:
    """Get logger for order management"""
    return get_existing_logger("order-management")

def get_risk_manager_logger() -> logging.Logger:
    """Get logger for risk manager"""
    return get_existing_logger("risk-manager")

def get_swift_client_logger() -> logging.Logger:
    """Get logger for Swift client"""
    return get_existing_logger("swift-client")

def get_orchestrator_logger() -> logging.Logger:
    """Get logger for orchestrator"""
    return get_existing_logger("orchestrator")

# Bug tracking integration
class BugTracker:
    """Enhanced bug tracking that integrates with logging system"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.active_bugs = {}
        self.bug_registry_file = LOG_DIR / "bug_registry_active.json"

    def log_bug(self, bug_id: str, description: str, root_cause: str = "",
                impact: str = "", priority: str = "medium",
                context: dict = None) -> str:
        """Log a new bug with comprehensive tracking"""
        if bug_id in self.active_bugs:
            self.logger.warning(f"Bug {bug_id} already exists, updating...")
            return bug_id

        bug_data = {
            "id": bug_id,
            "description": description,
            "root_cause": root_cause,
            "impact": impact,
            "priority": priority,
            "status": "active",
            "created": time.time(),
            "updated": time.time(),
            "context": context or {},
            "log_entries": [],
            "resolution_attempted": False,
            "resolution_notes": []
        }

        self.active_bugs[bug_id] = bug_data
        self._save_bug_registry()

        # Log the bug with comprehensive information
        self.logger.error(f"🐛 BUG DETECTED: {bug_id}")
        self.logger.error(f"   Description: {description}")
        if root_cause:
            self.logger.error(f"   Root Cause: {root_cause}")
        if impact:
            self.logger.error(f"   Impact: {impact}")
        self.logger.error(f"   Priority: {priority.upper()}")
        self.logger.error(f"   Context: {json.dumps(context, indent=2) if context else 'None'}")

        return bug_id

    def log_bug_resolution_attempt(self, bug_id: str, solution_attempted: str,
                                  success: bool = False, notes: str = "") -> None:
        """Log an attempt to resolve a bug"""
        if bug_id not in self.active_bugs:
            self.logger.warning(f"Attempting to resolve unknown bug {bug_id}")
            return

        bug_data = self.active_bugs[bug_id]
        bug_data["resolution_attempted"] = True
        bug_data["updated"] = time.time()

        resolution_entry = {
            "timestamp": time.time(),
            "solution_attempted": solution_attempted,
            "success": success,
            "notes": notes
        }

        bug_data["resolution_notes"].append(resolution_entry)

        if success:
            bug_data["status"] = "resolved"
            self.logger.info(f"✅ BUG RESOLVED: {bug_id}")
            self.logger.info(f"   Solution: {solution_attempted}")
            if notes:
                self.logger.info(f"   Notes: {notes}")
        else:
            self.logger.warning(f"❌ RESOLUTION FAILED: {bug_id}")
            self.logger.warning(f"   Attempted: {solution_attempted}")
            if notes:
                self.logger.warning(f"   Notes: {notes}")

        self._save_bug_registry()

    def log_error_with_bug_tracking(self, error: Exception, context: dict = None,
                                   auto_create_bug: bool = True) -> str:
        """Log an error with automatic bug tracking"""
        error_type = type(error).__name__
        error_msg = str(error)

        # Create a unique bug ID based on error type and message
        import hashlib
        bug_signature = f"{error_type}:{error_msg}"
        bug_id = f"ERR-{hashlib.md5(bug_signature.encode()).hexdigest()[:8].upper()}"

        # Log the error
        self.logger.error(f"❌ ERROR: {error_type}: {error_msg}")
        if context:
            self.logger.error(f"   Context: {json.dumps(context, indent=2)}")

        if auto_create_bug:
            description = f"Runtime error: {error_type} - {error_msg}"
            root_cause = f"Exception in {context.get('function', 'unknown') if context else 'unknown'}"
            impact = f"Affects {context.get('component', 'unknown') if context else 'unknown'}"

            self.log_bug(
                bug_id=bug_id,
                description=description,
                root_cause=root_cause,
                impact=impact,
                priority="high" if "critical" in error_msg.lower() else "medium",
                context=context
            )

        return bug_id

    def get_bug_summary(self) -> dict:
        """Get summary of all active bugs"""
        return {
            "total_active": len(self.active_bugs),
            "by_priority": {
                "critical": len([b for b in self.active_bugs.values() if b["priority"] == "critical"]),
                "high": len([b for b in self.active_bugs.values() if b["priority"] == "high"]),
                "medium": len([b for b in self.active_bugs.values() if b["priority"] == "medium"]),
                "low": len([b for b in self.active_bugs.values() if b["priority"] == "low"])
            },
            "recent_activity": sorted(
                [(bid, b["updated"]) for bid, b in self.active_bugs.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def _save_bug_registry(self) -> None:
        """Save active bug registry to file"""
        try:
            with open(self.bug_registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_bugs, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save bug registry: {e}")

    def _load_bug_registry(self) -> None:
        """Load active bug registry from file"""
        try:
            if self.bug_registry_file.exists():
                with open(self.bug_registry_file, 'r', encoding='utf-8') as f:
                    self.active_bugs = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load bug registry: {e}")

# Global bug tracker instance
_bug_trackers = {}

def get_bug_tracker(logger_name: str) -> BugTracker:
    """Get or create a bug tracker for a specific logger"""
    if logger_name not in _bug_trackers:
        logger = get_existing_logger(logger_name)
        _bug_trackers[logger_name] = BugTracker(logger)
        _bug_trackers[logger_name]._load_bug_registry()
    return _bug_trackers[logger_name]

# Enhanced logging functions with bug tracking
def log_error_with_tracking(logger: logging.Logger, error: Exception,
                           context: dict = None, component: str = "") -> str:
    """Log an error with automatic bug tracking"""
    tracker = get_bug_tracker(logger.name)

    if not context:
        context = {}

    if component:
        context["component"] = component

    # Get the calling function name
    import inspect
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back.f_back  # Go up two frames to get the actual caller
        context["function"] = caller_frame.f_code.co_name
        context["file"] = caller_frame.f_code.co_filename
        context["line"] = caller_frame.f_lineno
    except:
        pass

    return tracker.log_error_with_bug_tracking(error, context)

# Initialize logging directory on import
ensure_log_directory()

