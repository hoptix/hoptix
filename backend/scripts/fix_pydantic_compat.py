#!/usr/bin/env python3
"""
Compatibility fix for Pydantic v1/v2 issues with supabase/realtime packages.
This script patches the incompatibility if needed.
"""

import sys
import os


def patch_pydantic_import():
    """
    Monkey-patch pydantic to provide backwards compatibility for with_config.
    This is a temporary fix for the realtime package expecting Pydantic v1.
    """
    try:
        import pydantic

        # Check if we're on Pydantic v2
        if hasattr(pydantic, '__version__') and pydantic.__version__.startswith('2'):
            # Create a dummy with_config decorator that does nothing
            # This allows the import to succeed
            if not hasattr(pydantic, 'with_config'):
                def with_config(*args, **kwargs):
                    """Dummy decorator for Pydantic v1 compatibility."""
                    def decorator(cls):
                        return cls
                    return decorator

                pydantic.with_config = with_config
                print("✓ Applied Pydantic v1/v2 compatibility patch")

        return True

    except Exception as e:
        print(f"Warning: Could not apply Pydantic compatibility patch: {e}")
        return False


def check_supabase_import():
    """Test if supabase can be imported successfully."""
    try:
        # Apply the patch first
        patch_pydantic_import()

        # Try importing supabase
        from supabase import create_client
        print("✓ Supabase import successful")
        return True

    except ImportError as e:
        print(f"✗ Supabase import failed: {e}")
        return False


if __name__ == "__main__":
    # Run as a module that can be imported before other imports
    success = patch_pydantic_import()

    if "--test" in sys.argv:
        # Test mode - check if imports work
        import_ok = check_supabase_import()
        sys.exit(0 if import_ok else 1)