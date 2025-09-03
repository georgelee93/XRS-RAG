#!/usr/bin/env python3
"""
Automated QA Tests for RAG Chatbot
Uses Playwright for browser automation
"""

import asyncio
import json
import time
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Page, expect


class RAGChatbotQA:
    """Automated QA test suite for RAG Chatbot"""
    
    def __init__(self, base_url: str = "http://localhost:3001", api_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.api_url = api_url
        self.results: List[Dict[str, Any]] = []
        self.page: Page = None
        self.browser = None
        self.context = None
        
    async def setup(self):
        """Initialize browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # Set to True for CI/CD
            slow_mo=500  # Slow down for visibility
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True
        )
        self.page = await self.context.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
    async def teardown(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
    
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}: {details}")
    
    # =========================
    # System Health Tests
    # =========================
    
    async def test_backend_health(self):
        """Test backend health endpoint"""
        try:
            response = await self.page.request.get(f"{self.api_url}/api/health")
            data = await response.json()
            passed = response.status == 200 and data.get("status") == "healthy"
            self.record_result("Backend Health", passed, f"Status: {response.status}")
            return passed
        except Exception as e:
            self.record_result("Backend Health", False, str(e))
            return False
    
    async def test_frontend_loads(self):
        """Test frontend loads without errors"""
        try:
            response = await self.page.goto(f"{self.base_url}/index.html")
            passed = response.status == 200
            
            # Check for critical elements
            await self.page.wait_for_selector("#chat-form", timeout=5000)
            
            self.record_result("Frontend Loads", passed, f"Status: {response.status}")
            return passed
        except Exception as e:
            self.record_result("Frontend Loads", False, str(e))
            return False
    
    # =========================
    # Document Management Tests
    # =========================
    
    async def test_document_upload(self):
        """Test document upload functionality"""
        try:
            # Navigate to the page
            await self.page.goto(f"{self.base_url}/index.html")
            
            # Wait for file input
            file_input = await self.page.wait_for_selector('input[type="file"]', timeout=5000)
            
            # Create a test file
            test_file = Path("/tmp/test_document.txt")
            test_file.write_text("This is a test document for QA automation.\nIt contains sample text for testing.")
            
            # Upload the file
            await file_input.set_input_files(str(test_file))
            
            # Click upload button (adjust selector as needed)
            upload_button = await self.page.query_selector('button:has-text("Upload")')
            if upload_button:
                await upload_button.click()
                
                # Wait for success message or document to appear in list
                await self.page.wait_for_selector('.success-message, .document-item', timeout=10000)
                
                self.record_result("Document Upload", True, "File uploaded successfully")
                return True
            else:
                self.record_result("Document Upload", False, "Upload button not found")
                return False
                
        except Exception as e:
            self.record_result("Document Upload", False, str(e))
            return False
    
    async def test_document_list(self):
        """Test document list display"""
        try:
            # Click on documents tab/button if exists
            docs_button = await self.page.query_selector('[data-tab="documents"], button:has-text("Documents")')
            if docs_button:
                await docs_button.click()
                await self.page.wait_for_timeout(1000)
            
            # Check for document list
            doc_list = await self.page.query_selector('.document-list, #documents-list, [data-documents]')
            
            if doc_list:
                # Count documents
                doc_items = await self.page.query_selector_all('.document-item, .doc-row, [data-document]')
                self.record_result("Document List", True, f"Found {len(doc_items)} documents")
                return True
            else:
                self.record_result("Document List", False, "Document list not found")
                return False
                
        except Exception as e:
            self.record_result("Document List", False, str(e))
            return False
    
    # =========================
    # Chat Interface Tests
    # =========================
    
    async def test_send_message(self):
        """Test sending a chat message"""
        try:
            # Find chat input
            chat_input = await self.page.wait_for_selector(
                'textarea[name="message"], input[name="message"], #message-input', 
                timeout=5000
            )
            
            # Type a message
            test_message = "Hello, this is a test message from QA automation"
            await chat_input.fill(test_message)
            
            # Submit the form
            submit_button = await self.page.query_selector('button[type="submit"], button:has-text("Send")')
            if submit_button:
                await submit_button.click()
            else:
                # Try pressing Enter
                await chat_input.press("Enter")
            
            # Wait for response
            await self.page.wait_for_selector('.assistant-message, .ai-message, [data-role="assistant"]', timeout=15000)
            
            # Verify message appears in chat
            messages = await self.page.query_selector_all('.message, .chat-message')
            
            self.record_result("Send Message", True, f"Message sent and response received")
            return True
            
        except Exception as e:
            self.record_result("Send Message", False, str(e))
            return False
    
    async def test_document_qa(self):
        """Test asking questions about uploaded documents"""
        try:
            # Send a question about documents
            chat_input = await self.page.wait_for_selector(
                'textarea[name="message"], input[name="message"], #message-input',
                timeout=5000
            )
            
            question = "What documents do you have access to?"
            await chat_input.fill(question)
            
            # Submit
            submit_button = await self.page.query_selector('button[type="submit"], button:has-text("Send")')
            if submit_button:
                await submit_button.click()
            else:
                await chat_input.press("Enter")
            
            # Wait for response
            await self.page.wait_for_timeout(5000)
            
            # Check if response mentions documents or files
            response_elements = await self.page.query_selector_all('.assistant-message, .ai-message')
            
            if response_elements:
                last_response = response_elements[-1]
                response_text = await last_response.inner_text()
                
                # Check if response is relevant
                has_context = any(word in response_text.lower() for word in ['document', 'file', 'upload', 'test'])
                
                self.record_result("Document Q&A", has_context, "AI can reference documents")
                return has_context
            
            self.record_result("Document Q&A", False, "No response received")
            return False
            
        except Exception as e:
            self.record_result("Document Q&A", False, str(e))
            return False
    
    # =========================
    # Performance Tests
    # =========================
    
    async def test_page_load_time(self):
        """Test page load performance"""
        try:
            start_time = time.time()
            response = await self.page.goto(f"{self.base_url}/index.html")
            load_time = time.time() - start_time
            
            # Wait for main content
            await self.page.wait_for_selector('#chat-form', timeout=5000)
            total_time = time.time() - start_time
            
            passed = total_time < 3.0  # 3 second threshold
            self.record_result(
                "Page Load Time", 
                passed, 
                f"Load time: {total_time:.2f}s (threshold: 3s)"
            )
            return passed
            
        except Exception as e:
            self.record_result("Page Load Time", False, str(e))
            return False
    
    async def test_api_response_time(self):
        """Test API response time"""
        try:
            start_time = time.time()
            response = await self.page.request.post(
                f"{self.api_url}/api/chat",
                data=json.dumps({
                    "message": "test",
                    "session_id": "qa_test_session"
                }),
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            passed = response_time < 10.0  # 10 second threshold for chat
            self.record_result(
                "API Response Time",
                passed,
                f"Response time: {response_time:.2f}s (threshold: 10s)"
            )
            return passed
            
        except Exception as e:
            self.record_result("API Response Time", False, str(e))
            return False
    
    # =========================
    # Error Handling Tests
    # =========================
    
    async def test_empty_message_handling(self):
        """Test handling of empty messages"""
        try:
            chat_input = await self.page.wait_for_selector(
                'textarea[name="message"], input[name="message"], #message-input',
                timeout=5000
            )
            
            # Clear input and try to send
            await chat_input.fill("")
            
            submit_button = await self.page.query_selector('button[type="submit"]')
            if submit_button:
                # Check if button is disabled
                is_disabled = await submit_button.get_attribute("disabled")
                
                if not is_disabled:
                    await submit_button.click()
                    
                    # Check for error message
                    await self.page.wait_for_timeout(1000)
                    error = await self.page.query_selector('.error-message, .alert-danger')
                    
                    passed = error is not None or is_disabled is not None
                    self.record_result("Empty Message Handling", passed, "Empty message prevented")
                    return passed
                else:
                    self.record_result("Empty Message Handling", True, "Submit disabled for empty message")
                    return True
            
            self.record_result("Empty Message Handling", False, "Submit button not found")
            return False
            
        except Exception as e:
            self.record_result("Empty Message Handling", False, str(e))
            return False
    
    # =========================
    # Main Test Runner
    # =========================
    
    async def run_all_tests(self):
        """Run all automated tests"""
        print("=" * 60)
        print("Starting RAG Chatbot QA Automation")
        print("=" * 60)
        
        await self.setup()
        
        try:
            # System Health Tests
            print("\n--- System Health Tests ---")
            await self.test_backend_health()
            await self.test_frontend_loads()
            
            # Performance Tests
            print("\n--- Performance Tests ---")
            await self.test_page_load_time()
            await self.test_api_response_time()
            
            # Document Management Tests
            print("\n--- Document Management Tests ---")
            await self.test_document_upload()
            await self.test_document_list()
            
            # Chat Interface Tests
            print("\n--- Chat Interface Tests ---")
            await self.test_send_message()
            await self.test_document_qa()
            
            # Error Handling Tests
            print("\n--- Error Handling Tests ---")
            await self.test_empty_message_handling()
            
        finally:
            await self.teardown()
            
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("QA AUTOMATION REPORT")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        # Save report to file
        report_file = Path("qa_report.json")
        report_file.write_text(json.dumps(self.results, indent=2))
        print(f"\nDetailed report saved to: {report_file}")


async def main():
    """Main entry point"""
    qa = RAGChatbotQA()
    await qa.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())