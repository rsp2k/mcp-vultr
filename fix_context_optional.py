#!/usr/bin/env python3
"""
Make Context parameters optional across all notification-enabled functions.
This ensures backward compatibility with CLI while maintaining MCP notification functionality.
"""

import re
from pathlib import Path

def fix_context_parameters(file_path):
    """Make Context parameters optional and add conditional notifications."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix function signatures: ctx: Context -> ctx: Context | None = None
    content = re.sub(
        r'(\s+ctx:\s*Context)([,\)])',
        r'\1 | None = None\2',
        content
    )
    
    # Fix conditional notifications: await NotificationManager.notify -> if ctx is not None: await
    notification_patterns = [
        r'(\s+)(await NotificationManager\.notify[^(]+\(\s*ctx=ctx[^}]+\}?\s*\))',
        r'(\s+)(await NotificationManager\.notify[^(]+\(\s*ctx=ctx[^)]+\))',
    ]
    
    for pattern in notification_patterns:
        def add_condition(match):
            indent = match.group(1)
            notify_call = match.group(2)
            return f'{indent}if ctx is not None:\n{indent}    {notify_call}'
        
        content = re.sub(pattern, add_condition, content, flags=re.MULTILINE)
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Modules that need Context parameter fixes
modules_to_fix = [
    'src/mcp_vultr/instances.py',
    'src/mcp_vultr/ssh_keys.py', 
    'src/mcp_vultr/firewall.py',
    'src/mcp_vultr/load_balancer.py',
    'src/mcp_vultr/kubernetes.py',
    'src/mcp_vultr/block_storage.py',
    'src/mcp_vultr/container_registry.py',
    'src/mcp_vultr/vpcs.py',
    'src/mcp_vultr/reserved_ips.py',
    'src/mcp_vultr/users.py',
    'src/mcp_vultr/bare_metal.py',
    'src/mcp_vultr/object_storage.py',
    'src/mcp_vultr/cdn.py',
    'src/mcp_vultr/billing.py'
]

print("🔧 Making Context parameters optional for backward compatibility...")
changed_files = []

for module_path in modules_to_fix:
    if Path(module_path).exists():
        if fix_context_parameters(module_path):
            changed_files.append(module_path)
            print(f"✅ Fixed {module_path}")
        else:
            print(f"ℹ️  No changes needed in {module_path}")
    else:
        print(f"⚠️  {module_path} not found")

print(f"\n🎉 Context parameter fixes complete!")
print(f"📊 Modified {len(changed_files)} files")
print(f"✅ All notification-enabled functions now have optional Context")
print(f"🔄 Backward compatibility restored for CLI usage")

if changed_files:
    print(f"\n📋 Files modified:")
    for file in changed_files:
        print(f"  - {file}")