"""
Authentication API schemas.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=2, max_length=100, description="User full name")


class UserCreate(UserBase):
    """User registration schema"""
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "password": "securepassword123",
                "confirm_password": "securepassword123"
            }
        }


class UserResponse(UserBase):
    """User response schema"""
    id: str = Field(..., description="Unique user identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    is_active: bool = Field(default=True, description="Whether the user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")

    class Config:
        schema_extra = {
            "example": {
                "id": "user_123",
                "email": "user@example.com",
                "name": "John Doe",
                "tenant_id": "tenant_123",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "last_login_at": "2024-01-01T12:00:00Z"
            }
        }


class Token(BaseModel):
    """JWT token response schema"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class TokenData(BaseModel):
    """Token payload data schema"""
    sub: str = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    tenant_id: str = Field(..., description="Tenant identifier")
    name: str = Field(..., description="User name")
    exp: int = Field(..., description="Token expiration timestamp")


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password")

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "userpassword"
            }
        }


class LoginResponse(BaseModel):
    """Login response with user and token information"""
    user: UserResponse = Field(..., description="User information")
    token: Token = Field(..., description="Authentication tokens")

    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "id": "user_123",
                    "email": "user@example.com",
                    "name": "John Doe",
                    "tenant_id": "tenant_123",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_login_at": "2024-01-01T12:00:00Z"
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LogoutResponse(BaseModel):
    """Logout response schema"""
    message: str = Field(default="Successfully logged out", description="Logout message")

    class Config:
        schema_extra = {
            "example": {
                "message": "Successfully logged out"
            }
        }