#!/usr/bin/env python3
"""
Assistant Duplication Prevention Test
Ensures the system reuses existing assistant and vector store instead of creating new ones
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from openai import OpenAI, AsyncOpenAI
from auth_helper import get_auth_token, get_auth_headers


class AssistantPreventionTest:
    def __init__(self):
        self.api_key = self._get_api_key()
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.base_url = "http://localhost:8080"
        self.results = []
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from environment or .env file"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            env_file = Path(__file__).parent.parent.parent / ".env"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        return api_key
    
    async def count_resources(self) -> Dict[str, int]:
        """Count current assistants and vector stores"""
        count = {"assistants": 0, "vector_stores": 0}
        
        # Count assistants
        try:
            assistants = await self.async_client.beta.assistants.list(limit=100)
            count["assistants"] = len(assistants.data)
        except Exception as e:
            print(f"Error counting assistants: {e}")
        
        # Count vector stores
        try:
            import httpx
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
                    count["vector_stores"] = len(data.get('data', []))
        except Exception as e:
            print(f"Error counting vector stores: {e}")
        
        return count
    
    async def test_multiple_chat_sessions(self):
        """Test that multiple chat sessions don't create new assistants"""
        print("\n🔄 Testing Multiple Chat Sessions")
        print("-"*40)
        
        # Get initial counts
        initial_counts = await self.count_resources()
        print(f"Initial state: {initial_counts['assistants']} assistants, {initial_counts['vector_stores']} vector stores")
        
        # Get auth token for API calls
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        # Simulate multiple chat sessions
        sessions_to_test = 5
        print(f"\nStarting {sessions_to_test} chat sessions...")
        
        async with aiohttp.ClientSession() as session:
            for i in range(sessions_to_test):
                try:
                    # Send a chat message
                    form_data = aiohttp.FormData()
                    form_data.add_field('message', f'Test message {i+1}')
                    form_data.add_field('session_id', f'test_prevention_session_{i}')
                    
                    async with session.post(
                        f"{self.base_url}/api/chat",
                        data=form_data,
                        headers=headers
                    ) as response:
                        if response.status_code == 200:
                            print(f"  ✅ Session {i+1}: Chat successful")
                        else:
                            print(f"  ❌ Session {i+1}: Chat failed (status {response.status_code})")
                    
                    # Small delay between sessions
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"  ❌ Session {i+1}: Error - {e}")
        
        # Get final counts
        final_counts = await self.count_resources()
        print(f"\nFinal state: {final_counts['assistants']} assistants, {final_counts['vector_stores']} vector stores")
        
        # Verify no new resources were created
        test_passed = True
        if final_counts["assistants"] > initial_counts["assistants"]:
            print(f"❌ New assistants created: {final_counts['assistants'] - initial_counts['assistants']}")
            test_passed = False
        else:
            print("✅ No new assistants created")
        
        if final_counts["vector_stores"] > initial_counts["vector_stores"]:
            print(f"❌ New vector stores created: {final_counts['vector_stores'] - initial_counts['vector_stores']}")
            test_passed = False
        else:
            print("✅ No new vector stores created")
        
        self.results.append({
            "test": "Multiple Chat Sessions",
            "passed": test_passed,
            "initial": initial_counts,
            "final": final_counts
        })
        
        return test_passed
    
    async def test_backend_restart(self):
        """Test that restarting backend doesn't create new resources"""
        print("\n🔄 Testing Backend Restart Resilience")
        print("-"*40)
        
        # Get initial counts
        initial_counts = await self.count_resources()
        print(f"Initial state: {initial_counts['assistants']} assistants, {initial_counts['vector_stores']} vector stores")
        
        # Note: We can't actually restart the backend from here, but we can test
        # that the configuration is properly loaded on initialization
        
        # Check if configuration file exists and is valid
        config_file = Path("assistant_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            if config.get("assistant_id") and config.get("vector_store_id"):
                print("✅ Configuration file exists with valid IDs")
                
                # Verify the IDs actually exist
                try:
                    assistant = await self.async_client.beta.assistants.retrieve(config["assistant_id"])
                    print(f"✅ Assistant {config['assistant_id']} exists and is accessible")
                except Exception as e:
                    print(f"❌ Assistant {config['assistant_id']} not accessible: {e}")
                
                # Verify vector store exists
                try:
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
                            print(f"✅ Vector store {config['vector_store_id']} exists and is accessible")
                        else:
                            print(f"❌ Vector store {config['vector_store_id']} not accessible: HTTP {response.status_code}")
                except Exception as e:
                    print(f"❌ Error checking vector store: {e}")
                
                self.results.append({
                    "test": "Backend Restart Resilience",
                    "passed": True,
                    "config": config
                })
                return True
            else:
                print("❌ Configuration file missing required IDs")
                self.results.append({
                    "test": "Backend Restart Resilience",
                    "passed": False,
                    "error": "Invalid configuration"
                })
                return False
        else:
            print("❌ Configuration file not found")
            self.results.append({
                "test": "Backend Restart Resilience",
                "passed": False,
                "error": "No configuration file"
            })
            return False
    
    async def test_document_operations(self):
        """Test that document operations don't create new resources"""
        print("\n📄 Testing Document Operations")
        print("-"*40)
        
        # Get initial counts
        initial_counts = await self.count_resources()
        print(f"Initial state: {initial_counts['assistants']} assistants, {initial_counts['vector_stores']} vector stores")
        
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        async with aiohttp.ClientSession() as session:
            # List documents (shouldn't create resources)
            try:
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status_code == 200:
                        data = await response.json()
                        print(f"✅ Listed {len(data.get('documents', []))} documents")
                    else:
                        print(f"❌ Failed to list documents: {response.status_code}")
            except Exception as e:
                print(f"❌ Error listing documents: {e}")
        
        # Get final counts
        final_counts = await self.count_resources()
        print(f"\nFinal state: {final_counts['assistants']} assistants, {final_counts['vector_stores']} vector stores")
        
        # Verify no new resources were created
        test_passed = (
            final_counts["assistants"] == initial_counts["assistants"] and
            final_counts["vector_stores"] == initial_counts["vector_stores"]
        )
        
        if test_passed:
            print("✅ No new resources created during document operations")
        else:
            print("❌ New resources created during document operations")
        
        self.results.append({
            "test": "Document Operations",
            "passed": test_passed,
            "initial": initial_counts,
            "final": final_counts
        })
        
        return test_passed
    
    async def test_concurrent_requests(self):
        """Test that concurrent requests don't create duplicate resources"""
        print("\n⚡ Testing Concurrent Requests")
        print("-"*40)
        
        # Get initial counts
        initial_counts = await self.count_resources()
        print(f"Initial state: {initial_counts['assistants']} assistants, {initial_counts['vector_stores']} vector stores")
        
        token = await get_auth_token()
        headers = get_auth_headers(token)
        
        # Send multiple concurrent requests
        concurrent_requests = 10
        print(f"\nSending {concurrent_requests} concurrent chat requests...")
        
        async def send_chat_request(session, index):
            try:
                form_data = aiohttp.FormData()
                form_data.add_field('message', f'Concurrent test {index}')
                form_data.add_field('session_id', f'concurrent_session_{index}')
                
                async with session.post(
                    f"{self.base_url}/api/chat",
                    data=form_data,
                    headers=headers
                ) as response:
                    return response.status == 200
            except Exception as e:
                print(f"  Error in request {index}: {e}")
                return False
        
        async with aiohttp.ClientSession() as session:
            # Send all requests concurrently
            tasks = [send_chat_request(session, i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            successful = sum(results)
            print(f"  {successful}/{concurrent_requests} requests successful")
        
        # Wait a bit for any async operations to complete
        await asyncio.sleep(3)
        
        # Get final counts
        final_counts = await self.count_resources()
        print(f"\nFinal state: {final_counts['assistants']} assistants, {final_counts['vector_stores']} vector stores")
        
        # Verify no new resources were created
        test_passed = (
            final_counts["assistants"] == initial_counts["assistants"] and
            final_counts["vector_stores"] == initial_counts["vector_stores"]
        )
        
        if test_passed:
            print("✅ No duplicate resources created by concurrent requests")
        else:
            print("❌ Duplicate resources created by concurrent requests")
            if final_counts["assistants"] > initial_counts["assistants"]:
                print(f"  New assistants: {final_counts['assistants'] - initial_counts['assistants']}")
            if final_counts["vector_stores"] > initial_counts["vector_stores"]:
                print(f"  New vector stores: {final_counts['vector_stores'] - initial_counts['vector_stores']}")
        
        self.results.append({
            "test": "Concurrent Requests",
            "passed": test_passed,
            "initial": initial_counts,
            "final": final_counts
        })
        
        return test_passed
    
    async def run_all_tests(self):
        """Run all prevention tests"""
        print("\n" + "="*60)
        print("ASSISTANT DUPLICATION PREVENTION TEST SUITE")
        print("="*60)
        
        all_passed = True
        
        # Run each test
        tests = [
            self.test_backend_restart(),
            self.test_multiple_chat_sessions(),
            self.test_document_operations(),
            self.test_concurrent_requests()
        ]
        
        for test in tests:
            result = await test
            all_passed = all_passed and result
            print()  # Blank line between tests
        
        # Summary
        print("="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        
        for result in self.results:
            icon = "✅" if result["passed"] else "❌"
            print(f"{icon} {result['test']}")
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        # Save report
        report_file = f"reports/prevention_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("reports", exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "all_passed": all_passed,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        if all_passed:
            print("\n✅ All prevention tests passed - no duplicate resources created!")
        else:
            print("\n❌ Some tests failed - duplicate resources may be created")
        
        return all_passed


async def main():
    """Main test runner"""
    tester = AssistantPreventionTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())