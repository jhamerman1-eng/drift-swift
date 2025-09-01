#!/usr/bin/env python3
"""
Test script to verify PyYAML import works correctly in the test environment.
"""

def test_yaml_import():
    """Test that yaml can be imported and used."""
    try:
        import yaml
        print(f"✅ PyYAML imported successfully: version {yaml.__version__}")

        # Test basic YAML functionality
        test_data = {"test": "value", "number": 42}
        yaml_str = yaml.dump(test_data)
        parsed_data = yaml.safe_load(yaml_str)

        assert parsed_data["test"] == "value"
        assert parsed_data["number"] == 42

        print("✅ YAML dump/load functionality working")
        return True

    except ImportError as e:
        print(f"❌ PyYAML import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ YAML functionality test failed: {e}")
        return False

def test_conftest_import():
    """Test that conftest.py can be imported without issues."""
    try:
        import tests.conftest
        print("✅ conftest.py imported successfully")
        return True
    except ImportError as e:
        print(f"❌ conftest.py import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ conftest.py error: {e}")
        return False

if __name__ == "__main__":
    print("Testing PyYAML import and functionality...")
    yaml_ok = test_yaml_import()

    print("\nTesting conftest.py import...")
    conftest_ok = test_conftest_import()

    if yaml_ok and conftest_ok:
        print("\n🎉 All PyYAML tests passed! The dependency issue is resolved.")
    else:
        print("\n❌ Some tests failed. PyYAML dependency issue persists.")
        exit(1)


