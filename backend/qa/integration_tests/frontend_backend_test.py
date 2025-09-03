#!/usr/bin/env python3
"""
Frontend-Backend Integration Test
Tests the actual code paths used by the frontend to ensure consistency
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from auth_helper import get_auth_token, get_auth_headers

class FrontendBackendIntegrationTest:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.frontend_url = "http://localhost:3001"
        self.results = []
        
    async def test_frontend_api_consistency(self):
        """Test that frontend API calls match backend expectations"""
        print("\n🔄 Testing Frontend-Backend API Consistency")
        print("-"*40)
        
        # Get the frontend api.js file to understand what it's sending
        frontend_tests = []
        
        # Test 1: Chat message format
        test_name = "Chat Message Format"
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            # Test what frontend sends (FormData)
            form_data = aiohttp.FormData()
            form_data.add_field('message', 'Integration test message')
            form_data.add_field('session_id', 'integration_test_session')
            
            try:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Verify response structure matches what frontend expects
                        expected_fields = ['response', 'session_id']
                        missing_fields = [f for f in expected_fields if f not in data]
                        
                        if not missing_fields:
                            print(f"✅ {test_name}: Request/Response format correct")
                            self.results.append({
                                "test": test_name,
                                "status": "PASS",
                                "note": "Frontend FormData format works with backend"
                            })
                        else:
                            print(f"❌ {test_name}: Missing response fields: {missing_fields}")
                            self.results.append({
                                "test": test_name,
                                "status": "FAIL",
                                "error": f"Missing fields: {missing_fields}"
                            })
                    else:
                        print(f"❌ {test_name}: Failed with status {response.status}")
                        self.results.append({
                            "test": test_name,
                            "status": "FAIL",
                            "error": f"Status {response.status}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Test 2: Document list response format
        test_name = "Document List Response"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if response matches frontend expectations
                        if 'documents' in data and isinstance(data['documents'], list):
                            print(f"✅ {test_name}: Response format matches frontend")
                            self.results.append({
                                "test": test_name,
                                "status": "PASS"
                            })
                        else:
                            print(f"❌ {test_name}: Response format mismatch")
                            self.results.append({
                                "test": test_name,
                                "status": "FAIL",
                                "error": "Documents field missing or not array"
                            })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Test 3: Health check response format
        test_name = "Health Check Response"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/health/components",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Frontend expects 'healthy' field (not 'status')
                        if 'healthy' in data and isinstance(data['healthy'], bool):
                            print(f"✅ {test_name}: Response has correct 'healthy' field")
                            self.results.append({
                                "test": test_name,
                                "status": "PASS",
                                "note": "Using 'healthy' field, not 'status'"
                            })
                        else:
                            print(f"❌ {test_name}: Missing 'healthy' field")
                            self.results.append({
                                "test": test_name,
                                "status": "FAIL",
                                "error": "Frontend expects 'healthy' boolean field"
                            })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
    
    async def test_error_handling(self):
        """Test error scenarios to ensure frontend handles them properly"""
        print("\n⚠️ Testing Error Handling")
        print("-"*40)
        
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        # Test 1: Invalid session ID format
        test_name = "Invalid Session Handling"
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field('message', 'Test')
            form_data.add_field('session_id', '')  # Empty session ID
            
            try:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    # Should still work, creating new session
                    if response.status == 200:
                        print(f"✅ {test_name}: Handles empty session gracefully")
                        self.results.append({
                            "test": test_name,
                            "status": "PASS"
                        })
                    else:
                        print(f"⚠️ {test_name}: Status {response.status}")
                        self.results.append({
                            "test": test_name,
                            "status": "WARN",
                            "note": f"Status {response.status}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Test 2: Missing authentication
        test_name = "Missing Auth Handling"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/api/documents"
                    # No auth headers
                ) as response:
                    if response.status == 401:
                        print(f"✅ {test_name}: Correctly returns 401 for missing auth")
                        self.results.append({
                            "test": test_name,
                            "status": "PASS"
                        })
                    else:
                        print(f"❌ {test_name}: Expected 401, got {response.status}")
                        self.results.append({
                            "test": test_name,
                            "status": "FAIL",
                            "error": f"Expected 401, got {response.status}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
    
    async def test_data_flow(self):
        """Test complete data flow from frontend to backend and back"""
        print("\n📊 Testing Complete Data Flow")
        print("-"*40)
        
        token = await get_auth_token()
        headers = get_auth_headers(token)
        test_message = f"Integration test at {datetime.now().isoformat()}"
        
        test_name = "End-to-End Message Flow"
        async with aiohttp.ClientSession() as session:
            # Send message
            form_data = aiohttp.FormData()
            form_data.add_field('message', test_message)
            
            try:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Verify all expected fields
                        checks = {
                            "Has response": 'response' in data,
                            "Response not empty": bool(data.get('response')),
                            "Has session_id": 'session_id' in data,
                            "Session ID not empty": bool(data.get('session_id'))
                        }
                        
                        all_passed = all(checks.values())
                        
                        if all_passed:
                            print(f"✅ {test_name}: Complete flow working")
                            for check, passed in checks.items():
                                print(f"   ✅ {check}")
                            self.results.append({
                                "test": test_name,
                                "status": "PASS"
                            })
                        else:
                            print(f"⚠️ {test_name}: Some checks failed")
                            for check, passed in checks.items():
                                icon = "✅" if passed else "❌"
                                print(f"   {icon} {check}")
                            self.results.append({
                                "test": test_name,
                                "status": "PARTIAL",
                                "checks": checks
                            })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({
                    "test": test_name,
                    "status": "ERROR",
                    "error": str(e)
                })
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("FRONTEND-BACKEND INTEGRATION TEST SUITE")
        print("="*60)
        
        await self.test_frontend_api_consistency()
        await self.test_error_handling()
        await self.test_data_flow()
        
        # Summary
        print("\n" + "="*60)
        print("INTEGRATION TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] in ["FAIL", "ERROR"])
        partial = sum(1 for r in self.results if r["status"] == "PARTIAL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Partial: {partial}")
        print(f"⚠️ Warnings: {warned}")
        
        # Detailed results
        print("\nDetailed Results:")
        for result in self.results:
            icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] in ["FAIL", "ERROR"] else "⚠️"
            print(f"{icon} {result['test']}: {result['status']}")
            if result.get("note"):
                print(f"   Note: {result['note']}")
            if result.get("error"):
                print(f"   Error: {result['error']}")
        
        # Save report
        report_file = f"reports/integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("reports").mkdir(exist_ok=True)
        
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.results),
                    "passed": passed,
                    "failed": failed,
                    "partial": partial,
                    "warnings": warned
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return failed == 0

async def main():
    tester = FrontendBackendIntegrationTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())