"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, PostgresDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings configuration."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Domain Configuration
    domain: str = Field(default="mcp-vultr.l.supported.systems", env="DOMAIN")
    
    # Database Configuration
    database_url: PostgresDsn = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # OAuth Configuration
    oauth_enabled: bool = Field(default=True, env="OAUTH_ENABLED")
    oauth_issuer_url: str = Field(
        default="https://auth.l.inspect.systems/realms/mcp-vultr", 
        env="OAUTH_ISSUER_URL"
    )
    oauth_client_id: str = Field(default="mcp-vultr-webapp", env="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field(default="", env="OAUTH_CLIENT_SECRET")
    oauth_redirect_uri: str = Field(default="", env="OAUTH_REDIRECT_URI")
    oauth_jwks_cache_ttl: int = Field(default=3600, env="OAUTH_JWKS_CACHE_TTL")
    
    # Vultr Configuration
    vultr_api_key: str = Field(default="", env="VULTR_API_KEY")
    vultr_api_base_url: str = Field(
        default="https://api.vultr.com/v2", 
        env="VULTR_API_BASE_URL"
    )
    vultr_rate_limit: int = Field(default=100, env="VULTR_RATE_LIMIT")
    
    # Procrastinate Configuration
    procrastinate_database_url: PostgresDsn = Field(env="PROCRASTINATE_DATABASE_URL")
    procrastinate_queue_name: str = Field(default="service_collections", env="PROCRASTINATE_QUEUE_NAME")
    procrastinate_max_workers: int = Field(default=4, env="PROCRASTINATE_MAX_WORKERS")
    
    # Security Configuration
    secret_key: str = Field(default="change-in-production", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS Configuration
    allowed_origins: List[str] = Field(default_factory=list, env="ALLOWED_ORIGINS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Feature Flags
    enable_workflow_approvals: bool = Field(default=True, env="ENABLE_WORKFLOW_APPROVALS")
    enable_cost_estimation: bool = Field(default=True, env="ENABLE_COST_ESTIMATION")
    enable_audit_logging: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    
    # Performance Configuration
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")
    max_concurrent_operations: int = Field(default=10, env="MAX_CONCURRENT_OPERATIONS")
    operation_timeout_seconds: int = Field(default=600, env="OPERATION_TIMEOUT_SECONDS")
    
    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @validator("oauth_redirect_uri", always=True)
    def set_oauth_redirect_uri(cls, v, values):
        """Set default OAuth redirect URI based on domain."""
        if not v and "domain" in values:
            return f"https://{values['domain']}/auth/callback"
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """Validate secret key in production."""
        if v == "change-in-production":
            import os
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError("SECRET_KEY must be changed in production")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from Docker Compose .env


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()