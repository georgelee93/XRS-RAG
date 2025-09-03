#!/usr/bin/env python3
"""
Simple Browser UI Test for RAG Chatbot
Tests the web interface step by step
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_chat_interface():
    """Test the chat interface through browser"""
    
    print("=" * 60)
    print("SIMPLE BROWSER UI TEST")
    print("=" * 60)
    print()
    
    async with async_playwright() as p:
        # Launch browser
        print("🚀 Launching browser...")
        browser = await p.chromium.launch(
            headless=True,  # Run in background
            args=['--no-sandbox']  # Helps with some permission issues
        )
        
        # Create page
        page = await browser.new_page()
        print("✅ Browser started")
        
        try:
            # Test 1: Load Chat Page
            print("\n📄 TEST 1: Loading chat page...")
            await page.goto("http://localhost:3001/chat.html")
            await page.wait_for_timeout(2000)  # Wait 2 seconds
            
            # Check if chat form exists
            chat_form = await page.query_selector("#chatForm")
            if chat_form:
                print("✅ Chat page loaded successfully")
                await page.screenshot(path="/tmp/1_chat_page.png")
                print("   Screenshot saved: /tmp/1_chat_page.png")
            else:
                print("❌ Chat form not found")
                
            # Test 2: Send a Message
            print("\n💬 TEST 2: Sending a chat message...")
            
            # Find message input
            message_input = await page.query_selector('textarea[name="message"], #userMessage')
            
            if message_input:
                # Type message
                test_message = "Hello, this is a browser UI test. Can you tell me what documents you have?"
                await message_input.fill(test_message)
                print(f"   Typed: '{test_message[:50]}...'")
                
                # Submit form
                submit_button = await page.query_selector('button[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    print("   Clicked send button")
                else:
                    await message_input.press("Enter")
                    print("   Pressed Enter")
                
                # Wait for response (AI takes time)
                print("   Waiting for AI response (this may take 10-15 seconds)...")
                
                try:
                    # Wait up to 30 seconds for response
                    await page.wait_for_selector(
                        '.assistant-message, .ai-message, [data-role="assistant"], .message-assistant',
                        timeout=30000
                    )
                    
                    print("✅ AI response received!")
                    
                    # Take screenshot of conversation
                    await page.screenshot(path="/tmp/2_chat_conversation.png")
                    print("   Screenshot saved: /tmp/2_chat_conversation.png")
                    
                    # Get response text
                    responses = await page.query_selector_all('.assistant-message, .ai-message, [data-role="assistant"], .message-assistant')
                    if responses:
                        last_response = responses[-1]
                        response_text = await last_response.inner_text()
                        print(f"   AI said: '{response_text[:100]}...'")
                        
                except Exception as e:
                    print(f"❌ No response received: {e}")
                    await page.screenshot(path="/tmp/2_chat_error.png")
                    
            else:
                print("❌ Message input not found")
            
            # Test 3: Load Admin Page
            print("\n📊 TEST 3: Loading admin page...")
            await page.goto("http://localhost:3001/admin.html")
            await page.wait_for_timeout(2000)
            
            # Check for document section
            doc_section = await page.query_selector("#documentsSection, .documents-container, #documents-list")
            if doc_section:
                print("✅ Admin page loaded successfully")
                await page.screenshot(path="/tmp/3_admin_page.png")
                print("   Screenshot saved: /tmp/3_admin_page.png")
                
                # Count documents
                doc_items = await page.query_selector_all('.document-item, .doc-row, tr[data-document], .file-item')
                print(f"   Found {len(doc_items)} documents in list")
            else:
                print("❌ Document section not found")
            
            # Test 4: Check Upload Form
            print("\n📤 TEST 4: Checking upload form...")
            file_input = await page.query_selector('input[type="file"]')
            upload_button = await page.query_selector('button:has-text("Upload"), button:has-text("업로드")')
            
            if file_input and upload_button:
                print("✅ Upload form is present")
                print("   File input: Found")
                print("   Upload button: Found")
            else:
                print("❌ Upload form incomplete")
                print(f"   File input: {'Found' if file_input else 'Not found'}")
                print(f"   Upload button: {'Found' if upload_button else 'Not found'}")
            
            # Test 5: Responsive Design
            print("\n📱 TEST 5: Testing responsive design...")
            
            # Test mobile view
            await page.set_viewport_size({"width": 375, "height": 667})
            await page.goto("http://localhost:3001/chat.html")
            await page.wait_for_timeout(1000)
            
            mobile_form = await page.query_selector("#chatForm")
            if mobile_form and await mobile_form.is_visible():
                print("✅ Mobile view (375x667): Chat form visible")
                await page.screenshot(path="/tmp/4_mobile_view.png")
            else:
                print("❌ Mobile view: Chat form not visible")
            
            # Test tablet view
            await page.set_viewport_size({"width": 768, "height": 1024})
            await page.reload()
            await page.wait_for_timeout(1000)
            
            tablet_form = await page.query_selector("#chatForm")
            if tablet_form and await tablet_form.is_visible():
                print("✅ Tablet view (768x1024): Chat form visible")
                await page.screenshot(path="/tmp/5_tablet_view.png")
            else:
                print("❌ Tablet view: Chat form not visible")
            
            # Test desktop view
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.reload()
            await page.wait_for_timeout(1000)
            
            desktop_form = await page.query_selector("#chatForm")
            if desktop_form and await desktop_form.is_visible():
                print("✅ Desktop view (1920x1080): Chat form visible")
                await page.screenshot(path="/tmp/6_desktop_view.png")
            else:
                print("❌ Desktop view: Chat form not visible")
                
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Close browser
            await browser.close()
            print("\n🏁 Browser closed")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nScreenshots saved in /tmp/:")
    print("  1_chat_page.png - Initial chat page")
    print("  2_chat_conversation.png - Chat with AI response")
    print("  3_admin_page.png - Admin/document page")
    print("  4_mobile_view.png - Mobile responsive view")
    print("  5_tablet_view.png - Tablet responsive view")
    print("  6_desktop_view.png - Desktop responsive view")
    print("\nYou can view these screenshots to see the UI test results!")

if __name__ == "__main__":
    asyncio.run(test_chat_interface())