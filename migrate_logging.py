#!/usr/bin/env python3
"""
Logging Migration Script for Drift Trading Bots
Migrates applications from basicConfig to centralized logging system
"""

import os
import sys
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Add libs to path
sys.path.insert(0, str(Path(__file__).parent / "libs"))

try:
    from logging_config import (
        setup_critical_logging,
        setup_utility_logging,
        CRITICAL_LOGGERS,
        NON_CRITICAL_LOGGERS
    )
except ImportError:
    print("❌ Could not import logging_config. Make sure libs/logging_config.py exists.")
    sys.exit(1)

class LoggingMigrator:
    """Migrate applications from basicConfig to centralized logging"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / "backups" / "logging_migration"
        self.migration_results = []
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_file(self, file_path: Path) -> Path:
        """Create a backup of the original file"""
        backup_path = self.backup_dir / f"{file_path.name}.backup"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def is_critical_application(self, file_path: Path) -> bool:
        """Determine if a file is a critical application"""
        critical_patterns = [
            r"run_.*_bot",
            r"launch_.*_beta",
            r"run_all_bots",
            r"libs/.*",
            r"orchestrator/.*"
        ]
        
        file_str = str(file_path)
        for pattern in critical_patterns:
            if re.search(pattern, file_str):
                return True
        
        return False
    
    def migrate_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate a single file from basicConfig to centralized logging"""
        result = {
            'file': str(file_path),
            'migrated': False,
            'backup_created': False,
            'changes_made': [],
            'errors': []
        }
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            changes = []
            
            # Check if file needs migration
            if 'logging.basicConfig' not in content:
                result['changes_made'].append("No basicConfig found - no migration needed")
                return result
            
            # Create backup
            if not dry_run:
                backup_path = self.backup_file(file_path)
                result['backup_created'] = True
                result['changes_made'].append(f"Backup created: {backup_path.name}")
            
            # Determine application type and logger name
            is_critical = self.is_critical_application(file_path)
            
            # Generate logger name based on file path
            logger_name = self.generate_logger_name(file_path)
            
            # Replace logging.basicConfig with centralized logging
            new_content = self.replace_logging_config(content, logger_name, is_critical)
            
            if new_content != original_content:
                changes.append("Replaced logging.basicConfig with centralized logging")
                
                # Update logger usage
                new_content = self.update_logger_usage(new_content, logger_name)
                changes.append("Updated logger usage throughout file")
                
                # Mark as migrated
                result['migrated'] = True
                result['changes_made'].extend(changes)
                
                # Write changes if not dry run
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            else:
                result['changes_made'].append("No changes needed")
                
        except Exception as e:
            result['errors'].append(f"Migration error: {e}")
        
        return result
    
    def extract_logger_name(self, file_path: Path, content: str) -> str:
        """Extract logger name from existing logging configuration"""
        # Look for existing logger name
        logger_match = re.search(r'logger\s*=\s*logging\.getLogger\([\'"]([^\'"]+)[\'"]\)', content)
        if logger_match:
            return logger_match.group(1)
        
        # Look for logger name in comments or docstring
        logger_match = re.search(r'logger.*?[\'"]([^\'"]+)[\'"]', content)
        if logger_match:
            return logger_match.group(1)
        
        return ""
    
    def generate_logger_name(self, file_path: Path) -> str:
        """Generate a logger name based on file path"""
        # Remove .py extension and convert to logger name
        name = file_path.stem
        
        # Convert to snake_case if needed
        name = re.sub(r'([a-z])([A-Z])', r'\1-\2', name).lower()
        
        # Map common names to standard logger names
        name_mapping = {
            'run_mm_bot_v2': 'jit-mm-swift',
            'run_mm_bot': 'jit-mm-swift',
            'run_mm_bot_enhanced': 'jit-mm-swift',
            'launch_hedge_beta': 'hedge-bot',
            'launch_trend_beta': 'trend-bot',
            'run_all_bots': 'orchestrator'
        }
        
        return name_mapping.get(name, name)
    
    def replace_logging_config(self, content: str, logger_name: str, is_critical: bool) -> str:
        """Replace logging.basicConfig with centralized logging setup"""
        # Remove logging.basicConfig lines and related code
        lines = content.split('\n')
        new_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if we're starting basicConfig
            if 'logging.basicConfig(' in line:
                # Skip the basicConfig line and all related lines until closing parenthesis
                i += 1
                while i < len(lines) and ')' not in lines[i]:
                    i += 1
                # Skip the closing parenthesis line
                i += 1
                
                # Also skip the logger = logging.getLogger line if it follows
                if i < len(lines) and 'logger = logging.getLogger' in lines[i]:
                    i += 1
                
                continue
            
            new_lines.append(line)
            i += 1
        
        # Add centralized logging setup
        if is_critical:
            setup_code = f"""# Setup centralized logging
from libs.logging_config import setup_critical_logging
logger = setup_critical_logging("{logger_name}")"""
        else:
            setup_code = f"""# Setup centralized logging
from libs.logging_config import setup_utility_logging
logger = setup_utility_logging("{logger_name}")"""
        
        # Find the right place to insert the logging setup
        # Look for imports section
        import_section_end = 0
        for i, line in enumerate(new_lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_section_end = i + 1
        
        # Insert logging setup after imports
        new_lines.insert(import_section_end, setup_code)
        
        return '\n'.join(new_lines)
    
    def update_logger_usage(self, content: str, logger_name: str) -> str:
        """Update logger usage throughout the file"""
        # Replace print statements with logger calls where appropriate
        # This is a basic replacement - more sophisticated logic could be added
        
        # Replace print statements that look like logging
        content = re.sub(
            r'print\([\'"](ERROR|WARNING|INFO|DEBUG|CRITICAL):\s*([^\'"]+)[\'"]\)',
            r'logger.error("\2")',
            content
        )
        
        # Replace other print statements with info level
        content = re.sub(
            r'print\([\'"]([^\'"]+)[\'"]\)',
            r'logger.info("\1")',
            content
        )
        
        return content
    
    def migrate_critical_applications(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Migrate all critical applications"""
        print("🔧 Migrating Critical Applications...")
        print("=" * 60)
        
        critical_files = [
            "run_mm_bot_v2.py",
            "run_mm_bot.py", 
            "run_mm_bot_enhanced.py",
            "launch_hedge_beta.py",
            "launch_trend_beta.py",
            "run_all_bots.py"
        ]
        
        results = []
        for file_name in critical_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"📁 Migrating: {file_name}")
                result = self.migrate_file(file_path, dry_run)
                results.append(result)
                
                if result['migrated']:
                    print(f"   ✅ Migrated successfully")
                elif result['errors']:
                    print(f"   ❌ Errors: {', '.join(result['errors'])}")
                else:
                    print(f"   ⚠️  No changes made")
                    
            else:
                print(f"⚠️  File not found: {file_name}")
        
        return results
    
    def migrate_utility_applications(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Migrate utility applications"""
        print("\n🔧 Migrating Utility Applications...")
        print("=" * 60)
        
        utility_files = [
            "check_drift_trades.py",
            "devnet_test_connection.py",
            "test_monitoring.py",
            "test_rpc_health.py"
        ]
        
        results = []
        for file_name in utility_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                print(f"📁 Migrating: {file_name}")
                result = self.migrate_file(file_path, dry_run)
                results.append(result)
                
                if result['migrated']:
                    print(f"   ✅ Migrated successfully")
                elif result['errors']:
                    print(f"   ❌ Errors: {', '.join(result['errors'])}")
                else:
                    print(f"   ⚠️  No changes made")
                    
            else:
                print(f"⚠️  File not found: {file_name}")
        
        return results
    
    def run_migration(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run complete migration"""
        print("🔧 DRIFT TRADING BOTS - LOGGING MIGRATION")
        print("=" * 60)
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 Backup directory: {self.backup_dir}")
        print(f"🔍 Dry run: {'Yes' if dry_run else 'No'}")
        print()
        
        if dry_run:
            print("⚠️  DRY RUN MODE - No files will be modified")
            print()
        
        # Run migrations
        critical_results = self.migrate_critical_applications(dry_run)
        utility_results = self.migrate_utility_applications(dry_run)
        
        # Compile results
        migration_summary = {
            'critical_applications': critical_results,
            'utility_applications': utility_results,
            'total_migrated': sum(1 for r in critical_results + utility_results if r['migrated']),
            'total_errors': sum(1 for r in critical_results + utility_results if r['errors']),
            'backup_directory': str(self.backup_dir)
        }
        
        # Print summary
        print("\n📋 MIGRATION SUMMARY")
        print("=" * 60)
        print(f"🔧 Critical applications migrated: {sum(1 for r in critical_results if r['migrated'])}")
        print(f"🔧 Utility applications migrated: {sum(1 for r in utility_results if r['migrated'])}")
        print(f"📁 Total migrated: {migration_summary['total_migrated']}")
        print(f"❌ Total errors: {migration_summary['total_errors']}")
        
        if not dry_run:
            print(f"\n💾 Backups saved to: {self.backup_dir}")
            print("💡 Run 'python audit_logging.py' to verify the migration")
        
        return migration_summary

def main():
    """Main migration execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate logging configuration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    try:
        migrator = LoggingMigrator()
        migration_summary = migrator.run_migration(dry_run=args.dry_run)
        
        if migration_summary['total_errors'] > 0:
            print(f"\n❌ MIGRATION COMPLETED WITH ERRORS: {migration_summary['total_errors']} errors")
            sys.exit(1)
        else:
            print(f"\n✅ MIGRATION COMPLETED SUCCESSFULLY")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
