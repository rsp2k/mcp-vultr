#!/usr/bin/env python3
"""
Simple test to check if enum imports work without casting issues.
"""

import sys
import os

def test_enum_import():
    """Test if we can import enum-related code without issues."""
    print("Testing enum-related imports...")

    try:
        # Test importing the enum definitions
        from app.models.project import ProjectRole, ProjectStatus
        print("✓ Successfully imported ProjectRole and ProjectStatus")

        # Test enum values
        viewer_role = ProjectRole.VIEWER
        active_status = ProjectStatus.ACTIVE
        print(f"✓ Can access enum values: {viewer_role}, {active_status}")

        # Test enum conversion
        viewer_str = ProjectRole.VIEWER.value
        active_str = ProjectStatus.ACTIVE.value
        print(f"✓ Can convert enums to strings: {viewer_str}, {active_str}")

        # Test enum creation from strings
        viewer_enum = ProjectRole(viewer_str)
        active_enum = ProjectStatus(active_str)
        print(f"✓ Can create enums from strings: {viewer_enum}, {active_enum}")

        return True

    except Exception as e:
        print(f"✗ Import/enum test failed: {e}")
        return False

def test_rbac_import():
    """Test if we can import RBAC code without enum casting issues."""
    print("\nTesting RBAC imports...")

    try:
        # Test importing the RBAC class
        from app.middleware.rbac import ProjectAccessControl, ROLE_HIERARCHY
        print("✓ Successfully imported ProjectAccessControl and ROLE_HIERARCHY")

        # Test accessing the role hierarchy
        print(f"✓ Role hierarchy: {ROLE_HIERARCHY}")

        return True

    except Exception as e:
        print(f"✗ RBAC import test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        enum_test_result = test_enum_import()
        rbac_test_result = test_rbac_import()

        if enum_test_result and rbac_test_result:
            print("\n🎉 All enum-related imports work correctly!")
            sys.exit(0)
        else:
            print("\n❌ Some enum-related imports failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)