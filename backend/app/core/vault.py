"""
HashiCorp Vault client integration for JEEX Plan.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

DEV_PLACEHOLDER_TOKEN = "development-placeholder-token"
DEV_ENV_VALUES = {"dev", "development"}


class VaultClient:
    """HashiCorp Vault client for secret management."""

    def __init__(
        self,
        vault_url: str = "http://vault:8200",
        vault_token: str | None = None,
        timeout: int = 10,
    ) -> None:
        self.vault_url = vault_url.rstrip("/")

        resolved_token = vault_token or os.getenv("VAULT_TOKEN")
        env_value = next(
            (
                value
                for value in (
                    os.getenv("ENVIRONMENT"),
                    os.getenv("APP_ENV"),
                    os.getenv("FLASK_ENV"),
                )
                if value
            ),
            "development",
        ).lower()

        if not resolved_token:
            if env_value not in DEV_ENV_VALUES:
                raise RuntimeError(
                    "VAULT_TOKEN environment variable must be set outside development environments."
                )
            logger.warning(
                "VAULT_TOKEN not provided; using placeholder token because environment=%s",
                env_value,
            )
            resolved_token = DEV_PLACEHOLDER_TOKEN

        self.vault_token = resolved_token
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def client(self):
        """Async context manager for HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"X-Vault-Token": self.vault_token},
            )
        try:
            yield self._client
        except Exception as e:
            logger.error(f"Vault client error: {e}")
            raise
        # Don't close the client here - reuse it

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def health_check(self) -> bool:
        """Check Vault health status."""
        try:
            async with self.client() as client:
                response = await client.get(f"{self.vault_url}/v1/sys/health")
                return response.status_code in [200, 429, 472, 473]  # All valid states
        except Exception as e:
            logger.warning(f"Vault health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def put_secret(
        self, path: str, secrets: dict[str, Any], mount_point: str = "secret"
    ) -> bool:
        """Store secrets in Vault KV store."""
        try:
            async with self.client() as client:
                url = f"{self.vault_url}/v1/{mount_point}/data/{path}"
                payload = {"data": secrets}
                response = await client.post(url, json=payload)

                if response.status_code in [200, 204]:
                    logger.info(f"Successfully stored secret at {path}")
                    return True
                else:
                    logger.error(f"Failed to store secret: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error storing secret at {path}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_secret(
        self, path: str, mount_point: str = "secret"
    ) -> dict[str, Any] | None:
        """Retrieve secrets from Vault KV store."""
        try:
            async with self.client() as client:
                url = f"{self.vault_url}/v1/{mount_point}/data/{path}"
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("data", {})
                elif response.status_code == 404:
                    logger.info(f"Secret not found at {path}")
                    return None
                else:
                    logger.error(f"Failed to retrieve secret: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error retrieving secret at {path}: {e}")
            return None

    async def delete_secret(self, path: str, mount_point: str = "secret") -> bool:
        """Delete secrets from Vault KV store."""
        try:
            async with self.client() as client:
                url = f"{self.vault_url}/v1/{mount_point}/metadata/{path}"
                response = await client.delete(url)

                if response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted secret at {path}")
                    return True
                else:
                    logger.error(f"Failed to delete secret: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error deleting secret at {path}: {e}")
            return False

    async def list_secrets(self, path: str = "", mount_point: str = "secret") -> list | None:
        """List secrets in Vault KV store."""
        try:
            async with self.client() as client:
                url = f"{self.vault_url}/v1/{mount_point}/metadata/{path}"
                response = await client.request("LIST", url)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("keys", [])
                elif response.status_code == 404:
                    logger.info(f"Path not found: {path}")
                    return []
                else:
                    logger.error(f"Failed to list secrets: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error listing secrets at {path}: {e}")
            return None


# Global Vault client instance
vault_client = VaultClient()


async def get_vault_client() -> VaultClient:
    """Dependency injection for Vault client."""
    return vault_client


async def init_vault_secrets() -> None:
    """Initialize default secrets in Vault for development."""
    logger.info("Initializing Vault secrets...")

    # Database secrets
    db_secrets = {
        "username": "jeex_user",
        "password": "jeex_password",
        "host": "postgres",
        "port": "5432",
        "database": "jeex_db",
    }
    await vault_client.put_secret("database/postgres", db_secrets)

    # Redis secrets
    redis_secrets = {
        "host": "redis",
        "port": "6379",
        "password": "",  # No password in dev
    }
    await vault_client.put_secret("cache/redis", redis_secrets)

    # JWT secrets
    jwt_secrets = {
        "secret_key": "dev-jwt-secret-key-change-in-production",
        "algorithm": "HS256",
        "expire_minutes": "1440",  # 24 hours
    }
    await vault_client.put_secret("auth/jwt", jwt_secrets)

    # OpenAI API secrets (placeholder)
    openai_secrets = {
        "api_key": "sk-placeholder-openai-api-key",
        "organization": "",
    }
    await vault_client.put_secret("ai/openai", openai_secrets)

    logger.info("Vault secrets initialized successfully")


async def get_jwt_secret() -> str | None:
    """Get JWT secret from Vault."""
    secrets = await vault_client.get_secret("auth/jwt")
    if secrets:
        return secrets.get("secret_key")
    return None


async def get_oauth_secrets(provider: str) -> dict[str, str] | None:
    """Get OAuth secrets for a specific provider from Vault."""
    secrets = await vault_client.get_secret(f"oauth/{provider}")
    return secrets


async def rotate_jwt_secret(new_secret: str) -> bool:
    """Rotate JWT secret in Vault."""
    jwt_secrets = await vault_client.get_secret("auth/jwt")
    if jwt_secrets:
        jwt_secrets["secret_key"] = new_secret
        return await vault_client.put_secret("auth/jwt", jwt_secrets)
    return False


async def store_oauth_config(
    provider: str,
    client_id: str,
    client_secret: str,
    additional_config: dict[str, Any] | None = None
) -> bool:
    """Store OAuth provider configuration in Vault."""
    config = {
        "client_id": client_id,
        "client_secret": client_secret,
    }

    if additional_config:
        config.update(additional_config)

    return await vault_client.put_secret(f"oauth/{provider}", config)


async def cleanup_vault() -> None:
    """Cleanup Vault client on shutdown."""
    await vault_client.close()
