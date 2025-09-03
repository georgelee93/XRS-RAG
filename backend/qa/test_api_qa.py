#!/usr/bin/env python3
"""
API Endpoints QA Tests
Tests all REST API endpoints for proper functionality
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth_helper import get_auth_token

class ApiQA:
    """Comprehensive API endpoint tests"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.auth_token = None
        self.session_id = None
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def log_result(self, test_name: str, passed: bool, error: str = None):
        """Log test result"""
        if passed:
            print(f"✅ {test_name}")
            self.passed += 1
        else:
            print(f"❌ {test_name}: {error}")
            self.failed += 1
            self.errors.append(f"{test_name}: {error}")
    
    async def test_health_check(self) -> bool:
        """Test health check endpoints"""
        print("\n🔍 Testing health check endpoints...")
        
        try:
            import aiohttp
            
            # Test /api/health
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("GET /api/health", True)
                        if 'status' in data:
                            self.log_result("Health status field", True)
                    else:
                        self.log_result("GET /api/health", False, f"Status {response.status}")
                        
                # Test /api/health/components
                async with session.get(f"{self.base_url}/api/health/components") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("GET /api/health/components", True)
                        
                        # Check component statuses
                        expected_components = ['database', 'openai', 'assistant']
                        for component in expected_components:
                            if component in data:
                                self.log_result(f"Component {component} status", True)
                            else:
                                self.log_result(f"Component {component} status", False, "Missing")
                    else:
                        self.log_result("GET /api/health/components", False, f"Status {response.status}")
                        
            return True
            
        except Exception as e:
            self.log_result("Health check endpoints", False, str(e))
            return False
    
    async def test_auth_endpoints(self) -> bool:
        """Test authentication endpoints"""
        print("\n🔍 Testing authentication endpoints...")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Test login
                login_data = {
                    "email": "test.user@gmail.com",
                    "password": "Test123456!"
                }
                
                async with session.post(
                    f"{self.base_url}/api/auth/login",
                    json=login_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("POST /api/auth/login", True)
                        
                        if 'access_token' in data:
                            self.auth_token = data['access_token']
                            self.log_result("Auth token received", True)
                        else:
                            self.log_result("Auth token received", False, "No token in response")
                    else:
                        error_text = await response.text()
                        self.log_result("POST /api/auth/login", False, f"Status {response.status}: {error_text}")
                        
                        # Try to get token via helper
                        self.auth_token = await get_auth_token()
                        if self.auth_token:
                            self.log_result("Auth token via helper", True)
                        
            return bool(self.auth_token)
            
        except Exception as e:
            self.log_result("Auth endpoints", False, str(e))
            # Try to get token via helper as fallback
            try:
                self.auth_token = await get_auth_token()
                return bool(self.auth_token)
            except:
                return False
    
    async def test_document_endpoints(self) -> bool:
        """Test document management endpoints"""
        print("\n🔍 Testing document endpoints...")
        
        try:
            import aiohttp
            
            if not self.auth_token:
                self.auth_token = await get_auth_token()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with aiohttp.ClientSession() as session:
                # Test GET /api/documents
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("GET /api/documents", True)
                        
                        if 'documents' in data:
                            self.log_result(f"Documents list ({len(data['documents'])} docs)", True)
                        else:
                            self.log_result("Documents list", False, "No documents field")
                    else:
                        error_text = await response.text()
                        self.log_result("GET /api/documents", False, f"Status {response.status}: {error_text}")
                        
            return True
            
        except Exception as e:
            self.log_result("Document endpoints", False, str(e))
            return False
    
    async def test_session_endpoints(self) -> bool:
        """Test session management endpoints"""
        print("\n🔍 Testing session endpoints...")
        
        try:
            import aiohttp
            
            if not self.auth_token:
                self.auth_token = await get_auth_token()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with aiohttp.ClientSession() as session:
                # Test GET /api/sessions
                async with session.get(
                    f"{self.base_url}/api/sessions",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("GET /api/sessions", True)
                        
                        if 'sessions' in data:
                            self.log_result(f"Sessions list ({len(data['sessions'])} sessions)", True)
                            
                            # Store a session ID if available
                            if data['sessions'] and len(data['sessions']) > 0:
                                self.session_id = data['sessions'][0].get('session_id')
                        else:
                            self.log_result("Sessions list", False, "No sessions field")
                    else:
                        error_text = await response.text()
                        self.log_result("GET /api/sessions", False, f"Status {response.status}: {error_text}")
                        
                # If we have a session ID, test getting specific session
                if self.session_id:
                    async with session.get(
                        f"{self.base_url}/api/sessions/{self.session_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.log_result(f"GET /api/sessions/{self.session_id}", True)
                        else:
                            self.log_result(f"GET /api/sessions/{self.session_id}", False, f"Status {response.status}")
                            
            return True
            
        except Exception as e:
            self.log_result("Session endpoints", False, str(e))
            return False
    
    async def test_chat_endpoint(self) -> bool:
        """Test the chat endpoint thoroughly"""
        print("\n🔍 Testing chat endpoint...")
        
        try:
            import aiohttp
            
            if not self.auth_token:
                self.auth_token = await get_auth_token()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with aiohttp.ClientSession() as session:
                # Test 1: Simple message without session
                data = aiohttp.FormData()
                data.add_field('message', 'Hello, this is a test')
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    headers=headers,
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.log_result("POST /api/chat (new session)", True)
                        
                        # Check response structure
                        expected_fields = ['response', 'session_id']
                        for field in expected_fields:
                            if field in result:
                                self.log_result(f"Chat response field: {field}", True)
                            else:
                                self.log_result(f"Chat response field: {field}", False, "Missing")
                                
                        # Store session ID for next test
                        if 'session_id' in result:
                            self.session_id = result['session_id']
                    else:
                        error_text = await response.text()
                        self.log_result("POST /api/chat (new session)", False, f"Status {response.status}: {error_text}")
                        return False
                        
                # Test 2: Message with existing session
                if self.session_id:
                    data = aiohttp.FormData()
                    data.add_field('message', 'This is a follow-up message')
                    data.add_field('session_id', self.session_id)
                    
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        headers=headers,
                        data=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            self.log_result("POST /api/chat (existing session)", True)
                        else:
                            error_text = await response.text()
                            self.log_result("POST /api/chat (existing session)", False, f"Status {response.status}: {error_text}")
                            
            return True
            
        except Exception as e:
            self.log_result("Chat endpoint", False, str(e))
            return False
    
    async def test_usage_endpoints(self) -> bool:
        """Test usage tracking endpoints"""
        print("\n🔍 Testing usage endpoints...")
        
        try:
            import aiohttp
            
            if not self.auth_token:
                self.auth_token = await get_auth_token()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with aiohttp.ClientSession() as session:
                # Test GET /api/usage/summary
                async with session.get(
                    f"{self.base_url}/api/usage/summary",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.log_result("GET /api/usage/summary", True)
                        
                        expected_fields = ['total_messages', 'total_tokens', 'total_cost']
                        for field in expected_fields:
                            if field in data:
                                self.log_result(f"Usage field: {field}", True)
                            else:
                                self.log_result(f"Usage field: {field}", False, "Missing")
                    else:
                        error_text = await response.text()
                        self.log_result("GET /api/usage/summary", False, f"Status {response.status}: {error_text}")
                        
            return True
            
        except Exception as e:
            self.log_result("Usage endpoints", False, str(e))
            return False
    
    async def run_all_tests_async(self) -> bool:
        """Run all async tests"""
        print("\n" + "="*50)
        print("API ENDPOINTS QA TESTS")
        print("="*50)
        
        all_passed = True
        
        # Test 1: Health checks (no auth required)
        if not await self.test_health_check():
            all_passed = False
            
        # Test 2: Authentication
        if not await self.test_auth_endpoints():
            all_passed = False
            print("⚠️  Auth failed, some tests may fail")
            
        # Test 3: Documents
        if not await self.test_document_endpoints():
            all_passed = False
            
        # Test 4: Sessions
        if not await self.test_session_endpoints():
            all_passed = False
            
        # Test 5: Chat (the critical one!)
        if not await self.test_chat_endpoint():
            all_passed = False
            
        # Test 6: Usage
        if not await self.test_usage_endpoints():
            all_passed = False
        
        # Print summary
        print("\n" + "="*50)
        print("API QA SUMMARY")
        print("="*50)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        
        if self.errors:
            print("\n❌ Errors:")
            for error in self.errors:
                print(f"   - {error}")
        
        return all_passed
    
    def run_all_tests(self) -> bool:
        """Synchronous wrapper for async tests"""
        return asyncio.run(self.run_all_tests_async())

if __name__ == "__main__":
    qa = ApiQA()
    success = qa.run_all_tests()
    sys.exit(0 if success else 1)