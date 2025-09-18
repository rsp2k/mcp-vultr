#!/usr/bin/env python3
"""
Fix formatting issues from the automated Context parameter script.
"""

import re
from pathlib import Path

def fix_notification_formatting(file_path):
    """Fix malformed notification calls and duplicate conditions."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix duplicated if ctx is not None conditions
    content = re.sub(
        r'(\s+)if ctx is not None:\s*\n\s*if ctx is not None:\s*\n\s*\n\s*await NotificationManager\.notify',
        r'\1if ctx is not None:\n\1    await NotificationManager.notify',
        content,
        flags=re.MULTILINE
    )
    
    # Fix malformed await calls (missing proper indentation)
    content = re.sub(
        r'(\s+)if ctx is not None:\s*\n\s*await NotificationManager\.notify',
        r'\1if ctx is not None:\n\1    await NotificationManager.notify',
        content,
        flags=re.MULTILINE
    )
    
    # Fix line continuations in notify calls
    content = re.sub(
        r'await NotificationManager\.notify([^(]+)\(\s*ctx=ctx,([^)]+)\s*\)',
        r'await NotificationManager.notify\1(\n            ctx=ctx,\2\n        )',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Files that need formatting fixes
files_to_fix = [
    'src/mcp_vultr/instances.py',
    'src/mcp_vultr/ssh_keys.py', 
    'src/mcp_vultr/firewall.py',
    'src/mcp_vultr/load_balancer.py',
    'src/mcp_vultr/kubernetes.py',
    'src/mcp_vultr/block_storage.py',
    'src/mcp_vultr/container_registry.py',
    'src/mcp_vultr/vpcs.py',
    'src/mcp_vultr/reserved_ips.py',
    'src/mcp_vultr/users.py'
]

print("🔧 Fixing notification formatting issues...")
fixed_files = []

for file_path in files_to_fix:
    if Path(file_path).exists():
        if fix_notification_formatting(file_path):
            fixed_files.append(file_path)
            print(f"✅ Fixed formatting in {file_path}")
        else:
            print(f"ℹ️  No formatting issues in {file_path}")

print(f"\n🎉 Notification formatting fixes complete!")
print(f"📊 Fixed {len(fixed_files)} files")