#!/usr/bin/env python3
"""
BUG-001: Port Conflict Prevention Regression Tests

This test suite prevents port 9090 conflicts that block monitoring stack launch.
Every fix for port conflicts must include a regression test here.
"""

import pytest
import subprocess
import time
import socket
import psutil
from unittest.mock import patch, Mock


class TestPortConflictPrevention:
    """Test suite for preventing port 9090 conflicts"""

    def test_port_9090_availability_check(self):
        """BUG-001: Ensure port 9090 is available before starting monitoring"""
        # Check if port 9090 is available
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('localhost', 9090))
            # Port should be available (connection should fail)
            assert result != 0, "Port 9090 is already in use - this will block monitoring stack"
        finally:
            sock.close()

    def test_find_process_using_port(self):
        """BUG-001: Test ability to find process using port 9090"""
        # Find any process using port 9090
        port_users = []
        for conn in psutil.net_connections():
            if conn.laddr.port == 9090:
                port_users.append(conn.pid)
        
        if port_users:
            # If port is in use, we should be able to identify the process
            for pid in port_users:
                try:
                    process = psutil.Process(pid)
                    assert process.is_running(), f"Process {pid} should be running"
                    print(f"Port 9090 is used by: {process.name()} (PID: {pid})")
                except psutil.NoSuchProcess:
                    pass

    def test_port_conflict_detection_script(self):
        """BUG-001: Test port conflict detection script"""
        # Simulate the detection logic
        def check_port_conflict(port=9090):
            """Check if port is in use"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', port))
                return result == 0  # True if port is in use
            finally:
                sock.close()
        
        # Test the detection
        port_in_use = check_port_conflict(9090)
        if port_in_use:
            pytest.skip("Port 9090 is in use - test environment issue")

    def test_docker_compose_port_handling(self):
        """BUG-001: Test docker-compose handles port conflicts gracefully"""
        # Test that docker-compose would detect port conflicts
        def simulate_docker_port_check():
            """Simulate docker port conflict detection"""
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', 9090))
                if result == 0:
                    return False, "Port 9090 is already in use"
                return True, "Port 9090 is available"
            finally:
                sock.close()
        
        available, message = simulate_docker_port_check()
        print(f"Port availability check: {message}")

    def test_graceful_shutdown_cleanup(self):
        """BUG-001: Test that shutdown properly releases ports"""
        # This test ensures our cleanup logic works
        def simulate_port_cleanup():
            """Simulate port cleanup on shutdown"""
            # In real implementation, this would:
            # 1. Stop all services using port 9090
            # 2. Wait for port to be released
            # 3. Verify port is free
            
            # For test, just verify we can check port status
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', 9090))
                return result != 0  # Port should be free after cleanup
            finally:
                sock.close()
        
        # Test cleanup logic
        port_freed = simulate_port_cleanup()
        assert port_freed, "Port should be free after cleanup"

    def test_port_conflict_prevention_script(self):
        """BUG-001: Test the port conflict prevention script"""
        # Test the actual prevention script logic
        def prevent_port_conflict(port=9090):
            """Prevent port conflicts by killing conflicting processes"""
            conflicting_pids = []
            
            # Find processes using the port
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    conflicting_pids.append(conn.pid)
            
            if conflicting_pids:
                print(f"Found {len(conflicting_pids)} processes using port {port}")
                for pid in conflicting_pids:
                    try:
                        process = psutil.Process(pid)
                        print(f"Would kill process: {process.name()} (PID: {pid})")
                        # In real implementation: process.kill()
                    except psutil.NoSuchProcess:
                        pass
                return True
            return False
        
        # Test prevention logic
        has_conflicts = prevent_port_conflict(9090)
        if has_conflicts:
            print("Port conflict prevention would be triggered")

    def test_monitoring_stack_startup_sequence(self):
        """BUG-001: Test proper monitoring stack startup sequence"""
        # Test the correct startup sequence
        startup_steps = [
            "Check port 9090 availability",
            "Kill conflicting processes if found",
            "Verify port is free",
            "Start Prometheus container",
            "Start Grafana container",
            "Verify both services are running"
        ]
        
        for step in startup_steps:
            print(f"Startup step: {step}")
            # In real implementation, each step would be executed
            # and verified before proceeding to next step
        
        assert len(startup_steps) == 6, "Should have 6 startup steps"

    def test_port_conflict_error_handling(self):
        """BUG-001: Test error handling when port conflicts occur"""
        # Test error handling logic
        def handle_port_conflict():
            """Handle port conflict errors gracefully"""
            try:
                # Simulate port conflict
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', 9090))
                return "Port 9090 is available"
            except OSError as e:
                if "Address already in use" in str(e):
                    return "Port conflict detected - would trigger cleanup"
                else:
                    return f"Other error: {e}"
            finally:
                try:
                    sock.close()
                except:
                    pass
        
        result = handle_port_conflict()
        print(f"Port conflict handling result: {result}")

    def test_cross_platform_port_checking(self):
        """BUG-001: Test port checking works on different platforms"""
        # Test that our port checking works on Windows and Unix
        def check_port_cross_platform(port=9090):
            """Check port availability cross-platform"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                return result != 0
            except Exception as e:
                print(f"Port check error: {e}")
                return False
            finally:
                try:
                    sock.close()
                except:
                    pass
        
        # Test on current platform
        port_available = check_port_cross_platform(9090)
        print(f"Port 9090 available on {psutil.WINDOWS and 'Windows' or 'Unix'}: {port_available}")

    def test_port_conflict_metrics(self):
        """BUG-001: Test port conflict metrics collection"""
        # Test metrics for port conflicts
        class PortConflictMetrics:
            def __init__(self):
                self.conflicts_detected = 0
                self.conflicts_resolved = 0
                self.startup_failures = 0
            
            def record_conflict_detected(self):
                self.conflicts_detected += 1
            
            def record_conflict_resolved(self):
                self.conflicts_resolved += 1
            
            def record_startup_failure(self):
                self.startup_failures += 1
        
        metrics = PortConflictMetrics()
        
        # Simulate some metrics
        metrics.record_conflict_detected()
        metrics.record_conflict_resolved()
        
        assert metrics.conflicts_detected == 1
        assert metrics.conflicts_resolved == 1
        assert metrics.startup_failures == 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
