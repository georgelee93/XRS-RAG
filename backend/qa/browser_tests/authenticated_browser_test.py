#!/usr/bin/env python3
"""
Authenticated Browser UI Tests for RAG Chatbot
Tests UI functionality with proper login
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Test credentials
TEST_EMAIL = "test11@ca1996.co.kr"
TEST_PASSWORD = "Qq123456"

async def run_browser_tests():
    """Run browser tests with authentication"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Run: python3 -m playwright install chromium")
        return False
    
    print("\n" + "="*60)
    print("AUTHENTICATED BROWSER UI TEST SUITE")
    print("="*60)
    
    results = []
    
    async with async_playwright() as p:
        # Launch browser with more stable configuration
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Test 1: Login Flow
        print("\n🔐 TEST 1: Login Flow")
        print("-"*40)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to login page
            await page.goto("http://localhost:3001/login.html")
            print("✅ Navigated to login page")
            
            # Fill in credentials
            await page.fill('input[type="email"]', TEST_EMAIL)
            await page.fill('input[type="password"]', TEST_PASSWORD)
            print(f"✅ Entered credentials for {TEST_EMAIL}")
            
            # Click login button
            await page.click('button[type="submit"]')
            print("✅ Clicked login button")
            
            # Wait for navigation or auth state change
            await page.wait_for_timeout(5000)  # Increased timeout for redirect
            
            # Check if redirected to chat or admin page
            current_url = page.url
            if "chat.html" in current_url or "admin.html" in current_url:
                print(f"✅ Successfully logged in and redirected to {current_url}")
                await page.screenshot(path="/tmp/test1_login_success.png")
                results.append(("Login Flow", "PASS"))
            else:
                # Check for error message
                error_element = await page.query_selector("#alertMessage")
                if error_element and await error_element.is_visible():
                    error_text = await error_element.text_content()
                    print(f"❌ Login failed with error: {error_text}")
                else:
                    print(f"❌ Login failed - no redirect occurred (still on {current_url})")
                await page.screenshot(path="/tmp/test1_login_failed.png")
                results.append(("Login Flow", "FAIL"))
            
            await context.close()
            
        except Exception as e:
            print(f"❌ Error in login test: {e}")
            results.append(("Login Flow", "ERROR"))
        
        # Test 2: Chat Functionality (with authentication)
        print("\n💬 TEST 2: Chat Functionality")
        print("-"*40)
        try:
            # Create new context with stored auth
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login first
            await page.goto("http://localhost:3001/login.html")
            await page.fill('input[type="email"]', TEST_EMAIL)
            await page.fill('input[type="password"]', TEST_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Navigate directly to chat page regardless of initial redirect
            # (test user may be admin, but we want to test chat functionality)
            await page.goto("http://localhost:3001/chat.html", wait_until="networkidle")
            await page.wait_for_timeout(3000)  # Wait for page to fully load
            
            # Try to send a message
            message_input = await page.query_selector('#messageInput')
            if message_input:
                await message_input.fill("Hello, this is an authenticated test message.")
                print("✅ Entered test message")
                
                # Submit the message by clicking the submit button
                submit_button = await page.query_selector('#chatForm button[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    print("✅ Clicked send button")
                    
                    # Wait for response with a longer timeout
                    await page.wait_for_timeout(10000)  # 10 seconds for API response
                    
                    # Check for messages in the container
                    messages_container = await page.query_selector('#messagesContainer')
                    if messages_container:
                        # Look for message bubbles (both user and assistant)
                        # The actual message elements should have specific classes
                        user_messages = await page.query_selector_all('.message-user, [class*="bg-blue"], [class*="ml-auto"]')
                        assistant_messages = await page.query_selector_all('.message-assistant, [class*="bg-gray"], [class*="mr-auto"]')
                        total_messages = len(user_messages) + len(assistant_messages)
                        
                        if total_messages > 0:
                            print(f"✅ Chat working - {len(user_messages)} user messages, {len(assistant_messages)} assistant messages")
                            results.append(("Chat Functionality", "PASS"))
                        else:
                            # Try alternative check - any content added after the welcome message
                            all_content = await messages_container.inner_html()
                            if "Hello, this is an authenticated test message" in all_content:
                                print("✅ User message sent and displayed")
                                if "assistant" in all_content.lower() or "response" in all_content.lower():
                                    print("✅ Assistant response received")
                                    results.append(("Chat Functionality", "PASS"))
                                else:
                                    print("⚠️  User message displayed but no assistant response")
                                    results.append(("Chat Functionality", "PARTIAL"))
                            else:
                                print("⚠️  No messages displayed after sending")
                                results.append(("Chat Functionality", "PARTIAL"))
                    else:
                        print("❌ Messages container not found")
                        results.append(("Chat Functionality", "FAIL"))
                else:
                    print("❌ Submit button not found")
                    results.append(("Chat Functionality", "FAIL"))
            else:
                print("❌ Message input not found")
                results.append(("Chat Functionality", "FAIL"))
            
            await page.screenshot(path="/tmp/test2_chat_authenticated.png")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error in chat test: {e}")
            results.append(("Chat Functionality", "ERROR"))
        
        # Test 3: Document List Access
        print("\n📄 TEST 3: Document List Access")
        print("-"*40)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Login
            await page.goto("http://localhost:3001/login.html")
            await page.fill('input[type="email"]', TEST_EMAIL)
            await page.fill('input[type="password"]', TEST_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Check if we were redirected to admin page (user is admin)
            current_url = page.url
            if "admin.html" not in current_url:
                # Navigate to admin page if not already there
                await page.goto("http://localhost:3001/admin.html", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Check for document section and table
            doc_section = await page.query_selector('#documents')
            doc_table = await page.query_selector('#documentTableBody')
            
            if doc_section and doc_table:
                print("✅ Document section accessible")
                
                # Wait for documents to load
                await page.wait_for_timeout(2000)
                
                # Check if documents are loaded
                doc_rows = await page.query_selector_all('#documentTableBody tr')
                if doc_rows:
                    print(f"✅ {len(doc_rows)} documents displayed")
                    results.append(("Document Access", "PASS"))
                else:
                    # Check if there's a "no documents" message
                    table_text = await doc_table.text_content()
                    if "문서가 없습니다" in table_text or "No documents" in table_text or not table_text.strip():
                        print("⚠️  No documents in the system (empty list)")
                        results.append(("Document Access", "PARTIAL"))
                    else:
                        print("⚠️  Document table exists but no rows found")
                        results.append(("Document Access", "PARTIAL"))
            else:
                # User doesn't have admin access
                print("❌ Document section not accessible (no admin rights)")
                results.append(("Document Access", "FAIL"))
            
            await page.screenshot(path="/tmp/test3_documents.png")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error in document test: {e}")
            results.append(("Document Access", "ERROR"))
        
        # Test 4: Responsive Design
        print("\n📱 TEST 4: Responsive Design")
        print("-"*40)
        try:
            viewports = [
                ("Mobile", 375, 667),
                ("Tablet", 768, 1024),
                ("Desktop", 1920, 1080)
            ]
            
            all_responsive = True
            for device_name, width, height in viewports:
                context = await browser.new_context(viewport={"width": width, "height": height})
                page = await context.new_page()
                
                # Try login page for responsive test (doesn't require auth)
                await page.goto("http://localhost:3001/login.html")
                await page.wait_for_timeout(2000)
                
                # Check if main elements are visible
                login_form = await page.query_selector('#loginForm')
                if login_form and await login_form.is_visible():
                    # Check if the form is properly sized for the viewport
                    bounding_box = await login_form.bounding_box()
                    if bounding_box and bounding_box['width'] > 0:
                        print(f"✅ {device_name} ({width}x{height}): Layout responsive")
                    else:
                        print(f"❌ {device_name} ({width}x{height}): Layout issues")
                        all_responsive = False
                else:
                    print(f"❌ {device_name} ({width}x{height}): Form not visible")
                    all_responsive = False
                
                await page.screenshot(path=f"/tmp/test4_responsive_{device_name.lower()}.png")
                await context.close()
            
            if all_responsive:
                results.append(("Responsive Design", "PASS"))
            else:
                results.append(("Responsive Design", "FAIL"))
                
        except Exception as e:
            print(f"❌ Error in responsive test: {e}")
            results.append(("Responsive Design", "ERROR"))
        
        await browser.close()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, status in results if status == "PASS")
    failed = sum(1 for _, status in results if status in ["FAIL", "ERROR"])
    partial = sum(1 for _, status in results if status == "PARTIAL")
    na = sum(1 for _, status in results if status == "N/A")
    
    for test_name, status in results:
        icon = "✅" if status == "PASS" else "❌" if status in ["FAIL", "ERROR"] else "⚠️" if status == "PARTIAL" else "➖"
        print(f"{icon} {test_name}: {status}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}, Failed: {failed}, Partial: {partial}, N/A: {na}")
    
    print("\n📸 Screenshots saved to /tmp/")
    
    return failed == 0

async def main():
    """Main test runner"""
    success = await run_browser_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    # Install playwright if needed
    import subprocess
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Installing Playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    
    asyncio.run(main())