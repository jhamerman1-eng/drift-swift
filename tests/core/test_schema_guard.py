"""
Schema Guard Tests - Prevent accidental changes to core settings schema.

This test ensures the core settings schema hasn't changed unexpectedly.
Update EXPECTED when you *intentionally* change CoreSettings.
"""

from core.schema import schema_checksum

# UPDATE THIS VALUE when you make *intentional* changes to the core settings schema
# Run: python -c "from core.schema import schema_checksum; print(schema_checksum())"
# Then update EXPECTED with the printed value
EXPECTED = "PLACEHOLDER_UPDATE_THIS_AFTER_FIRST_RUN"

def test_core_schema_has_not_changed():
    """
    Test that the core schema hasn't changed unexpectedly.

    If this test fails, it means the core settings schema has been modified.
    This could be either:
    1. An accidental change that should be reverted, or
    2. An intentional change that requires updating EXPECTED

    For intentional changes:
    1. Run: python -c "from core.schema import schema_checksum; print(schema_checksum())"
    2. Update EXPECTED with the new checksum
    3. Update the schema documentation in docs/core_schema.md
    4. Notify the team about the breaking change
    """
    current = schema_checksum()

    # This assertion will fail if schema has changed
    assert current == EXPECTED, (
        f"Core schema has changed! Current checksum: {current}\n"
        "This indicates a modification to the core settings structure.\n"
        "If this change was intentional:\n"
        "1. Update EXPECTED with the new checksum\n"
        "2. Update docs/core_schema.md\n"
        "3. Notify team of breaking change\n"
        "If this was accidental, revert the schema changes."
    )

def test_schema_checksum_is_valid():
    """Test that schema checksum generation works correctly."""
    checksum = schema_checksum()

    # Checksum should be a valid SHA256 hex string
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA256 is 64 characters
    assert checksum.isalnum()  # Should only contain alphanumeric characters
    assert all(c in '0123456789abcdef' for c in checksum.lower())  # Should be hex

def test_schema_is_deterministic():
    """Test that schema generation is deterministic."""
    checksum1 = schema_checksum()
    checksum2 = schema_checksum()

    # Multiple calls should produce the same checksum
    assert checksum1 == checksum2, "Schema checksum should be deterministic"
