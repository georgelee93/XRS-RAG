#!/usr/bin/env python3
"""
Content-Type and Request Format Testing
Tests API endpoints with different content types to ensure proper handling
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

class ContentTypeValidator:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.results = []
        
    async def test_chat_with_json(self, token):
        """Test chat endpoint with JSON (should fail with 422)"""
        test_name = "Chat API with JSON"
        headers = get_auth_headers(token)
        headers['Content-Type'] = 'application/json'
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "message": "Test message",
                    "session_id": "test_json_session"
                }
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 422:
                        print(f"✅ {test_name}: Correctly rejected JSON (422)")
                        self.results.append({
                            "test": test_name, 
                            "status": "PASS",
                            "note": "Backend correctly expects FormData, not JSON"
                        })
                    elif response.status == 200:
                        print(f"⚠️ {test_name}: Unexpectedly accepted JSON")
                        self.results.append({
                            "test": test_name,
                            "status": "WARN",
                            "note": "Backend accepted JSON when it should require FormData"
                        })
                    else:
                        print(f"❌ {test_name}: Unexpected status {response.status}")
                        self.results.append({
                            "test": test_name,
                            "status": "FAIL",
                            "error": f"Status {response.status}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
    
    async def test_chat_with_formdata(self, token):
        """Test chat endpoint with FormData (should succeed)"""
        test_name = "Chat API with FormData"
        headers = get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            try:
                form_data = aiohttp.FormData()
                form_data.add_field('message', 'Test message with FormData')
                form_data.add_field('session_id', 'test_formdata_session')
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "response" in data:
                            print(f"✅ {test_name}: Success with FormData")
                            self.results.append({"test": test_name, "status": "PASS"})
                        else:
                            print(f"⚠️ {test_name}: Response missing expected fields")
                            self.results.append({
                                "test": test_name,
                                "status": "WARN",
                                "note": "Response structure unexpected"
                            })
                    else:
                        error = await response.text()
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        self.results.append({
                            "test": test_name,
                            "status": "FAIL",
                            "error": f"Status {response.status}: {error[:100]}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
    
    async def test_document_upload_formats(self, token):
        """Test document upload with different content types"""
        test_name = "Document Upload Content-Type"
        headers = get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            try:
                # Create a test file
                form_data = aiohttp.FormData()
                form_data.add_field(
                    'files',
                    b'Test document content',
                    filename='test.txt',
                    content_type='text/plain'
                )
                
                async with session.post(
                    f"{self.base_url}/api/documents/upload",
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status in [200, 201]:
                        print(f"✅ {test_name}: FormData upload successful")
                        self.results.append({"test": test_name, "status": "PASS"})
                    elif response.status == 403:
                        print(f"⚠️ {test_name}: Admin access required")
                        self.results.append({
                            "test": test_name,
                            "status": "SKIP",
                            "note": "Requires admin privileges"
                        })
                    else:
                        print(f"❌ {test_name}: Failed (Status: {response.status})")
                        self.results.append({
                            "test": test_name,
                            "status": "FAIL",
                            "error": f"Status {response.status}"
                        })
            except Exception as e:
                print(f"❌ {test_name}: Error - {e}")
                self.results.append({"test": test_name, "status": "ERROR", "error": str(e)})
    
    async def test_all_endpoints_content_types(self, token):
        """Test various endpoints with different content types"""
        test_cases = [
            {
                "name": "Sessions List (GET)",
                "method": "GET",
                "endpoint": "/api/sessions",
                "content_type": None,
                "expected_status": [200]
            },
            {
                "name": "Documents List (GET)",
                "method": "GET",
                "endpoint": "/api/documents",
                "content_type": None,
                "expected_status": [200]
            },
            {
                "name": "Health Check (GET)",
                "method": "GET",
                "endpoint": "/api/health/components",
                "content_type": None,
                "expected_status": [200]
            }
        ]
        
        headers = get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            for test_case in test_cases:
                try:
                    if test_case["content_type"]:
                        headers["Content-Type"] = test_case["content_type"]
                    
                    async with session.request(
                        test_case["method"],
                        f"{self.base_url}{test_case['endpoint']}",
                        headers=headers
                    ) as response:
                        if response.status in test_case["expected_status"]:
                            print(f"✅ {test_case['name']}: OK")
                            self.results.append({
                                "test": test_case['name'],
                                "status": "PASS"
                            })
                        else:
                            print(f"❌ {test_case['name']}: Unexpected status {response.status}")
                            self.results.append({
                                "test": test_case['name'],
                                "status": "FAIL",
                                "error": f"Expected {test_case['expected_status']}, got {response.status}"
                            })
                except Exception as e:
                    print(f"❌ {test_case['name']}: Error - {e}")
                    self.results.append({
                        "test": test_case['name'],
                        "status": "ERROR",
                        "error": str(e)
                    })
    
    async def run_all_tests(self):
        """Run all content-type validation tests"""
        print("\n" + "="*60)
        print("CONTENT-TYPE VALIDATION TEST SUITE")
        print("="*60)
        
        # Get authentication
        print("\n🔐 Getting authentication token...")
        token = await get_auth_token()
        if not token:
            print("❌ Failed to authenticate")
            return False
        
        print("\n📋 Running Content-Type Tests...")
        print("-"*40)
        
        # Run all tests
        await self.test_chat_with_json(token)
        await self.test_chat_with_formdata(token)
        await self.test_document_upload_formats(token)
        await self.test_all_endpoints_content_types(token)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] in ["FAIL", "ERROR"])
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warned}")
        print(f"⏭️  Skipped: {skipped}")
        
        # Save report
        report_file = f"reports/content_type_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("reports").mkdir(exist_ok=True)
        
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.results),
                    "passed": passed,
                    "failed": failed,
                    "warnings": warned,
                    "skipped": skipped
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return failed == 0

async def main():
    validator = ContentTypeValidator()
    success = await validator.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())