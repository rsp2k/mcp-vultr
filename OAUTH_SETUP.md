# OAuth/OIDC Setup Guide for MCP Vultr

This guide shows how to configure and use OAuth/OIDC authentication with the MCP Vultr server using Keycloak.

## Overview

The OAuth-enhanced MCP Vultr server provides:
- **Secure Authentication**: JWT-based authentication via Keycloak
- **Permission-Based Access**: Role-based access control for tools
- **API Key Management**: Vultr API keys stored securely in user profiles
- **Backward Compatibility**: Falls back to environment variable API keys
- **Enterprise Ready**: Multi-user support with granular permissions

## Quick Start

### 1. Environment Configuration

Create a `.env` file or set environment variables:

```bash
# OAuth Configuration (set OAUTH_ENABLED=true to enable)
OAUTH_ENABLED=true
OAUTH_ISSUER_URL=https://auth.l.inspect.systems/realms/mcp-vultr
OAUTH_CLIENT_ID=mcp-vultr-server
OAUTH_CLIENT_SECRET=mcp-vultr-server-secret-change-in-production
OAUTH_JWKS_URL=https://auth.l.inspect.systems/realms/mcp-vultr/protocol/openid-connect/certs
OAUTH_AUDIENCE=mcp-vultr-server

# Fallback API Key (used when OAuth is disabled or for fallback)
VULTR_API_KEY=your-vultr-api-key-here
```

### 2. Running the OAuth-Enhanced Server

```bash
# Using the OAuth server directly
python -m mcp_vultr.oauth_server

# Or use the enhanced server with explicit transport
python -c "
from mcp_vultr.oauth_server import run_oauth_server
run_oauth_server(transport='stdio')
"
```

### 3. Claude Desktop Configuration

Update your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "vultr-oauth": {
      "command": "python",
      "args": ["-m", "mcp_vultr.oauth_server"],
      "env": {
        "OAUTH_ENABLED": "true",
        "OAUTH_ISSUER_URL": "https://auth.l.inspect.systems/realms/mcp-vultr",
        "OAUTH_CLIENT_ID": "mcp-vultr-server",
        "OAUTH_CLIENT_SECRET": "mcp-vultr-server-secret-change-in-production",
        "VULTR_API_KEY": "your-fallback-api-key"
      }
    }
  }
}
```

## Authentication Modes

### OAuth Mode (Recommended)
When `OAUTH_ENABLED=true`, the server requires JWT authentication:
- Users must authenticate via Keycloak
- API keys are extracted from JWT tokens
- Permission-based access control is enforced
- Tools require appropriate permissions

### Fallback Mode
When `OAUTH_ENABLED=false` or OAuth is not configured:
- Uses environment variable `VULTR_API_KEY`
- Full admin access granted
- No authentication required
- Backward compatible with existing setups

## User Management

### Creating Users in Keycloak

1. **Access Keycloak Admin Console**:
   ```
   https://auth.l.inspect.systems/admin/
   ```

2. **Navigate to MCP Vultr Realm**:
   - Select "mcp-vultr" realm from dropdown

3. **Create New User**:
   - Go to Users → Add User
   - Set username, email, first name, last name
   - Enable the user

4. **Set Password**:
   - Go to Credentials tab
   - Set permanent password

5. **Configure Vultr API Key**:
   - Go to Attributes tab
   - Add attribute: `vultr_api_key` = `your-vultr-api-key`

6. **Assign Roles**:
   - Go to Role Mappings tab
   - Assign appropriate realm roles:
     - `vultr-viewer`: Read-only access
     - `vultr-manager`: Management operations
     - `vultr-admin`: Full access

### Permission Levels

| Role | Description | Tool Access |
|------|-------------|-------------|
| `vultr-viewer` | Read-only access | list_*, get_*, view operations |
| `vultr-manager` | Management operations | create_*, update_*, delete_* (most resources) |
| `vultr-admin` | Full administrative access | All tools including user management |
| `service-collection-owner` | Service collection management | Collection creation and management |
| `service-collection-editor` | Edit assigned collections | Edit specific collections |
| `workflow-approver` | Approve workflows | Approval operations |

## Authentication Flow

### 1. Client Authentication
Clients must include a Bearer token in requests:
```
Authorization: Bearer <jwt-token>
```

### 2. Token Validation
The server validates JWT tokens:
- Verifies signature using Keycloak JWKS
- Checks issuer and audience
- Extracts user information and permissions

### 3. API Key Injection
- Extracts `vultr_api_key` from JWT token
- Creates Vultr client with user's API key
- Injects into tool execution context

### 4. Permission Checking
Before tool execution:
- Validates user has required permission
- Maps tool names to permission requirements
- Rejects unauthorized requests

## Example Usage

### Getting an Access Token

```bash
# Direct password grant (for testing)
curl -X POST "https://auth.l.inspect.systems/realms/mcp-vultr/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=mcp-vultr-cli" \
  -d "username=your-username" \
  -d "password=your-password"
```

### Using the Token

```bash
# Example MCP call with authentication
echo '{"method": "tools/call", "params": {"name": "list_domains"}}' | \
  python -m mcp_vultr.oauth_server
```

## Troubleshooting

### Common Issues

1. **"Authentication required" Error**
   - Ensure `OAUTH_ENABLED=true`
   - Verify Bearer token in Authorization header
   - Check token hasn't expired

2. **"Insufficient permissions" Error**
   - Verify user has required role in Keycloak
   - Check role mapping configuration
   - Ensure tool requires appropriate permission level

3. **"No API key available" Error**
   - Add `vultr_api_key` attribute to user in Keycloak
   - Verify API key is valid in Vultr
   - Check fallback `VULTR_API_KEY` environment variable

4. **Token Validation Fails**
   - Verify JWKS URL is accessible
   - Check issuer URL matches Keycloak realm
   - Ensure client configuration is correct

### Debug Mode

Enable debug logging:
```bash
# Set log level for debugging
export LOG_LEVEL=DEBUG
python -m mcp_vultr.oauth_server
```

### Testing Configuration

Test OAuth configuration:
```python
from mcp_vultr.oauth_auth import OAuthConfig, OAuthAuthenticator

# Load and test configuration
config = OAuthConfig.from_env()
print(f"OAuth Enabled: {config.enabled}")
print(f"Issuer: {config.issuer_url}")

# Test JWKS endpoint
auth = OAuthAuthenticator(config)
jwks = await auth.get_jwks()
print(f"JWKS Keys: {len(jwks['keys'])}")
```

## Security Considerations

### Production Deployment

1. **Change Default Secrets**:
   - Update client secrets in Keycloak
   - Use strong, unique passwords
   - Rotate credentials regularly

2. **HTTPS Only**:
   - Always use HTTPS for Keycloak
   - Secure token transmission
   - Prevent token interception

3. **Token Lifetime**:
   - Configure appropriate token expiration
   - Implement token refresh flows
   - Monitor for expired tokens

4. **API Key Security**:
   - Store API keys securely in Keycloak
   - Limit API key permissions in Vultr
   - Audit API key usage

### Network Security

- Firewall rules for Keycloak access
- VPN or private network deployment
- Rate limiting and DDoS protection
- Log monitoring and alerting

## Integration Examples

### Python Client Example

```python
import httpx
from mcp_vultr.oauth_auth import OAuthConfig, UserContext

async def authenticate_user(username: str, password: str) -> str:
    """Get access token for user."""
    config = OAuthConfig.from_env()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.issuer_url}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "mcp-vultr-cli",
                "username": username,
                "password": password,
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]

# Usage
token = await authenticate_user("ryan", "password")
print(f"Access token: {token}")
```

### Claude Desktop with Authentication

The OAuth server integrates seamlessly with Claude Desktop. When properly configured, Claude will:
1. Use the OAuth-enhanced server
2. Extract user context from MCP session
3. Apply permission-based access control
4. Use user-specific Vultr API keys

## Support

For issues and questions:
- Check Keycloak admin console for user configuration
- Verify environment variables are set correctly
- Review server logs for authentication errors
- Test JWKS endpoint accessibility

## Next Steps

1. Set up Keycloak realm using provided configuration
2. Create test users with appropriate roles
3. Configure environment variables
4. Test authentication flow
5. Deploy to production with security hardening