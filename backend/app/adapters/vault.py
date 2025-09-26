"""
HashiCorp Vault adapter for secrets management.
"""

import os
from typing import Any

import hvac
from hvac.exceptions import VaultError
from requests import exceptions as requests_exceptions

from app.core.config import settings
from app.core.logger import LoggerMixin, get_logger

logger = get_logger(__name__)


class VaultAdapter(LoggerMixin):
    """HashiCorp Vault adapter for secrets management"""

    def __init__(self) -> None:
        super().__init__()
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Vault client connection"""
        try:
            self.client = hvac.Client(
                url=settings.VAULT_ADDR,
                token=settings.VAULT_TOKEN,
                verify=False,  # For development - use proper SSL in production
            )

            if self.client.is_authenticated():
                logger.info("Vault client initialized", url=settings.VAULT_ADDR)
            else:
                raise VaultError("Vault authentication failed")

        except (VaultError, requests_exceptions.RequestException) as exc:
            logger.error("Failed to initialize Vault client", error=str(exc))
            self.client = None

    async def health_check(self) -> dict[str, Any]:
        """Check Vault service health"""
        try:
            if not self.client:
                return {
                    "status": "unhealthy",
                    "message": "Vault client not initialized",
                    "details": {},
                }

            health = self.client.sys.health()
            return {
                "status": "healthy",
                "message": "Vault connection successful",
                "details": {
                    "initialized": health.get("initialized", False),
                    "sealed": health.get("sealed", True),
                    "version": health.get("version", "unknown"),
                    "cluster_name": health.get("cluster_name", "unknown"),
                },
            }

        except (VaultError, requests_exceptions.RequestException) as exc:
            logger.error("Vault health check failed", error=str(exc))
            return {
                "status": "unhealthy",
                "message": f"Vault connection failed: {exc!s}",
                "details": {"error": str(exc)},
            }

    async def read_secret(self, path: str) -> dict[str, Any] | None:
        """
        Read secret from Vault.

        Args:
            path: Secret path in Vault (e.g., 'secret/data/jeex_plan/api_keys')

        Returns:
            Dictionary containing secret data or None if not found
        """
        try:
            if not self.client:
                logger.warning("Vault client not available, returning None")
                return None

            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            if response and "data" in response:
                return response["data"]["data"]
            return None

        except VaultError as e:
            logger.error("Failed to read secret from Vault", path=path, error=str(e))
            return None

    async def write_secret(self, path: str, data: dict[str, Any]) -> bool:
        """
        Write secret to Vault.

        Args:
            path: Secret path in Vault
            data: Dictionary containing secret data

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client:
                logger.warning("Vault client not available, cannot write secret")
                return False

            self.client.secrets.kv.v2.create_or_update_secret(path=path, secret=data)
            logger.info("Secret written to Vault", path=path)
            return True

        except VaultError as e:
            logger.error("Failed to write secret to Vault", path=path, error=str(e))
            return False

    async def delete_secret(self, path: str) -> bool:
        """
        Delete secret from Vault.

        Args:
            path: Secret path in Vault

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client:
                logger.warning("Vault client not available, cannot delete secret")
                return False

            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
            logger.info("Secret deleted from Vault", path=path)
            return True

        except VaultError as e:
            logger.error("Failed to delete secret from Vault", path=path, error=str(e))
            return False

    async def list_secrets(self, path: str = "") -> list[str] | None:
        """
        List secrets at given path.

        Args:
            path: Base path to list secrets from

        Returns:
            List of secret paths or None if failed
        """
        try:
            if not self.client:
                logger.warning("Vault client not available, cannot list secrets")
                return None

            response = self.client.secrets.kv.v2.list_secrets(path=path)
            if response and "data" in response:
                return response["data"]["keys"]
            return []

        except VaultError as e:
            logger.error("Failed to list secrets from Vault", path=path, error=str(e))
            return None

    # Environment-specific secret management
    async def get_environment_secrets(self, environment: str) -> dict[str, Any]:
        """
        Get all secrets for a specific environment.

        Args:
            environment: Environment name (e.g., 'development', 'production')

        Returns:
            Dictionary of environment secrets
        """
        path = f"secret/data/jeex_plan/{environment}"
        return await self.read_secret(path) or {}

    async def set_environment_secrets(
        self, environment: str, secrets: dict[str, Any]
    ) -> bool:
        """
        Set secrets for a specific environment.

        Args:
            environment: Environment name
            secrets: Dictionary of secrets to set

        Returns:
            True if successful, False otherwise
        """
        path = f"secret/data/jeex_plan/{environment}"
        return await self.write_secret(path, secrets)

    # Tenant-specific secrets
    async def get_tenant_secrets(self, tenant_id: str) -> dict[str, Any]:
        """
        Get secrets for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary of tenant secrets
        """
        path = f"secret/data/tenants/{tenant_id}"
        return await self.read_secret(path) or {}

    async def set_tenant_secrets(self, tenant_id: str, secrets: dict[str, Any]) -> bool:
        """
        Set secrets for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            secrets: Dictionary of tenant secrets

        Returns:
            True if successful, False otherwise
        """
        path = f"secret/data/tenants/{tenant_id}"
        return await self.write_secret(path, secrets)

    # API key management
    async def get_api_key(self, provider: str) -> str | None:
        """
        Get API key for a specific provider.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')

        Returns:
            API key string or None if not found
        """
        secrets = await self.get_environment_secrets(settings.ENVIRONMENT)
        return secrets.get(f"{provider}_api_key")

    async def set_api_key(self, provider: str, api_key: str) -> bool:
        """
        Set API key for a specific provider.

        Args:
            provider: Provider name
            api_key: API key string

        Returns:
            True if successful, False otherwise
        """
        secrets = await self.get_environment_secrets(settings.ENVIRONMENT)
        secrets[f"{provider}_api_key"] = api_key
        return await self.set_environment_secrets(settings.ENVIRONMENT, secrets)

    # Database credentials management
    async def get_database_credentials(self) -> dict[str, Any]:
        """
        Get database credentials from Vault.

        Returns:
            Dictionary with database connection parameters
        """
        path = "secret/data/jeex_plan/database"
        return await self.read_secret(path) or {}

    async def set_database_credentials(self, credentials: dict[str, Any]) -> bool:
        """
        Set database credentials in Vault.

        Args:
            credentials: Dictionary with database connection parameters

        Returns:
            True if successful, False otherwise
        """
        path = "secret/data/jeex_plan/database"
        return await self.write_secret(path, credentials)

    # Configuration management
    async def get_app_config(self) -> dict[str, Any]:
        """
        Get application configuration from Vault.

        Returns:
            Dictionary with application configuration
        """
        path = "secret/data/jeex_plan/config"
        return await self.read_secret(path) or {}

    async def set_app_config(self, config: dict[str, Any]) -> bool:
        """
        Set application configuration in Vault.

        Args:
            config: Dictionary with application configuration

        Returns:
            True if successful, False otherwise
        """
        path = "secret/data/jeex_plan/config"
        return await self.write_secret(path, config)

    # Fallback to environment variables when Vault is not available
    async def get_secret_with_fallback(
        self, vault_path: str, env_var: str, default: str | None = None
    ) -> str | None:
        """
        Get secret from Vault with fallback to environment variable.

        Args:
            vault_path: Path to secret in Vault
            env_var: Environment variable name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        if self.client:
            secret_data = await self.read_secret(vault_path)
            if secret_data and "value" in secret_data:
                value = secret_data["value"]
                if value is None:
                    return default
                return str(value)

        return os.getenv(env_var, default)

    async def initialize_vault_secrets(self) -> bool:
        """
        Initialize default Vault secrets for the application.

        This should be called during application setup or deployment.
        """
        try:
            if not self.client:
                logger.warning("Vault client not available, skipping initialization")
                return False

            # Create initial structure
            initial_secrets = {
                "development": {
                    "openai_api_key": settings.OPENAI_API_KEY,
                    "anthropic_api_key": settings.ANTHROPIC_API_KEY,
                    "debug": True,
                },
                "production": {"debug": False},
                "config": {
                    "app_name": settings.APP_NAME,
                    "version": "1.0.0",
                    "environment": settings.ENVIRONMENT,
                },
            }

            for path, data in initial_secrets.items():
                await self.write_secret(f"secret/data/jeex_plan/{path}", data)

            logger.info("Vault secrets initialized successfully")
            return True

        except (VaultError, requests_exceptions.RequestException) as exc:
            logger.error("Failed to initialize Vault secrets", error=str(exc))
            return False
