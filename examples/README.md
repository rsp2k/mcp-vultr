# MCP Vultr Examples

This directory contains example scripts and configurations for using the MCP Vultr server with OAuth authentication.

## Files

### `oauth_test.py`
Comprehensive test script for OAuth/OIDC authentication functionality.

**Usage:**
```bash
# Set environment variables
export OAUTH_ENABLED=true
export OAUTH_ISSUER_URL=https://auth.l.inspect.systems/realms/mcp-vultr
export TEST_USERNAME=your-username
export TEST_PASSWORD=your-password

# Run the test
python examples/oauth_test.py
```

**What it tests:**
- OAuth configuration loading
- JWKS endpoint accessibility
- Access token acquisition
- JWT token validation
- Permission checking
- Tool access control

## OAuth Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# OAuth Configuration
OAUTH_ENABLED=true
OAUTH_ISSUER_URL=https://auth.l.inspect.systems/realms/mcp-vultr
OAUTH_CLIENT_ID=mcp-vultr-server
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_JWKS_URL=https://auth.l.inspect.systems/realms/mcp-vultr/protocol/openid-connect/certs
OAUTH_AUDIENCE=mcp-vultr-server

# Fallback API Key
VULTR_API_KEY=your-vultr-api-key

# Test Credentials (for oauth_test.py)
TEST_USERNAME=your-test-username
TEST_PASSWORD=your-test-password
```

## Running Examples

### Prerequisites
1. Keycloak server running with mcp-vultr realm configured
2. Test user created in Keycloak with appropriate roles
3. Environment variables configured

### OAuth Test Script
```bash
# Install dependencies
uv sync

# Run OAuth test
uv run python examples/oauth_test.py
```

### OAuth-Enhanced MCP Server
```bash
# Run OAuth-enhanced server
uv run mcp-vultr-oauth

# Or with explicit transport
uv run python -m mcp_vultr.oauth_server
```

## Expected Output

The OAuth test script should produce output similar to:
```
🚀 MCP Vultr OAuth Authentication Test
============================================================
🔐 Testing OAuth Configuration
==================================================
OAuth Enabled: True
Issuer URL: https://auth.l.inspect.systems/realms/mcp-vultr
Client ID: mcp-vultr-server
...
✅ Access token obtained (length: 1234)
✅ Token validated successfully!
   Username: testuser
   Email: test@example.com
   Permissions: ['vultr-admin', 'vultr-manager', 'vultr-viewer']
   Has Vultr API Key: ✓
...
🎉 OAuth Authentication Test Complete!
```

## Troubleshooting

### Common Issues

1. **"JWKS endpoint error"**
   - Verify Keycloak server is running
   - Check OAUTH_JWKS_URL is correct
   - Ensure network connectivity

2. **"Failed to get access token"**
   - Verify test user exists in Keycloak
   - Check username/password are correct
   - Ensure mcp-vultr-cli client is configured

3. **"Token validation failed"**
   - Check client secret configuration
   - Verify audience and issuer URLs
   - Ensure token hasn't expired

### Debug Mode

Run with debug logging:
```bash
export LOG_LEVEL=DEBUG
python examples/oauth_test.py
```