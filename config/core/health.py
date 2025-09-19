"""
Health Checks

Comprehensive health validation with severity levels and mocked testing support.
Validates RPC, Swift, wallet, and system readiness before trading.
"""

import asyncio
import aiohttp
import socket
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Union
from pathlib import Path
import logging
import time

from ..secrets import load_keypair, validate_keypair_file, KeypairError


@dataclass
class HealthCheck:
    """
    Individual health check result
    """
    name: str
    passed: bool
    message: str
    severity: str = "warn"  # "critical" or "warn"
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """
    Comprehensive health checking system with severity-based policies
    """
    
    def __init__(self, mock_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.mock_mode = mock_mode
        self._mock_responses: Dict[str, Dict[str, Any]] = {}
    
    def set_mock_response(self, check_name: str, passed: bool, message: str, details: Optional[Dict] = None):
        """Set mock response for testing"""
        self._mock_responses[check_name] = {
            "passed": passed,
            "message": message,
            "details": details or {}
        }
    
    async def check_rpc_endpoint(self, url: str, timeout: int = 30) -> HealthCheck:
        """
        Check RPC endpoint health
        
        Args:
            url: RPC endpoint URL
            timeout: Timeout in seconds
            
        Returns:
            HealthCheck result
        """
        start_time = time.time()
        
        if self.mock_mode and "rpc" in self._mock_responses:
            mock = self._mock_responses["rpc"]
            return HealthCheck(
                name="RPC Endpoint",
                passed=mock["passed"],
                message=mock["message"],
                severity="critical",
                duration_ms=(time.time() - start_time) * 1000,
                details=mock["details"]
            )
        
        try:
            # Test RPC with getHealth method
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(url, json=payload) as response:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        if "result" in data and data["result"] == "ok":
                            return HealthCheck(
                                name="RPC Endpoint",
                                passed=True,
                                message=f"RPC healthy: {url}",
                                severity="critical",
                                duration_ms=duration_ms,
                                details={"url": url, "status": response.status}
                            )
                        else:
                            return HealthCheck(
                                name="RPC Endpoint",
                                passed=False,
                                message=f"RPC unhealthy response: {data}",
                                severity="critical",
                                duration_ms=duration_ms,
                                details={"url": url, "response": data}
                            )
                    else:
                        return HealthCheck(
                            name="RPC Endpoint",
                            passed=False,
                            message=f"RPC returned HTTP {response.status}",
                            severity="critical",
                            duration_ms=duration_ms,
                            details={"url": url, "status": response.status}
                        )
                        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="RPC Endpoint",
                passed=False,
                message=f"RPC timeout after {timeout}s",
                severity="critical",
                duration_ms=duration_ms,
                details={"url": url, "timeout": timeout}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="RPC Endpoint",
                passed=False,
                message=f"RPC connection failed: {e}",
                severity="critical",
                duration_ms=duration_ms,
                details={"url": url, "error": str(e)}
            )
    
    async def check_swift_sidecar(self, base_url: str, timeout: int = 5) -> HealthCheck:
        """
        Check Swift sidecar health
        
        Args:
            base_url: Swift sidecar base URL
            timeout: Timeout in seconds
            
        Returns:
            HealthCheck result
        """
        start_time = time.time()
        
        if self.mock_mode and "swift" in self._mock_responses:
            mock = self._mock_responses["swift"]
            return HealthCheck(
                name="Swift Sidecar",
                passed=mock["passed"],
                message=mock["message"],
                severity="warn",
                duration_ms=(time.time() - start_time) * 1000,
                details=mock["details"]
            )
        
        try:
            health_url = f"{base_url.rstrip('/')}/health"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(health_url) as response:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return HealthCheck(
                                name="Swift Sidecar",
                                passed=True,
                                message=f"Swift sidecar healthy: {base_url}",
                                severity="warn",
                                duration_ms=duration_ms,
                                details={"url": base_url, "response": data}
                            )
                        except:
                            # Health endpoint exists but no JSON response
                            return HealthCheck(
                                name="Swift Sidecar",
                                passed=True,
                                message=f"Swift sidecar responding: {base_url}",
                                severity="warn",
                                duration_ms=duration_ms,
                                details={"url": base_url, "status": response.status}
                            )
                    else:
                        return HealthCheck(
                            name="Swift Sidecar",
                            passed=False,
                            message=f"Swift sidecar returned HTTP {response.status}",
                            severity="warn",
                            duration_ms=duration_ms,
                            details={"url": base_url, "status": response.status}
                        )
                        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Swift Sidecar",
                passed=False,
                message=f"Swift sidecar timeout after {timeout}s",
                severity="warn",
                duration_ms=duration_ms,
                details={"url": base_url, "timeout": timeout}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Swift Sidecar",
                passed=False,
                message=f"Swift sidecar connection failed: {e}",
                severity="warn",
                duration_ms=duration_ms,
                details={"url": base_url, "error": str(e)}
            )
    
    def check_wallet_file(self, file_path: Optional[Union[str, Path]] = None) -> HealthCheck:
        """
        Check wallet file health
        
        Args:
            file_path: Optional specific file path to check
            
        Returns:
            HealthCheck result
        """
        start_time = time.time()
        
        if self.mock_mode and "wallet" in self._mock_responses:
            mock = self._mock_responses["wallet"]
            return HealthCheck(
                name="Wallet File",
                passed=mock["passed"],
                message=mock["message"],
                severity="critical",
                duration_ms=(time.time() - start_time) * 1000,
                details=mock["details"]
            )
        
        try:
            if file_path:
                # Check specific file
                validation = validate_keypair_file(file_path)
                duration_ms = (time.time() - start_time) * 1000
                
                if validation["format_valid"] and validation["permissions_ok"]:
                    return HealthCheck(
                        name="Wallet File",
                        passed=True,
                        message=f"Wallet file valid: {file_path}",
                        severity="critical",
                        duration_ms=duration_ms,
                        details={
                            "file_path": str(file_path),
                            "public_key": validation["public_key"]
                        }
                    )
                else:
                    errors = validation.get("errors", [])
                    return HealthCheck(
                        name="Wallet File",
                        passed=False,
                        message=f"Wallet file invalid: {'; '.join(errors)}",
                        severity="critical",
                        duration_ms=duration_ms,
                        details=validation
                    )
            else:
                # Try to load from standard locations
                keypair_info = load_keypair()
                duration_ms = (time.time() - start_time) * 1000
                
                return HealthCheck(
                    name="Wallet File",
                    passed=keypair_info.validated,
                    message=f"Wallet loaded from {keypair_info.source}",
                    severity="critical",
                    duration_ms=duration_ms,
                    details={
                        "source": keypair_info.source,
                        "public_key": keypair_info.public_key,
                        "permissions_ok": keypair_info.permissions_ok
                    }
                )
                
        except KeypairError as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Wallet File",
                passed=False,
                message=f"Wallet error: {e}",
                severity="critical",
                duration_ms=duration_ms,
                details={"error": str(e)}
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Wallet File",
                passed=False,
                message=f"Wallet check failed: {e}",
                severity="critical",
                duration_ms=duration_ms,
                details={"error": str(e)}
            )
    
    def check_network_connectivity(self) -> HealthCheck:
        """
        Check basic network connectivity
        
        Returns:
            HealthCheck result
        """
        start_time = time.time()
        
        if self.mock_mode and "network" in self._mock_responses:
            mock = self._mock_responses["network"]
            return HealthCheck(
                name="Network Connectivity",
                passed=mock["passed"],
                message=mock["message"],
                severity="critical",
                duration_ms=(time.time() - start_time) * 1000,
                details=mock["details"]
            )
        
        try:
            # Try to resolve a reliable DNS name
            socket.gethostbyname("google.com")
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheck(
                name="Network Connectivity",
                passed=True,
                message="Network connectivity OK",
                severity="critical",
                duration_ms=duration_ms,
                details={"test": "DNS resolution"}
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Network Connectivity",
                passed=False,
                message=f"Network connectivity failed: {e}",
                severity="critical",
                duration_ms=duration_ms,
                details={"error": str(e)}
            )
    
    def check_disk_space(self, min_free_gb: float = 1.0) -> HealthCheck:
        """
        Check available disk space
        
        Args:
            min_free_gb: Minimum free space in GB
            
        Returns:
            HealthCheck result
        """
        start_time = time.time()
        
        if self.mock_mode and "disk" in self._mock_responses:
            mock = self._mock_responses["disk"]
            return HealthCheck(
                name="Disk Space",
                passed=mock["passed"],
                message=mock["message"],
                severity="warn",
                duration_ms=(time.time() - start_time) * 1000,
                details=mock["details"]
            )
        
        try:
            import shutil
            free_bytes = shutil.disk_usage(".").free
            free_gb = free_bytes / (1024 ** 3)
            duration_ms = (time.time() - start_time) * 1000
            
            if free_gb >= min_free_gb:
                return HealthCheck(
                    name="Disk Space",
                    passed=True,
                    message=f"Disk space OK: {free_gb:.1f}GB free",
                    severity="warn",
                    duration_ms=duration_ms,
                    details={"free_gb": free_gb, "min_required_gb": min_free_gb}
                )
            else:
                return HealthCheck(
                    name="Disk Space",
                    passed=False,
                    message=f"Low disk space: {free_gb:.1f}GB free (need {min_free_gb}GB)",
                    severity="warn",
                    duration_ms=duration_ms,
                    details={"free_gb": free_gb, "min_required_gb": min_free_gb}
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="Disk Space",
                passed=False,
                message=f"Disk space check failed: {e}",
                severity="warn",
                duration_ms=duration_ms,
                details={"error": str(e)}
            )


async def run_health_checks(
    rpc_url: Optional[str] = None,
    swift_url: Optional[str] = None,
    wallet_path: Optional[Union[str, Path]] = None,
    mock_mode: bool = False
) -> Dict[str, Any]:
    """
    Run comprehensive health checks
    
    Args:
        rpc_url: RPC endpoint to test
        swift_url: Swift sidecar URL to test
        wallet_path: Wallet file path to test
        mock_mode: Use mocked responses for testing
        
    Returns:
        Dictionary with health check results and summary
    """
    checker = HealthChecker(mock_mode=mock_mode)
    results = []
    
    # Network connectivity (always run first)
    results.append(checker.check_network_connectivity())
    
    # RPC endpoint check
    if rpc_url:
        results.append(await checker.check_rpc_endpoint(rpc_url))
    
    # Swift sidecar check
    if swift_url:
        results.append(await checker.check_swift_sidecar(swift_url))
    
    # Wallet check
    results.append(checker.check_wallet_file(wallet_path))
    
    # Disk space check
    results.append(checker.check_disk_space())
    
    # Categorize results
    critical_checks = [r for r in results if r.severity == "critical"]
    warning_checks = [r for r in results if r.severity == "warn"]
    
    critical_failures = [r for r in critical_checks if not r.passed]
    warning_failures = [r for r in warning_checks if not r.passed]
    
    # Overall status
    overall_healthy = len(critical_failures) == 0
    
    summary = {
        "healthy": overall_healthy,
        "total_checks": len(results),
        "passed_checks": len([r for r in results if r.passed]),
        "critical_failures": len(critical_failures),
        "warning_failures": len(warning_failures),
        "total_duration_ms": sum(r.duration_ms or 0 for r in results),
        "checks": results,
        "should_proceed": len(critical_failures) == 0  # Fail-fast only on criticals
    }
    
    return summary


def format_health_report(health_results: Dict[str, Any]) -> str:
    """
    Format health check results into a readable report
    
    Args:
        health_results: Results from run_health_checks
        
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("🏥 HEALTH CHECK REPORT")
    lines.append("=" * 50)
    
    summary = health_results
    lines.append(f"Overall Status: {'✅ HEALTHY' if summary['healthy'] else '❌ UNHEALTHY'}")
    lines.append(f"Total Checks: {summary['total_checks']}")
    lines.append(f"Passed: {summary['passed_checks']}")
    lines.append(f"Critical Failures: {summary['critical_failures']}")
    lines.append(f"Warning Failures: {summary['warning_failures']}")
    lines.append(f"Total Duration: {summary['total_duration_ms']:.1f}ms")
    lines.append("")
    
    # Individual check results
    for check in summary['checks']:
        status_icon = "✅" if check.passed else ("❌" if check.severity == "critical" else "⚠️")
        severity_label = f"[{check.severity.upper()}]"
        duration = f"({check.duration_ms:.1f}ms)" if check.duration_ms else ""
        
        lines.append(f"{status_icon} {check.name} {severity_label} {duration}")
        lines.append(f"   {check.message}")
        
        if check.details and not check.passed:
            for key, value in check.details.items():
                if key != "error":  # Don't duplicate error message
                    lines.append(f"   {key}: {value}")
        lines.append("")
    
    # Recommendations
    if not summary['healthy']:
        lines.append("🔧 RECOMMENDATIONS:")
        critical_failures = [r for r in summary['checks'] if r.severity == "critical" and not r.passed]
        
        if critical_failures:
            lines.append("Critical issues must be resolved before proceeding:")
            for check in critical_failures:
                lines.append(f"   • {check.name}: {check.message}")
        
        warning_failures = [r for r in summary['checks'] if r.severity == "warn" and not r.passed]
        if warning_failures:
            lines.append("Warnings (can proceed but should be addressed):")
            for check in warning_failures:
                lines.append(f"   • {check.name}: {check.message}")
    
    return "\n".join(lines)
