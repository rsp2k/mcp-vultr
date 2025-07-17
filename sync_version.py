#!/usr/bin/env python3
"""
Version synchronization script for mcp-vultr.

This script ensures that the version number in pyproject.toml 
and src/mcp_vultr/_version.py are kept in sync.

Usage:
    python sync_version.py              # Check if versions are in sync
    python sync_version.py --update     # Update _version.py to match pyproject.toml
    python sync_version.py --set 1.0.2  # Set both versions to 1.0.2
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib or tomli not available. Install with: pip install tomli")
        sys.exit(1)


def get_version_from_pyproject() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    return data["project"]["version"]


def get_version_from_version_py() -> str:
    """Get version from _version.py."""
    version_path = Path("src/mcp_vultr/_version.py")
    if not version_path.exists():
        raise FileNotFoundError("src/mcp_vultr/_version.py not found")
    
    with open(version_path, "r") as f:
        content = f.read()
    
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Could not find __version__ in _version.py")
    
    return match.group(1)


def update_version_py(new_version: str) -> None:
    """Update version in _version.py."""
    version_path = Path("src/mcp_vultr/_version.py")
    
    content = f'''"""Version information for mcp-vultr package."""

__version__ = "{new_version}"
__version_info__ = tuple(int(i) for i in __version__.split(".") if i.isdigit())
'''
    
    with open(version_path, "w") as f:
        f.write(content)
    
    print(f"✅ Updated _version.py to {new_version}")


def update_pyproject_toml(new_version: str) -> None:
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    
    with open(pyproject_path, "r") as f:
        content = f.read()
    
    # Replace version line
    pattern = r'(version\s*=\s*)["\'][^"\']+["\']'
    replacement = f'\\1"{new_version}"'
    new_content = re.sub(pattern, replacement, content)
    
    with open(pyproject_path, "w") as f:
        f.write(new_content)
    
    print(f"✅ Updated pyproject.toml to {new_version}")


def check_versions() -> tuple[str, str, bool]:
    """Check if versions are in sync."""
    try:
        pyproject_version = get_version_from_pyproject()
        version_py_version = get_version_from_version_py()
        
        in_sync = pyproject_version == version_py_version
        
        return pyproject_version, version_py_version, in_sync
    
    except Exception as e:
        print(f"❌ Error reading versions: {e}")
        sys.exit(1)


def validate_version(version: str) -> bool:
    """Validate version format (basic semver check)."""
    pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+(?:\.\d+)?)?$'
    return bool(re.match(pattern, version))


def main():
    parser = argparse.ArgumentParser(description="Sync version numbers between files")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--update", action="store_true", 
                       help="Update _version.py to match pyproject.toml")
    group.add_argument("--set", metavar="VERSION",
                       help="Set both files to the specified version")
    
    args = parser.parse_args()
    
    if args.set:
        if not validate_version(args.set):
            print(f"❌ Invalid version format: {args.set}")
            print("Expected format: X.Y.Z or X.Y.Z-suffix")
            sys.exit(1)
        
        update_pyproject_toml(args.set)
        update_version_py(args.set)
        print(f"✅ Set both versions to {args.set}")
        
    elif args.update:
        pyproject_version, version_py_version, in_sync = check_versions()
        
        if in_sync:
            print(f"✅ Versions already in sync: {pyproject_version}")
        else:
            update_version_py(pyproject_version)
            print(f"✅ Updated _version.py from {version_py_version} to {pyproject_version}")
    
    else:
        # Default: check status
        pyproject_version, version_py_version, in_sync = check_versions()
        
        print("📋 Version Status:")
        print(f"   pyproject.toml: {pyproject_version}")
        print(f"   _version.py:    {version_py_version}")
        
        if in_sync:
            print("✅ Versions are in sync!")
        else:
            print("❌ Versions are out of sync!")
            print("\nTo fix:")
            print("   python sync_version.py --update    # Update _version.py to match pyproject.toml")
            print("   python sync_version.py --set X.Y.Z # Set both to version X.Y.Z")
            sys.exit(1)


if __name__ == "__main__":
    main()
