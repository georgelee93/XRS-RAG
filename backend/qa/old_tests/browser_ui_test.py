#!/usr/bin/env python3
"""
Browser UI Test Suite for RAG Chatbot
Tests the actual web interface using Playwright browser automation
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from playwright.async_api import async_playwright, Page, expect


class BrowserUITest:
    """Test the actual browser UI of RAG Chatbot"""
    
    def __init__(self):
        self.base_url = "http://localhost:3001"
        self.test_session_id = str(uuid.uuid4())
        self.test_results = []
        self.page: Page = None
        self.browser = None
        self.context = None
        self.playwright = None
        
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {details}")
    
    async def setup(self):
        """Initialize browser"""
        try:
            self.playwright = await async_playwright().start()
            # Use headless mode for stability
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Run headless for stability
                slow_mo=100  # Small delay between actions
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            self.page = await self.context.new_page()
            
            # Enable console logging
            self.page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
            
            print("✅ Browser launched successfully (headless mode)")
            return True
        except Exception as e:
            print(f"❌ Failed to launch browser: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def teardown(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    # ========================================
    # TEST 1: Navigate to Chat Page
    # ========================================
    
    async def test_navigate_to_chat(self):
        """Test navigation to chat page"""
        print("\n🌐 TEST 1: Navigate to Chat Page")
        print("-" * 50)
        
        try:
            # Go to chat page
            await self.page.goto(f"{self.base_url}/chat.html")
            
            # Wait for chat form to load
            chat_form = await self.page.wait_for_selector("#chatForm", timeout=5000)
            
            if chat_form:
                # Take screenshot
                await self.page.screenshot(path="/tmp/chat_page_loaded.png")
                self.record_test("Navigate to Chat", True, "Chat page loaded successfully")
                return True
            else:
                self.record_test("Navigate to Chat", False, "Chat form not found")
                return False
                
        except Exception as e:
            self.record_test("Navigate to Chat", False, str(e))
            return False
    
    # ========================================
    # TEST 2: Send Chat Message
    # ========================================
    
    async def test_send_chat_message(self):
        """Test sending a message through the chat interface"""
        print("\n💬 TEST 2: Send Chat Message")
        print("-" * 50)
        
        try:
            # Find message input
            message_input = await self.page.query_selector('textarea[name="message"], #userMessage')
            
            if not message_input:
                self.record_test("Send Chat Message", False, "Message input not found")
                return False
            
            # Type a test message
            test_message = "Hello, this is an automated UI test. What documents do you have?"
            await message_input.fill(test_message)
            print(f"   Typed: '{test_message}'")
            
            # Find and click send button
            send_button = await self.page.query_selector('button[type="submit"]')
            if send_button:
                await send_button.click()
                print("   Clicked send button")
            else:
                # Try pressing Enter
                await message_input.press("Enter")
                print("   Pressed Enter to send")
            
            # Wait for AI response (with longer timeout for AI processing)
            print("   Waiting for AI response...")
            
            # Wait for a response message to appear
            response_selector = '.assistant-message, .ai-message, [data-role="assistant"], .message-assistant'
            
            try:
                await self.page.wait_for_selector(response_selector, timeout=30000)
                
                # Get the response text
                response_elements = await self.page.query_selector_all(response_selector)
                if response_elements:
                    last_response = response_elements[-1]
                    response_text = await last_response.inner_text()
                    
                    # Take screenshot of conversation
                    await self.page.screenshot(path="/tmp/chat_conversation.png")
                    
                    self.record_test(
                        "Send Chat Message", 
                        True, 
                        f"Response received: {response_text[:100]}..."
                    )
                    return True
                else:
                    self.record_test("Send Chat Message", False, "No response element found")
                    return False
                    
            except Exception as timeout_error:
                await self.page.screenshot(path="/tmp/chat_timeout.png")
                self.record_test("Send Chat Message", False, f"Timeout waiting for response: {timeout_error}")
                return False
                
        except Exception as e:
            self.record_test("Send Chat Message", False, str(e))
            return False
    
    # ========================================
    # TEST 3: Navigate to Admin Page
    # ========================================
    
    async def test_navigate_to_admin(self):
        """Test navigation to admin page for document management"""
        print("\n📂 TEST 3: Navigate to Admin Page")
        print("-" * 50)
        
        try:
            # Go to admin page
            await self.page.goto(f"{self.base_url}/admin.html")
            
            # Wait for document section
            doc_section = await self.page.wait_for_selector("#documentsSection, .documents-container", timeout=5000)
            
            if doc_section:
                await self.page.screenshot(path="/tmp/admin_page.png")
                self.record_test("Navigate to Admin", True, "Admin page loaded")
                return True
            else:
                self.record_test("Navigate to Admin", False, "Document section not found")
                return False
                
        except Exception as e:
            self.record_test("Navigate to Admin", False, str(e))
            return False
    
    # ========================================
    # TEST 4: Upload Document
    # ========================================
    
    async def test_document_upload(self):
        """Test document upload through the web interface"""
        print("\n📤 TEST 4: Document Upload")
        print("-" * 50)
        
        try:
            # Create a test file
            test_content = """
            UI Test Document
            ================
            Test ID: UI_TEST_2025
            This document was uploaded through browser automation.
            It should be searchable through the chat interface.
            """
            
            test_file_path = "/tmp/ui_test_document.txt"
            with open(test_file_path, 'w') as f:
                f.write(test_content)
            
            # Find file input
            file_input = await self.page.query_selector('input[type="file"]')
            
            if not file_input:
                self.record_test("Document Upload", False, "File input not found")
                return False
            
            # Set the file
            await file_input.set_input_files(test_file_path)
            print(f"   Selected file: {test_file_path}")
            
            # Find and click upload button
            upload_button = await self.page.query_selector('button:has-text("Upload"), button:has-text("업로드")')
            
            if upload_button:
                await upload_button.click()
                print("   Clicked upload button")
                
                # Wait for success message or document to appear
                try:
                    await self.page.wait_for_selector(
                        '.success-message, .alert-success, .document-item',
                        timeout=10000
                    )
                    
                    await self.page.screenshot(path="/tmp/document_uploaded.png")
                    self.record_test("Document Upload", True, "Document uploaded successfully")
                    return True
                    
                except:
                    self.record_test("Document Upload", False, "No success indication after upload")
                    return False
            else:
                self.record_test("Document Upload", False, "Upload button not found")
                return False
                
        except Exception as e:
            self.record_test("Document Upload", False, str(e))
            return False
    
    # ========================================
    # TEST 5: Check Document List
    # ========================================
    
    async def test_document_list(self):
        """Test if documents are displayed in the list"""
        print("\n📋 TEST 5: Document List")
        print("-" * 50)
        
        try:
            # Refresh to ensure latest data
            await self.page.reload()
            await self.page.wait_for_timeout(2000)
            
            # Look for document items
            doc_items = await self.page.query_selector_all(
                '.document-item, .doc-row, tr[data-document], .file-item'
            )
            
            if doc_items and len(doc_items) > 0:
                # Count and display info
                doc_count = len(doc_items)
                
                # Get first document's text
                first_doc = doc_items[0]
                doc_text = await first_doc.inner_text()
                
                await self.page.screenshot(path="/tmp/document_list.png")
                
                self.record_test(
                    "Document List",
                    True,
                    f"Found {doc_count} documents. First: {doc_text[:50]}..."
                )
                return True
            else:
                self.record_test("Document List", False, "No documents found in list")
                return False
                
        except Exception as e:
            self.record_test("Document List", False, str(e))
            return False
    
    # ========================================
    # TEST 6: Test Document Retrieval in Chat
    # ========================================
    
    async def test_document_retrieval_in_chat(self):
        """Test if chat can retrieve info from uploaded document"""
        print("\n🔍 TEST 6: Document Retrieval in Chat")
        print("-" * 50)
        
        try:
            # Go back to chat page
            await self.page.goto(f"{self.base_url}/chat.html")
            await self.page.wait_for_selector("#chatForm", timeout=5000)
            
            # Ask about the test document
            message_input = await self.page.query_selector('textarea[name="message"], #userMessage')
            
            if not message_input:
                self.record_test("Document Retrieval", False, "Message input not found")
                return False
            
            # Ask about specific content from test document
            test_query = "What is the Test ID mentioned in the UI Test Document?"
            await message_input.fill(test_query)
            print(f"   Asked: '{test_query}'")
            
            # Send the message
            send_button = await self.page.query_selector('button[type="submit"]')
            if send_button:
                await send_button.click()
            else:
                await message_input.press("Enter")
            
            # Wait for response
            print("   Waiting for AI to retrieve document info...")
            
            try:
                await self.page.wait_for_selector(
                    '.assistant-message, .ai-message, [data-role="assistant"]',
                    timeout=30000
                )
                
                # Get all responses
                response_elements = await self.page.query_selector_all(
                    '.assistant-message, .ai-message, [data-role="assistant"]'
                )
                
                if response_elements:
                    # Get the last response
                    last_response = response_elements[-1]
                    response_text = await last_response.inner_text()
                    
                    # Check if response contains the test ID
                    contains_test_id = "UI_TEST_2025" in response_text
                    
                    await self.page.screenshot(path="/tmp/document_retrieval.png")
                    
                    self.record_test(
                        "Document Retrieval",
                        contains_test_id,
                        "AI found document content" if contains_test_id else "Document content not retrieved"
                    )
                    return contains_test_id
                    
            except:
                self.record_test("Document Retrieval", False, "Timeout waiting for response")
                return False
                
        except Exception as e:
            self.record_test("Document Retrieval", False, str(e))
            return False
    
    # ========================================
    # TEST 7: Test Responsive Design
    # ========================================
    
    async def test_responsive_design(self):
        """Test UI on different screen sizes"""
        print("\n📱 TEST 7: Responsive Design")
        print("-" * 50)
        
        try:
            viewports = [
                {"name": "Mobile", "width": 375, "height": 667},
                {"name": "Tablet", "width": 768, "height": 1024},
                {"name": "Desktop", "width": 1920, "height": 1080}
            ]
            
            all_responsive = True
            
            for viewport in viewports:
                # Set viewport size
                await self.page.set_viewport_size(
                    {"width": viewport["width"], "height": viewport["height"]}
                )
                
                # Navigate to chat
                await self.page.goto(f"{self.base_url}/chat.html")
                
                # Check if chat form is visible
                chat_form = await self.page.query_selector("#chatForm")
                
                if chat_form:
                    is_visible = await chat_form.is_visible()
                    
                    # Take screenshot
                    filename = f"/tmp/responsive_{viewport['name'].lower()}.png"
                    await self.page.screenshot(path=filename)
                    
                    self.record_test(
                        f"Responsive - {viewport['name']}",
                        is_visible,
                        f"{viewport['width']}x{viewport['height']} - {'OK' if is_visible else 'Failed'}"
                    )
                    
                    if not is_visible:
                        all_responsive = False
                else:
                    self.record_test(f"Responsive - {viewport['name']}", False, "Chat form not found")
                    all_responsive = False
            
            return all_responsive
            
        except Exception as e:
            self.record_test("Responsive Design", False, str(e))
            return False
    
    # ========================================
    # Main Test Runner
    # ========================================
    
    async def run_all_tests(self):
        """Run all browser UI tests"""
        print("=" * 60)
        print("BROWSER UI TEST SUITE FOR RAG CHATBOT")
        print("=" * 60)
        print()
        print("Testing the actual web interface with browser automation")
        print()
        
        # Setup browser
        if not await self.setup():
            print("Failed to setup browser. Exiting.")
            return
        
        try:
            # Run tests
            await self.test_navigate_to_chat()
            await self.test_send_chat_message()
            await self.test_navigate_to_admin()
            await self.test_document_upload()
            await self.test_document_list()
            await self.test_document_retrieval_in_chat()
            await self.test_responsive_design()
            
        finally:
            # Always cleanup
            await self.teardown()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("BROWSER UI TEST REPORT")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        if passed == total:
            print("\n🎉 All browser UI tests passed!")
            print("\nScreenshots saved in /tmp/:")
            print("  - chat_page_loaded.png")
            print("  - chat_conversation.png")
            print("  - admin_page.png")
            print("  - document_uploaded.png")
            print("  - document_list.png")
            print("  - document_retrieval.png")
            print("  - responsive_*.png")
        
        # Save detailed report
        report_file = Path("browser_ui_test_report.json")
        report_file.write_text(json.dumps(self.test_results, indent=2))
        print(f"\nDetailed report saved to: {report_file}")


async def main():
    """Main entry point"""
    tester = BrowserUITest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())