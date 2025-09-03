#!/usr/bin/env python3
"""
Deployable Test Suite - Works for both local and deployed environments
Can be run in CI/CD pipelines
"""

import asyncio
import aiohttp
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from supabase import create_client, Client
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config import get_qa_config

# Load environment variables
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
load_dotenv(env_path)

class DeployableRAGTest:
    """Test suite that can run against any environment"""
    
    def __init__(self, environment: str = None):
        # Get configuration for target environment
        self.config = get_qa_config(environment)
        print(f"\nInitializing tests for environment: {self.config.environment.value}")
        print(f"Backend URL: {self.config.backend_url}")
        print(f"Frontend URL: {self.config.frontend_url}")
        
        # Initialize clients
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_ANON_KEY")
        )
        
        # Test data
        self.test_session_id = str(uuid.uuid4())
        self.test_results = []
        self.uploaded_file_id = None
        self.uploaded_file_name = None
        
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "environment": self.config.environment.value
        })
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {details}")
    
    # ========================================
    # Health Check - Should run first
    # ========================================
    
    async def test_health_check(self):
        """Test if the service is reachable"""
        print("\n🏥 TEST: Health Check")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = self.config.get_headers()
                async with session.get(
                    f"{self.config.backend_url}/api/health",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.record_test(
                            "Health Check",
                            True,
                            f"Service healthy: {data.get('status', 'ok')}"
                        )
                        return True
                    else:
                        self.record_test(
                            "Health Check",
                            False,
                            f"Status {response.status}"
                        )
                        return False
        except Exception as e:
            self.record_test("Health Check", False, str(e))
            return False
    
    # ========================================
    # API Tests
    # ========================================
    
    async def test_document_list(self):
        """Test document listing API"""
        print("\n📄 TEST: Document List API")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = self.config.get_headers()
                async with session.get(
                    f"{self.config.backend_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        doc_count = len(data.get("documents", []))
                        self.record_test(
                            "Document List API",
                            True,
                            f"Retrieved {doc_count} documents"
                        )
                        return True
                    else:
                        self.record_test(
                            "Document List API",
                            False,
                            f"Status {response.status}"
                        )
                        return False
        except Exception as e:
            self.record_test("Document List API", False, str(e))
            return False
    
    async def test_chat_api(self):
        """Test chat API without file upload"""
        print("\n💬 TEST: Chat API")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = self.config.get_headers({"Content-Type": "application/json"})
                payload = {
                    "message": "Hello, this is a test message",
                    "session_id": self.test_session_id
                }
                
                async with session.post(
                    f"{self.config.backend_url}/api/chat",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        duration = data.get("duration_seconds", 0)
                        self.record_test(
                            "Chat API",
                            True,
                            f"Response in {duration:.2f}s"
                        )
                        return True
                    else:
                        self.record_test(
                            "Chat API",
                            False,
                            f"Status {response.status}"
                        )
                        return False
        except Exception as e:
            self.record_test("Chat API", False, str(e))
            return False
    
    async def test_document_upload(self):
        """Test document upload (only in non-production)"""
        if self.config.environment.value == "production":
            print("\n📝 TEST: Document Upload (Skipped in production)")
            self.record_test("Document Upload", True, "Skipped in production")
            return True
            
        print("\n📝 TEST: Document Upload")
        print("-" * 40)
        
        try:
            # Create test document
            test_content = f"Test document created at {datetime.now().isoformat()}"
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                test_file_path = f.name
            
            # Upload
            async with aiohttp.ClientSession() as session:
                headers = self.config.get_headers()
                with open(test_file_path, 'rb') as file:
                    data = aiohttp.FormData()
                    data.add_field('files', file, filename='qa_test.txt')
                    
                    async with session.post(
                        f"{self.config.backend_url}/api/documents/upload",
                        headers=headers,
                        data=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("documents"):
                                doc = result["documents"][0]
                                self.uploaded_file_id = doc.get("file_id")
                                self.record_test(
                                    "Document Upload",
                                    True,
                                    f"Uploaded: {doc.get('filename')}"
                                )
                                return True
                        
                        self.record_test("Document Upload", False, f"Status {response.status}")
                        return False
                        
        except Exception as e:
            self.record_test("Document Upload", False, str(e))
            return False
        finally:
            if 'test_file_path' in locals():
                os.unlink(test_file_path)
    
    # ========================================
    # Frontend Tests (if accessible)
    # ========================================
    
    async def test_frontend_accessible(self):
        """Test if frontend is accessible"""
        print("\n🌐 TEST: Frontend Accessibility")
        print("-" * 40)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try different paths based on environment
                paths = ["/public/admin.html", "/admin.html", "/"]
                
                for path in paths:
                    url = f"{self.config.frontend_url}{path}"
                    try:
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                self.record_test(
                                    "Frontend Accessible",
                                    True,
                                    f"Found at {path}"
                                )
                                return True
                    except:
                        continue
                
                self.record_test("Frontend Accessible", False, "Not accessible")
                return False
                
        except Exception as e:
            self.record_test("Frontend Accessible", False, str(e))
            return False
    
    # ========================================
    # Cleanup
    # ========================================
    
    async def cleanup(self):
        """Clean up test data"""
        if self.config.environment.value == "production":
            print("\n🧹 Cleanup skipped in production")
            return
            
        print("\n🧹 Cleaning up test data...")
        
        # Delete uploaded file if exists
        if self.uploaded_file_id:
            try:
                async with aiohttp.ClientSession() as session:
                    headers = self.config.get_headers()
                    async with session.delete(
                        f"{self.config.backend_url}/api/documents/{self.uploaded_file_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            print(f"  Deleted test file: {self.uploaded_file_id}")
            except:
                pass
    
    # ========================================
    # Main Test Runner
    # ========================================
    
    async def run_all_tests(self):
        """Run all tests appropriate for the environment"""
        print("=" * 60)
        print(f"DEPLOYABLE RAG TEST SUITE - {self.config.environment.value.upper()}")
        print("=" * 60)
        
        # Run tests in order
        tests_to_run = [
            self.test_health_check,
            self.test_document_list,
            self.test_chat_api,
            self.test_frontend_accessible,
        ]
        
        # Add upload test only for non-production
        if self.config.environment.value != "production":
            tests_to_run.append(self.test_document_upload)
        
        for test in tests_to_run:
            await test()
        
        # Cleanup
        await self.cleanup()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\nEnvironment: {self.config.environment.value}")
        print(f"Backend: {self.config.backend_url}")
        print(f"Frontend: {self.config.frontend_url}")
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        # Save report
        report_file = f"test_report_{self.config.environment.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
        
        # Return exit code for CI/CD
        return 0 if failed == 0 else 1


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run RAG Chatbot tests')
    parser.add_argument(
        '--env',
        choices=['local', 'staging', 'production'],
        default='local',
        help='Environment to test (default: local)'
    )
    
    args = parser.parse_args()
    
    tester = DeployableRAGTest(environment=args.env)
    exit_code = await tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())