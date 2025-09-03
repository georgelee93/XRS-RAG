#!/usr/bin/env python3
"""
Frontend Admin UI Test using Playwright
Tests the actual browser interface to ensure documents are displayed correctly
"""

import asyncio
import os
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Any
import json
import aiohttp
from datetime import datetime

class AdminUITester:
    def __init__(self):
        self.frontend_url = "http://localhost:3000"
        self.backend_url = "http://localhost:8080"
        self.test_results = []
        self.browser: Browser = None
        self.page: Page = None
        
    def record_test(self, test_name: str, passed: bool, details: str):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {details}")
    
    async def setup_browser(self):
        """Initialize browser and page"""
        self.playwright = await async_playwright().start()
        
        # Try different browser launch configurations
        launch_configs = [
            {'headless': True, 'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']},
            {'headless': False, 'args': ['--no-sandbox']},
            {'headless': True}
        ]
        
        for config in launch_configs:
            try:
                self.browser = await self.playwright.chromium.launch(**config)
                break
            except Exception as e:
                print(f"Failed with config {config}: {e}")
                continue
        
        if not self.browser:
            raise Exception("Could not launch browser with any configuration")
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        self.page = await context.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        
        # Enable error logging
        self.page.on("pageerror", lambda exc: print(f"Browser error: {exc}"))
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
        except:
            pass
        
        try:
            if self.browser:
                await self.browser.close()
        except:
            pass
        
        try:
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except:
            pass
    
    async def test_admin_page_loads(self) -> bool:
        """Test if admin page loads successfully"""
        try:
            # Navigate to admin page
            response = await self.page.goto(f"{self.frontend_url}/public/admin.html", 
                                           wait_until="networkidle")
            
            if response.status != 200:
                self.record_test("Admin Page Load", False, f"Status {response.status}")
                return False
            
            # Wait for page to be fully loaded
            await self.page.wait_for_load_state("domcontentloaded")
            
            # Check if the main container exists
            admin_container = await self.page.query_selector("#adminApp")
            
            if admin_container:
                self.record_test("Admin Page Load", True, "Page loaded successfully")
                return True
            else:
                self.record_test("Admin Page Load", False, "Admin container not found")
                return False
                
        except Exception as e:
            self.record_test("Admin Page Load", False, str(e))
            return False
    
    async def test_document_table_exists(self) -> bool:
        """Test if document table exists on the page"""
        try:
            # Wait for document table to appear
            table_selector = "#documentTableBody"
            await self.page.wait_for_selector(table_selector, timeout=5000)
            
            table_element = await self.page.query_selector(table_selector)
            
            if table_element:
                self.record_test("Document Table Exists", True, "Table element found")
                return True
            else:
                self.record_test("Document Table Exists", False, "Table element not found")
                return False
                
        except Exception as e:
            self.record_test("Document Table Exists", False, f"Timeout or error: {e}")
            return False
    
    async def test_api_call_made(self) -> bool:
        """Test if the admin page makes the API call to fetch documents"""
        try:
            # Set up request interception
            api_called = False
            api_response = None
            
            async def handle_response(response):
                nonlocal api_called, api_response
                if "/api/documents" in response.url:
                    api_called = True
                    try:
                        api_response = await response.json()
                    except:
                        api_response = await response.text()
            
            self.page.on("response", handle_response)
            
            # Reload the page to trigger API calls
            await self.page.reload(wait_until="networkidle")
            
            # Wait a bit for API calls
            await asyncio.sleep(2)
            
            if api_called:
                self.record_test("API Call Made", True, f"API called, response type: {type(api_response)}")
                return True
            else:
                self.record_test("API Call Made", False, "No API call to /api/documents detected")
                return False
                
        except Exception as e:
            self.record_test("API Call Made", False, str(e))
            return False
    
    async def test_documents_displayed(self) -> bool:
        """Test if documents are actually displayed in the table"""
        try:
            # First, get the expected documents from the API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/api/documents") as response:
                    api_data = await response.json()
                    expected_docs = api_data.get("documents", []) if isinstance(api_data, dict) else api_data
            
            expected_count = len(expected_docs)
            
            # Wait for table to be populated
            await asyncio.sleep(2)
            
            # Count rows in the document table
            rows = await self.page.query_selector_all("#documentTableBody tr")
            actual_count = len(rows)
            
            # Check for empty state message
            empty_message = await self.page.query_selector(".empty-state")
            
            if expected_count > 0:
                if actual_count > 0:
                    # Check if the count matches
                    if actual_count == expected_count:
                        self.record_test(
                            "Documents Displayed", 
                            True, 
                            f"All {actual_count} documents displayed correctly"
                        )
                    else:
                        self.record_test(
                            "Documents Displayed", 
                            False, 
                            f"Count mismatch: Expected {expected_count}, got {actual_count}"
                        )
                    
                    # Check first document details
                    if expected_docs:
                        first_doc = expected_docs[0]
                        first_row = rows[0]
                        
                        # Check if filename is displayed
                        filename_elem = await first_row.query_selector("td:nth-child(3)")
                        if filename_elem:
                            filename_text = await filename_elem.inner_text()
                            expected_name = first_doc.get("display_name", "")
                            
                            if expected_name in filename_text:
                                self.record_test(
                                    "Document Content Correct", 
                                    True, 
                                    f"First document name matches: {expected_name}"
                                )
                            else:
                                self.record_test(
                                    "Document Content Correct", 
                                    False, 
                                    f"Name mismatch: Expected '{expected_name}', got '{filename_text}'"
                                )
                    
                    return actual_count > 0
                    
                elif empty_message:
                    empty_text = await empty_message.inner_text()
                    self.record_test(
                        "Documents Displayed", 
                        False, 
                        f"Empty state shown despite {expected_count} documents in API. Message: {empty_text}"
                    )
                    return False
                else:
                    self.record_test(
                        "Documents Displayed", 
                        False, 
                        f"No documents shown, expected {expected_count}"
                    )
                    return False
            else:
                # No documents expected
                if empty_message:
                    self.record_test(
                        "Documents Displayed", 
                        True, 
                        "Correctly showing empty state (no documents)"
                    )
                    return True
                else:
                    self.record_test(
                        "Documents Displayed", 
                        actual_count == 0, 
                        f"Expected no documents, found {actual_count} rows"
                    )
                    return actual_count == 0
                    
        except Exception as e:
            self.record_test("Documents Displayed", False, str(e))
            return False
    
    async def test_console_errors(self) -> bool:
        """Check for JavaScript errors in the console"""
        try:
            # Collect console errors
            console_errors = []
            
            def handle_console(msg):
                if msg.type in ["error", "warning"]:
                    console_errors.append({
                        "type": msg.type,
                        "text": msg.text
                    })
            
            self.page.on("console", handle_console)
            
            # Reload page to capture all console messages
            await self.page.reload(wait_until="networkidle")
            await asyncio.sleep(2)
            
            if console_errors:
                self.record_test(
                    "No Console Errors", 
                    False, 
                    f"Found {len(console_errors)} errors: {console_errors[:3]}"
                )
                
                # Print detailed errors
                print("\n🔴 Console Errors Details:")
                for error in console_errors[:5]:
                    print(f"  - {error['type']}: {error['text']}")
                
                return False
            else:
                self.record_test("No Console Errors", True, "No JavaScript errors found")
                return True
                
        except Exception as e:
            self.record_test("No Console Errors", False, str(e))
            return False
    
    async def take_screenshot(self, name: str):
        """Take a screenshot for debugging"""
        try:
            screenshot_path = f"qa/screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            await self.page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"Failed to take screenshot: {e}")
    
    async def run_tests(self):
        """Run all admin UI tests"""
        print("="*60)
        print("ADMIN UI FRONTEND TEST")
        print("="*60)
        
        try:
            await self.setup_browser()
            
            # Test 1: Page loads
            print("\n🔍 Test 1: Admin Page Load")
            await self.test_admin_page_loads()
            
            # Test 2: Document table exists
            print("\n🔍 Test 2: Document Table Structure")
            await self.test_document_table_exists()
            
            # Test 3: API call is made
            print("\n🔍 Test 3: API Integration")
            await self.test_api_call_made()
            
            # Test 4: Documents are displayed
            print("\n🔍 Test 4: Document Display")
            await self.test_documents_displayed()
            
            # Test 5: Check for console errors
            print("\n🔍 Test 5: JavaScript Errors")
            await self.test_console_errors()
            
            # Take a screenshot for debugging
            await self.take_screenshot("admin_page_final")
            
        finally:
            await self.cleanup()
        
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
        
        # Save results to file
        with open("qa/frontend_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
            print(f"\nDetailed results saved to: qa/frontend_test_results.json")
        
        return self.test_results


async def main():
    tester = AdminUITester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())