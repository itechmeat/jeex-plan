"""
Application configuration with environment variable support,
Vault integration, and type validation using Pydantic settings.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
try:
    from pydantic.fields import FieldValidationInfo  # type: ignore
except ImportError:  # Pydantic >=2.11 uses ValidationInfo instead
    from pydantic import ValidationInfo as FieldValidationInfo


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = {"extra": "ignore"}

    # Application
    APP_NAME: str = "JEEX Plan API"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    SECRET_KEY: str = Field(default="dev-secret-key", env="SECRET_KEY")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Default Technology Stack
    DEFAULT_TECHNOLOGY_STACK: List[str] = Field(
        default=["JavaScript", "Node.js", "React", "PostgreSQL"],
        env="DEFAULT_TECHNOLOGY_STACK"
    )

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS_STR: Optional[str] = Field(default=None, env="ALLOWED_ORIGINS")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/jeex_plan",
        env="DATABASE_URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        env="REDIS_URL"
    )
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # Qdrant Vector Database
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        env="QDRANT_URL"
    )
    QDRANT_API_KEY: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    QDRANT_COLLECTION: str = Field(default="jeex_plan_documents", env="QDRANT_COLLECTION")

    # HashiCorp Vault
    VAULT_ADDR: str = Field(
        default="http://vault:8200",
        env="VAULT_ADDR"
    )
    VAULT_TOKEN: Optional[str] = Field(default=None, env="VAULT_TOKEN")
    USE_VAULT: bool = Field(default=True, env="USE_VAULT")

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = "HS256"

    # OAuth2 Settings
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None, env="GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None, env="GITHUB_CLIENT_SECRET")
    OAUTH_REDIRECT_URL: str = Field(default="http://localhost:5210/auth/callback", env="OAUTH_REDIRECT_URL")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4", env="DEFAULT_LLM_MODEL")

    # Embedding Settings
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    EMBEDDING_MAX_CHUNK_SIZE: int = Field(default=1000, env="EMBEDDING_MAX_CHUNK_SIZE")
    EMBEDDING_CHUNK_OVERLAP: int = Field(default=200, env="EMBEDDING_CHUNK_OVERLAP")
    EMBEDDING_BATCH_SIZE: int = Field(default=10, env="EMBEDDING_BATCH_SIZE")

    # Observability
    ENABLE_OBSERVABILITY: bool = Field(default=False, env="ENABLE_OBSERVABILITY")
    OTLP_ENDPOINT: Optional[str] = Field(default=None, env="OTLP_ENDPOINT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Cache Settings
    CACHE_DEFAULT_TTL: int = Field(default=3600, env="CACHE_DEFAULT_TTL")  # 1 hour
    CACHE_SEARCH_TTL: int = Field(default=1800, env="CACHE_SEARCH_TTL")  # 30 minutes
    CACHE_EMBEDDING_TTL: int = Field(default=86400, env="CACHE_EMBEDDING_TTL")  # 24 hours

    # File Storage
    UPLOAD_DIR: str = Field(default="/app/uploads", env="UPLOAD_DIR")
    EXPORT_DIR: str = Field(default="/app/exports", env="EXPORT_DIR")

    # Multi-tenancy
    DEFAULT_TENANT_ID: str = Field(default="default", env="DEFAULT_TENANT_ID")
    ENABLE_TENANT_ISOLATION: bool = Field(default=True, env="ENABLE_TENANT_ISOLATION")


    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("VAULT_TOKEN", mode="before")
    @classmethod
    def validate_vault_token(cls, token: Optional[str], info: FieldValidationInfo):
        """Ensure Vault token is provided when Vault is enabled."""
        use_vault = info.data.get("USE_VAULT", True)
        placeholder = "__REPLACE_WITH_TOKEN__"

        if not use_vault:
            return token

        if token in (None, "", placeholder):
            raise ValueError(
                "VAULT_TOKEN must be set when USE_VAULT is true and cannot be the placeholder value"
            )

        return token

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Get allowed origins for CORS"""
        if self.ALLOWED_ORIGINS_STR:
            # Remove quotes and split by comma
            origins_str = self.ALLOWED_ORIGINS_STR.strip().strip('"').strip("'")
            return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
        return ["http://localhost:5200", "http://localhost:3000", "http://localhost:8080"]

    def get_database_settings(self) -> dict:
        """Get database connection settings"""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DEBUG,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_pre_ping": True,
        }

    def get_redis_settings(self) -> dict:
        """Get Redis connection settings"""
        from urllib.parse import urlparse
        parsed = urlparse(self.REDIS_URL)

        settings = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 6379,
            "decode_responses": True,
        }

        # Use password from URL or from separate env var
        if parsed.password:
            settings["password"] = parsed.password
        elif self.REDIS_PASSWORD:
            settings["password"] = self.REDIS_PASSWORD

        return settings


logger = logging.getLogger(__name__)


class VaultSettings:
    """Settings manager with Vault integration for hybrid secret management.

    In development: Uses .env file secrets
    In production: Uses Vault for sensitive secrets with .env fallbacks
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._vault_cache: Dict[str, Any] = {}
        self._use_vault = settings.USE_VAULT and settings.is_production

    async def get_vault_secret(self, path: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get secret from Vault with caching."""
        if not self._use_vault:
            logger.debug(f"Vault disabled or not in production, skipping secret {path}")
            return None

        if use_cache and path in self._vault_cache:
            return self._vault_cache[path]

        try:
            # Import here to avoid circular imports
            from .vault import vault_client
            secrets = await vault_client.get_secret(path)
            if secrets and use_cache:
                self._vault_cache[path] = secrets
            logger.info(f"Successfully retrieved secret from Vault: {path}")
            return secrets
        except Exception as e:
            logger.warning(f"Failed to get secret from Vault at {path}: {e}")
            return None

    async def get_database_url(self) -> str:
        """Get database URL from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("database/postgres")
            if secrets:
                logger.info("Using database URL from Vault")
                if secrets.get("async_url"):
                    return secrets["async_url"]
                if secrets.get("url"):
                    return secrets["url"]
                return (
                    f"postgresql://{secrets['username']}:{secrets['password']}"
                    f"@{secrets['host']}:{secrets['port']}/{secrets['database']}"
                )
            logger.warning("Failed to get database secrets from Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return getattr(self.settings, 'DATABASE_URL', 'postgresql://postgres:password@localhost:5432/jeex_plan')

    async def get_redis_url(self) -> str:
        """Get Redis URL from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("cache/redis")
            if secrets:
                logger.info("Using Redis URL from Vault")
                password_part = f":{secrets['password']}@" if secrets.get('password') else ""
                return f"redis://{password_part}{secrets['host']}:{secrets['port']}/0"
            logger.warning("Failed to get Redis secrets from Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return getattr(self.settings, 'REDIS_URL', 'redis://localhost:6379')

    async def get_jwt_secret(self) -> str:
        """Get JWT secret from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("auth/jwt")
            if secrets:
                logger.info("Using JWT secret from Vault")
                return secrets.get('secret_key', self.settings.SECRET_KEY)
            logger.warning("Failed to get JWT secret from Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.SECRET_KEY

    async def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("ai/openai")
            if secrets:
                logger.info("Using OpenAI API key from Vault")
                return secrets.get('api_key')
            logger.debug("No OpenAI API key found in Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.OPENAI_API_KEY

    async def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("ai/anthropic")
            if secrets:
                logger.info("Using Anthropic API key from Vault")
                return secrets.get('api_key')
            logger.debug("No Anthropic API key found in Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.ANTHROPIC_API_KEY


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


def get_vault_settings() -> VaultSettings:
    """Get Vault-integrated settings."""
    return VaultSettings(get_settings())


# Global settings instance
settings = get_settings()
