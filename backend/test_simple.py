#!/usr/bin/env python3
"""
Simple test script to verify auth endpoints work
"""
import asyncio
import httpx

async def test_auth_endpoints():
    """Test authentication endpoints"""
    base_url = "http://172.20.0.1:5210"  # Docker gateway IP

    async with httpx.AsyncClient() as client:
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
    asyncio.run(test_auth_endpoints())