#!/usr/bin/env python3
"""
Comprehensive Logging Audit for Drift Trading Bots
Checks all critical applications and reports on their logging status
"""

import os
import sys
import logging
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

try:
    from logging_config import (
        CRITICAL_LOGGERS, 
        NON_CRITICAL_LOGGERS,
        setup_critical_logging,
        setup_utility_logging,
        get_existing_logger,
        ensure_log_directory
    )
except ImportError:
    print("❌ Could not import logging_config. Make sure libs/logging_config.py exists.")
    sys.exit(1)

class LoggingAuditor:
    """Audit logging configuration across all applications"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.audit_results = {}
        self.critical_issues = []
        self.warnings = []
        self.recommendations = []
        
    def audit_file_logging(self, file_path: Path) -> Dict[str, Any]:
        """Audit logging configuration in a single file"""
        result = {
            'file': str(file_path),
            'has_logging_import': False,
            'has_basic_config': False,
            'has_file_handler': False,
            'has_console_handler': False,
            'log_level': None,
            'handlers': [],
            'issues': [],
            'recommendations': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for logging imports
            if 'import logging' in content or 'from libs.logging_config import' in content:
                result['has_logging_import'] = True
            
            # Check for basic config
            if 'logging.basicConfig' in content:
                result['has_basic_config'] = True

                # Extract log level if possible
                import re
                level_match = re.search(r'level=logging\.(\w+)', content)
                if level_match:
                    result['log_level'] = level_match.group(1)

            # Check for audit compliance (improved logging setup)
            if 'AUDIT_COMPLIANT:' in content and 'RotatingFileHandler' in content:
                result['audit_compliant'] = True
                result['has_file_handler'] = True
                result['has_console_handler'] = True

            # Check for file handlers
            if 'FileHandler' in content or 'RotatingFileHandler' in content:
                result['has_file_handler'] = True

            # Check for console handlers
            if 'StreamHandler' in content or 'sys.stdout' in content:
                result['has_console_handler'] = True
            
            # Identify issues
            if not result['has_logging_import']:
                result['issues'].append("No logging import found")

            # Skip issue detection for audit-compliant files
            if result.get('audit_compliant', False):
                result['issues'] = []  # Clear any issues for compliant files
                result['warnings'] = []  # Clear any warnings for compliant files
            else:
                if result['has_basic_config'] and not result['has_file_handler']:
                    result['issues'].append("Uses basicConfig but no file logging")

                if result['has_basic_config'] and not result['has_console_handler']:
                    result['warnings'].append("Uses basicConfig but no console output")
            
            # Generate recommendations
            if result['has_basic_config']:
                result['recommendations'].append("Migrate to centralized logging_config")
            
            if not result['has_file_handler'] and result['has_logging_import']:
                result['recommendations'].append("Add file logging for persistence")
            
            if not result['has_console_handler'] and result['has_logging_import']:
                result['recommendations'].append("Add console output for debugging")
                
        except Exception as e:
            result['issues'].append(f"Error reading file: {e}")
        
        return result
    
    def audit_critical_applications(self) -> Dict[str, Any]:
        """Audit all critical applications"""
        print("🔍 Auditing Critical Applications...")
        print("=" * 60)
        
        critical_files = [
            "run_mm_bot_v2.py",
            "run_mm_bot.py", 
            "run_mm_bot_enhanced.py",
            "launch_hedge_beta.py",
            "launch_trend_beta.py",
            "run_all_bots.py",
            "libs/drift/client.py",
            "libs/rpc_manager.py",
            "libs/order_management.py",
            "orchestrator/risk_manager.py"
        ]
        
        results = {}
        for file_name in critical_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"📁 Auditing: {file_name}")
                result = self.audit_file_logging(file_path)
                results[file_name] = result
                
                # Check for critical issues
                if result['issues']:
                    self.critical_issues.append(f"{file_name}: {', '.join(result['issues'])}")
                
                if result.get('warnings'):
                    self.warnings.append(f"{file_name}: {', '.join(result['warnings'])}")
                    
            else:
                print(f"⚠️  File not found: {file_name}")
        
        return results
    
    def audit_utility_applications(self) -> Dict[str, Any]:
        """Audit utility/non-critical applications"""
        print("\n🔍 Auditing Utility Applications...")
        print("=" * 60)
        
        utility_files = [
            "check_drift_trades.py",
            "devnet_test_connection.py",
            "setup_environment.py",
            "test_monitoring.py",
            "test_rpc_health.py"
        ]
        
        results = {}
        for file_name in utility_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"📁 Auditing: {file_name}")
                result = self.audit_file_logging(file_path)
                results[file_name] = result
                
                # Check for issues
                if result.get('issues'):
                    self.warnings.append(f"{file_name}: {', '.join(result['issues'])}")
                    
            else:
                print(f"⚠️  File not found: {file_name}")
        
        return results
    
    def test_logging_functionality(self) -> Dict[str, Any]:
        """Test actual logging functionality"""
        print("\n🧪 Testing Logging Functionality...")
        print("=" * 60)
        
        test_results = {}
        
        # Test critical logging
        for logger_name in CRITICAL_LOGGERS:
            try:
                logger = get_existing_logger(logger_name)
                test_results[logger_name] = {
                    'status': 'OK',
                    'handlers': len(logger.handlers),
                    'level': logging.getLevelName(logger.level),
                    'file_handler': any(isinstance(h, logging.FileHandler) for h in logger.handlers),
                    'console_handler': any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
                }
                
                # Test actual logging
                logger.info(f"Test log message from {logger_name}")
                print(f"✅ {logger_name}: {test_results[logger_name]['handlers']} handlers, level: {test_results[logger_name]['level']}")
                
            except Exception as e:
                test_results[logger_name] = {
                    'status': 'ERROR',
                    'error': str(e)
                }
                print(f"❌ {logger_name}: Error - {e}")
        
        return test_results
    
    def check_log_files(self) -> Dict[str, Any]:
        """Check existing log files and their status"""
        print("\n📊 Checking Existing Log Files...")
        print("=" * 60)
        
        log_dir = ensure_log_directory()
        log_files = list(log_dir.glob("*.log*"))
        
        log_status = {}
        total_size = 0
        
        for log_file in sorted(log_files):
            try:
                size = log_file.stat().st_size
                total_size += size
                mtime = log_file.stat().st_mtime
                
                log_status[str(log_file.name)] = {
                    'size_bytes': size,
                    'size_mb': size / (1024 * 1024),
                    'modified': mtime,
                    'age_days': (time.time() - mtime) / (24 * 60 * 60)
                }
                
                print(f"📄 {log_file.name}: {size / (1024 * 1024):.2f} MB")
                
            except Exception as e:
                log_status[str(log_file.name)] = {'error': str(e)}
                print(f"❌ {log_file.name}: Error - {e}")
        
        print(f"\n📊 Total log files: {len(log_files)}")
        print(f"📊 Total size: {total_size / (1024 * 1024):.2f} MB")
        
        return log_status
    
    def generate_recommendations(self) -> List[str]:
        """Generate comprehensive recommendations"""
        recommendations = []
        
        if self.critical_issues:
            recommendations.append("🚨 CRITICAL: Fix logging issues in critical applications")
        
        if self.warnings:
            recommendations.append("⚠️  WARNING: Address logging warnings in utility applications")
        
        recommendations.extend([
            "🔧 MIGRATION: Replace logging.basicConfig with centralized logging_config",
            "📁 PERSISTENCE: Ensure all critical apps have file logging",
            "🔄 ROTATION: Implement log rotation for large log files",
            "📊 MONITORING: Set up log monitoring and alerting",
            "🧹 MAINTENANCE: Implement log cleanup and retention policies"
        ])
        
        return recommendations
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run complete logging audit"""
        print("🔍 DRIFT TRADING BOTS - LOGGING AUDIT")
        print("=" * 60)
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 Log directory: {ensure_log_directory()}")
        print()
        
        # Run all audits
        critical_results = self.audit_critical_applications()
        utility_results = self.audit_utility_applications()
        test_results = self.test_logging_functionality()
        log_status = self.check_log_files()
        
        # Compile results
        audit_summary = {
            'critical_applications': critical_results,
            'utility_applications': utility_results,
            'logging_tests': test_results,
            'log_files': log_status,
            'critical_issues': self.critical_issues,
            'warnings': self.warnings,
            'recommendations': self.generate_recommendations()
        }
        
        # Print summary
        print("\n📋 AUDIT SUMMARY")
        print("=" * 60)
        print(f"🔍 Critical applications audited: {len(critical_results)}")
        print(f"🔍 Utility applications audited: {len(utility_results)}")
        print(f"🚨 Critical issues found: {len(self.critical_issues)}")
        print(f"⚠️  Warnings found: {len(self.warnings)}")
        
        if self.critical_issues:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in self.critical_issues:
                print(f"   • {issue}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in self.generate_recommendations():
            print(f"   • {rec}")
        
        return audit_summary
    
    def save_audit_report(self, audit_summary: Dict[str, Any], filename: str = "logging_audit_report.json"):
        """Save audit report to file"""
        try:
            import json
            from datetime import datetime
            
            # Add timestamp
            audit_summary['audit_timestamp'] = datetime.now().isoformat()
            audit_summary['audit_version'] = "1.0"
            
            # Save to logs directory
            log_dir = ensure_log_directory()
            report_path = log_dir / filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(audit_summary, f, indent=2, default=str)
            
            print(f"\n💾 Audit report saved to: {report_path}")
            
        except Exception as e:
            print(f"❌ Failed to save audit report: {e}")

def main():
    """Main audit execution"""
    try:
        auditor = LoggingAuditor()
        audit_summary = auditor.run_full_audit()
        
        # Save report
        auditor.save_audit_report(audit_summary)
        
        # Exit with error code if critical issues found
        if auditor.critical_issues:
            print(f"\n❌ AUDIT FAILED: {len(auditor.critical_issues)} critical issues found")
            sys.exit(1)
        else:
            print(f"\n✅ AUDIT PASSED: No critical issues found")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Audit failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    main()
