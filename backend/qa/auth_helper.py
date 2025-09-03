#!/usr/bin/env python3
"""
Authentication helper for QA tests
"""

import asyncio
import aiohttp
import json
from typing import Optional, Dict

# Test credentials - Updated with new test user
TEST_EMAIL = "test.user@gmail.com"
TEST_PASSWORD = "Test123456!"

async def get_auth_token() -> Optional[str]:
    """
    Get authentication token from Supabase
    Returns the access token or None if authentication fails
    """
    # Supabase URL and anon key - Updated with new Supabase project
    supabase_url = "https://utowhepyocvkjqtxdsnj.supabase.co"
    supabase_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0b3doZXB5b2N2a2pxdHhkc25qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY3ODQyMjAsImV4cCI6MjA3MjM2MDIyMH0.K6SXf_2Wn3yPD813HrX2h2py50G_fW5Put3s3ymOC1M"
    
    async with aiohttp.ClientSession() as session:
        try:
            # Sign in endpoint
            url = f"{supabase_url}/auth/v1/token?grant_type=password"
            
            headers = {
                "apikey": supabase_anon_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    access_token = data.get("access_token")
                    if access_token:
                        print(f"✅ Authentication successful for {TEST_EMAIL}")
                        return access_token
                    else:
                        print("❌ Authentication response missing access_token")
                        return None
                else:
                    error_text = await response.text()
                    print(f"❌ Authentication failed (Status: {response.status})")
                    print(f"   Error: {error_text[:200]}")
                    return None
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return None

def get_auth_headers(token: str = None) -> Dict[str, str]:
    """
    Get authentication headers for API requests
    """
    if not token:
        return {}
    
    return {
        "Authorization": f"Bearer {token}"
    }

async def test_auth():
    """
    Test authentication
    """
    token = await get_auth_token()
    if token:
        print(f"Token (first 20 chars): {token[:20]}...")
        return token
    else:
        print("Failed to get authentication token")
        return None

if __name__ == "__main__":
    # Test the authentication
    asyncio.run(test_auth())