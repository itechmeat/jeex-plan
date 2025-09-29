"""
Application configuration with environment variable support,
Vault integration, and type validation using Pydantic settings.
"""

import logging
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from pydantic.fields import FieldValidationInfo  # type: ignore
except ImportError:  # Pydantic >=2.11 uses ValidationInfo instead
    from pydantic import ValidationInfo as FieldValidationInfo


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(extra="ignore")

    # Application
    APP_NAME: str = "JEEX Plan API"
    ENVIRONMENT: str = Field(default="development")
    SECRET_KEY: str = Field(default="dev-secret-key")
    DEBUG: bool = Field(default=False)

    # Default Technology Stack
    DEFAULT_TECHNOLOGY_STACK: list[str] = Field(
        default=["JavaScript", "Node.js", "React", "PostgreSQL"],
    )

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS_STR: str | None = Field(default=None, alias="ALLOWED_ORIGINS")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/jeex_plan",
    )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")
    REDIS_PASSWORD: str | None = Field(default=None)

    # Qdrant Vector Database
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str | None = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="jeex_plan_documents")

    # HashiCorp Vault
    VAULT_ADDR: str = Field(default="http://vault:8200")
    VAULT_TOKEN: str | None = Field(default=None)
    USE_VAULT: bool = Field(default=True)
    VAULT_VERIFY: bool | str = Field(default=True)

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    ALGORITHM: str = "HS256"

    # OAuth2 Settings
    GOOGLE_CLIENT_ID: str | None = Field(default=None)
    GOOGLE_CLIENT_SECRET: str | None = Field(default=None)
    GITHUB_CLIENT_ID: str | None = Field(default=None)
    GITHUB_CLIENT_SECRET: str | None = Field(default=None)
    OAUTH_REDIRECT_URL: str = Field(default="http://localhost:5210/auth/callback")

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW: int = Field(default=60)  # seconds

    # LLM Settings
    OPENAI_API_KEY: str | None = Field(default=None)
    OPENAI_BASE_URL: str | None = Field(default=None)
    ANTHROPIC_API_KEY: str | None = Field(default=None)
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4")

    # Embedding Settings
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    EMBEDDING_MAX_CHUNK_SIZE: int = Field(default=1000)
    EMBEDDING_CHUNK_OVERLAP: int = Field(default=200)
    EMBEDDING_BATCH_SIZE: int = Field(default=10)

    # Observability
    ENABLE_OBSERVABILITY: bool = Field(default=False)
    OTLP_ENDPOINT: str | None = Field(default=None)
    LOG_LEVEL: str = Field(default="INFO")

    # Cache Settings
    CACHE_DEFAULT_TTL: int = Field(default=3600)  # 1 hour
    CACHE_SEARCH_TTL: int = Field(default=1800)  # 30 minutes
    CACHE_EMBEDDING_TTL: int = Field(default=86400)  # 24 hours
    CACHE_STATS_TTL: int = Field(default=300)  # 5 minutes
    CACHE_WARMUP_DELAY_SEC: float = Field(default=0.1)

    # File Storage
    UPLOAD_DIR: str = Field(default="/app/uploads")
    EXPORT_DIR: str = Field(default="/app/exports")

    # Multi-tenancy
    DEFAULT_TENANT_ID: str = Field(default="default")
    ENABLE_TENANT_ISOLATION: bool = Field(default=True)

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("VAULT_TOKEN", mode="before")
    @classmethod
    def validate_vault_token(
        cls, token: str | None, info: FieldValidationInfo
    ) -> str | None:
        """Ensure Vault token is provided when Vault is enabled."""
        use_vault = info.data.get("USE_VAULT", True)
        placeholder = "__REPLACE_WITH_TOKEN__"

        if not use_vault:
            return token

        if token in (None, "", placeholder):
            raise ValueError("VAULT_TOKEN must be set when USE_VAULT is true")

        if isinstance(token, str) and len(token) < 10:
            raise ValueError("VAULT_TOKEN appears to be too short to be valid")

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
    def ALLOWED_ORIGINS(self) -> list[str]:
        """Get allowed origins for CORS"""
        if self.ALLOWED_ORIGINS_STR:
            # Remove quotes and split by comma
            origins_str = self.ALLOWED_ORIGINS_STR.strip().strip('"').strip("'")
            return [
                origin.strip() for origin in origins_str.split(",") if origin.strip()
            ]
        return [
            "http://localhost:5200",
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    def get_database_settings(self) -> dict[str, Any]:
        """Get database connection settings"""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DEBUG,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_pre_ping": True,
        }

    def get_redis_settings(self) -> dict[str, Any]:
        """Get Redis connection settings"""
        from urllib.parse import urlparse

        parsed = urlparse(self.REDIS_URL)

        settings_dict: dict[str, Any] = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 6379,
            "decode_responses": True,
        }

        # Use password from URL or from separate env var
        if parsed.password:
            settings_dict["password"] = parsed.password
        elif self.REDIS_PASSWORD:
            settings_dict["password"] = self.REDIS_PASSWORD

        return settings_dict


logger = logging.getLogger(__name__)


class VaultSettings:
    """Settings manager with Vault integration for hybrid secret management.

    In development: Uses .env file secrets
    In production: Uses Vault for sensitive secrets with .env fallbacks
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._vault_cache: dict[str, dict[str, Any]] = {}
        self._use_vault = settings.USE_VAULT and settings.is_production

    async def get_vault_secret(
        self, path: str, *, use_cache: bool = True
    ) -> dict[str, Any] | None:
        """Get secret from Vault with caching."""
        if not self._use_vault:
            logger.debug(
                "Vault disabled or not in production; skipping secret %s", path
            )
            return None

        if use_cache and path in self._vault_cache:
            return self._vault_cache[path]

        try:
            # Import here to avoid circular imports
            from .vault import vault_client

            secrets: dict[str, Any] | None = await vault_client.get_secret(path)
            if secrets and use_cache:
                self._vault_cache[path] = secrets
            if secrets:
                logger.info("Successfully retrieved secret from Vault path %s", path)
            return secrets
        except Exception as exc:
            logger.warning("Failed to get secret from Vault path %s: %s", path, exc)
            return None

    async def get_database_url(self) -> str:
        """Get database URL from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("database/postgres")
            if secrets:
                logger.info("Using database URL from Vault")
                async_url = secrets.get("async_url")
                if isinstance(async_url, str):
                    return async_url

                sync_url = secrets.get("url")
                if isinstance(sync_url, str):
                    return sync_url

                username = secrets.get("username")
                password = secrets.get("password")
                host = secrets.get("host")
                port = secrets.get("port")
                database = secrets.get("database")

                if all(
                    isinstance(value, str)
                    for value in (username, password, host, database)
                ) and isinstance(port, (int, str)):
                    port_str = str(port)
                    return (
                        f"postgresql://{username}:{password}"
                        f"@{host}:{port_str}/{database}"
                    )
                logger.warning(
                    "Failed to get database secrets from Vault, using env fallback"
                )

        # Fallback to environment variables (development or Vault failure)
        return self.settings.DATABASE_URL

    async def get_redis_url(self) -> str:
        """Get Redis URL from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("cache/redis")
            if secrets:
                logger.info("Using Redis URL from Vault")
                password_part = (
                    f":{secrets['password']}@"
                    if isinstance(secrets.get("password"), str)
                    else ""
                )
                host = secrets.get("host")
                port = secrets.get("port")
                if isinstance(host, str) and isinstance(port, (int, str)):
                    return f"redis://{password_part}{host}:{port}/0"
            logger.warning("Failed to get Redis secrets from Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.REDIS_URL

    async def get_jwt_secret(self) -> str:
        """Get JWT secret from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("auth/jwt")
            if secrets:
                logger.info("Using JWT secret from Vault")
                secret_key = secrets.get("secret_key")
                if isinstance(secret_key, str):
                    return secret_key
                logger.warning(
                    "Failed to get JWT secret from Vault, using env fallback"
                )

        # Fallback to environment variables (development or Vault failure)
        return self.settings.SECRET_KEY

    async def get_openai_api_key(self) -> str | None:
        """Get OpenAI API key from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("ai/openai")
            if secrets:
                logger.info("Using OpenAI API key from Vault")
                api_key = secrets.get("api_key")
                if isinstance(api_key, str):
                    return api_key
            logger.debug("No OpenAI API key found in Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.OPENAI_API_KEY

    async def get_anthropic_api_key(self) -> str | None:
        """Get Anthropic API key from Vault in production or fallback to env config."""
        if self._use_vault:
            secrets = await self.get_vault_secret("ai/anthropic")
            if secrets:
                logger.info("Using Anthropic API key from Vault")
                api_key = secrets.get("api_key")
                if isinstance(api_key, str):
                    return api_key
            logger.debug("No Anthropic API key found in Vault, using env fallback")

        # Fallback to environment variables (development or Vault failure)
        return self.settings.ANTHROPIC_API_KEY


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


def get_vault_settings() -> VaultSettings:
    """Get Vault-integrated settings."""
    return VaultSettings(get_settings())


# Shared middleware configuration
EXEMPT_PATHS = [
    # Documentation and health endpoints
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/ready",
    "/system/status",
    "/api/v1/info",
    "/api/v1/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/oauth",
    "/api/v1/auth/providers",
    "/api/v1/agents/health",
    "/",
]

# Global settings instance
settings = get_settings()
