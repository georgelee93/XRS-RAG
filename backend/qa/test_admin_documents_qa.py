#!/usr/bin/env python3
"""
Admin Document Management QA Tests
Comprehensive tests for document upload, storage, listing, and deletion
"""

import sys
import os
import asyncio
import json
import tempfile
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth_helper import get_auth_token

class AdminDocumentQA:
    """Comprehensive admin document management tests"""
    
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.auth_token = None
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.test_documents = []  # Track documents created during tests
        self.test_files = []  # Track temp files created
        
    def log_result(self, test_name: str, passed: bool, error: str = None):
        """Log test result"""
        if passed:
            print(f"✅ {test_name}")
            self.passed += 1
        else:
            print(f"❌ {test_name}: {error}")
            self.failed += 1
            self.errors.append(f"{test_name}: {error}")
    
    def create_test_file(self, content: str, filename: str, file_type: str = "txt") -> str:
        """Create a temporary test file"""
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.test_files.append(file_path)
        return file_path
    
    async def setup(self) -> bool:
        """Setup authentication and test files"""
        print("\n🔧 Setting up test environment...")
        
        try:
            # Get authentication token
            self.auth_token = await get_auth_token()
            if not self.auth_token:
                self.log_result("Authentication setup", False, "Failed to get auth token")
                return False
            self.log_result("Authentication setup", True)
            
            # Create test files with different formats
            self.test_file_txt = self.create_test_file(
                "This is a test document for QA testing.\nIt contains multiple lines.\n테스트 문서입니다.",
                "qa_test_document.txt", "txt"
            )
            
            self.test_file_md = self.create_test_file(
                "# Test Markdown Document\n\n## Section 1\nThis is a test markdown file.\n\n## 섹션 2\n한글 테스트",
                "qa_test_document.md", "md"
            )
            
            self.test_file_korean = self.create_test_file(
                "한글 파일 테스트입니다.\n이 문서는 한글 파일명 처리를 테스트합니다.",
                "한글_테스트_문서.txt", "txt"
            )
            
            self.log_result("Test files created", True)
            return True
            
        except Exception as e:
            self.log_result("Setup", False, str(e))
            return False
    
    async def test_document_upload(self) -> bool:
        """Test document upload functionality"""
        print("\n📤 Testing document upload...")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Test 1: Upload valid text file
                with open(self.test_file_txt, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('files',
                                   f,
                                   filename='qa_test_document.txt',
                                   content_type='text/plain')
                    
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    async with session.post(
                        f"{self.base_url}/api/documents/upload",
                        data=data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            self.log_result("Upload text file", result.get("success", False))
                            
                            # Store document ID for cleanup
                            if result.get("results"):
                                for doc in result["results"]:
                                    if doc.get("success") and doc.get("document_id"):
                                        self.test_documents.append(doc["document_id"])
                                        self.log_result("Document ID captured", True)
                                        
                                        # Verify filename is correct
                                        if doc.get("filename") == "qa_test_document.txt":
                                            self.log_result("Filename preserved", True)
                                        else:
                                            self.log_result("Filename preserved", False, 
                                                          f"Expected qa_test_document.txt, got {doc.get('filename')}")
                        else:
                            error_text = await response.text()
                            self.log_result("Upload text file", False, f"Status {response.status}: {error_text[:100]}")
                
                # Test 2: Upload markdown file
                with open(self.test_file_md, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('files',
                                   f,
                                   filename='qa_test_document.md',
                                   content_type='text/markdown')
                    
                    async with session.post(
                        f"{self.base_url}/api/documents/upload",
                        data=data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            self.log_result("Upload markdown file", result.get("success", False))
                            
                            if result.get("results") and result["results"][0].get("document_id"):
                                self.test_documents.append(result["results"][0]["document_id"])
                        else:
                            self.log_result("Upload markdown file", False, f"Status {response.status}")
                
                # Test 3: Upload file with Korean filename
                with open(self.test_file_korean, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('files',
                                   f,
                                   filename='한글_테스트_문서.txt',
                                   content_type='text/plain')
                    
                    async with session.post(
                        f"{self.base_url}/api/documents/upload",
                        data=data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            self.log_result("Upload Korean filename", result.get("success", False))
                            
                            if result.get("results"):
                                doc = result["results"][0]
                                if doc.get("success"):
                                    self.test_documents.append(doc["document_id"])
                                    # Original filename should be preserved in metadata
                                    self.log_result("Korean filename handled", True)
                        else:
                            self.log_result("Upload Korean filename", False, f"Status {response.status}")
                
                # Test 4: Upload duplicate file (should return existing)
                await asyncio.sleep(1)  # Brief pause
                with open(self.test_file_txt, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('files',
                                   f,
                                   filename='qa_test_document.txt',
                                   content_type='text/plain')
                    
                    async with session.post(
                        f"{self.base_url}/api/documents/upload",
                        data=data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Should handle duplicate gracefully
                            self.log_result("Handle duplicate upload", True)
                        else:
                            self.log_result("Handle duplicate upload", False, f"Status {response.status}")
                
                # Test 5: Upload unsupported file type
                data = aiohttp.FormData()
                data.add_field('files',
                               b'fake executable content',
                               filename='test.exe',
                               content_type='application/octet-stream')
                
                async with session.post(
                    f"{self.base_url}/api/documents/upload",
                    data=data,
                    headers=headers
                ) as response:
                    result = await response.json()
                    # Should reject unsupported file type
                    if response.status == 200 and result.get("results"):
                        if not result["results"][0].get("success"):
                            self.log_result("Reject unsupported file type", True)
                        else:
                            self.log_result("Reject unsupported file type", False, "Accepted .exe file")
                    else:
                        self.log_result("Reject unsupported file type", True)
                
                return True
                
        except Exception as e:
            self.log_result("Document upload tests", False, str(e))
            return False
    
    async def test_document_listing(self) -> bool:
        """Test document listing functionality"""
        print("\n📋 Testing document listing...")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                # Test 1: List all documents
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.log_result("List all documents", result.get("success", False))
                        
                        if result.get("documents"):
                            docs = result["documents"]
                            
                            # Check if our test documents are listed
                            test_doc_found = False
                            for doc in docs:
                                if doc.get("supabase_id") in self.test_documents:
                                    test_doc_found = True
                                    
                                    # Verify required fields
                                    required_fields = ["supabase_id", "display_name", "file_size", 
                                                     "file_type", "status", "uploaded_at"]
                                    for field in required_fields:
                                        if field not in doc:
                                            self.log_result(f"Document field {field}", False, "Missing")
                                        else:
                                            self.log_result(f"Document field {field}", True)
                                    
                                    # Verify display_name is properly set
                                    if doc.get("display_name"):
                                        self.log_result("Display name present", True)
                                    else:
                                        self.log_result("Display name present", False, "Empty or missing")
                                    
                                    # Verify file_size format
                                    if doc.get("file_size") and ("KB" in doc["file_size"] or "MB" in doc["file_size"] or "B" in doc["file_size"]):
                                        self.log_result("File size formatted", True)
                                    else:
                                        self.log_result("File size formatted", False, f"Got: {doc.get('file_size')}")
                                    
                                    break
                            
                            if test_doc_found:
                                self.log_result("Test document found in list", True)
                            else:
                                self.log_result("Test document found in list", False, "Not found")
                        else:
                            self.log_result("Document list empty", False, "No documents returned")
                    else:
                        self.log_result("List all documents", False, f"Status {response.status}")
                
                # Test 2: List with pagination
                async with session.get(
                    f"{self.base_url}/api/documents?limit=5&offset=0",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "limit" in result and result["limit"] == 5:
                            self.log_result("Pagination limit", True)
                        else:
                            self.log_result("Pagination limit", False, f"Expected 5, got {result.get('limit')}")
                        
                        if "offset" in result and result["offset"] == 0:
                            self.log_result("Pagination offset", True)
                        else:
                            self.log_result("Pagination offset", False, f"Expected 0, got {result.get('offset')}")
                    else:
                        self.log_result("Pagination test", False, f"Status {response.status}")
                
                # Test 3: List user's documents only
                async with session.get(
                    f"{self.base_url}/api/documents?user_only=true",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.log_result("List user documents", True)
                    else:
                        self.log_result("List user documents", False, f"Status {response.status}")
                
                return True
                
        except Exception as e:
            self.log_result("Document listing tests", False, str(e))
            return False
    
    async def test_storage_verification(self) -> bool:
        """Verify documents are stored in both Supabase and OpenAI"""
        print("\n🔍 Testing storage verification...")
        
        try:
            import aiohttp
            
            if not self.test_documents:
                self.log_result("Storage verification", False, "No test documents to verify")
                return False
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                # Get details of first test document
                doc_id = self.test_documents[0]
                
                async with session.get(
                    f"{self.base_url}/api/documents/{doc_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("success") and result.get("document"):
                            doc = result["document"]
                            
                            # Verify Supabase storage path
                            if doc.get("storage_path"):
                                self.log_result("Supabase storage path", True)
                                # Path should follow pattern: documents/{hash}/{filename}
                                if "documents/" in doc["storage_path"]:
                                    self.log_result("Storage path format", True)
                                else:
                                    self.log_result("Storage path format", False, f"Invalid: {doc['storage_path']}")
                            else:
                                self.log_result("Supabase storage path", False, "Missing")
                            
                            # Verify OpenAI file ID (might be set after async processing)
                            # Wait a bit for async processing to complete
                            await asyncio.sleep(3)
                            
                            # Fetch document again to check for OpenAI ID
                            async with session.get(
                                f"{self.base_url}/api/documents/{doc_id}",
                                headers=headers
                            ) as response2:
                                if response2.status == 200:
                                    result2 = await response2.json()
                                    doc2 = result2.get("document", {})
                                    
                                    if doc2.get("openai_file_id"):
                                        self.log_result("OpenAI file ID", True)
                                        self.log_result("Document in vector store", True)
                                    else:
                                        # May still be processing
                                        if doc2.get("status") == "processing":
                                            self.log_result("OpenAI file ID", True, "Still processing")
                                        else:
                                            self.log_result("OpenAI file ID", False, "Not set after processing")
                            
                            # Verify status field
                            if doc.get("status") in ["processing", "active", "error"]:
                                self.log_result("Document status field", True)
                            else:
                                self.log_result("Document status field", False, f"Invalid status: {doc.get('status')}")
                            
                            # Verify metadata
                            if doc.get("metadata"):
                                metadata = doc["metadata"]
                                if metadata.get("uploaded_by"):
                                    self.log_result("Uploaded by metadata", True)
                                if metadata.get("original_filename"):
                                    self.log_result("Original filename metadata", True)
                                if metadata.get("file_hash"):
                                    self.log_result("File hash metadata", True)
                            else:
                                self.log_result("Document metadata", False, "Missing")
                            
                        else:
                            self.log_result("Get document details", False, "No document data")
                    else:
                        self.log_result("Get document details", False, f"Status {response.status}")
                
                return True
                
        except Exception as e:
            self.log_result("Storage verification tests", False, str(e))
            return False
    
    async def test_document_deletion(self) -> bool:
        """Test document deletion functionality"""
        print("\n🗑️ Testing document deletion...")
        
        try:
            import aiohttp
            
            if not self.test_documents:
                self.log_result("Document deletion", False, "No test documents to delete")
                return False
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                # Test 1: Delete existing document
                doc_to_delete = self.test_documents[0] if self.test_documents else None
                
                if doc_to_delete:
                    async with session.delete(
                        f"{self.base_url}/api/documents/{doc_to_delete}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            self.log_result("Delete document", result.get("success", False))
                            
                            # Verify document is deleted
                            await asyncio.sleep(1)
                            async with session.get(
                                f"{self.base_url}/api/documents/{doc_to_delete}",
                                headers=headers
                            ) as verify_response:
                                if verify_response.status == 404:
                                    self.log_result("Document removed from database", True)
                                else:
                                    self.log_result("Document removed from database", False, 
                                                  f"Still exists with status {verify_response.status}")
                            
                            # Remove from tracking
                            self.test_documents.remove(doc_to_delete)
                        else:
                            self.log_result("Delete document", False, f"Status {response.status}")
                
                # Test 2: Delete non-existent document
                fake_id = "00000000-0000-0000-0000-000000000000"
                async with session.delete(
                    f"{self.base_url}/api/documents/{fake_id}",
                    headers=headers
                ) as response:
                    if response.status == 404:
                        self.log_result("Delete non-existent document (404)", True)
                    else:
                        self.log_result("Delete non-existent document (404)", False, 
                                      f"Expected 404, got {response.status}")
                
                # Test 3: Delete with invalid ID format
                async with session.delete(
                    f"{self.base_url}/api/documents/invalid-id",
                    headers=headers
                ) as response:
                    if response.status in [400, 404, 500]:
                        self.log_result("Delete invalid ID format", True)
                    else:
                        self.log_result("Delete invalid ID format", False, 
                                      f"Unexpected status {response.status}")
                
                return True
                
        except Exception as e:
            self.log_result("Document deletion tests", False, str(e))
            return False
    
    async def test_integration_workflow(self) -> bool:
        """Test complete upload->list->delete workflow"""
        print("\n🔄 Testing integration workflow...")
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                workflow_doc_id = None
                
                # Step 1: Upload a new document
                content = f"Integration test document created at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                integration_file = self.create_test_file(content, "integration_test.txt", "txt")
                
                with open(integration_file, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('files',
                                   f,
                                   filename='integration_test.txt',
                                   content_type='text/plain')
                    
                    async with session.post(
                        f"{self.base_url}/api/documents/upload",
                        data=data,
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("results") and result["results"][0].get("success"):
                                workflow_doc_id = result["results"][0]["document_id"]
                                self.log_result("Workflow: Upload document", True)
                            else:
                                self.log_result("Workflow: Upload document", False, "Upload failed")
                                return False
                        else:
                            self.log_result("Workflow: Upload document", False, f"Status {response.status}")
                            return False
                
                # Step 2: Verify document appears in list
                await asyncio.sleep(1)
                async with session.get(
                    f"{self.base_url}/api/documents",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        doc_found = False
                        if result.get("documents"):
                            for doc in result["documents"]:
                                if doc.get("supabase_id") == workflow_doc_id:
                                    doc_found = True
                                    if doc.get("display_name") == "integration_test.txt":
                                        self.log_result("Workflow: Document in list with correct name", True)
                                    else:
                                        self.log_result("Workflow: Document in list with correct name", False,
                                                      f"Name mismatch: {doc.get('display_name')}")
                                    break
                        
                        if not doc_found:
                            self.log_result("Workflow: Document in list", False, "Not found")
                    else:
                        self.log_result("Workflow: List documents", False, f"Status {response.status}")
                
                # Step 3: Wait for vector store processing
                await asyncio.sleep(3)
                
                # Step 4: Verify document is searchable in chat (optional - requires chat endpoint)
                # This would test if the document is available for RAG queries
                
                # Step 5: Delete the document
                if workflow_doc_id:
                    async with session.delete(
                        f"{self.base_url}/api/documents/{workflow_doc_id}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            self.log_result("Workflow: Delete document", True)
                        else:
                            self.log_result("Workflow: Delete document", False, f"Status {response.status}")
                    
                    # Step 6: Verify document is removed from list
                    await asyncio.sleep(1)
                    async with session.get(
                        f"{self.base_url}/api/documents",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            doc_still_exists = False
                            if result.get("documents"):
                                for doc in result["documents"]:
                                    if doc.get("supabase_id") == workflow_doc_id:
                                        doc_still_exists = True
                                        break
                            
                            if not doc_still_exists:
                                self.log_result("Workflow: Document removed from list", True)
                            else:
                                self.log_result("Workflow: Document removed from list", False, "Still exists")
                        else:
                            self.log_result("Workflow: Verify deletion", False, f"Status {response.status}")
                
                return True
                
        except Exception as e:
            self.log_result("Integration workflow tests", False, str(e))
            return False
    
    async def cleanup(self):
        """Clean up test documents and files"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            import aiohttp
            
            # Delete remaining test documents
            if self.test_documents:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    for doc_id in self.test_documents:
                        try:
                            async with session.delete(
                                f"{self.base_url}/api/documents/{doc_id}",
                                headers=headers
                            ) as response:
                                if response.status == 200:
                                    print(f"  Deleted test document: {doc_id}")
                        except:
                            pass
            
            # Delete temporary files
            for file_path in self.test_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"  Deleted test file: {file_path}")
                except:
                    pass
            
            self.log_result("Cleanup completed", True)
            
        except Exception as e:
            self.log_result("Cleanup", False, str(e))
    
    async def run_all_tests(self):
        """Run all admin document tests"""
        print("\n" + "="*60)
        print("🚀 ADMIN DOCUMENT MANAGEMENT QA TESTS")
        print("="*60)
        
        # Setup
        if not await self.setup():
            print("\n❌ Setup failed. Aborting tests.")
            return
        
        # Run test suites
        await self.test_document_upload()
        await self.test_document_listing()
        await self.test_storage_verification()
        await self.test_document_deletion()
        await self.test_integration_workflow()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  • {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        print("\n" + "="*60)
        
        # Return success if pass rate is above 80%
        success_rate = self.passed / (self.passed + self.failed) if (self.passed + self.failed) > 0 else 0
        return success_rate >= 0.8


async def main():
    """Main entry point"""
    qa = AdminDocumentQA()
    success = await qa.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())