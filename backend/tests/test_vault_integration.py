"""
Test Vault integration for Epic 01 - Secrets management.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.core.vault import (
    VaultClient,
    get_vault_client,
    get_jwt_secret,
    get_oauth_secrets,
    rotate_jwt_secret,
    store_oauth_config,
    init_vault_secrets
)


class TestVaultClient:
    """Test VaultClient functionality."""

    @pytest.fixture
    def vault_client(self):
        """Create a VaultClient for testing."""
        return VaultClient(vault_url="http://test-vault:8200", vault_token="test-token")

    @pytest.mark.asyncio
    async def test_vault_client_initialization(self, vault_client):
        """Test VaultClient initialization."""
        assert vault_client.vault_url == "http://test-vault:8200"
        assert vault_client.vault_token == "test-token"
        assert vault_client.timeout == 10

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_health_check_success(self, mock_client, vault_client):
        """Test successful health check."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.health_check()
        assert result is True

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_health_check_failure(self, mock_client, vault_client):
        """Test failed health check."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.health_check()
        assert result is False

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_put_secret_success(self, mock_client, vault_client):
        """Test successfully storing a secret."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        secrets = {"username": "test", "password": "secret123"}
        result = await vault_client.put_secret("test/path", secrets)

        assert result is True
        mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_get_secret_success(self, mock_client, vault_client):
        """Test successfully retrieving a secret."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": {
                    "username": "test",
                    "password": "secret123"
                }
            }
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.get_secret("test/path")

        assert result is not None
        assert result["username"] == "test"
        assert result["password"] == "secret123"

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_get_secret_not_found(self, mock_client, vault_client):
        """Test retrieving a nonexistent secret."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.get_secret("nonexistent/path")
        assert result is None

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_delete_secret_success(self, mock_client, vault_client):
        """Test successfully deleting a secret."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 204

        mock_client_instance = AsyncMock()
        mock_client_instance.delete.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.delete_secret("test/path")
        assert result is True

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_list_secrets_success(self, mock_client, vault_client):
        """Test successfully listing secrets."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "keys": ["secret1", "secret2", "secret3"]
            }
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.list_secrets("test/path")

        assert result is not None
        assert len(result) == 3
        assert "secret1" in result
        assert "secret2" in result
        assert "secret3" in result


class TestVaultHelperFunctions:
    """Test Vault helper functions."""

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    async def test_get_jwt_secret_success(self, mock_get_secret):
        """Test successfully getting JWT secret."""
        mock_get_secret.return_value = {
            "secret_key": "test-jwt-secret",
            "algorithm": "HS256",
            "expire_minutes": "1440"
        }

        result = await get_jwt_secret()
        assert result == "test-jwt-secret"

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    async def test_get_jwt_secret_not_found(self, mock_get_secret):
        """Test getting JWT secret when not found."""
        mock_get_secret.return_value = None

        result = await get_jwt_secret()
        assert result is None

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    async def test_get_oauth_secrets_success(self, mock_get_secret):
        """Test successfully getting OAuth secrets."""
        mock_get_secret.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "redirect_uri": "http://localhost:3000/callback"
        }

        result = await get_oauth_secrets("google")
        assert result is not None
        assert result["client_id"] == "test-client-id"
        assert result["client_secret"] == "test-client-secret"

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    async def test_get_oauth_secrets_not_found(self, mock_get_secret):
        """Test getting OAuth secrets when not found."""
        mock_get_secret.return_value = None

        result = await get_oauth_secrets("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    @patch('app.core.vault.vault_client.put_secret')
    async def test_rotate_jwt_secret_success(self, mock_put_secret, mock_get_secret):
        """Test successfully rotating JWT secret."""
        mock_get_secret.return_value = {
            "secret_key": "old-secret",
            "algorithm": "HS256",
            "expire_minutes": "1440"
        }
        mock_put_secret.return_value = True

        result = await rotate_jwt_secret("new-secret")
        assert result is True

        # Verify the secret was updated
        mock_put_secret.assert_called_once_with(
            "auth/jwt",
            {
                "secret_key": "new-secret",
                "algorithm": "HS256",
                "expire_minutes": "1440"
            }
        )

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.get_secret')
    async def test_rotate_jwt_secret_no_existing(self, mock_get_secret):
        """Test rotating JWT secret when no existing secret."""
        mock_get_secret.return_value = None

        result = await rotate_jwt_secret("new-secret")
        assert result is False

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.put_secret')
    async def test_store_oauth_config_success(self, mock_put_secret):
        """Test successfully storing OAuth configuration."""
        mock_put_secret.return_value = True

        result = await store_oauth_config(
            "google",
            "test-client-id",
            "test-client-secret",
            {"redirect_uri": "http://localhost:3000/callback"}
        )

        assert result is True
        mock_put_secret.assert_called_once_with(
            "oauth/google",
            {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uri": "http://localhost:3000/callback"
            }
        )

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.put_secret')
    async def test_store_oauth_config_minimal(self, mock_put_secret):
        """Test storing OAuth configuration with minimal data."""
        mock_put_secret.return_value = True

        result = await store_oauth_config(
            "github",
            "github-client-id",
            "github-client-secret"
        )

        assert result is True
        mock_put_secret.assert_called_once_with(
            "oauth/github",
            {
                "client_id": "github-client-id",
                "client_secret": "github-client-secret"
            }
        )


class TestVaultInitialization:
    """Test Vault initialization."""

    @pytest.mark.asyncio
    @patch('app.core.vault.vault_client.put_secret')
    async def test_init_vault_secrets(self, mock_put_secret):
        """Test initializing Vault secrets."""
        mock_put_secret.return_value = True

        await init_vault_secrets()

        # Verify all expected secrets were stored
        expected_calls = [
            (("database/postgres",), {}),
            (("cache/redis",), {}),
            (("auth/jwt",), {}),
            (("ai/openai",), {}),
        ]

        assert mock_put_secret.call_count == 4

        # Check that database secrets were stored
        database_call = next(
            call for call in mock_put_secret.call_args_list
            if call[0][0] == "database/postgres"
        )
        assert database_call is not None

        # Check that JWT secrets were stored
        jwt_call = next(
            call for call in mock_put_secret.call_args_list
            if call[0][0] == "auth/jwt"
        )
        assert jwt_call is not None


class TestVaultDependencyInjection:
    """Test Vault dependency injection."""

    @pytest.mark.asyncio
    async def test_get_vault_client(self):
        """Test getting Vault client through dependency injection."""
        client = await get_vault_client()
        assert client is not None
        assert isinstance(client, VaultClient)


class TestVaultErrorHandling:
    """Test Vault error handling."""

    @pytest.fixture
    def vault_client(self):
        """Create a VaultClient for testing."""
        return VaultClient(vault_url="http://test-vault:8200", vault_token="test-token")

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_put_secret_error(self, mock_client, vault_client):
        """Test error handling when storing a secret fails."""
        # Mock an exception
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("Connection error")
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.put_secret("test/path", {"key": "value"})
        assert result is False

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_get_secret_error(self, mock_client, vault_client):
        """Test error handling when retrieving a secret fails."""
        # Mock an exception
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("Connection error")
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.get_secret("test/path")
        assert result is None

    @pytest.mark.asyncio
    @patch('app.core.vault.httpx.AsyncClient')
    async def test_health_check_exception(self, mock_client, vault_client):
        """Test health check when an exception occurs."""
        # Mock an exception
        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = Exception("Connection error")
        mock_client.return_value = mock_client_instance

        vault_client._client = mock_client_instance

        result = await vault_client.health_check()
        assert result is False


class TestVaultClientLifecycle:
    """Test Vault client lifecycle management."""

    @pytest.mark.asyncio
    async def test_client_close(self):
        """Test closing Vault client."""
        client = VaultClient()

        # Simulate client being used
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            # Use the client
            async with client.client() as c:
                assert c is not None

            # Close the client
            await client.close()

            # Verify close was called
            mock_client_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_reuse(self):
        """Test that client instances are reused."""
        client = VaultClient()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance

            # Use the client multiple times
            async with client.client() as c1:
                pass

            async with client.client() as c2:
                pass

            # Client should only be created once
            assert mock_client_class.call_count == 1