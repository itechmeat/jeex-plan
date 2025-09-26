#!/usr/bin/env python3
"""
Initialize Vault secrets for JEEX Plan application.
This script sets up all required secrets in HashiCorp Vault.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.vault import init_vault_secrets, vault_client

logger = get_logger()


async def check_vault_health() -> bool | None:
    """Check if Vault is healthy and accessible."""
    logger.info("Checking Vault health...")

    try:
        is_healthy = await vault_client.health_check()
        if is_healthy:
            logger.info("✅ Vault is healthy and accessible")
            return True
        else:
            logger.error("❌ Vault health check failed")
            return False
    except Exception as exc:
        logger.error("❌ Failed to connect to Vault", error=str(exc))
        return False


async def verify_secrets():
    """Verify that all required secrets are accessible."""
    logger.info("Verifying secrets...")

    required_secrets = [
        "database/postgres",
        "cache/redis",
        "auth/jwt",
        "ai/openai"
    ]

    all_present = True

    for secret_path in required_secrets:
        try:
            secret = await vault_client.get_secret(secret_path)
            if secret:
                logger.info("✅ Secret found", secret_path=secret_path)
            else:
                logger.warning("⚠️  Secret missing", secret_path=secret_path)
                all_present = False
        except Exception as exc:
            logger.error(
                "❌ Failed to read secret",
                secret_path=secret_path,
                error=str(exc),
            )
            all_present = False

    return all_present


async def list_all_secrets() -> None:
    """List all secrets in Vault for debugging."""
    logger.info("Listing all secrets...")

    try:
        secrets = await vault_client.list_secrets()
        if secrets:
            logger.info("Found secret paths", count=len(secrets))
            for secret in secrets:
                logger.info("Secret path", path=secret)
        else:
            logger.info("No secrets found")
    except Exception as exc:
        logger.error("Failed to list secrets", error=str(exc))


async def setup_database_secrets():
    """Setup database-specific secrets."""
    logger.info("Setting up database secrets...")

    from urllib.parse import quote, unquote, urlparse, urlunsplit

    settings = get_settings()

    db_url = settings.DATABASE_URL

    parsed = urlparse(db_url) if db_url else None
    scheme = (parsed.scheme or "").lower() if parsed else ""

    default_user = "jeex_user"
    default_password = "jeex_password"
    default_host = "postgres"
    default_port = "5432"
    default_db = "jeex_plan"

    if scheme.startswith("postgresql"):
        username = unquote(parsed.username) if parsed.username else default_user
        password = unquote(parsed.password) if parsed.password else default_password
        hostname = parsed.hostname or default_host
        port = str(parsed.port or default_port)
        database = parsed.path.lstrip("/") or default_db
        query = parsed.query or ""
    else:
        username = default_user
        password = default_password
        hostname = default_host
        port = default_port
        database = default_db
        query = ""

    # Normalize potential IPv6 hosts for URL construction
    def format_host(host: str) -> str:
        if ":" in host and not host.startswith("["):
            return f"[{host}]"
        return host

    def build_netloc(user: str, pwd: str, host: str, port_str: str) -> str:
        auth_part = ""
        if user:
            auth_part = quote(user)
            if pwd is not None:
                auth_part += f":{quote(pwd)}"
            auth_part += "@"
        host_part = format_host(host)
        port_value = f":{port_str}" if port_str else ""
        return f"{auth_part}{host_part}{port_value}"

    def build_url(scheme: str) -> str:
        netloc = build_netloc(username, password, hostname, port)
        path = f"/{database}" if database else ""
        return urlunsplit((scheme, netloc, path, query, ""))

    canonical_url = build_url("postgresql")
    async_url = build_url("postgresql+asyncpg")

    db_secrets = {
        "username": username,
        "password": password,
        "host": hostname,
        "port": str(port),
        "database": database,
        "url": canonical_url,
        "async_url": async_url,
    }

    success = await vault_client.put_secret("database/postgres", db_secrets)
    if success:
        logger.info("✅ Database secrets configured")
    else:
        logger.error("❌ Failed to configure database secrets")

    return success


async def setup_enhanced_secrets():
    """Setup enhanced secrets for production readiness."""
    logger.info("Setting up enhanced secrets...")

    # Enhanced JWT secrets
    jwt_secrets = {
        "secret_key": "jeex-plan-jwt-secret-key-production-change-this",
        "algorithm": "HS256",
        "access_token_expire_minutes": "30",
        "refresh_token_expire_days": "7"
    }

    # Enhanced Redis secrets
    redis_secrets = {
        "host": "redis",
        "port": "6379",
        "password": "",  # No password in dev
        "url": "redis://redis:6379/0",
        "max_connections": "20"
    }

    # AI/LLM secrets (placeholders)
    openai_secrets = {
        "api_key": "sk-placeholder-openai-api-key-replace-in-production",
        "default_model": "gpt-4",
        "max_tokens": "4000",
        "temperature": "0.7"
    }

    anthropic_secrets = {
        "api_key": "sk-ant-placeholder-anthropic-key-replace-in-production"
    }

    # Application secrets
    app_secrets = {
        "secret_key": "jeex-plan-app-secret-key-production-change-this",
        "encryption_key": "jeex-plan-encryption-key-32-chars",
        "cors_origins": "http://localhost:3000,http://localhost:5200",
        "environment": "development"
    }

    secrets_to_setup = [
        ("auth/jwt", jwt_secrets),
        ("cache/redis", redis_secrets),
        ("ai/openai", openai_secrets),
        ("ai/anthropic", anthropic_secrets),
        ("app/config", app_secrets)
    ]

    all_success = True

    for path, secrets in secrets_to_setup:
        success = await vault_client.put_secret(path, secrets)
        if success:
            logger.info("✅ Enhanced secrets configured", secret_path=path)
        else:
            logger.error("❌ Failed to configure secrets", secret_path=path)
            all_success = False

    return all_success


async def main() -> None:
    """Main initialization function."""
    logger.info("🚀 Starting Vault initialization for JEEX Plan...")

    # Check Vault health
    if not await check_vault_health():
        logger.error("❌ Cannot proceed - Vault is not accessible")
        sys.exit(1)

    # Initialize basic secrets
    try:
        await init_vault_secrets()
        logger.info("✅ Basic secrets initialized")
    except Exception as exc:
        logger.error("❌ Failed to initialize basic secrets", error=str(exc))
        sys.exit(1)

    # Setup enhanced secrets
    if not await setup_enhanced_secrets():
        logger.warning("⚠️  Some enhanced secrets failed to initialize")

    # Setup database secrets with proper parsing
    if not await setup_database_secrets():
        logger.warning("⚠️  Database secrets initialization had issues")

    # Verify all secrets
    if await verify_secrets():
        logger.info("✅ All required secrets are present and accessible")
    else:
        logger.warning("⚠️  Some required secrets are missing")

    # List all secrets for debugging
    await list_all_secrets()

    # Cleanup
    await vault_client.close()

    logger.info("🎉 Vault initialization completed!")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run the async main function
    asyncio.run(main())
