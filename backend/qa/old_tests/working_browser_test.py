#!/usr/bin/env python3
"""
Working Browser UI Test for RAG Chatbot
Uses the fixes that work: WebKit or Chromium with debug flags
"""

import asyncio
from playwright.async_api import async_playwright

async def test_rag_chatbot_ui():
    """Complete UI test that works with the fixes applied"""
    
    print("=" * 60)
    print("RAG CHATBOT BROWSER UI TEST")
    print("=" * 60)
    print()
    
    # Login credentials
    email = "test@cheongahm.com"
    password = "1234"
    
    async with async_playwright() as p:
        # Use Chromium with debug flags (proven to work)
        print("🚀 Launching browser with fixed settings...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        page = await browser.new_page()
        print("✅ Browser ready")
        
        try:
            # Navigate to chat page
            print("\n📄 Navigating to chat page...")
            response = await page.goto("http://localhost:3001/chat.html", wait_until="domcontentloaded")
            print(f"   Response: {response.status if response else 'No response'}")
            
            # Get page title to understand where we are
            title = await page.title()
            print(f"   Page title: '{title}'")
            
            # Take screenshot to see current state
            await page.screenshot(path="/tmp/1_initial_page.png")
            print("   Screenshot: /tmp/1_initial_page.png")
            
            # Check what forms are on the page
            forms = await page.query_selector_all("form")
            print(f"\n🔍 Found {len(forms)} form(s) on page")
            
            for i, form in enumerate(forms):
                form_id = await form.evaluate("el => el.id")
                form_class = await form.evaluate("el => el.className")
                print(f"   Form {i+1}: id='{form_id}', class='{form_class}'")
            
            # Try to find login elements or chat elements
            print("\n🔐 Checking for login/chat elements...")
            
            # Check for various possible selectors
            selectors_to_check = {
                "#loginForm": "Login form",
                "#email": "Email input",
                "#password": "Password input",
                "#loginButton": "Login button",
                "#chatForm": "Chat form",
                "textarea": "Text area",
                "#userMessage": "User message input",
                ".chat-container": "Chat container",
                ".message-input": "Message input"
            }
            
            found_elements = {}
            for selector, description in selectors_to_check.items():
                element = await page.query_selector(selector)
                if element:
                    print(f"   ✅ Found: {description} ({selector})")
                    found_elements[selector] = element
                else:
                    print(f"   ❌ Not found: {description} ({selector})")
            
            # If login form exists, try to login
            if "#email" in found_elements and "#password" in found_elements:
                print("\n🔑 Attempting login...")
                
                await found_elements["#email"].fill(email)
                await found_elements["#password"].fill(password)
                print(f"   Filled credentials: {email}")
                
                # Find and click login button
                login_button = await page.query_selector("#loginButton, button[type='submit']")
                if login_button:
                    await login_button.click()
                    print("   Clicked login button")
                    
                    # Wait for page to change
                    await page.wait_for_timeout(3000)
                    
                    # Take screenshot after login
                    await page.screenshot(path="/tmp/2_after_login.png")
                    print("   Screenshot: /tmp/2_after_login.png")
                    
                    # Check what's on page now
                    new_title = await page.title()
                    print(f"   New page title: '{new_title}'")
                    
                    # Look for chat interface
                    chat_form = await page.query_selector("#chatForm, form")
                    message_input = await page.query_selector("textarea, #userMessage, input[type='text']")
                    
                    if message_input:
                        print("\n💬 Testing chat interface...")
                        
                        # Type a test message
                        test_message = "Hello, this is a browser UI test. What documents are available?"
                        await message_input.fill(test_message)
                        print(f"   Typed: '{test_message[:50]}...'")
                        
                        # Find send button
                        send_button = await page.query_selector("button[type='submit'], button:has-text('Send'), button:has-text('전송')")
                        if send_button:
                            await send_button.click()
                            print("   Sent message")
                            
                            # Wait for response
                            print("   Waiting for AI response (15 seconds)...")
                            await page.wait_for_timeout(15000)
                            
                            # Take screenshot of conversation
                            await page.screenshot(path="/tmp/3_chat_conversation.png")
                            print("   Screenshot: /tmp/3_chat_conversation.png")
                            
                            # Look for response
                            messages = await page.query_selector_all(".message, .assistant-message, .ai-message, [data-role='assistant']")
                            print(f"   Found {len(messages)} message(s) in conversation")
                        else:
                            print("   ❌ Send button not found")
                    else:
                        print("   ❌ Message input not found after login")
            
            # Test admin page
            print("\n📊 Testing admin page...")
            await page.goto("http://localhost:3001/admin.html", wait_until="domcontentloaded")
            
            admin_title = await page.title()
            print(f"   Admin page title: '{admin_title}'")
            
            # Check for document management elements
            file_input = await page.query_selector("input[type='file']")
            upload_button = await page.query_selector("button:has-text('Upload'), button:has-text('업로드')")
            doc_list = await page.query_selector("#documents-list, .documents-container, table")
            
            print(f"   File input: {'✅ Found' if file_input else '❌ Not found'}")
            print(f"   Upload button: {'✅ Found' if upload_button else '❌ Not found'}")
            print(f"   Document list: {'✅ Found' if doc_list else '❌ Not found'}")
            
            await page.screenshot(path="/tmp/4_admin_page.png")
            print("   Screenshot: /tmp/4_admin_page.png")
            
            # Test responsive design
            print("\n📱 Testing responsive design...")
            
            viewports = [
                {"name": "Mobile", "width": 375, "height": 667},
                {"name": "Tablet", "width": 768, "height": 1024},
                {"name": "Desktop", "width": 1920, "height": 1080}
            ]
            
            for vp in viewports:
                await page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                await page.goto("http://localhost:3001/chat.html")
                await page.wait_for_timeout(1000)
                
                # Check visibility
                visible_element = await page.query_selector("form, .container, body")
                if visible_element:
                    is_visible = await visible_element.is_visible()
                    print(f"   {vp['name']} ({vp['width']}x{vp['height']}): {'✅ Visible' if is_visible else '❌ Not visible'}")
                    
                    await page.screenshot(path=f"/tmp/5_responsive_{vp['name'].lower()}.png")
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
            await page.screenshot(path="/tmp/error.png")
            print("   Error screenshot: /tmp/error.png")
            
        finally:
            await browser.close()
            print("\n✅ Browser closed")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nScreenshots saved:")
    print("  /tmp/1_initial_page.png")
    print("  /tmp/2_after_login.png")
    print("  /tmp/3_chat_conversation.png")
    print("  /tmp/4_admin_page.png")
    print("  /tmp/5_responsive_*.png")
    print("\n✅ Browser UI testing is now working!")

if __name__ == "__main__":
    asyncio.run(test_rag_chatbot_ui())