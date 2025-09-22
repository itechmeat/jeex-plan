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


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    APP_NAME: str = "JEEX Plan API"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    SECRET_KEY: str = Field(default="dev-secret-key", env="SECRET_KEY")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:5200", "http://localhost:3000"],
        env="ALLOWED_ORIGINS"
    )

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
    VAULT_TOKEN: str = Field(default="dev-token-jeex-plan", env="VAULT_TOKEN")
    USE_VAULT: bool = Field(default=True, env="USE_VAULT")

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = "HS256"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4", env="DEFAULT_LLM_MODEL")

    # Observability
    OTLP_ENDPOINT: Optional[str] = Field(default=None, env="OTLP_ENDPOINT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # File Storage
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    EXPORT_DIR: str = Field(default="./exports", env="EXPORT_DIR")

    # Multi-tenancy
    DEFAULT_TENANT_ID: str = Field(default="default", env="DEFAULT_TENANT_ID")
    ENABLE_TENANT_ISOLATION: bool = Field(default=True, env="ENABLE_TENANT_ISOLATION")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

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
        settings = {
            "host": self.REDIS_URL.split("://")[1].split(":")[0],
            "port": int(self.REDIS_URL.split(":")[-1].split("/")[0]),
            "decode_responses": True,
        }
        if self.REDIS_PASSWORD:
            settings["password"] = self.REDIS_PASSWORD
        return settings


logger = logging.getLogger(__name__)


class VaultSettings:
    """Settings manager with Vault integration."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._vault_cache: Dict[str, Any] = {}

    async def get_vault_secret(self, path: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get secret from Vault with caching."""
        if not self.settings.USE_VAULT:
            return None

        if use_cache and path in self._vault_cache:
            return self._vault_cache[path]

        try:
            # Import here to avoid circular imports
            from .vault import vault_client
            secrets = await vault_client.get_secret(path)
            if secrets and use_cache:
                self._vault_cache[path] = secrets
            return secrets
        except Exception as e:
            logger.warning(f"Failed to get secret from Vault at {path}: {e}")
            return None

    async def get_database_url(self) -> str:
        """Get database URL from Vault or fallback to config."""
        if self.settings.USE_VAULT:
            secrets = await self.get_vault_secret("database/postgres")
            if secrets:
                return f"postgresql://{secrets['username']}:{secrets['password']}@{secrets['host']}:{secrets['port']}/{secrets['database']}"

        return self.settings.DATABASE_URL

    async def get_redis_url(self) -> str:
        """Get Redis URL from Vault or fallback to config."""
        if self.settings.USE_VAULT:
            secrets = await self.get_vault_secret("cache/redis")
            if secrets:
                password_part = f":{secrets['password']}@" if secrets.get('password') else ""
                return f"redis://{password_part}{secrets['host']}:{secrets['port']}/0"

        return self.settings.REDIS_URL

    async def get_jwt_secret(self) -> str:
        """Get JWT secret from Vault or fallback to config."""
        if self.settings.USE_VAULT:
            secrets = await self.get_vault_secret("auth/jwt")
            if secrets:
                return secrets.get('secret_key', self.settings.SECRET_KEY)

        return self.settings.SECRET_KEY

    async def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from Vault or fallback to config."""
        if self.settings.USE_VAULT:
            secrets = await self.get_vault_secret("ai/openai")
            if secrets:
                return secrets.get('api_key')

        return self.settings.OPENAI_API_KEY


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


def get_vault_settings() -> VaultSettings:
    """Get Vault-integrated settings."""
    return VaultSettings(get_settings())


# Global settings instance
settings = get_settings()