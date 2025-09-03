#!/usr/bin/env python3
"""
Chat Functionality QA Tests
Tests the chat API, message processing, and assistant integration
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.retrieval_client import RetrievalAPIClient
from core.services.chat_service import get_chat_service
from core.session_manager import get_session_manager
from core.config import get_settings
from auth_helper import get_auth_token

class ChatQA:
    """Comprehensive chat functionality tests"""
    
    def __init__(self):
        self.settings = get_settings()
        self.auth_token = None
        self.session_id = None
        self.retrieval_client = None
        self.chat_service = None
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
    
    async def test_retrieval_client_methods(self) -> bool:
        """Test that RetrievalAPIClient has all required methods"""
        print("\n🔍 Testing RetrievalAPIClient methods...")
        
        try:
            # Initialize retrieval client
            self.retrieval_client = RetrievalAPIClient()
            
            # Check critical methods
            required_methods = [
                'process_with_thread',  # The method that was missing!
                'create_thread',
                'add_message',
                'run_assistant',
                'wait_for_run_completion',
                'get_messages',
                'search'
            ]
            
            for method_name in required_methods:
                if hasattr(self.retrieval_client, method_name):
                    self.log_result(f"Method exists: {method_name}", True)
                else:
                    self.log_result(f"Method exists: {method_name}", False, "Method not found")
                    return False
                    
            # Test that methods are callable
            for method_name in required_methods:
                method = getattr(self.retrieval_client, method_name)
                if callable(method):
                    self.log_result(f"Method callable: {method_name}", True)
                else:
                    self.log_result(f"Method callable: {method_name}", False, "Not callable")
                    return False
                    
            return True
            
        except Exception as e:
            self.log_result("RetrievalAPIClient initialization", False, str(e))
            return False
    
    async def test_chat_service_initialization(self) -> bool:
        """Test chat service initialization"""
        print("\n🔍 Testing Chat Service initialization...")
        
        try:
            # Get chat service
            self.chat_service = get_chat_service()
            self.log_result("Chat service initialization", True)
            
            # Check if it has the right strategy
            if hasattr(self.chat_service, 'strategy'):
                strategy_name = type(self.chat_service.strategy).__name__
                self.log_result(f"Chat strategy: {strategy_name}", True)
            else:
                self.log_result("Chat strategy check", False, "No strategy attribute")
                return False
                
            return True
            
        except Exception as e:
            self.log_result("Chat service initialization", False, str(e))
            return False
    
    async def test_thread_creation(self) -> bool:
        """Test thread creation in assistant"""
        print("\n🔍 Testing thread creation...")
        
        try:
            if not self.retrieval_client:
                self.retrieval_client = RetrievalAPIClient()
                
            # Create a thread
            thread = await self.retrieval_client.create_thread()
            
            if thread and hasattr(thread, 'id'):
                self.log_result(f"Thread created: {thread.id}", True)
                return True
            else:
                self.log_result("Thread creation", False, "No thread ID returned")
                return False
                
        except Exception as e:
            self.log_result("Thread creation", False, str(e))
            return False
    
    async def test_message_processing(self) -> bool:
        """Test message processing through chat service"""
        print("\n🔍 Testing message processing...")
        
        try:
            if not self.chat_service:
                self.chat_service = get_chat_service()
            
            # Process a test message
            result = await self.chat_service.process_message(
                message="Hello, this is a test message",
                user_id="test_user"
            )
            
            # Check result structure
            if result and isinstance(result, dict):
                required_fields = ['response', 'session_id']
                for field in required_fields:
                    if field in result:
                        self.log_result(f"Response field: {field}", True)
                    else:
                        self.log_result(f"Response field: {field}", False, "Missing field")
                        
                # Store session ID for later tests
                if 'session_id' in result:
                    self.session_id = result['session_id']
                    
                return 'response' in result
            else:
                self.log_result("Message processing", False, "Invalid response format")
                return False
                
        except Exception as e:
            self.log_result("Message processing", False, str(e))
            return False
    
    async def test_process_with_thread_method(self) -> bool:
        """Specifically test the process_with_thread method"""
        print("\n🔍 Testing process_with_thread method...")
        
        try:
            if not self.retrieval_client:
                self.retrieval_client = RetrievalAPIClient()
            
            # Test the specific method that was missing
            result = await self.retrieval_client.process_with_thread(
                message="Test message for process_with_thread",
                thread_id=None  # Let it create a new thread
            )
            
            # Check result structure
            if result and isinstance(result, dict):
                expected_keys = ['response', 'thread_id', 'usage', 'metadata']
                for key in expected_keys:
                    if key in result:
                        self.log_result(f"process_with_thread returns: {key}", True)
                    else:
                        self.log_result(f"process_with_thread returns: {key}", False, "Missing key")
                        
                return 'response' in result
            else:
                self.log_result("process_with_thread", False, "Invalid response")
                return False
                
        except Exception as e:
            self.log_result("process_with_thread", False, str(e))
            return False
    
    async def test_session_management(self) -> bool:
        """Test session management"""
        print("\n🔍 Testing session management...")
        
        try:
            session_manager = get_session_manager()
            
            # Create a session
            session = session_manager.create_session(
                user_id="test_user",
                title="Test Session"
            )
            
            if session and 'session_id' in session:
                self.log_result(f"Session created: {session['session_id']}", True)
                
                # Add a message
                session_manager.add_message(
                    session_id=session['session_id'],
                    role="user",
                    content="Test message"
                )
                self.log_result("Message added to session", True)
                
                # Retrieve messages
                messages = session_manager.get_messages(session['session_id'])
                if messages and len(messages) > 0:
                    self.log_result(f"Messages retrieved: {len(messages)}", True)
                else:
                    self.log_result("Message retrieval", False, "No messages found")
                    
                return True
            else:
                self.log_result("Session creation", False, "No session ID")
                return False
                
        except Exception as e:
            self.log_result("Session management", False, str(e))
            return False
    
    async def test_api_endpoint(self) -> bool:
        """Test the /api/chat endpoint directly"""
        print("\n🔍 Testing /api/chat endpoint...")
        
        try:
            import aiohttp
            
            # Get auth token
            if not self.auth_token:
                self.auth_token = await get_auth_token()
            
            # Prepare request
            url = f"http://localhost:{self.settings.port}/api/chat"
            headers = {
                "Authorization": f"Bearer {self.auth_token}"
            }
            
            # Create form data (the endpoint expects FormData)
            data = aiohttp.FormData()
            data.add_field('message', 'Test message via API')
            if self.session_id:
                data.add_field('session_id', self.session_id)
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.log_result("API /api/chat endpoint", True)
                        
                        # Check response structure
                        if 'response' in result:
                            self.log_result("API returns response field", True)
                        if 'session_id' in result:
                            self.log_result("API returns session_id field", True)
                            
                        return True
                    else:
                        error_text = await response.text()
                        self.log_result("API /api/chat endpoint", False, f"Status {response.status}: {error_text}")
                        return False
                        
        except Exception as e:
            self.log_result("API /api/chat endpoint", False, str(e))
            return False
    
    async def run_all_tests_async(self) -> bool:
        """Run all async tests"""
        print("\n" + "="*50)
        print("CHAT FUNCTIONALITY QA TESTS")
        print("="*50)
        
        all_passed = True
        
        # Test 1: Check RetrievalAPIClient methods
        if not await self.test_retrieval_client_methods():
            all_passed = False
            
        # Test 2: Chat service initialization
        if not await self.test_chat_service_initialization():
            all_passed = False
            
        # Test 3: Thread creation
        if not await self.test_thread_creation():
            all_passed = False
            
        # Test 4: The specific method that was missing
        if not await self.test_process_with_thread_method():
            all_passed = False
            
        # Test 5: Message processing
        if not await self.test_message_processing():
            all_passed = False
            
        # Test 6: Session management
        if not await self.test_session_management():
            all_passed = False
            
        # Test 7: API endpoint
        if not await self.test_api_endpoint():
            all_passed = False
        
        # Print summary
        print("\n" + "="*50)
        print("CHAT QA SUMMARY")
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
    qa = ChatQA()
    success = qa.run_all_tests()
    sys.exit(0 if success else 1)