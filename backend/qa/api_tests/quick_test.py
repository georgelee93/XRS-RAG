#!/usr/bin/env python3
"""
Quick test to verify basic functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_backend_health():
    """Test backend health endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8080/api/health") as response:
                data = await response.json()
                if response.status == 200 and data.get("status") == "healthy":
                    print("✅ Backend Health: OK")
                    return True
                else:
                    print(f"❌ Backend Health: Failed (Status: {response.status})")
                    return False
        except Exception as e:
            print(f"❌ Backend Health: Error - {e}")
            return False

async def test_chat_api():
    """Test chat API endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "message": "Hello, this is a test message",
                "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            headers = {"Content-Type": "application/json"}
            
            async with session.post(
                "http://localhost:8080/api/chat",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        print("✅ Chat API: OK")
                        print(f"   Response preview: {data.get('response', '')[:100]}...")
                        return True
                    else:
                        print(f"❌ Chat API: Response not successful - {data.get('error')}")
                        return False
                else:
                    print(f"❌ Chat API: Failed (Status: {response.status})")
                    text = await response.text()
                    print(f"   Error: {text[:200]}")
                    return False
        except Exception as e:
            print(f"❌ Chat API: Error - {e}")
            return False

async def test_documents_list():
    """Test documents list endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8080/api/documents") as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data.get("documents"), list):
                        count = len(data["documents"])
                        print(f"✅ Documents List: OK ({count} documents)")
                        if count > 0:
                            print(f"   First document: {data['documents'][0].get('name', 'N/A')}")
                        return True
                    else:
                        print("❌ Documents List: Invalid response format")
                        return False
                else:
                    print(f"❌ Documents List: Failed (Status: {response.status})")
                    return False
        except Exception as e:
            print(f"❌ Documents List: Error - {e}")
            return False

async def test_frontend_access():
    """Test frontend accessibility"""
    async with aiohttp.ClientSession() as session:
        try:
            # Test chat page specifically
            async with session.get("http://localhost:3001/chat.html") as response:
                if response.status == 200:
                    content = await response.text()
                    if "chatForm" in content and "messagesContainer" in content:
                        print("✅ Frontend Access: OK (chat page loaded)")
                        return True
                    else:
                        print("❌ Frontend Access: Page loaded but missing expected elements")
                        return False
                else:
                    print(f"❌ Frontend Access: Failed (Status: {response.status})")
                    return False
        except Exception as e:
            print(f"❌ Frontend Access: Error - {e}")
            print("   Make sure frontend is running on port 3001")
            return False

async def main():
    """Run all quick tests"""
    print("=" * 60)
    print("RAG Chatbot Quick Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    # Test backend
    print("Testing Backend...")
    results.append(await test_backend_health())
    results.append(await test_documents_list())
    
    # Test chat (might take longer)
    print("\nTesting Chat API (this may take a few seconds)...")
    results.append(await test_chat_api())
    
    # Test frontend
    print("\nTesting Frontend...")
    results.append(await test_frontend_access())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({passed/total*100:.0f}%)")
    print(f"Failed: {failed} ({failed/total*100:.0f}%)")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)