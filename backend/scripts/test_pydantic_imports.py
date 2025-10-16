#!/usr/bin/env python3
"""
Test script to diagnose and fix Pydantic import issues.
Run this to check if the supabase/realtime imports are working correctly.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_pydantic_version():
    """Check which version of Pydantic is installed."""
    try:
        import pydantic
        print(f"✓ Pydantic version: {pydantic.__version__}")

        # Check for v1 vs v2 features
        if hasattr(pydantic, 'with_config'):
            print("  - Has 'with_config' (v1 feature)")
        else:
            print("  - No 'with_config' (v2 behavior)")

        if hasattr(pydantic, 'ConfigDict'):
            print("  - Has 'ConfigDict' (v2 feature)")
        else:
            print("  - No 'ConfigDict' (v1 behavior)")

        return pydantic.__version__
    except ImportError as e:
        print(f"✗ Pydantic not installed: {e}")
        return None


def test_realtime_import():
    """Test if realtime package can be imported."""
    try:
        import realtime
        print(f"✓ Realtime package import successful")

        # Check what it's trying to import from pydantic
        try:
            from realtime.types import BaseModel
            print("  - Can import realtime.types")
        except ImportError as e:
            print(f"  - Cannot import realtime.types: {e}")

        return True
    except ImportError as e:
        print(f"✗ Realtime import failed: {e}")
        return False


def test_supabase_import():
    """Test if supabase can be imported."""
    try:
        from supabase import create_client
        print("✓ Supabase import successful")
        return True
    except ImportError as e:
        print(f"✗ Supabase import failed: {e}")
        print(f"  Error details: {e}")
        return False


def test_with_compatibility_fix():
    """Test imports with the compatibility fix applied."""
    print("\n--- Testing with compatibility fix ---")

    try:
        import fix_pydantic_compat
        fix_pydantic_compat.patch_pydantic_import()
        print("✓ Compatibility patch applied")
    except Exception as e:
        print(f"✗ Could not apply compatibility patch: {e}")
        return False

    # Now test imports again
    realtime_ok = test_realtime_import()
    supabase_ok = test_supabase_import()

    return realtime_ok and supabase_ok


def test_lightweight_db():
    """Test the lightweight database module."""
    print("\n--- Testing lightweight database module ---")

    try:
        from services.database_voice import SupaVoice
        print("✓ Lightweight database module import successful")

        # Test initialization (without actual connection)
        try:
            # Temporarily set dummy env vars for testing
            old_url = os.environ.get("SUPABASE_URL")
            old_key = os.environ.get("SUPABASE_SERVICE_KEY")

            os.environ["SUPABASE_URL"] = "https://dummy.supabase.co"
            os.environ["SUPABASE_SERVICE_KEY"] = "dummy-key"

            db = SupaVoice()
            print("✓ Lightweight database can be initialized")

            # Restore env vars
            if old_url:
                os.environ["SUPABASE_URL"] = old_url
            else:
                del os.environ["SUPABASE_URL"]

            if old_key:
                os.environ["SUPABASE_SERVICE_KEY"] = old_key
            else:
                del os.environ["SUPABASE_SERVICE_KEY"]

            return True

        except Exception as e:
            print(f"✗ Lightweight database initialization failed: {e}")
            return False

    except ImportError as e:
        print(f"✗ Lightweight database module import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Pydantic/Supabase Import Diagnostics ===\n")

    # Test current state
    print("--- Current Environment ---")
    pydantic_version = test_pydantic_version()
    realtime_ok = test_realtime_import()
    supabase_ok = test_supabase_import()

    # If imports fail, try with compatibility fix
    if not (realtime_ok and supabase_ok):
        compat_ok = test_with_compatibility_fix()
    else:
        compat_ok = True
        print("\n✓ No compatibility fix needed - imports work as-is")

    # Test lightweight DB module
    lightweight_ok = test_lightweight_db()

    # Summary
    print("\n=== Summary ===")
    print(f"Pydantic Version: {pydantic_version}")
    print(f"Realtime Import: {'✓' if realtime_ok else '✗'}")
    print(f"Supabase Import: {'✓' if supabase_ok else '✗'}")
    print(f"With Compatibility Fix: {'✓' if compat_ok else '✗'}")
    print(f"Lightweight DB Module: {'✓' if lightweight_ok else '✗'}")

    if lightweight_ok:
        print("\n✅ SOLUTION: Use the lightweight database module for voice diarization")
        print("   The system will automatically fall back to this if needed.")
    elif compat_ok:
        print("\n✅ SOLUTION: The compatibility fix resolves the import issues")
        print("   The system will apply this automatically at startup.")
    else:
        print("\n❌ Manual intervention may be needed")
        print("   Consider using the lightweight database module or updating packages")

    return 0 if (compat_ok or lightweight_ok) else 1


if __name__ == "__main__":
    sys.exit(main())