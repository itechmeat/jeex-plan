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

from app.core.vault import vault_client, init_vault_secrets
from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger()


async def check_vault_health():
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
    except Exception as e:
        logger.error(f"❌ Failed to connect to Vault: {e}")
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
                logger.info(f"✅ Secret found: {secret_path}")
            else:
                logger.warning(f"⚠️  Secret missing: {secret_path}")
                all_present = False
        except Exception as e:
            logger.error(f"❌ Failed to read secret {secret_path}: {e}")
            all_present = False

    return all_present


async def list_all_secrets():
    """List all secrets in Vault for debugging."""
    logger.info("Listing all secrets...")

    try:
        secrets = await vault_client.list_secrets()
        if secrets:
            logger.info(f"Found {len(secrets)} secret paths:")
            for secret in secrets:
                logger.info(f"  - {secret}")
        else:
            logger.info("No secrets found")
    except Exception as e:
        logger.error(f"Failed to list secrets: {e}")


async def setup_database_secrets():
    """Setup database-specific secrets."""
    logger.info("Setting up database secrets...")

    settings = get_settings()

    # Extract database details from URL if available
    db_url = settings.DATABASE_URL
    if "postgresql://" in db_url:
        # Parse URL: postgresql://user:pass@host:port/db
        parts = db_url.replace("postgresql://", "").split("/")
        db_name = parts[-1] if len(parts) > 1 else "jeex_plan"

        host_part = parts[0].split("@")[-1] if "@" in parts[0] else "postgres:5432"
        host, port = host_part.split(":") if ":" in host_part else (host_part, "5432")

        user_pass = parts[0].split("@")[0] if "@" in parts[0] else "jeex_user:jeex_password"
        user, password = user_pass.split(":") if ":" in user_pass else (user_pass, "jeex_password")
    else:
        # Default values
        user = "jeex_user"
        password = "jeex_password"
        host = "postgres"
        port = "5432"
        db_name = "jeex_plan"

    db_secrets = {
        "username": user,
        "password": password,
        "host": host,
        "port": port,
        "database": db_name,
        "url": f"postgresql://{user}:{password}@{host}:{port}/{db_name}",
        "async_url": f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
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
    ai_secrets = {
        "openai_api_key": "sk-placeholder-openai-api-key-replace-in-production",
        "anthropic_api_key": "sk-ant-placeholder-anthropic-key-replace-in-production",
        "default_model": "gpt-4",
        "max_tokens": "4000",
        "temperature": "0.7"
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
        ("ai/openai", ai_secrets),
        ("app/config", app_secrets)
    ]

    all_success = True

    for path, secrets in secrets_to_setup:
        success = await vault_client.put_secret(path, secrets)
        if success:
            logger.info(f"✅ Enhanced secrets configured: {path}")
        else:
            logger.error(f"❌ Failed to configure secrets: {path}")
            all_success = False

    return all_success


async def main():
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
    except Exception as e:
        logger.error(f"❌ Failed to initialize basic secrets: {e}")
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