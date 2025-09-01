#!/usr/bin/env python3
"""
Test script to verify Python version requirements for the project.
"""

import sys

def test_python_version():
    """Test that Python version meets project requirements."""
    required_version = (3, 10)
    current_version = sys.version_info

    print(f"Current Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    print(f"Required Python version: {required_version[0]}.{required_version[1]}+")

    if current_version >= required_version:
        print("✅ Python version requirement met!")
        return True
    else:
        print("❌ Python version too old!")
        print(f"   Need Python {required_version[0]}.{required_version[1]}+")
        print(f"   Found Python {current_version.major}.{current_version.minor}.{current_version.micro}")
        return False

def test_supported_versions():
    """Test that only supported Python versions are used."""
    supported_versions = [(3, 10), (3, 11)]
    current_version = sys.version_info[:2]  # (major, minor)

    print(f"Current Python version: {current_version[0]}.{current_version[1]}")

    if current_version in supported_versions:
        print("✅ Using supported Python version!")
        return True
    else:
        print("❌ Using unsupported Python version!")
        print(f"   Supported versions: {', '.join(f'{v[0]}.{v[1]}' for v in supported_versions)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Python Version Validation Test")
    print("=" * 50)

    version_ok = test_python_version()
    supported_ok = test_supported_versions()

    print("\n" + "=" * 50)
    if version_ok and supported_ok:
        print("🎉 All Python version checks passed!")
        sys.exit(0)
    else:
        print("❌ Python version validation failed!")
        sys.exit(1)


