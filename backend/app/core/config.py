"""
Application configuration with environment variable support
and type validation using Pydantic settings.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


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
        default="http://localhost:8200",
        env="VAULT_ADDR"
    )
    VAULT_TOKEN: Optional[str] = Field(default=None, env="VAULT_TOKEN")

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

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("ENVIRONMENT")
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


# Global settings instance
settings = Settings()