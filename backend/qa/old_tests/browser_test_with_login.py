#!/usr/bin/env python3
"""
Browser UI Test with Login for RAG Chatbot
Tests the web interface after logging in
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_with_login():
    """Test the chat interface after logging in"""
    
    print("=" * 60)
    print("BROWSER UI TEST WITH LOGIN")
    print("=" * 60)
    print()
    
    # Login credentials
    email = "test@cheongahm.com"
    password = "1234"
    
    async with async_playwright() as p:
        # Launch browser
        print("🚀 Launching browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox']
        )
        
        # Create page
        page = await browser.new_page()
        print("✅ Browser started")
        
        try:
            # Step 1: Login
            print("\n🔐 STEP 1: Login")
            print("-" * 40)
            
            await page.goto("http://localhost:3001/chat.html")
            print(f"   Navigated to chat page")
            
            # Fill login form
            email_input = await page.query_selector("#email")
            password_input = await page.query_selector("#password")
            login_button = await page.query_selector("#loginButton")
            
            if email_input and password_input and login_button:
                await email_input.fill(email)
                await password_input.fill(password)
                print(f"   Entered credentials: {email}")
                
                # Click login
                await login_button.click()
                print("   Clicked login button")
                
                # Wait for navigation or page change
                await page.wait_for_timeout(3000)
                
                # Check if we're logged in (chat form should appear)
                chat_form = await page.query_selector("#chatForm")
                if chat_form:
                    print("✅ Login successful - Chat interface loaded")
                    await page.screenshot(path="/tmp/1_after_login.png")
                    print("   Screenshot: /tmp/1_after_login.png")
                else:
                    print("⚠️  Chat form not found after login, checking for other elements...")
                    
                    # Check what's on the page now
                    forms = await page.query_selector_all("form")
                    print(f"   Forms on page: {len(forms)}")
                    for form in forms:
                        form_id = await form.evaluate("el => el.id")
                        print(f"     Form ID: {form_id}")
            else:
                print("❌ Login form elements not found")
                return
            
            # Step 2: Test Chat Interface
            print("\n💬 STEP 2: Test Chat Interface")
            print("-" * 40)
            
            # Try to find message input with various selectors
            message_selectors = [
                'textarea[name="message"]',
                '#userMessage',
                'textarea',
                '.message-input',
                'input[type="text"][placeholder*="message"]'
            ]
            
            message_input = None
            for selector in message_selectors:
                message_input = await page.query_selector(selector)
                if message_input:
                    print(f"   Found message input: {selector}")
                    break
            
            if message_input:
                # Type and send message
                test_message = "Hello, this is an automated test. What documents are available?"
                await message_input.fill(test_message)
                print(f"   Typed: '{test_message[:50]}...'")
                
                # Find send button
                send_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Send")',
                    'button:has-text("전송")',
                    '.send-button'
                ]
                
                send_button = None
                for selector in send_selectors:
                    send_button = await page.query_selector(selector)
                    if send_button:
                        await send_button.click()
                        print(f"   Clicked send button: {selector}")
                        break
                
                if not send_button:
                    # Try pressing Enter
                    await message_input.press("Enter")
                    print("   Pressed Enter to send")
                
                # Wait for response
                print("   Waiting for AI response (may take 10-15 seconds)...")
                
                response_selectors = [
                    '.assistant-message',
                    '.ai-message',
                    '[data-role="assistant"]',
                    '.message-assistant',
                    '.bot-message'
                ]
                
                response_found = False
                for selector in response_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=20000)
                        response_found = True
                        print(f"✅ AI response received! (found: {selector})")
                        
                        # Get response text
                        response_elements = await page.query_selector_all(selector)
                        if response_elements:
                            last_response = response_elements[-1]
                            response_text = await last_response.inner_text()
                            print(f"   AI said: '{response_text[:100]}...'")
                        
                        await page.screenshot(path="/tmp/2_chat_conversation.png")
                        print("   Screenshot: /tmp/2_chat_conversation.png")
                        break
                        
                    except:
                        continue
                
                if not response_found:
                    print("⚠️  No AI response found after waiting")
                    await page.screenshot(path="/tmp/2_chat_no_response.png")
                    
            else:
                print("❌ Message input not found")
            
            # Step 3: Navigate to Admin Page
            print("\n📊 STEP 3: Admin/Documents Page")
            print("-" * 40)
            
            # Try to navigate to admin
            await page.goto("http://localhost:3001/admin.html")
            await page.wait_for_timeout(2000)
            
            # Check if we need to login again
            login_form = await page.query_selector("#loginForm")
            if login_form:
                print("   Admin page requires login, logging in...")
                email_input = await page.query_selector("#email")
                password_input = await page.query_selector("#password")
                login_button = await page.query_selector("#loginButton")
                
                if email_input and password_input and login_button:
                    await email_input.fill(email)
                    await password_input.fill(password)
                    await login_button.click()
                    await page.wait_for_timeout(3000)
            
            # Check for document elements
            doc_selectors = [
                '#documentsSection',
                '.documents-container',
                '#documents-list',
                '.document-list',
                'table',
                '.files-table'
            ]
            
            doc_found = False
            for selector in doc_selectors:
                element = await page.query_selector(selector)
                if element:
                    print(f"✅ Found document section: {selector}")
                    doc_found = True
                    
                    # Count documents
                    doc_items = await page.query_selector_all('.document-item, .doc-row, tr[data-document], tbody tr')
                    print(f"   Documents in list: {len(doc_items)}")
                    break
            
            if doc_found:
                await page.screenshot(path="/tmp/3_admin_page.png")
                print("   Screenshot: /tmp/3_admin_page.png")
            else:
                print("❌ Document section not found")
            
            # Check for upload form
            file_input = await page.query_selector('input[type="file"]')
            upload_button = await page.query_selector('button:has-text("Upload"), button:has-text("업로드")')
            
            if file_input:
                print("✅ File upload input found")
            if upload_button:
                print("✅ Upload button found")
            
            # Step 4: Test Responsive Design
            print("\n📱 STEP 4: Responsive Design Test")
            print("-" * 40)
            
            viewports = [
                {"name": "Mobile", "width": 375, "height": 667},
                {"name": "Tablet", "width": 768, "height": 1024},
                {"name": "Desktop", "width": 1920, "height": 1080}
            ]
            
            for viewport in viewports:
                await page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
                await page.goto("http://localhost:3001/chat.html")
                await page.wait_for_timeout(1500)
                
                # Check if login is needed
                login_form = await page.query_selector("#loginForm")
                if login_form:
                    # Quick login
                    email_input = await page.query_selector("#email")
                    password_input = await page.query_selector("#password")
                    login_button = await page.query_selector("#loginButton")
                    
                    if email_input and password_input and login_button:
                        await email_input.fill(email)
                        await password_input.fill(password)
                        await login_button.click()
                        await page.wait_for_timeout(2000)
                
                # Check if chat interface is visible
                chat_visible = False
                for selector in ["#chatForm", "form", ".chat-container"]:
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            chat_visible = True
                            break
                
                if chat_visible:
                    print(f"✅ {viewport['name']} ({viewport['width']}x{viewport['height']}): Interface visible")
                    await page.screenshot(path=f"/tmp/4_responsive_{viewport['name'].lower()}.png")
                else:
                    print(f"❌ {viewport['name']}: Interface not visible")
            
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path="/tmp/error_screenshot.png")
            print("Error screenshot: /tmp/error_screenshot.png")
            
        finally:
            # Close browser
            await browser.close()
            print("\n🏁 Browser closed")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nTest Credentials Used:")
    print(f"  Email: {email}")
    print(f"  Password: {password}")
    print("\nScreenshots saved in /tmp/:")
    print("  1_after_login.png - After successful login")
    print("  2_chat_conversation.png - Chat with AI response")
    print("  3_admin_page.png - Admin/documents page")
    print("  4_responsive_*.png - Different screen sizes")
    print("\n✅ Browser UI tests with login completed!")

if __name__ == "__main__":
    asyncio.run(test_with_login())