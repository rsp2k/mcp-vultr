# Vultr MCP Notification System

## Overview

The Vultr MCP package now includes a comprehensive resource change notification system that keeps MCP clients synchronized with server state changes. This system provides real-time updates when Vultr resources are modified through the MCP tools.

## Architecture

### NotificationManager

The core component is the `NotificationManager` class in `src/mcp_vultr/notification_manager.py`:

```python
class NotificationManager:
    """Manages resource change notifications across all Vultr MCP services."""
    
    # Maps 63+ operations to their affected MCP resources
    OPERATION_RESOURCE_MAP: Dict[str, list[str]] = {
        "create_domain": ["domains://list"],
        "delete_domain": ["domains://list", "domains://{domain}/records"],
        # ... extensive mapping for all operations
    }
```

### Dual-Mode Operation

The system supports both CLI and MCP usage through optional Context parameters:

```python
async def create_domain(
    domain: str, 
    ip: str, 
    ctx: Context | None = None,  # Optional for backward compatibility
    dns_sec: str = "disabled"
) -> dict[str, Any]:
    result = await vultr_client.create_domain(domain, ip, dns_sec)
    
    # Notify only when MCP context is available
    if ctx is not None:
        await NotificationManager.notify_dns_changes(
            ctx=ctx, operation="create_domain", domain=domain
        )
    
    return result
```

## Implementation Coverage

### Modules with Notification Support (12 total)

1. **DNS** (`dns.py`) - 5 operations: create/delete domains, create/update/delete records
2. **Instances** (`instances.py`) - 7 operations: create, start, stop, reboot, reinstall, update, delete
3. **Load Balancers** (`load_balancer.py`) - 6 operations: create, update, delete, SSL management
4. **Snapshots** (`snapshots.py`) - 4 operations: create, create_from_url, update, delete
5. **SSH Keys** (`ssh_keys.py`) - 3 operations: create, update, delete
6. **Startup Scripts** (`startup_scripts.py`) - 4 operations: create, update, delete, create_common
7. **Users** (`users.py`) - 6 operations: create, update, delete, API key management
8. **Reserved IPs** (`reserved_ips.py`) - 6 operations: create, update, delete, attach, detach, convert
9. **Block Storage** (`block_storage.py`) - 5 operations: create, update, delete, attach, detach
10. **Firewall** (`firewall.py`) - 6 operations: group/rule create/update/delete, bulk setup
11. **VPCs** (`vpcs.py`) - 3 operations: create, update, delete
12. **Container Registry** (`container_registry.py`) - 3 operations: create, update, delete

### Error Handling Improvements (16 modules)

Fixed resource functions to return empty arrays instead of throwing errors when no resources exist:

```python
@mcp.resource("domains://list")
async def list_domains_resource() -> list[dict[str, Any]]:
    """List all DNS domains."""
    try:
        return await vultr_client.list_domains()
    except Exception:
        # Return empty list instead of error when no domains exist
        return []
```

## Benefits

### For MCP Clients
- **Real-time Updates**: Automatically refresh resource lists when changes occur
- **Consistent State**: Client UI stays synchronized with server state
- **Efficient Polling**: Reduces need for periodic resource list requests

### For CLI Users
- **No Breaking Changes**: All existing CLI commands work unchanged
- **Optional Enhancement**: No performance impact when notifications aren't needed

### For Development
- **Foundation for CI/CD**: Enables workflow triggers based on resource changes
- **Audit Trail**: All resource modifications can be tracked and logged
- **Multi-channel Ready**: Architecture supports VAPID, SMTP, webhook notifications

## Operation Categories

### Resource Lifecycle
- **Create Operations**: Trigger `list` resource updates
- **Update Operations**: Trigger both `list` and specific resource updates
- **Delete Operations**: Trigger `list` resource updates

### Attachment Operations
- **Attach/Detach**: Update both parent and child resource lists
- **Convert**: Handle resource type transitions (e.g., IP to reserved IP)

### Bulk Operations
- **Setup Utilities**: Batch operations notify once after completion
- **Import/Export**: Trigger comprehensive resource updates

## Usage Examples

### MCP Client (with notifications)
```python
# Client will receive automatic updates
await create_domain("example.com", "192.168.1.1", ctx=mcp_context)
# Resource list automatically updated in client UI
```

### CLI Usage (without notifications)
```bash
# Works exactly as before - no changes required
mcp-vultr domains create example.com 192.168.1.1
```

### Custom Integration
```python
# Enable selective notifications
ctx = FastMCPContext() if enable_notifications else None
await create_instance("web-server", "ewr", "vc2-1c-1gb", ctx=ctx)
```

## Future Enhancements

### Multi-channel Notifications
- **VAPID Push**: Browser notifications for web clients
- **SMTP Email**: Email alerts for critical operations
- **Webhook**: Integration with external monitoring systems

### OAuth/OIDC Integration
- **Permission-based Notifications**: Filter based on user permissions
- **Audit Logging**: Track all notification events with user context
- **Approval Workflows**: Trigger human-in-the-loop processes

### Infrastructure CI/CD
- **Service Collections**: Group resources by project/environment
- **Workflow Triggers**: Automatic deployments based on resource changes
- **Rollback Capabilities**: Revert operations with proper notifications

## Migration Notes

This update maintains 100% backward compatibility. Existing code will continue to work unchanged, with notifications automatically enabled when MCP context is available.

No configuration changes are required for basic usage. Advanced notification features (multi-channel, filtering) will be configurable through environment variables or MCP server settings.