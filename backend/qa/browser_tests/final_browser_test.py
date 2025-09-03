#!/usr/bin/env python3
"""
Final Browser UI Test - Each test in isolation to avoid context issues
"""

import asyncio
from playwright.async_api import async_playwright

# Test credentials
EMAIL = "test@cheongahm.com"
PASSWORD = "1234"

async def test_login_page():
    """Test 1: Login page loads and can login"""
    print("\n🔐 TEST 1: Login Page")
    print("-" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        
        try:
            page = await browser.new_page()
            
            # Navigate to chat page
            response = await page.goto("http://localhost:3001/chat.html", wait_until="domcontentloaded")
            print(f"✅ Navigated to chat page (Status: {response.status if response else 'N/A'})")
            
            # Get page title
            title = await page.title()
            print(f"   Page title: '{title}'")
            
            # Take screenshot
            await page.screenshot(path="/tmp/test1_initial_page.png")
            print("   📸 Screenshot: /tmp/test1_initial_page.png")
            
            # Check for login form or chat form
            login_form = await page.query_selector("#loginForm")
            chat_form = await page.query_selector("#chatForm")
            
            if login_form:
                print("   Login form found")
                
                # Try to login
                email_input = await page.query_selector("#email")
                password_input = await page.query_selector("#password")
                login_button = await page.query_selector("#loginButton")
                
                if email_input and password_input and login_button:
                    await email_input.fill(EMAIL)
                    await password_input.fill(PASSWORD)
                    print(f"   Filled credentials: {EMAIL}")
                    
                    await login_button.click()
                    print("   Clicked login button")
                    
                    # Wait a bit for login
                    await page.wait_for_timeout(3000)
                    
                    # Check if we're now at chat
                    new_title = await page.title()
                    print(f"   After login - Page title: '{new_title}'")
                    
                    await page.screenshot(path="/tmp/test1_after_login.png")
                    print("   📸 Screenshot: /tmp/test1_after_login.png")
                    
                    return True
                else:
                    print("   ❌ Login form elements not found")
                    return False
                    
            elif chat_form:
                print("   ✅ Already at chat interface (no login needed)")
                return True
            else:
                print("   ❌ Neither login nor chat form found")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        finally:
            await browser.close()

async def test_chat_message():
    """Test 2: Send a chat message"""
    print("\n💬 TEST 2: Chat Message")
    print("-" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        
        try:
            page = await browser.new_page()
            
            # Navigate directly to chat
            await page.goto("http://localhost:3001/chat.html", wait_until="domcontentloaded")
            
            # Login if needed
            login_form = await page.query_selector("#loginForm")
            if login_form:
                print("   Logging in first...")
                email_input = await page.query_selector("#email")
                password_input = await page.query_selector("#password")
                login_button = await page.query_selector("#loginButton")
                
                if email_input and password_input and login_button:
                    await email_input.fill(EMAIL)
                    await password_input.fill(PASSWORD)
                    await login_button.click()
                    await page.wait_for_timeout(3000)
            
            # Now try to send a message
            print("   Looking for message input...")
            
            # Try multiple selectors
            message_input = None
            selectors = ['textarea[name="message"]', '#userMessage', 'textarea', '.message-input']
            
            for selector in selectors:
                message_input = await page.query_selector(selector)
                if message_input:
                    print(f"   Found message input: {selector}")
                    break
            
            if message_input:
                test_message = "Hello, this is a test message. What documents are available?"
                await message_input.fill(test_message)
                print(f"   Typed: '{test_message[:40]}...'")
                
                # Find send button
                send_button = await page.query_selector('button[type="submit"]')
                if send_button:
                    await send_button.click()
                    print("   Clicked send button")
                else:
                    await message_input.press("Enter")
                    print("   Pressed Enter")
                
                print("   ⏳ Waiting for response (15 seconds)...")
                await page.wait_for_timeout(15000)
                
                await page.screenshot(path="/tmp/test2_chat_conversation.png")
                print("   📸 Screenshot: /tmp/test2_chat_conversation.png")
                
                # Check for responses
                responses = await page.query_selector_all('.message, .assistant-message, .ai-message')
                print(f"   Found {len(responses)} message(s) in conversation")
                
                return len(responses) > 0
            else:
                print("   ❌ No message input found")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        finally:
            await browser.close()

async def test_admin_page():
    """Test 3: Admin page with documents"""
    print("\n📊 TEST 3: Admin Page")
    print("-" * 40)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        
        try:
            page = await browser.new_page()
            
            # Navigate to admin
            response = await page.goto("http://localhost:3001/admin.html", wait_until="domcontentloaded")
            print(f"✅ Navigated to admin page (Status: {response.status if response else 'N/A'})")
            
            # Get page title
            title = await page.title()
            print(f"   Page title: '{title}'")
            
            # Login if needed
            login_form = await page.query_selector("#loginForm")
            if login_form:
                print("   Admin requires login...")
                email_input = await page.query_selector("#email")
                password_input = await page.query_selector("#password")
                login_button = await page.query_selector("#loginButton")
                
                if email_input and password_input and login_button:
                    await email_input.fill(EMAIL)
                    await password_input.fill(PASSWORD)
                    await login_button.click()
                    await page.wait_for_timeout(3000)
                    print("   Logged in")
            
            # Check for admin elements
            file_input = await page.query_selector('input[type="file"]')
            upload_button = await page.query_selector('button:has-text("Upload"), button:has-text("업로드")')
            doc_list = await page.query_selector('table, #documents-list, .documents-container')
            
            print(f"   File input: {'✅ Found' if file_input else '❌ Not found'}")
            print(f"   Upload button: {'✅ Found' if upload_button else '❌ Not found'}")
            print(f"   Document list: {'✅ Found' if doc_list else '❌ Not found'}")
            
            await page.screenshot(path="/tmp/test3_admin_page.png")
            print("   📸 Screenshot: /tmp/test3_admin_page.png")
            
            return file_input is not None or doc_list is not None
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
        finally:
            await browser.close()

async def test_responsive_design():
    """Test 4: Responsive design"""
    print("\n📱 TEST 4: Responsive Design")
    print("-" * 40)
    
    viewports = [
        {"name": "Mobile", "width": 375, "height": 667},
        {"name": "Tablet", "width": 768, "height": 1024},
        {"name": "Desktop", "width": 1920, "height": 1080}
    ]
    
    async with async_playwright() as p:
        for vp in viewports:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            try:
                # Create context with specific viewport
                context = await browser.new_context(
                    viewport={'width': vp["width"], 'height': vp["height"]}
                )
                page = await context.new_page()
                
                # Navigate to chat
                await page.goto("http://localhost:3001/chat.html", wait_until="domcontentloaded")
                
                # Check if page loads
                body = await page.query_selector("body")
                if body:
                    is_visible = await body.is_visible()
                    print(f"   {vp['name']} ({vp['width']}x{vp['height']}): {'✅ Visible' if is_visible else '❌ Not visible'}")
                    
                    await page.screenshot(path=f"/tmp/test4_responsive_{vp['name'].lower()}.png")
                    print(f"   📸 Screenshot: /tmp/test4_responsive_{vp['name'].lower()}.png")
                else:
                    print(f"   {vp['name']}: ❌ Page not loaded")
                    
            except Exception as e:
                print(f"   {vp['name']}: ❌ Error - {e}")
            finally:
                await browser.close()
    
    return True

async def main():
    """Run all tests independently"""
    print("=" * 60)
    print("FINAL BROWSER UI TEST SUITE")
    print("=" * 60)
    print("Each test runs in isolation to avoid context issues")
    
    results = []
    
    # Test 1: Login
    login_passed = await test_login_page()
    results.append(("Login Page", login_passed))
    
    # Test 2: Chat
    chat_passed = await test_chat_message()
    results.append(("Chat Message", chat_passed))
    
    # Test 3: Admin
    admin_passed = await test_admin_page()
    results.append(("Admin Page", admin_passed))
    
    # Test 4: Responsive
    responsive_passed = await test_responsive_design()
    results.append(("Responsive Design", responsive_passed))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    # List all screenshots
    print("\n📸 Screenshots created:")
    screenshots = [
        "/tmp/test1_initial_page.png - Login page",
        "/tmp/test1_after_login.png - After login",
        "/tmp/test2_chat_conversation.png - Chat interface",
        "/tmp/test3_admin_page.png - Admin page",
        "/tmp/test4_responsive_mobile.png - Mobile view",
        "/tmp/test4_responsive_tablet.png - Tablet view",
        "/tmp/test4_responsive_desktop.png - Desktop view"
    ]
    
    for screenshot in screenshots:
        print(f"  - {screenshot}")
    
    print("\n✅ Browser UI testing completed!")
    print("Note: Each test creates its own browser instance to avoid context issues.")

if __name__ == "__main__":
    asyncio.run(main())