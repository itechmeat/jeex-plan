#!/usr/bin/env python3
"""
Simple test script to verify auth endpoints work
"""
import asyncio
import os

import httpx


async def probe_auth_endpoints() -> None:
    """Test authentication endpoints"""
    base_url = os.getenv("JEEX_API_BASE_URL", "http://localhost:8000")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test providers endpoint (GET)
        print("Testing /auth/providers...")
        try:
            response = await client.get(f"{base_url}/auth/providers")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

        # Test register endpoint (POST)
        print("\nTesting /auth/register...")
        try:
            data = {
                "email": "test@example.com",
                "full_name": "Test User",
                "password": "testpass123",
                "confirm_password": "testpass123"
            }
            response = await client.post(
                f"{base_url}/auth/register",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(probe_auth_endpoints())
