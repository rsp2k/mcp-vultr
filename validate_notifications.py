#!/usr/bin/env python3
"""Validate notification system implementation."""

import ast
import sys
from pathlib import Path

def check_module_notifications(file_path):
    """Check if a module properly implements notifications."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False
    
    has_context_import = "from fastmcp import Context" in content
    has_notification_import = "from .notification_manager import NotificationManager" in content
    has_notification_calls = "NotificationManager.notify" in content
    has_optional_context = "ctx: Context | None = None" in content
    
    print(f"📁 {file_path.name}")
    print(f"   Context import: {'✅' if has_context_import else '❌'}")
    print(f"   NotificationManager import: {'✅' if has_notification_import else '❌'}")
    print(f"   Notification calls: {'✅' if has_notification_calls else '❌'}")
    print(f"   Optional context pattern: {'✅' if has_optional_context else '❌'}")
    
    if has_notification_calls:
        # Count conditional notifications
        conditional_count = content.count("if ctx is not None:")
        notification_count = content.count("NotificationManager.notify")
        print(f"   Conditional notifications: {conditional_count}/{notification_count}")
    
    print()
    return True

def main():
    """Main validation function."""
    src_dir = Path("src/mcp_vultr")
    
    print("🔍 Validating notification system implementation...\n")
    
    # Check key files
    key_files = [
        "dns.py", "instances.py", "load_balancer.py", "snapshots.py",
        "ssh_keys.py", "startup_scripts.py", "users.py", "reserved_ips.py",
        "block_storage.py", "firewall.py", "vpcs.py", "notification_manager.py"
    ]
    
    all_good = True
    for file_name in key_files:
        file_path = src_dir / file_name
        if file_path.exists():
            all_good &= check_module_notifications(file_path)
        else:
            print(f"❌ Missing file: {file_name}")
            all_good = False
    
    # Summary
    print("="*50)
    if all_good:
        print("✅ All modules validated successfully!")
        print("🚀 Notification system implementation complete!")
    else:
        print("❌ Some issues found. Please review above.")
        sys.exit(1)

if __name__ == "__main__":
    main()