"""
QA Test Suite for Chat History Functionality
Tests session creation, retrieval, and user association
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.session_manager import get_session_manager
from core.supabase_client import get_supabase_manager

class ChatHistoryQA:
    """QA tests for chat history functionality"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        self.supabase = get_supabase_manager()
        self.base_url = "http://localhost:8080"
        self.test_user_email = "test11@ca1996.co.kr"
        self.test_password = "Qq123456"
        self.auth_token = None
        self.test_results = []
        self.test_session_ids = []  # Track sessions created during testing
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # Print result
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details:
            print(f"  Details: {details}")
    
    def get_auth_token(self) -> Optional[str]:
        """Get authentication token for API calls"""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY")
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Sign in with test user
            auth_response = supabase.auth.sign_in_with_password({
                "email": self.test_user_email,
                "password": self.test_password
            })
            
            if auth_response.session:
                self.auth_token = auth_response.session.access_token
                return self.auth_token
            else:
                raise Exception("Failed to authenticate")
                
        except Exception as e:
            self.log_result("Authentication", False, str(e))
            return None
    
    def test_session_creation_with_user(self):
        """Test that new sessions are created with proper user_id"""
        try:
            # Create a new session
            new_session = self.session_manager.create_session(
                user_id=self.test_user_email,
                thread_id=None,
                title=f"QA Test Session {datetime.now().strftime('%H:%M:%S')}"
            )
            
            self.test_session_ids.append(new_session['session_id'])
            
            # Verify session has user_id
            if new_session.get('user_id') == self.test_user_email:
                self.log_result(
                    "Session Creation with User ID", 
                    True, 
                    f"Session {new_session['session_id'][:8]}... created with correct user_id"
                )
            else:
                self.log_result(
                    "Session Creation with User ID", 
                    False, 
                    f"user_id mismatch: expected {self.test_user_email}, got {new_session.get('user_id')}"
                )
                
        except Exception as e:
            self.log_result("Session Creation with User ID", False, str(e))
    
    def test_session_retrieval_by_user(self):
        """Test that sessions can be retrieved by user_id"""
        try:
            # Get sessions for test user
            sessions = self.session_manager.list_sessions(
                user_id=self.test_user_email,
                limit=10,
                offset=0
            )
            
            if sessions and len(sessions) > 0:
                # Verify all returned sessions belong to the user
                all_correct_user = all(
                    s.get('user_id') == self.test_user_email or s.get('user_id') == '7b0e5fb7-e716-4707-b1bc-849fdda4485e'
                    for s in sessions
                )
                
                self.log_result(
                    "Session Retrieval by User", 
                    all_correct_user, 
                    f"Found {len(sessions)} sessions for user"
                )
            else:
                self.log_result(
                    "Session Retrieval by User", 
                    False, 
                    "No sessions found for user"
                )
                
        except Exception as e:
            self.log_result("Session Retrieval by User", False, str(e))
    
    def test_message_addition_to_session(self):
        """Test adding messages to a session"""
        try:
            # Create a test session first
            test_session = self.session_manager.create_session(
                user_id=self.test_user_email,
                title="QA Message Test Session"
            )
            self.test_session_ids.append(test_session['session_id'])
            
            # Add test messages
            msg1 = self.session_manager.add_message(
                session_id=test_session['session_id'],
                role="user",
                content="QA test user message",
                metadata={"test": True}
            )
            
            msg2 = self.session_manager.add_message(
                session_id=test_session['session_id'],
                role="assistant",
                content="QA test assistant response",
                metadata={"test": True}
            )
            
            # Retrieve messages
            messages = self.session_manager.get_messages(
                test_session['session_id'], 
                limit=10
            )
            
            if len(messages) >= 2:
                self.log_result(
                    "Message Addition to Session", 
                    True, 
                    f"Successfully added {len(messages)} messages"
                )
            else:
                self.log_result(
                    "Message Addition to Session", 
                    False, 
                    f"Expected at least 2 messages, got {len(messages)}"
                )
                
        except Exception as e:
            self.log_result("Message Addition to Session", False, str(e))
    
    def test_api_session_list_endpoint(self):
        """Test the /api/sessions endpoint"""
        try:
            if not self.auth_token:
                self.get_auth_token()
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(
                f"{self.base_url}/api/sessions",
                headers=headers,
                params={"limit": 20, "offset": 0}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                has_required_fields = all(
                    key in data for key in ['success', 'sessions', 'total', 'user_id']
                )
                
                if has_required_fields and data['success']:
                    session_count = len(data.get('sessions', []))
                    self.log_result(
                        "API Session List Endpoint", 
                        True, 
                        f"Endpoint working, returned {session_count} sessions"
                    )
                else:
                    self.log_result(
                        "API Session List Endpoint", 
                        False, 
                        "Missing required fields in response"
                    )
            else:
                self.log_result(
                    "API Session List Endpoint", 
                    False, 
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
                
        except Exception as e:
            self.log_result("API Session List Endpoint", False, str(e))
    
    def test_api_session_detail_endpoint(self):
        """Test the /api/sessions/{session_id} endpoint"""
        try:
            if not self.auth_token:
                self.get_auth_token()
            
            # First get a session ID
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            list_response = requests.get(
                f"{self.base_url}/api/sessions",
                headers=headers,
                params={"limit": 1}
            )
            
            if list_response.status_code == 200:
                sessions = list_response.json().get('sessions', [])
                
                if sessions:
                    session_id = sessions[0]['session_id']
                    
                    # Get session details
                    detail_response = requests.get(
                        f"{self.base_url}/api/sessions/{session_id}",
                        headers=headers
                    )
                    
                    if detail_response.status_code == 200:
                        data = detail_response.json()
                        
                        has_required_fields = all(
                            key in data for key in ['success', 'session', 'messages']
                        )
                        
                        if has_required_fields:
                            msg_count = len(data.get('messages', []))
                            self.log_result(
                                "API Session Detail Endpoint", 
                                True, 
                                f"Retrieved session with {msg_count} messages"
                            )
                        else:
                            self.log_result(
                                "API Session Detail Endpoint", 
                                False, 
                                "Missing required fields"
                            )
                    else:
                        self.log_result(
                            "API Session Detail Endpoint", 
                            False, 
                            f"HTTP {detail_response.status_code}"
                        )
                else:
                    self.log_result(
                        "API Session Detail Endpoint", 
                        False, 
                        "No sessions available to test"
                    )
            else:
                self.log_result(
                    "API Session Detail Endpoint", 
                    False, 
                    "Could not get session list"
                )
                
        except Exception as e:
            self.log_result("API Session Detail Endpoint", False, str(e))
    
    def test_session_field_consistency(self):
        """Test that session fields are consistent across backend"""
        try:
            # Create a test session
            test_session = self.session_manager.create_session(
                user_id=self.test_user_email,
                title="Field Consistency Test"
            )
            self.test_session_ids.append(test_session['session_id'])
            
            # Check required fields
            required_fields = ['session_id', 'user_id', 'session_title', 'created_at']
            missing_fields = [f for f in required_fields if f not in test_session]
            
            if not missing_fields:
                self.log_result(
                    "Session Field Consistency", 
                    True, 
                    "All required fields present"
                )
            else:
                self.log_result(
                    "Session Field Consistency", 
                    False, 
                    f"Missing fields: {missing_fields}"
                )
                
        except Exception as e:
            self.log_result("Session Field Consistency", False, str(e))
    
    def test_orphaned_sessions_check(self):
        """Check for orphaned sessions without user_id"""
        try:
            # Query database directly for sessions without user_id
            result = self.supabase.client.table("chat_sessions").select("session_id, user_id").is_("user_id", "null").execute()
            
            orphaned_count = len(result.data) if result.data else 0
            
            if orphaned_count == 0:
                self.log_result(
                    "Orphaned Sessions Check", 
                    True, 
                    "No orphaned sessions found"
                )
            else:
                self.log_result(
                    "Orphaned Sessions Check", 
                    False, 
                    f"Found {orphaned_count} sessions without user_id"
                )
                
        except Exception as e:
            self.log_result("Orphaned Sessions Check", False, str(e))
    
    def cleanup_test_sessions(self):
        """Clean up sessions created during testing"""
        try:
            deleted_count = 0
            for session_id in self.test_session_ids:
                try:
                    if self.session_manager.delete_session(session_id):
                        deleted_count += 1
                except:
                    pass  # Ignore individual deletion errors
            
            print(f"\n🧹 Cleanup: Deleted {deleted_count}/{len(self.test_session_ids)} test sessions")
            
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
    
    def run_all_tests(self):
        """Run all QA tests"""
        print("\n" + "="*60)
        print("CHAT HISTORY QA TEST SUITE")
        print("="*60 + "\n")
        
        # Run tests
        self.test_session_creation_with_user()
        self.test_session_retrieval_by_user()
        self.test_message_addition_to_session()
        self.test_api_session_list_endpoint()
        self.test_api_session_detail_endpoint()
        self.test_session_field_consistency()
        self.test_orphaned_sessions_check()
        
        # Cleanup
        self.cleanup_test_sessions()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate == 100:
            print("\n🎉 All chat history tests passed!")
        elif pass_rate >= 80:
            print(f"\n⚠️  {total - passed} test(s) failed. Review the details above.")
        else:
            print(f"\n❌ Multiple tests failed ({total - passed}/{total}). Critical issues detected.")
        
        return pass_rate == 100

if __name__ == "__main__":
    qa = ChatHistoryQA()
    success = qa.run_all_tests()