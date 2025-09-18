#!/usr/bin/env python3
"""
OAuth Authentication Test Script for MCP Vultr

This script demonstrates how to test OAuth authentication with the MCP Vultr server.
It includes examples of token generation, validation, and API key extraction.
"""

import asyncio
import os
import httpx
from typing import Optional

from mcp_vultr.oauth_auth import OAuthConfig, OAuthAuthenticator, UserContext


async def get_access_token(
    username: str, 
    password: str, 
    config: OAuthConfig
) -> Optional[str]:
    """
    Get an access token using direct password grant.
    
    Note: This is for testing only. Production should use proper OAuth flows.
    """
    token_url = f"{config.issuer_url}/protocol/openid-connect/token"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": "mcp-vultr-cli",  # Use CLI client for password grant
                    "username": username,
                    "password": password,
                }
            )
            response.raise_for_status()
            token_data = response.json()
            return token_data.get("access_token")
        except httpx.HTTPError as e:
            print(f"❌ Failed to get access token: {e}")
            return None


async def test_token_validation(token: str, config: OAuthConfig) -> Optional[UserContext]:
    """Test JWT token validation and user context extraction."""
    authenticator = OAuthAuthenticator(config)
    
    try:
        user_context = await authenticator.validate_token(token)
        if user_context:
            print(f"✅ Token validated successfully!")
            print(f"   Username: {user_context.username}")
            print(f"   Email: {user_context.email}")
            print(f"   Permissions: {[p.value for p in user_context.permissions]}")
            print(f"   Has Vultr API Key: {'✓' if user_context.vultr_api_key else '✗'}")
            return user_context
        else:
            print("❌ Token validation failed")
            return None
    except Exception as e:
        print(f"❌ Token validation error: {e}")
        return None


async def test_oauth_configuration():
    """Test OAuth configuration loading."""
    print("🔐 Testing OAuth Configuration")
    print("=" * 50)
    
    config = OAuthConfig.from_env()
    print(f"OAuth Enabled: {config.enabled}")
    print(f"Issuer URL: {config.issuer_url}")
    print(f"Client ID: {config.client_id}")
    print(f"JWKS URL: {config.jwks_url}")
    print(f"Audience: {config.audience}")
    print(f"Client Secret Set: {'✓' if config.client_secret else '✗'}")
    
    if not config.enabled:
        print("\n⚠️  OAuth is disabled. Set OAUTH_ENABLED=true to enable.")
        return None
    
    return config


async def test_jwks_endpoint(config: OAuthConfig):
    """Test JWKS endpoint accessibility."""
    print("\n🔑 Testing JWKS Endpoint")
    print("=" * 50)
    
    authenticator = OAuthAuthenticator(config)
    
    try:
        jwks = await authenticator.get_jwks()
        print(f"✅ JWKS endpoint accessible")
        print(f"   Number of keys: {len(jwks.get('keys', []))}")
        
        for i, key in enumerate(jwks.get('keys', [])):
            print(f"   Key {i+1}: {key.get('kid', 'no-kid')} ({key.get('alg', 'no-alg')})")
        
        return True
    except Exception as e:
        print(f"❌ JWKS endpoint error: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 MCP Vultr OAuth Authentication Test")
    print("=" * 60)
    
    # Test OAuth configuration
    config = await test_oauth_configuration()
    if not config:
        return
    
    # Test JWKS endpoint
    jwks_ok = await test_jwks_endpoint(config)
    if not jwks_ok:
        return
    
    # Get credentials from environment or prompt
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    
    if not username or not password:
        print("\n📝 User Credentials")
        print("=" * 50)
        print("Set TEST_USERNAME and TEST_PASSWORD environment variables,")
        print("or enter credentials manually:")
        print()
        
        if not username:
            username = input("Username: ")
        if not password:
            password = input("Password: ")
    
    if not username or not password:
        print("❌ Username and password required for testing")
        return
    
    # Test token acquisition
    print(f"\n🎫 Getting Access Token for User: {username}")
    print("=" * 50)
    
    token = await get_access_token(username, password, config)
    if not token:
        return
    
    print(f"✅ Access token obtained (length: {len(token)})")
    print(f"   Token preview: {token[:50]}...")
    
    # Test token validation
    print(f"\n🔍 Validating Token")
    print("=" * 50)
    
    user_context = await test_token_validation(token, config)
    if not user_context:
        return
    
    # Test permission checking
    print(f"\n🛡️  Testing Permissions")
    print("=" * 50)
    
    from mcp_vultr.oauth_auth import Permission
    
    test_permissions = [
        Permission.VIEWER,
        Permission.MANAGER,
        Permission.ADMIN,
        Permission.SERVICE_COLLECTION_OWNER,
    ]
    
    for permission in test_permissions:
        has_permission = user_context.has_permission(permission)
        status = "✅" if has_permission else "❌"
        print(f"   {status} {permission.value}")
    
    # Test tool access
    print(f"\n🔧 Testing Tool Access")
    print("=" * 50)
    
    test_tools = [
        "list_domains",        # Should be available to viewers
        "create_domain",       # Should require manager+
        "delete_domain",       # Should require manager+
        "create_user",         # Should require admin
    ]
    
    for tool in test_tools:
        can_access = user_context.can_access_tool(tool)
        status = "✅" if can_access else "❌"
        print(f"   {status} {tool}")
    
    print(f"\n🎉 OAuth Authentication Test Complete!")


if __name__ == "__main__":
    # Set up test environment variables if not already set
    if not os.getenv("OAUTH_ENABLED"):
        os.environ["OAUTH_ENABLED"] = "true"
    if not os.getenv("OAUTH_ISSUER_URL"):
        os.environ["OAUTH_ISSUER_URL"] = "https://auth.l.inspect.systems/realms/mcp-vultr"
    if not os.getenv("OAUTH_CLIENT_ID"):
        os.environ["OAUTH_CLIENT_ID"] = "mcp-vultr-server"
    if not os.getenv("OAUTH_JWKS_URL"):
        os.environ["OAUTH_JWKS_URL"] = "https://auth.l.inspect.systems/realms/mcp-vultr/protocol/openid-connect/certs"
    if not os.getenv("OAUTH_AUDIENCE"):
        os.environ["OAUTH_AUDIENCE"] = "mcp-vultr-server"
    
    asyncio.run(main())