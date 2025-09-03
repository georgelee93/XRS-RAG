#!/usr/bin/env python3
"""
Authenticated API Tests for RAG Chatbot
Tests all API endpoints with proper authentication
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from auth_helper import get_auth_token, get_auth_headers

class AuthenticatedAPITester:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.frontend_url = "http://localhost:3001"
        self.token = None
        self.headers = {}
        self.results = []
        
    async def setup(self):
        """Get authentication token"""
        print("🔐 Setting up authentication...")
        self.token = await get_auth_token()
        if self.token:
            self.headers = get_auth_headers(self.token)
            print("✅ Authentication setup complete")
            return True
        else:
            print("❌ Failed to get authentication token")
            return False
    
    async def test_health_endpoint(self):
        """Test health endpoint (no auth required)"""
        test_name = "Health Check"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/api/health/components") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("healthy"):
                            print(f"✅ {test_name}: OK")
                            self.results.append({"test": test_name, "status": "PASS"})
                            return True
                    print(f"❌ {test_name}: Failed (Status: {response.status})")
                    self.results.append({"test": test_name, "status": "FAIL", "error": f"Status {response.status}"})
                    return False
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
                return False
    
    async def test_documents_list(self):
        """Test documents list endpoint (auth required)"""
        test_name = "Documents List"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "documents" in data:
                            count = len(data["documents"])
                            print(f"✅ {test_name}: OK ({count} documents)")
                            self.results.append({"test": test_name, "status": "PASS", "count": count})
                            return True
                    elif response.status == 401:
                        print(f"❌ {test_name}: Authentication required")
                        self.results.append({"test": test_name, "status": "FAIL", "error": "Auth required"})
                    else:
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        self.results.append({"test": test_name, "status": "FAIL", "error": f"Status {response.status}"})
                    return False
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
                return False
    
    async def test_chat_api(self):
        """Test chat API endpoint (auth required)"""
        test_name = "Chat API"
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "message": "Hello, this is a test message. What documents are available?",
                    "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                }
                
                # Create form data
                form_data = aiohttp.FormData()
                form_data.add_field('message', payload['message'])
                form_data.add_field('session_id', payload['session_id'])
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "response" in data:
                            response_preview = data["response"][:100] if data["response"] else "Empty response"
                            print(f"✅ {test_name}: OK")
                            print(f"   Response preview: {response_preview}...")
                            self.results.append({"test": test_name, "status": "PASS"})
                            return True
                    elif response.status == 401:
                        print(f"❌ {test_name}: Authentication required")
                        self.results.append({"test": test_name, "status": "FAIL", "error": "Auth required"})
                    else:
                        error_text = await response.text()
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        print(f"   Error: {error_text[:200]}")
                        self.results.append({"test": test_name, "status": "FAIL", "error": f"Status {response.status}"})
                    return False
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
                return False
    
    async def test_sessions_list(self):
        """Test sessions list endpoint (auth required)"""
        test_name = "Sessions List"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/sessions",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "sessions" in data:
                            count = len(data["sessions"])
                            print(f"✅ {test_name}: OK ({count} sessions)")
                            self.results.append({"test": test_name, "status": "PASS", "count": count})
                            return True
                    elif response.status == 401:
                        print(f"❌ {test_name}: Authentication required")
                        self.results.append({"test": test_name, "status": "FAIL", "error": "Auth required"})
                    else:
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        self.results.append({"test": test_name, "status": "FAIL", "error": f"Status {response.status}"})
                    return False
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
                return False
    
    async def test_frontend_access(self):
        """Test frontend accessibility"""
        test_name = "Frontend Access"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.frontend_url}/chat.html") as response:
                    if response.status == 200:
                        content = await response.text()
                        if "chatForm" in content and "messagesContainer" in content:
                            print(f"✅ {test_name}: OK (chat page loaded)")
                            self.results.append({"test": test_name, "status": "PASS"})
                            return True
                        else:
                            print(f"❌ {test_name}: Page loaded but missing expected elements")
                            self.results.append({"test": test_name, "status": "FAIL", "error": "Missing elements"})
                    else:
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        self.results.append({"test": test_name, "status": "FAIL", "error": f"Status {response.status}"})
                    return False
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
                return False
    
    async def run_all_tests(self):
        """Run all authenticated API tests"""
        print("\n" + "="*60)
        print("AUTHENTICATED API TEST SUITE")
        print("="*60)
        
        # Setup authentication
        if not await self.setup():
            print("\n⚠️  Cannot proceed without authentication")
            return False
        
        print("\n📋 Running API Tests...")
        print("-"*40)
        
        # Run tests
        tests = [
            self.test_health_endpoint(),
            self.test_documents_list(),
            self.test_chat_api(),
            self.test_sessions_list(),
            self.test_frontend_access()
        ]
        
        results = await asyncio.gather(*tests)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] in ["FAIL", "ERROR"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"❌ Failed: {failed} ({failed/total*100:.1f}%)")
        
        # Save report
        report_file = f"reports/authenticated_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("reports", exist_ok=True)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{passed/total*100:.1f}%"
            },
            "results": self.results
        }
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        if failed > 0:
            print("\n⚠️  Some tests failed. Check the report for details.")
            return False
        else:
            print("\n✅ All tests passed!")
            return True

async def main():
    """Main test runner"""
    tester = AuthenticatedAPITester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())