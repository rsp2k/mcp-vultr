"""
FastMCP-based authentication integration for Service Collection webapp.

This module integrates FastMCP's JWT authentication providers with our webapp,
creating a unified authentication system between the MCP server and webapp frontend.
"""

import os
from typing import Optional
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.providers.github import GitHubProvider
from fastapi import HTTPException, status
import structlog

logger = structlog.get_logger()


class UnifiedAuthConfig:
    """Unified authentication configuration for both MCP server and webapp."""
    
    def __init__(self):
        # GitHub OAuth (primary authentication method)
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        
        # Use configured domain for redirect URI
        domain = os.getenv("DOMAIN", "localhost:9321")
        protocol = "https" if not domain.startswith("localhost") else "http"
        default_redirect = f"{protocol}://{domain}/auth/github/callback"
        self.github_redirect_uri = os.getenv("GITHUB_REDIRECT_URI", default_redirect)
        
        # JWT Configuration (development/fallback)
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
        # Explicit authentication mode selection
        self.auth_mode = os.getenv("AUTH_MODE", self._determine_auth_mode())
    
    def _determine_auth_mode(self) -> str:
        """Determine which authentication mode to use."""
        if self.github_client_id and self.github_client_secret:
            return "github"
        else:
            return "jwt"


class FastMCPAuthProvider:
    """FastMCP authentication provider for the webapp."""
    
    def __init__(self):
        self.config = UnifiedAuthConfig()
        self.provider = self._create_provider()
        
        logger.info("FastMCP auth provider initialized", 
                   auth_mode=self.config.auth_mode,
                   github_enabled=bool(self.config.github_client_id))
    
    def _create_provider(self):
        """Create the appropriate FastMCP authentication provider."""
        if self.config.auth_mode == "github":
            # Use FastMCP GitHub OAuth provider directly
            return GitHubProvider(
                client_id=self.config.github_client_id,
                client_secret=self.config.github_client_secret
            )
        else:
            # Fallback to simple JWT with shared secret
            return JWTVerifier(
                public_key=self.config.jwt_secret_key,
                algorithm=self.config.jwt_algorithm,
                issuer="service-collection-webapp",
                audience="service-collection-webapp"
            )
    
    async def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify a JWT token using FastMCP's authentication providers.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload if valid, None if invalid
        """
        try:
            # Use FastMCP's token verification
            access_token = await self.provider.verify_token(token)
            if access_token:
                # For JWT tokens, claims are stored in access_token.claims
                claims = getattr(access_token, 'claims', {})
                return {
                    "user_id": claims.get('sub'),
                    "email": claims.get('email'),
                    "permissions": claims.get('permissions', []),
                    "exp": claims.get('exp'),
                    "iat": claims.get('iat')
                }
            return None
        except Exception as e:
            logger.warning("Token verification failed", error=str(e), token_prefix=token[:20])
            return None
    
    def get_auth_metadata(self) -> dict:
        """Get authentication metadata for frontend configuration."""
        return {
            "auth_mode": self.config.auth_mode,
            "github_client_id": self.config.github_client_id if self.config.auth_mode == "github" else None,
            "github_redirect_uri": self.config.github_redirect_uri if self.config.auth_mode == "github" else None,
            "supports_github": bool(self.config.github_client_id),
            "supports_jwt": True  # Always available as fallback
        }


# Global auth provider instance
auth_provider = FastMCPAuthProvider()


async def get_current_user_from_fastmcp(token: str) -> Optional[dict]:
    """
    Get current user information using FastMCP authentication.
    
    This replaces our custom JWT implementation with FastMCP's robust providers.
    """
    return await auth_provider.verify_token(token)


def get_auth_metadata() -> dict:
    """Get authentication configuration metadata."""
    return auth_provider.get_auth_metadata()