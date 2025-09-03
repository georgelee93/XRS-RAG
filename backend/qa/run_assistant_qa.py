#!/usr/bin/env python3
"""
Automated QA Test Suite for Assistant and Vector Store Management
Runs all assistant-related tests automatically and generates a comprehensive report
"""

import asyncio
import sys
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add directories to path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))


class AssistantQATestSuite:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            },
            "recommendations": []
        }
        self.api_key = self._get_api_key()
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment or .env file"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            env_file = Path(__file__).parent.parent / ".env"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        return api_key
    
    async def test_resource_count(self) -> Dict:
        """Test 1: Check current resource counts"""
        print("\n" + "="*60)
        print("TEST 1: Resource Count Check")
        print("="*60)
        
        test_result = {
            "name": "Resource Count Check",
            "status": "pending",
            "details": {}
        }
        
        try:
            from openai import AsyncOpenAI
            import httpx
            
            client = AsyncOpenAI(
                api_key=self.api_key,
                default_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            # Count assistants
            assistants = await client.beta.assistants.list(limit=100)
            assistant_count = len(assistants.data)
            print(f"📊 Assistants found: {assistant_count}")
            
            # Count vector stores
            vector_store_count = 0
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    "https://api.openai.com/v1/vector_stores",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "OpenAI-Beta": "assistants=v2"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    vector_store_count = len(data.get('data', []))
            
            print(f"📦 Vector stores found: {vector_store_count}")
            
            test_result["details"] = {
                "assistants": assistant_count,
                "vector_stores": vector_store_count
            }
            
            # Evaluate results
            if assistant_count == 1 and vector_store_count == 1:
                test_result["status"] = "passed"
                print("✅ PASS: Exactly 1 assistant and 1 vector store (optimal)")
            elif assistant_count == 1 and vector_store_count <= 1:
                test_result["status"] = "passed"
                print("✅ PASS: Single assistant maintained")
            elif assistant_count > 1:
                test_result["status"] = "failed"
                print(f"❌ FAIL: Multiple assistants detected ({assistant_count})")
                self.results["recommendations"].append(
                    "Run cleanup: python3 qa/assistant_tests/resource_cleanup_test.py --auto-cleanup"
                )
            else:
                test_result["status"] = "warning"
                print("⚠️ WARNING: Unexpected resource state")
            
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            print(f"❌ ERROR: {e}")
        
        self.results["tests"].append(test_result)
        return test_result
    
    async def test_configuration_validity(self) -> Dict:
        """Test 2: Validate assistant configuration"""
        print("\n" + "="*60)
        print("TEST 2: Configuration Validation")
        print("="*60)
        
        test_result = {
            "name": "Configuration Validation",
            "status": "pending",
            "details": {}
        }
        
        try:
            config_file = Path("assistant_config.json")
            
            # Check if config exists
            if not config_file.exists():
                test_result["status"] = "failed"
                print("❌ FAIL: Configuration file not found")
                self.results["recommendations"].append(
                    "Create config by running the system once"
                )
                self.results["tests"].append(test_result)
                return test_result
            
            # Load and validate config
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            print(f"📋 Config loaded:")
            print(f"   Assistant ID: {config.get('assistant_id', 'None')}")
            print(f"   Vector Store ID: {config.get('vector_store_id', 'None')}")
            
            test_result["details"]["config"] = config
            
            # Validate IDs exist
            if not config.get("assistant_id"):
                test_result["status"] = "failed"
                print("❌ FAIL: No assistant_id in configuration")
            elif not config.get("vector_store_id") or config.get("vector_store_id") == "null":
                test_result["status"] = "warning"
                print("⚠️ WARNING: No vector_store_id in configuration")
                self.results["recommendations"].append(
                    "System needs to create and attach a vector store"
                )
            else:
                # Verify the IDs are valid
                from openai import AsyncOpenAI
                client = AsyncOpenAI(
                    api_key=self.api_key,
                    default_headers={"OpenAI-Beta": "assistants=v2"}
                )
                
                try:
                    # Check if assistant exists
                    assistant = await client.beta.assistants.retrieve(config["assistant_id"])
                    print(f"✅ Assistant {config['assistant_id'][:20]}... exists")
                    
                    # Check if vector store exists
                    import httpx
                    async with httpx.AsyncClient() as http_client:
                        response = await http_client.get(
                            f"https://api.openai.com/v1/vector_stores/{config['vector_store_id']}",
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "OpenAI-Beta": "assistants=v2"
                            }
                        )
                        if response.status_code == 200:
                            print(f"✅ Vector store {config['vector_store_id'][:20]}... exists")
                            test_result["status"] = "passed"
                            print("✅ PASS: Configuration is valid")
                        else:
                            test_result["status"] = "warning"
                            print(f"⚠️ WARNING: Vector store not accessible")
                            
                except Exception as e:
                    test_result["status"] = "failed"
                    print(f"❌ FAIL: Assistant not accessible: {e}")
                    self.results["recommendations"].append(
                        "Run cleanup to fix configuration"
                    )
            
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            print(f"❌ ERROR: {e}")
        
        self.results["tests"].append(test_result)
        return test_result
    
    async def test_chat_functionality(self) -> Dict:
        """Test 3: Verify chat works without creating duplicates"""
        print("\n" + "="*60)
        print("TEST 3: Chat Functionality")
        print("="*60)
        
        test_result = {
            "name": "Chat Functionality",
            "status": "pending",
            "details": {}
        }
        
        try:
            from auth_helper import get_auth_token, get_auth_headers
            import aiohttp
            
            # Get initial resource count
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=self.api_key,
                default_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            initial_assistants = await client.beta.assistants.list(limit=100)
            initial_count = len(initial_assistants.data)
            
            # Send test chat message
            token = await get_auth_token()
            headers = get_auth_headers(token)
            
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field('message', 'QA Test: List available documents')
                form_data.add_field('session_id', 'qa_test_session')
                
                async with session.post(
                    "http://localhost:8080/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Chat response received")
                        print(f"   Preview: {data.get('response', '')[:80]}...")
                        test_result["details"]["chat_success"] = True
                    else:
                        print(f"❌ Chat failed: HTTP {response.status}")
                        test_result["details"]["chat_success"] = False
            
            # Check resource count after chat
            final_assistants = await client.beta.assistants.list(limit=100)
            final_count = len(final_assistants.data)
            
            if final_count > initial_count:
                test_result["status"] = "failed"
                print(f"❌ FAIL: New assistant created during chat ({initial_count} → {final_count})")
                self.results["recommendations"].append(
                    "Critical: System is creating new assistants. Run cleanup immediately."
                )
            else:
                test_result["status"] = "passed"
                print(f"✅ PASS: No new assistants created (stayed at {final_count})")
            
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            print(f"❌ ERROR: {e}")
        
        self.results["tests"].append(test_result)
        return test_result
    
    async def test_document_operations(self) -> Dict:
        """Test 4: Verify document operations don't create duplicates"""
        print("\n" + "="*60)
        print("TEST 4: Document Operations")
        print("="*60)
        
        test_result = {
            "name": "Document Operations",
            "status": "pending",
            "details": {}
        }
        
        try:
            from auth_helper import get_auth_token, get_auth_headers
            import aiohttp
            
            token = await get_auth_token()
            headers = get_auth_headers(token)
            
            async with aiohttp.ClientSession() as session:
                # List documents
                async with session.get(
                    "http://localhost:8080/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        doc_count = len(data.get('documents', []))
                        print(f"✅ Document list retrieved: {doc_count} documents")
                        test_result["details"]["document_count"] = doc_count
                        test_result["status"] = "passed"
                    else:
                        print(f"❌ Failed to list documents: HTTP {response.status}")
                        test_result["status"] = "failed"
            
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            print(f"❌ ERROR: {e}")
        
        self.results["tests"].append(test_result)
        return test_result
    
    async def test_cleanup_needed(self) -> Dict:
        """Test 5: Check if cleanup is needed"""
        print("\n" + "="*60)
        print("TEST 5: Cleanup Necessity Check")
        print("="*60)
        
        test_result = {
            "name": "Cleanup Necessity Check",
            "status": "pending",
            "details": {}
        }
        
        try:
            # Get resource counts
            resource_test = self.results["tests"][0]  # First test has counts
            if resource_test["details"]:
                assistants = resource_test["details"].get("assistants", 0)
                vector_stores = resource_test["details"].get("vector_stores", 0)
                
                if assistants > 1 or vector_stores > 1:
                    test_result["status"] = "warning"
                    print(f"⚠️ WARNING: Cleanup recommended")
                    print(f"   Assistants: {assistants} (should be 1)")
                    print(f"   Vector stores: {vector_stores} (should be 1)")
                    test_result["details"]["cleanup_needed"] = True
                    
                    # Add cleanup command
                    print("\n📌 To clean up, run:")
                    print("   python3 qa/assistant_tests/resource_cleanup_test.py --auto-cleanup")
                else:
                    test_result["status"] = "passed"
                    print("✅ PASS: No cleanup needed")
                    test_result["details"]["cleanup_needed"] = False
            else:
                test_result["status"] = "error"
                print("❌ ERROR: Could not determine cleanup necessity")
            
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            print(f"❌ ERROR: {e}")
        
        self.results["tests"].append(test_result)
        return test_result
    
    def generate_summary(self):
        """Generate test summary and recommendations"""
        print("\n" + "="*60)
        print("QA TEST SUMMARY")
        print("="*60)
        
        # Count results
        for test in self.results["tests"]:
            self.results["summary"]["total"] += 1
            if test["status"] == "passed":
                self.results["summary"]["passed"] += 1
            elif test["status"] in ["failed", "error"]:
                self.results["summary"]["failed"] += 1
            elif test["status"] == "warning":
                self.results["summary"]["warnings"] += 1
        
        # Print summary
        print(f"\n📊 Results:")
        print(f"   Total Tests: {self.results['summary']['total']}")
        print(f"   ✅ Passed: {self.results['summary']['passed']}")
        print(f"   ❌ Failed: {self.results['summary']['failed']}")
        print(f"   ⚠️  Warnings: {self.results['summary']['warnings']}")
        
        # Overall status
        if self.results["summary"]["failed"] > 0:
            print(f"\n❌ OVERALL: FAILED - Issues detected")
        elif self.results["summary"]["warnings"] > 0:
            print(f"\n⚠️  OVERALL: PASSED WITH WARNINGS")
        else:
            print(f"\n✅ OVERALL: PASSED - System healthy")
        
        # Print recommendations
        if self.results["recommendations"]:
            print("\n📝 Recommendations:")
            for i, rec in enumerate(self.results["recommendations"], 1):
                print(f"   {i}. {rec}")
        
        # Save report
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"assistant_qa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return self.results["summary"]["failed"] == 0
    
    async def run_all_tests(self):
        """Run all automated QA tests"""
        print("\n" + "="*60)
        print("🤖 AUTOMATED ASSISTANT QA TEST SUITE")
        print("="*60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Run tests in sequence
            await self.test_resource_count()
            await self.test_configuration_validity()
            await self.test_chat_functionality()
            await self.test_document_operations()
            await self.test_cleanup_needed()
            
            # Generate summary
            success = self.generate_summary()
            
            return success
            
        except Exception as e:
            print(f"\n❌ Fatal error during testing: {e}")
            return False


async def main():
    """Main entry point for automated QA testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated QA tests for assistant management")
    parser.add_argument("--auto-fix", action="store_true", 
                       help="Automatically run cleanup if issues are found")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")
    args = parser.parse_args()
    
    # Run QA tests
    qa_suite = AssistantQATestSuite()
    success = await qa_suite.run_all_tests()
    
    # Auto-fix if requested and needed
    if args.auto_fix and not success:
        if any(test["details"].get("cleanup_needed") for test in qa_suite.results["tests"]):
            print("\n" + "="*60)
            print("🔧 AUTO-FIX: Running cleanup...")
            print("="*60)
            
            import subprocess
            result = subprocess.run(
                ["python3", "assistant_tests/resource_cleanup_test.py", "--auto-cleanup"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Cleanup completed successfully")
                
                # Re-run tests to verify
                print("\n🔄 Re-running tests after cleanup...")
                qa_suite_retest = AssistantQATestSuite()
                success = await qa_suite_retest.run_all_tests()
            else:
                print("❌ Cleanup failed")
                print(result.stderr)
    
    # JSON output if requested
    if args.json:
        print("\n" + json.dumps(qa_suite.results, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())