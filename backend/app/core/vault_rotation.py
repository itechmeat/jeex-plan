"""
Vault secret rotation policies and management.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .vault import vault_client

logger = logging.getLogger(__name__)


@dataclass
class RotationPolicy:
    """Secret rotation policy configuration."""
    path: str
    rotation_interval_days: int
    auto_rotate: bool = True
    notification_days_before: int = 7
    last_rotated: Optional[datetime] = None


class SecretRotationManager:
    """Manages secret rotation policies and schedules."""

    def __init__(self):
        self.policies: Dict[str, RotationPolicy] = {}
        self._setup_default_policies()

    def _setup_default_policies(self):
        """Setup default rotation policies for development."""
        self.policies = {
            "auth/jwt": RotationPolicy(
                path="auth/jwt",
                rotation_interval_days=90,  # 3 months
                auto_rotate=True,
                notification_days_before=7
            ),
            "database/postgres": RotationPolicy(
                path="database/postgres",
                rotation_interval_days=180,  # 6 months
                auto_rotate=False,  # Manual rotation for DB
                notification_days_before=14
            ),
            "ai/openai": RotationPolicy(
                path="ai/openai",
                rotation_interval_days=365,  # 1 year
                auto_rotate=False,  # Manual rotation for external APIs
                notification_days_before=30
            )
        }

    async def add_policy(self, policy: RotationPolicy):
        """Add a new rotation policy."""
        self.policies[policy.path] = policy
        await self._store_policy(policy)
        logger.info(f"Added rotation policy for {policy.path}")

    async def _store_policy(self, policy: RotationPolicy):
        """Store rotation policy metadata in Vault."""
        metadata = {
            "rotation_interval_days": policy.rotation_interval_days,
            "auto_rotate": policy.auto_rotate,
            "notification_days_before": policy.notification_days_before,
            "last_rotated": policy.last_rotated.isoformat() if policy.last_rotated else None,
            "policy_created": datetime.utcnow().isoformat()
        }

        await vault_client.put_secret(
            f"policies/{policy.path.replace('/', '_')}",
            metadata,
            mount_point="secret"
        )

    async def get_policy(self, path: str) -> Optional[RotationPolicy]:
        """Get rotation policy for a secret path."""
        return self.policies.get(path)

    async def check_rotation_needed(self, path: str) -> tuple[bool, Optional[str]]:
        """Check if a secret needs rotation."""
        policy = await self.get_policy(path)
        if not policy:
            return False, "No rotation policy found"

        if not policy.last_rotated:
            return True, "Secret has never been rotated"

        days_since_rotation = (datetime.utcnow() - policy.last_rotated).days
        days_until_rotation = policy.rotation_interval_days - days_since_rotation

        if days_until_rotation <= 0:
            return True, f"Secret is {abs(days_until_rotation)} days overdue for rotation"
        elif days_until_rotation <= policy.notification_days_before:
            return False, f"Secret will need rotation in {days_until_rotation} days"

        return False, f"Secret rotation not needed for {days_until_rotation} days"

    async def rotate_jwt_secret(self) -> bool:
        """Rotate JWT secret key."""
        try:
            import secrets
            import string

            # Generate new secret key
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            new_secret = ''.join(secrets.choice(alphabet) for _ in range(64))

            # Get current JWT config
            current_config = await vault_client.get_secret("auth/jwt")
            if not current_config:
                logger.error("Current JWT config not found")
                return False

            # Update with new secret
            new_config = current_config.copy()
            new_config["secret_key"] = new_secret
            new_config["rotated_at"] = datetime.utcnow().isoformat()

            # Store new config
            success = await vault_client.put_secret("auth/jwt", new_config)
            if success:
                # Update policy last_rotated
                policy = self.policies.get("auth/jwt")
                if policy:
                    policy.last_rotated = datetime.utcnow()
                    await self._store_policy(policy)

                logger.info("JWT secret rotated successfully")
                return True
            else:
                logger.error("Failed to store new JWT secret")
                return False

        except Exception as e:
            logger.error(f"Error rotating JWT secret: {e}")
            return False

    async def rotate_database_password(self) -> bool:
        """Rotate database password (simulation for dev)."""
        try:
            import secrets
            import string

            # Generate new password
            alphabet = string.ascii_letters + string.digits
            new_password = ''.join(secrets.choice(alphabet) for _ in range(32))

            # Get current DB config
            current_config = await vault_client.get_secret("database/postgres")
            if not current_config:
                logger.error("Current database config not found")
                return False

            # In production, you would:
            # 1. Create new database user with new password
            # 2. Update application to use new credentials
            # 3. Remove old database user
            # For dev, we just update the stored config

            new_config = current_config.copy()
            new_config["password"] = new_password
            new_config["rotated_at"] = datetime.utcnow().isoformat()
            new_config["previous_password"] = current_config.get("password")  # Keep for rollback

            # Store new config
            success = await vault_client.put_secret("database/postgres", new_config)
            if success:
                # Update policy last_rotated
                policy = self.policies.get("database/postgres")
                if policy:
                    policy.last_rotated = datetime.utcnow()
                    await self._store_policy(policy)

                logger.warning("Database password rotation simulated (dev mode)")
                return True
            else:
                logger.error("Failed to store new database password")
                return False

        except Exception as e:
            logger.error(f"Error rotating database password: {e}")
            return False

    async def check_all_secrets(self) -> Dict[str, tuple[bool, str]]:
        """Check rotation status for all managed secrets."""
        results = {}

        for path in self.policies.keys():
            needs_rotation, reason = await self.check_rotation_needed(path)
            results[path] = (needs_rotation, reason)

        return results

    async def auto_rotate_eligible_secrets(self) -> Dict[str, bool]:
        """Automatically rotate eligible secrets."""
        results = {}

        for path, policy in self.policies.items():
            if not policy.auto_rotate:
                continue

            needs_rotation, reason = await self.check_rotation_needed(path)
            if needs_rotation:
                logger.info(f"Auto-rotating secret: {path} - {reason}")

                if path == "auth/jwt":
                    success = await self.rotate_jwt_secret()
                    results[path] = success
                else:
                    logger.warning(f"No auto-rotation handler for {path}")
                    results[path] = False

        return results

    async def get_rotation_report(self) -> Dict[str, dict]:
        """Generate rotation status report."""
        report = {}

        for path, policy in self.policies.items():
            needs_rotation, reason = await self.check_rotation_needed(path)

            report[path] = {
                "policy": {
                    "rotation_interval_days": policy.rotation_interval_days,
                    "auto_rotate": policy.auto_rotate,
                    "notification_days_before": policy.notification_days_before
                },
                "status": {
                    "needs_rotation": needs_rotation,
                    "reason": reason,
                    "last_rotated": policy.last_rotated.isoformat() if policy.last_rotated else None
                }
            }

        return report


# Global rotation manager instance
rotation_manager = SecretRotationManager()


async def init_rotation_policies():
    """Initialize rotation policies."""
    logger.info("Initializing secret rotation policies...")

    # Store all policies in Vault
    for policy in rotation_manager.policies.values():
        await rotation_manager._store_policy(policy)

    logger.info(f"Initialized {len(rotation_manager.policies)} rotation policies")


async def run_rotation_check():
    """Run periodic rotation check (called by scheduler)."""
    logger.info("Running scheduled rotation check...")

    # Check all secrets
    status_report = await rotation_manager.check_all_secrets()

    # Log warnings for secrets needing attention
    for path, (needs_rotation, reason) in status_report.items():
        if needs_rotation:
            logger.warning(f"Secret rotation needed: {path} - {reason}")
        elif "will need rotation" in reason:
            logger.info(f"Secret rotation upcoming: {path} - {reason}")

    # Auto-rotate eligible secrets
    auto_rotation_results = await rotation_manager.auto_rotate_eligible_secrets()

    if auto_rotation_results:
        for path, success in auto_rotation_results.items():
            if success:
                logger.info(f"Successfully auto-rotated: {path}")
            else:
                logger.error(f"Failed to auto-rotate: {path}")

    logger.info("Scheduled rotation check completed")