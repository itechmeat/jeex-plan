"""
Password service for password hashing and verification.
Separated from AuthService to follow Single Responsibility Principle.
"""

import secrets

from passlib.context import CryptContext
from passlib.exc import (
    InvalidHashError,
    MalformedHashError,
    PasswordValueError,
    UnknownHashError,
)


class PasswordService:
    """Service responsible only for password operations."""

    def __init__(self, schemes: list[str] | None = None) -> None:
        """Initialize password service with configurable schemes."""
        schemes = schemes or ["bcrypt"]
        self.pwd_context = CryptContext(schemes=schemes, deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against its hash."""
        if not plain_password or not hashed_password:
            return False

        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except (UnknownHashError, InvalidHashError, MalformedHashError, PasswordValueError):
            return False

    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        if not password:
            raise ValueError("Password cannot be empty")

        # Validate password strength
        self._validate_password_strength(password)

        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            raise ValueError(f"Failed to hash password: {e}") from e

    def generate_random_password(self, length: int = 12) -> str:
        """Generate a cryptographically secure random password."""
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")

        # Use secure random generator
        alphabet = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        )
        password = "".join(secrets.choice(alphabet) for _ in range(length))

        # Ensure password meets complexity requirements
        if not self._meets_complexity_requirements(password):
            return self.generate_random_password(length)

        return password

    def generate_password_and_hash(self, length: int = 12) -> tuple[str, str]:
        """Generate random password and return both plain and hashed versions."""
        plain_password = self.generate_random_password(length)
        hashed_password = self.get_password_hash(plain_password)
        return plain_password, hashed_password

    def _validate_password_strength(self, password: str) -> None:
        """Validate password meets minimum security requirements."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one digit
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must contain at least one digit")

        # Check for at least one letter
        if not any(char.isalpha() for char in password):
            raise ValueError("Password must contain at least one letter")

        # Check for common passwords (basic check)
        common_passwords = {
            "password",
            "123456",
            "password123",
            "admin",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "dragon",
            "password1",
        }
        if password.lower() in common_passwords:
            raise ValueError("Password is too common")

    def _meets_complexity_requirements(self, password: str) -> bool:
        """Check if password meets complexity requirements."""
        try:
            self._validate_password_strength(password)
            return True
        except ValueError:
            return False

    def is_hash_valid(self, hashed_password: str) -> bool:
        """Check if a hash is valid and current."""
        if not hashed_password:
            return False

        try:
            # Check if the hash needs to be updated (deprecated scheme)
            return not self.pwd_context.needs_update(hashed_password)
        except (UnknownHashError, InvalidHashError, MalformedHashError, PasswordValueError):
            return False

    def update_hash_if_needed(
        self, plain_password: str, current_hash: str
    ) -> str | None:
        """Update hash if using deprecated scheme, return new hash if updated."""
        if not self.is_hash_valid(current_hash):
            return self.get_password_hash(plain_password)

        if self.pwd_context.needs_update(current_hash):
            return self.get_password_hash(plain_password)

        return None
