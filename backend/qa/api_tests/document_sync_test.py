#!/usr/bin/env python3
"""
Document Synchronization Test
Tests that documents are properly synced between OpenAI, Supabase, and the Admin UI
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any
from openai import AsyncOpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DocumentSyncTester:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_ANON_KEY")
        )
        
        self.test_results = []
    
    def record_test(self, test_name: str, passed: bool, details: str):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {details}")
    
    async def check_openai_documents(self) -> Dict[str, Any]:
        """Check documents in OpenAI"""
        try:
            # Get assistant to check vector store
            assistant = await self.openai_client.beta.assistants.retrieve(self.assistant_id)
            
            # Get vector store files
            vector_store_id = None
            if assistant.tool_resources and assistant.tool_resources.file_search:
                vector_store_ids = assistant.tool_resources.file_search.vector_store_ids
                if vector_store_ids:
                    vector_store_id = vector_store_ids[0]
            
            openai_files = []
            if vector_store_id:
                # List files in vector store
                vector_files = await self.openai_client.vector_stores.files.list(
                    vector_store_id=vector_store_id
                )
                
                for vf in vector_files.data:
                    try:
                        file = await self.openai_client.files.retrieve(vf.id)
                        openai_files.append({
                            "id": file.id,
                            "filename": file.filename,
                            "bytes": file.bytes,
                            "created_at": file.created_at,
                            "status": vf.status
                        })
                    except Exception as e:
                        print(f"  Warning: Could not retrieve file {vf.id}: {e}")
            
            self.record_test(
                "OpenAI Documents Check",
                True,
                f"Found {len(openai_files)} documents in OpenAI"
            )
            
            return {
                "count": len(openai_files),
                "files": openai_files,
                "vector_store_id": vector_store_id
            }
            
        except Exception as e:
            self.record_test("OpenAI Documents Check", False, str(e))
            return {"count": 0, "files": [], "error": str(e)}
    
    def check_supabase_documents(self) -> Dict[str, Any]:
        """Check documents in Supabase database"""
        try:
            # Query documents table
            response = self.supabase.table("documents").select("*").eq(
                "status", "active"
            ).execute()
            
            supabase_docs = []
            if response.data:
                for doc in response.data:
                    supabase_docs.append({
                        "document_id": doc.get("document_id"),
                        "openai_file_id": doc.get("openai_file_id"),
                        "filename": doc.get("filename"),
                        "status": doc.get("status"),
                        "size_bytes": doc.get("size_bytes"),
                        "created_at": doc.get("created_at")
                    })
            
            self.record_test(
                "Supabase Documents Check",
                True,
                f"Found {len(supabase_docs)} active documents in Supabase"
            )
            
            return {
                "count": len(supabase_docs),
                "documents": supabase_docs
            }
            
        except Exception as e:
            self.record_test("Supabase Documents Check", False, str(e))
            return {"count": 0, "documents": [], "error": str(e)}
    
    async def check_api_documents(self) -> Dict[str, Any]:
        """Check documents returned by API endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/documents") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        documents = data if isinstance(data, list) else data.get("documents", [])
                        
                        self.record_test(
                            "API Documents Endpoint",
                            True,
                            f"API returned {len(documents)} documents"
                        )
                        
                        return {
                            "count": len(documents),
                            "documents": documents,
                            "status_code": response.status
                        }
                    else:
                        error_text = await response.text()
                        self.record_test(
                            "API Documents Endpoint",
                            False,
                            f"Status {response.status}: {error_text}"
                        )
                        return {
                            "count": 0,
                            "documents": [],
                            "status_code": response.status,
                            "error": error_text
                        }
                        
        except Exception as e:
            self.record_test("API Documents Endpoint", False, str(e))
            return {"count": 0, "documents": [], "error": str(e)}
    
    async def check_admin_page_request(self) -> Dict[str, Any]:
        """Simulate the admin page's request to get documents"""
        try:
            # Check what the admin page JavaScript would receive
            async with aiohttp.ClientSession() as session:
                # First check if there's an auth requirement
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError:
                        data = {"error": "Invalid JSON response", "raw": response_text[:200]}
                    
                    self.record_test(
                        "Admin Page Document Request",
                        response.status == 200,
                        f"Status {response.status}, Response type: {type(data).__name__}"
                    )
                    
                    return {
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "data": data,
                        "raw_text": response_text[:500] if response.status != 200 else None
                    }
                    
        except Exception as e:
            self.record_test("Admin Page Document Request", False, str(e))
            return {"error": str(e)}
    
    def compare_document_sources(self, openai_data: Dict, supabase_data: Dict, api_data: Dict):
        """Compare documents across all sources"""
        print("\n" + "="*60)
        print("DOCUMENT SOURCE COMPARISON")
        print("="*60)
        
        # Extract file IDs from each source
        openai_ids = {f["id"] for f in openai_data.get("files", [])}
        supabase_ids = {d["openai_file_id"] for d in supabase_data.get("documents", []) if d["openai_file_id"]}
        api_ids = {d.get("openai_file_id") or d.get("file_id") for d in api_data.get("documents", []) if d.get("openai_file_id") or d.get("file_id")}
        
        print(f"\n📊 Document Counts:")
        print(f"  OpenAI:   {openai_data.get('count', 0)} documents")
        print(f"  Supabase: {supabase_data.get('count', 0)} documents")
        print(f"  API:      {api_data.get('count', 0)} documents")
        
        # Find discrepancies
        only_in_openai = openai_ids - supabase_ids
        only_in_supabase = supabase_ids - openai_ids
        in_both_not_api = (openai_ids & supabase_ids) - api_ids
        
        if only_in_openai:
            print(f"\n⚠️ Documents only in OpenAI ({len(only_in_openai)}):")
            for file_id in list(only_in_openai)[:5]:
                file = next((f for f in openai_data["files"] if f["id"] == file_id), {})
                print(f"  - {file_id}: {file.get('filename', 'unknown')}")
        
        if only_in_supabase:
            print(f"\n⚠️ Documents only in Supabase ({len(only_in_supabase)}):")
            for file_id in list(only_in_supabase)[:5]:
                doc = next((d for d in supabase_data["documents"] if d["openai_file_id"] == file_id), {})
                print(f"  - {file_id}: {doc.get('filename', 'unknown')}")
        
        if in_both_not_api:
            print(f"\n❌ Documents in OpenAI & Supabase but NOT returned by API ({len(in_both_not_api)}):")
            for file_id in list(in_both_not_api)[:5]:
                print(f"  - {file_id}")
        
        # Check if all three match
        all_match = (openai_data.get('count', 0) == supabase_data.get('count', 0) == api_data.get('count', 0))
        
        self.record_test(
            "Document Sync Verification",
            all_match and len(only_in_openai) == 0 and len(only_in_supabase) == 0,
            f"Sync status: {'✅ All sources match' if all_match else '❌ Sources do not match'}"
        )
    
    async def run_tests(self):
        """Run all document sync tests"""
        print("="*60)
        print("DOCUMENT SYNCHRONIZATION TEST")
        print("="*60)
        
        # 1. Check OpenAI documents
        print("\n🔍 Checking OpenAI Documents...")
        openai_data = await self.check_openai_documents()
        
        # 2. Check Supabase documents
        print("\n🔍 Checking Supabase Documents...")
        supabase_data = self.check_supabase_documents()
        
        # 3. Check API endpoint
        print("\n🔍 Checking API Documents Endpoint...")
        api_data = await self.check_api_documents()
        
        # 4. Check admin page request
        print("\n🔍 Simulating Admin Page Request...")
        admin_data = await self.check_admin_page_request()
        
        # 5. Compare all sources
        self.compare_document_sources(openai_data, supabase_data, api_data)
        
        # 6. Debug information
        print("\n" + "="*60)
        print("DEBUG INFORMATION")
        print("="*60)
        
        if api_data.get("count", 0) == 0 and (openai_data.get("count", 0) > 0 or supabase_data.get("count", 0) > 0):
            print("\n❌ API is not returning documents that exist in the system!")
            print("\nPossible causes:")
            print("  1. API endpoint has a bug in document retrieval")
            print("  2. Document status filtering issue")
            print("  3. Database connection problem")
            print("  4. Incorrect response format")
            
            # Show sample API response
            if api_data.get("documents") is not None:
                print(f"\nAPI Response sample: {json.dumps(api_data.get('documents', [])[:1], indent=2, default=str)}")
        
        # Print admin page response details
        if admin_data:
            print(f"\nAdmin Page Response Status: {admin_data.get('status_code')}")
            if admin_data.get('data'):
                print(f"Admin Page Data Type: {type(admin_data['data'])}")
                if isinstance(admin_data['data'], dict):
                    print(f"Admin Page Data Keys: {list(admin_data['data'].keys())}")
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {total-passed} ({(total-passed)/total*100:.1f}%)")
        
        if passed < total:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        return self.test_results


async def main():
    tester = DocumentSyncTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())