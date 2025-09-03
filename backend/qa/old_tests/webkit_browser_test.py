#!/usr/bin/env python3
"""
Browser UI Test using WebKit instead of Chromium
Testing with different browser engine to avoid Chromium issues
"""

import asyncio
import os
from playwright.async_api import async_playwright

# Enable debugging
os.environ['DEBUG'] = 'pw:api'

async def test_with_webkit():
    """Test using WebKit browser instead of Chromium"""
    
    print("=" * 60)
    print("WEBKIT BROWSER TEST")
    print("=" * 60)
    print()
    print("Using WebKit (Safari engine) instead of Chromium")
    print("Node.js version: v24.4.0")
    print("Python version: 3.9.6")
    print()
    
    # Login credentials
    email = "test@cheongahm.com"
    password = "1234"
    
    try:
        playwright = await async_playwright().start()
        print("✅ Playwright started")
        
        # Try WebKit instead of Chromium
        print("🌐 Launching WebKit browser...")
        browser = await playwright.webkit.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        print("✅ WebKit browser launched")
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True
        )
        print("✅ Browser context created")
        
        page = await context.new_page()
        print("✅ New page created")
        
        # Test 1: Navigate to chat page
        print("\n📄 TEST 1: Navigate to login page")
        print("-" * 40)
        
        try:
            response = await page.goto("http://localhost:3001/chat.html", wait_until="domcontentloaded", timeout=10000)
            print(f"   Navigation response: {response.status if response else 'No response'}")
            
            # Check page title
            title = await page.title()
            print(f"   Page title: '{title}'")
            
            # Check for login form
            login_form = await page.query_selector("#loginForm")
            if login_form:
                print("✅ Login form found")
                
                # Try to login
                print("\n🔐 TEST 2: Login")
                print("-" * 40)
                
                email_input = await page.query_selector("#email")
                password_input = await page.query_selector("#password")
                login_button = await page.query_selector("#loginButton")
                
                if email_input and password_input and login_button:
                    await email_input.fill(email)
                    await password_input.fill(password)
                    print(f"   Filled credentials: {email}")
                    
                    await login_button.click()
                    print("   Clicked login button")
                    
                    # Wait for navigation
                    await page.wait_for_timeout(3000)
                    
                    # Check what's on page now
                    chat_form = await page.query_selector("#chatForm")
                    if chat_form:
                        print("✅ Login successful - Chat form found")
                        
                        # Test sending a message
                        print("\n💬 TEST 3: Send message")
                        print("-" * 40)
                        
                        message_input = await page.query_selector('textarea[name="message"], #userMessage, textarea')
                        if message_input:
                            await message_input.fill("Test message from WebKit browser")
                            print("✅ Message typed")
                            
                            # Try to submit
                            submit_button = await page.query_selector('button[type="submit"]')
                            if submit_button:
                                await submit_button.click()
                                print("✅ Message sent")
                            else:
                                await message_input.press("Enter")
                                print("✅ Pressed Enter to send")
                        else:
                            print("❌ Message input not found")
                    else:
                        print("❌ Chat form not found after login")
                        
                        # Debug what's on the page
                        forms = await page.query_selector_all("form")
                        print(f"   Forms on page: {len(forms)}")
                else:
                    print("❌ Login form elements not found")
            else:
                print("❌ Login form not found")
                
        except Exception as nav_error:
            print(f"❌ Navigation error: {nav_error}")
            
        # Clean up
        await browser.close()
        await playwright.stop()
        print("\n✅ Browser closed successfully")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("WEBKIT TEST COMPLETE")
    print("=" * 60)

async def test_with_chromium_debug():
    """Test Chromium with full debugging"""
    
    print("\n" + "=" * 60)
    print("CHROMIUM DEBUG TEST")
    print("=" * 60)
    print()
    
    try:
        playwright = await async_playwright().start()
        print("✅ Playwright started")
        
        # Try different launch options
        print("🔧 Launching Chromium with debug options...")
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',  # Sometimes helps with crashes
                '--disable-gpu'
            ]
        )
        print("✅ Chromium launched with debug flags")
        
        page = await browser.new_page()
        print("✅ Page created")
        
        # Simple navigation test
        try:
            await page.goto("http://localhost:3001", timeout=5000)
            print("✅ Navigation successful")
            
            title = await page.title()
            print(f"   Page title: '{title}'")
            
        except Exception as nav_error:
            print(f"❌ Navigation failed: {nav_error}")
        
        await browser.close()
        await playwright.stop()
        print("✅ Cleanup complete")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run both tests"""
    
    # Test with WebKit
    await test_with_webkit()
    
    # Test with Chromium debug options
    await test_with_chromium_debug()

if __name__ == "__main__":
    # Run with debugging enabled
    print("Running with DEBUG=pw:api enabled")
    asyncio.run(main())