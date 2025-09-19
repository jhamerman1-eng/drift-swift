#!/usr/bin/env python3
"""
Logging Monitoring and Maintenance for Drift Trading Bots
Monitors log health, rotation, and provides maintenance recommendations
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

try:
    from logging_config import (
        ensure_log_directory,
        cleanup_old_logs,
        CRITICAL_LOGGERS,
        NON_CRITICAL_LOGGERS
    )
except ImportError:
    print("❌ Could not import logging_config. Make sure libs/logging_config.py exists.")
    sys.exit(1)

class LoggingMonitor:
    """Monitor and maintain logging system health"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.log_dir = ensure_log_directory()
        self.monitoring_results = {}
        
        # Monitoring thresholds
        self.MAX_LOG_SIZE_MB = 100  # 100MB
        self.MAX_LOG_AGE_DAYS = 30  # 30 days
        self.CRITICAL_LOG_SIZE_MB = 500  # 500MB
        
    def check_log_health(self) -> Dict[str, Any]:
        """Check overall log health"""
        print("🔍 Checking Log Health...")
        print("=" * 60)
        
        log_files = list(self.log_dir.glob("*.log*"))
        total_size = 0
        health_issues = []
        warnings = []
        
        for log_file in sorted(log_files):
            try:
                size = log_file.stat().st_size
                total_size += size
                mtime = log_file.stat().st_mtime
                age_days = (time.time() - mtime) / (24 * 60 * 60)
                
                file_info = {
                    'name': log_file.name,
                    'size_bytes': size,
                    'size_mb': size / (1024 * 1024),
                    'modified': mtime,
                    'age_days': age_days,
                    'status': 'OK'
                }
                
                # Check for issues
                if size > (self.CRITICAL_LOG_SIZE_MB * 1024 * 1024):
                    file_info['status'] = 'CRITICAL'
                    health_issues.append(f"{log_file.name}: CRITICAL size ({size / (1024 * 1024):.1f} MB)")
                elif size > (self.MAX_LOG_SIZE_MB * 1024 * 1024):
                    file_info['status'] = 'WARNING'
                    warnings.append(f"{log_file.name}: Large size ({size / (1024 * 1024):.1f} MB)")
                
                if age_days > self.MAX_LOG_AGE_DAYS:
                    file_info['status'] = 'WARNING'
                    warnings.append(f"{log_file.name}: Old file ({age_days:.1f} days)")
                
                self.monitoring_results[log_file.name] = file_info
                
                # Display status
                status_icon = {
                    'OK': '✅',
                    'WARNING': '⚠️',
                    'CRITICAL': '🚨'
                }
                print(f"{status_icon[file_info['status']]} {log_file.name}: {size / (1024 * 1024):.2f} MB, {age_days:.1f} days old")
                
            except Exception as e:
                health_issues.append(f"{log_file.name}: Error - {e}")
                print(f"❌ {log_file.name}: Error - {e}")
        
        print(f"\n📊 Total log files: {len(log_files)}")
        print(f"📊 Total size: {total_size / (1024 * 1024):.2f} MB")
        
        if health_issues:
            print(f"\n🚨 Health Issues: {len(health_issues)}")
            for issue in health_issues:
                print(f"   • {issue}")
        
        if warnings:
            print(f"\n⚠️  Warnings: {len(warnings)}")
            for warning in warnings:
                print(f"   • {warning}")
        
        return {
            'total_files': len(log_files),
            'total_size_mb': total_size / (1024 * 1024),
            'health_issues': health_issues,
            'warnings': warnings,
            'file_details': self.monitoring_results
        }
    
    def check_log_rotation(self) -> Dict[str, Any]:
        """Check if log rotation is working properly"""
        print("\n🔄 Checking Log Rotation...")
        print("=" * 60)
        
        rotation_issues = []
        rotation_warnings = []
        
        for logger_name in CRITICAL_LOGGERS:
            log_file = self.log_dir / f"{logger_name}.log"
            backup_files = list(self.log_dir.glob(f"{logger_name}.log.*"))
            
            if log_file.exists():
                main_size = log_file.stat().st_size
                
                if main_size > (50 * 1024 * 1024):  # 50MB
                    if not backup_files:
                        rotation_issues.append(f"{logger_name}: Main log is large ({main_size / (1024 * 1024):.1f} MB) but no backups found")
                    else:
                        print(f"✅ {logger_name}: Main log {main_size / (1024 * 1024):.1f} MB, {len(backup_files)} backups")
                else:
                    print(f"✅ {logger_name}: Main log size OK ({main_size / (1024 * 1024):.1f} MB)")
            else:
                rotation_warnings.append(f"{logger_name}: No log file found")
        
        return {
            'rotation_issues': rotation_issues,
            'rotation_warnings': rotation_warnings
        }
    
    def check_log_content_quality(self) -> Dict[str, Any]:
        """Check log content quality and patterns"""
        print("\n📊 Checking Log Content Quality...")
        print("=" * 60)
        
        quality_issues = []
        quality_warnings = []
        
        for logger_name in CRITICAL_LOGGERS:
            log_file = self.log_dir / f"{logger_name}.log"
            
            if log_file.exists() and log_file.stat().st_size > 0:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    if not lines:
                        quality_warnings.append(f"{logger_name}: Log file is empty")
                        continue
                    
                    # Check for error patterns
                    error_lines = [line for line in lines if 'ERROR' in line or 'CRITICAL' in line]
                    warning_lines = [line for line in lines if 'WARNING' in line]
                    
                    # Check for recent activity (last 24 hours)
                    recent_lines = 0
                    current_time = time.time()
                    
                    for line in lines[-100:]:  # Check last 100 lines
                        try:
                            # Try to parse timestamp from log line
                            if '|' in line:
                                timestamp_str = line.split('|')[0].strip()
                                # This is a simplified timestamp check
                                if any(time_str in timestamp_str for time_str in ['2025', '2024']):
                                    recent_lines += 1
                        except:
                            pass
                    
                    print(f"📄 {logger_name}: {len(lines)} lines, {len(error_lines)} errors, {len(warning_lines)} warnings")
                    
                    if len(error_lines) > 10:
                        quality_warnings.append(f"{logger_name}: High error count ({len(error_lines)})")
                    
                    if recent_lines < 5:
                        quality_warnings.append(f"{logger_name}: Low recent activity ({recent_lines} recent lines)")
                        
                except Exception as e:
                    quality_issues.append(f"{logger_name}: Error reading log - {e}")
            else:
                quality_warnings.append(f"{logger_name}: No log file or empty file")
        
        return {
            'quality_issues': quality_issues,
            'quality_warnings': quality_warnings
        }
    
    def perform_maintenance(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform log maintenance tasks"""
        print("\n🧹 Performing Log Maintenance...")
        print("=" * 60)
        
        maintenance_results = {
            'cleanup_performed': False,
            'files_removed': 0,
            'errors': []
        }
        
        if not dry_run:
            try:
                print("🧹 Cleaning up old log files...")
                cleanup_old_logs()
                maintenance_results['cleanup_performed'] = True
                print("✅ Cleanup completed")
            except Exception as e:
                maintenance_results['errors'].append(f"Cleanup error: {e}")
                print(f"❌ Cleanup error: {e}")
        else:
            print("🔍 DRY RUN: Would clean up old log files")
        
        return maintenance_results
    
    def generate_recommendations(self) -> List[str]:
        """Generate maintenance and improvement recommendations"""
        recommendations = []
        
        # Check total log size
        total_size = sum(info['size_mb'] for info in self.monitoring_results.values())
        if total_size > 1000:  # 1GB
            recommendations.append("🚨 CRITICAL: Total log size exceeds 1GB - implement aggressive cleanup")
        elif total_size > 500:  # 500MB
            recommendations.append("⚠️  WARNING: Total log size is large - consider cleanup")
        
        # Check for critical issues
        critical_files = [name for name, info in self.monitoring_results.items() if info['status'] == 'CRITICAL']
        if critical_files:
            recommendations.append(f"🚨 CRITICAL: {len(critical_files)} log files need immediate attention")
        
        # Check for warnings
        warning_files = [name for name, info in self.monitoring_results.items() if info['status'] == 'WARNING']
        if warning_files:
            recommendations.append(f"⚠️  WARNING: {len(warning_files)} log files have warnings")
        
        # General recommendations
        recommendations.extend([
            "📊 MONITORING: Set up automated log monitoring and alerting",
            "🔄 ROTATION: Ensure all critical loggers have proper rotation configured",
            "🧹 MAINTENANCE: Run log cleanup weekly to prevent disk space issues",
            "📈 ANALYSIS: Consider log aggregation and analysis tools for better insights"
        ])
        
        return recommendations
    
    def run_full_monitoring(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run complete logging monitoring and maintenance"""
        print("🔍 DRIFT TRADING BOTS - LOGGING MONITORING")
        print("=" * 60)
        print(f"📁 Log directory: {self.log_dir}")
        print(f"🔍 Dry run: {'Yes' if dry_run else 'No'}")
        print()
        
        # Run all monitoring checks
        health_results = self.check_log_health()
        rotation_results = self.check_log_rotation()
        quality_results = self.check_log_content_quality()
        maintenance_results = self.perform_maintenance(dry_run)
        
        # Compile results
        monitoring_summary = {
            'timestamp': datetime.now().isoformat(),
            'health_check': health_results,
            'rotation_check': rotation_results,
            'quality_check': quality_results,
            'maintenance': maintenance_results,
            'recommendations': self.generate_recommendations()
        }
        
        # Print summary
        print("\n📋 MONITORING SUMMARY")
        print("=" * 60)
        print(f"🔍 Health issues: {len(health_results['health_issues'])}")
        print(f"🔄 Rotation issues: {len(rotation_results['rotation_issues'])}")
        print(f"📊 Quality issues: {len(quality_results['quality_issues'])}")
        print(f"🧹 Maintenance performed: {maintenance_results['cleanup_performed']}")
        
        # Print recommendations
        if monitoring_summary['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in monitoring_summary['recommendations']:
                print(f"   • {rec}")
        
        # Determine overall status
        total_issues = (
            len(health_results['health_issues']) +
            len(rotation_results['rotation_issues']) +
            len(quality_results['quality_issues'])
        )
        
        if total_issues == 0:
            print(f"\n✅ MONITORING PASSED: All systems healthy")
            return_code = 0
        else:
            print(f"\n⚠️  MONITORING COMPLETED: {total_issues} issues found")
            return_code = 1
        
        return monitoring_summary, return_code
    
    def save_monitoring_report(self, monitoring_summary: Dict[str, Any], filename: str = "logging_monitoring_report.json"):
        """Save monitoring report to file"""
        try:
            report_path = self.log_dir / filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(monitoring_summary, f, indent=2, default=str)
            
            print(f"\n💾 Monitoring report saved to: {report_path}")
            
        except Exception as e:
            print(f"❌ Failed to save monitoring report: {e}")

def main():
    """Main monitoring execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor and maintain logging system")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--maintenance-only", action="store_true", help="Only perform maintenance tasks")
    
    args = parser.parse_args()
    
    try:
        monitor = LoggingMonitor()
        
        if args.maintenance_only:
            # Only run maintenance
            maintenance_results = monitor.perform_maintenance(dry_run=args.dry_run)
            if maintenance_results['errors']:
                print(f"\n❌ Maintenance completed with errors: {len(maintenance_results['errors'])}")
                sys.exit(1)
            else:
                print(f"\n✅ Maintenance completed successfully")
                sys.exit(0)
        else:
            # Run full monitoring
            monitoring_summary, return_code = monitor.run_full_monitoring(dry_run=args.dry_run)
            
            # Save report
            monitor.save_monitoring_report(monitoring_summary)
            
            sys.exit(return_code)
            
    except Exception as e:
        print(f"❌ Monitoring failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

