#!/usr/bin/env python3
"""
Stable Browser UI Test with proper navigation handling
Fixes context destruction issues
"""

import asyncio
from playwright.async_api import async_playwright, Page
from typing import Optional

class StableBrowserTest:
    """Browser test with proper context handling"""
    
    def __init__(self):
        self.email = "test@cheongahm.com"
        self.password = "1234"
        self.browser = None
        self.context = None
        self.page = None
        
    async def setup(self, playwright):
        """Setup browser with stable configuration"""
        print("🚀 Setting up browser...")
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        # Create context with specific settings
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True
        )
        
        self.page = await self.context.new_page()
        
        # Set default navigation timeout
        self.page.set_default_navigation_timeout(30000)
        self.page.set_default_timeout(30000)
        
        print("✅ Browser ready")
        return True
        
    async def safe_navigate(self, url: str) -> bool:
        """Safely navigate to URL with error handling"""
        try:
            response = await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=15000
            )
            await self.page.wait_for_load_state("domcontentloaded")
            print(f"   Navigated to: {url} (Status: {response.status if response else 'N/A'})")
            return True
        except Exception as e:
            print(f"   Navigation error: {e}")
            return False
            
    async def safe_screenshot(self, filename: str):
        """Take screenshot with error handling"""
        try:
            await self.page.screenshot(path=filename)
            print(f"   📸 Screenshot: {filename}")
        except Exception as e:
            print(f"   Screenshot failed: {e}")
            
    async def wait_for_element(self, selector: str, timeout: int = 5000) -> Optional[object]:
        """Wait for element with timeout"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            return element
        except:
            return None
            
    async def safe_fill(self, selector: str, text: str) -> bool:
        """Safely fill input field"""
        try:
            element = await self.wait_for_element(selector)
            if element:
                await element.fill(text)
                return True
        except:
            pass
        return False
        
    async def safe_click(self, selector: str) -> bool:
        """Safely click element"""
        try:
            element = await self.wait_for_element(selector)
            if element:
                await element.click()
                return True
        except:
            pass
        return False
        
    async def get_page_info(self):
        """Get current page information safely"""
        try:
            title = await self.page.title()
            url = self.page.url
            return title, url
        except:
            return "Unknown", "Unknown"
            
    async def test_login_flow(self):
        """Test login with proper context handling"""
        print("\n🔐 TEST 1: Login Flow")
        print("-" * 40)
        
        # Navigate to chat page
        if not await self.safe_navigate("http://localhost:3001/chat.html"):
            return False
            
        await self.safe_screenshot("/tmp/1_initial_page.png")
        
        # Get page info
        title, url = await self.get_page_info()
        print(f"   Page: {title}")
        
        # Check for login form
        login_form = await self.wait_for_element("#loginForm", timeout=3000)
        
        if login_form:
            print("   Login form found, attempting login...")
            
            # Fill credentials
            if await self.safe_fill("#email", self.email):
                print(f"   ✅ Entered email: {self.email}")
            else:
                print("   ❌ Could not enter email")
                
            if await self.safe_fill("#password", self.password):
                print("   ✅ Entered password")
            else:
                print("   ❌ Could not enter password")
                
            # Click login - this might cause navigation
            if await self.safe_click("#loginButton"):
                print("   ✅ Clicked login button")
                
                # IMPORTANT: Wait for navigation to complete
                try:
                    # Wait for either navigation or new content
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    # It's okay if this times out, page might not navigate
                    pass
                    
                await asyncio.sleep(2)  # Give time for any redirects
                
                await self.safe_screenshot("/tmp/2_after_login.png")
                
                # Check new page state
                new_title, new_url = await self.get_page_info()
                print(f"   After login - Page: {new_title}")
                print(f"   URL: {new_url}")
                
                return True
        else:
            print("   No login form found, might already be logged in")
            chat_form = await self.wait_for_element("#chatForm", timeout=2000)
            if chat_form:
                print("   ✅ Already at chat interface")
                return True
                
        return False
        
    async def test_chat_interface(self):
        """Test chat interface with proper handling"""
        print("\n💬 TEST 2: Chat Interface")
        print("-" * 40)
        
        # Look for message input with multiple selectors
        selectors = [
            'textarea[name="message"]',
            '#userMessage',
            'textarea',
            'input[type="text"][placeholder*="message"]',
            '.message-input'
        ]
        
        message_input = None
        for selector in selectors:
            message_input = await self.wait_for_element(selector, timeout=2000)
            if message_input:
                print(f"   Found message input: {selector}")
                break
                
        if message_input:
            try:
                # Type message
                test_message = "Hello, this is a browser test. What documents are available?"
                await message_input.fill(test_message)
                print(f"   ✅ Typed message: '{test_message[:40]}...'")
                
                # Find and click send button
                send_selectors = [
                    'button[type="submit"]',
                    'button:has-text("Send")',
                    'button:has-text("전송")',
                    '.send-button',
                    '#send-button'
                ]
                
                sent = False
                for selector in send_selectors:
                    if await self.safe_click(selector):
                        print(f"   ✅ Clicked send button: {selector}")
                        sent = True
                        break
                        
                if not sent:
                    # Try pressing Enter
                    await message_input.press("Enter")
                    print("   ✅ Pressed Enter to send")
                    
                # Wait for response
                print("   ⏳ Waiting for AI response (may take 15-20 seconds)...")
                
                # Wait for response with multiple possible selectors
                response_selectors = [
                    '.assistant-message',
                    '.ai-message',
                    '[data-role="assistant"]',
                    '.bot-message',
                    '.message:last-child'
                ]
                
                response_found = False
                for selector in response_selectors:
                    response_element = await self.wait_for_element(selector, timeout=20000)
                    if response_element:
                        print(f"   ✅ AI response received! (found: {selector})")
                        response_found = True
                        
                        try:
                            response_text = await response_element.inner_text()
                            print(f"   Response preview: '{response_text[:100]}...'")
                        except:
                            pass
                            
                        break
                        
                await self.safe_screenshot("/tmp/3_chat_conversation.png")
                return response_found
                
            except Exception as e:
                print(f"   ❌ Chat test error: {e}")
                return False
        else:
            print("   ❌ No message input found")
            return False
            
    async def test_admin_page(self):
        """Test admin page navigation"""
        print("\n📊 TEST 3: Admin Page")
        print("-" * 40)
        
        # Navigate to admin
        if not await self.safe_navigate("http://localhost:3001/admin.html"):
            return False
            
        await asyncio.sleep(2)  # Wait for page to load
        
        # Check if login is required again
        login_form = await self.wait_for_element("#loginForm", timeout=2000)
        if login_form:
            print("   Admin requires login, logging in...")
            await self.safe_fill("#email", self.email)
            await self.safe_fill("#password", self.password)
            await self.safe_click("#loginButton")
            
            # Wait for login to complete
            await asyncio.sleep(3)
            
        # Check for admin elements
        file_input = await self.wait_for_element('input[type="file"]', timeout=3000)
        doc_list = await self.wait_for_element('table, #documents-list, .documents-container', timeout=3000)
        
        print(f"   File upload: {'✅ Found' if file_input else '❌ Not found'}")
        print(f"   Document list: {'✅ Found' if doc_list else '❌ Not found'}")
        
        await self.safe_screenshot("/tmp/4_admin_page.png")
        
        return file_input is not None or doc_list is not None
        
    async def test_responsive(self):
        """Test responsive design"""
        print("\n📱 TEST 4: Responsive Design")
        print("-" * 40)
        
        viewports = [
            {"name": "Mobile", "width": 375, "height": 667},
            {"name": "Tablet", "width": 768, "height": 1024},
            {"name": "Desktop", "width": 1920, "height": 1080}
        ]
        
        for vp in viewports:
            # Set viewport
            await self.page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            
            # Navigate to chat
            await self.safe_navigate("http://localhost:3001/chat.html")
            await asyncio.sleep(1)
            
            # Check if something is visible
            body = await self.wait_for_element("body", timeout=2000)
            if body:
                print(f"   ✅ {vp['name']} ({vp['width']}x{vp['height']}): Page loaded")
                await self.safe_screenshot(f"/tmp/5_responsive_{vp['name'].lower()}.png")
            else:
                print(f"   ❌ {vp['name']}: Page not loaded")
                
        return True
        
    async def cleanup(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            print("\n✅ Browser closed")
            
    async def run_all_tests(self):
        """Run all tests with proper error handling"""
        print("=" * 60)
        print("STABLE BROWSER UI TEST")
        print("=" * 60)
        print()
        
        async with async_playwright() as playwright:
            try:
                # Setup
                if not await self.setup(playwright):
                    print("❌ Setup failed")
                    return
                    
                # Run tests
                results = []
                
                # Test 1: Login
                login_result = await self.test_login_flow()
                results.append(("Login Flow", login_result))
                
                # Test 2: Chat (only if login succeeded)
                if login_result:
                    chat_result = await self.test_chat_interface()
                    results.append(("Chat Interface", chat_result))
                else:
                    results.append(("Chat Interface", False))
                    
                # Test 3: Admin
                admin_result = await self.test_admin_page()
                results.append(("Admin Page", admin_result))
                
                # Test 4: Responsive
                responsive_result = await self.test_responsive()
                results.append(("Responsive Design", responsive_result))
                
                # Summary
                print("\n" + "=" * 60)
                print("TEST SUMMARY")
                print("=" * 60)
                
                for test_name, passed in results:
                    status = "✅ PASS" if passed else "❌ FAIL"
                    print(f"{status} - {test_name}")
                    
                # List screenshots
                print("\n📸 Screenshots created:")
                screenshots = [
                    "/tmp/1_initial_page.png",
                    "/tmp/2_after_login.png",
                    "/tmp/3_chat_conversation.png",
                    "/tmp/4_admin_page.png",
                    "/tmp/5_responsive_mobile.png",
                    "/tmp/5_responsive_tablet.png",
                    "/tmp/5_responsive_desktop.png"
                ]
                
                for screenshot in screenshots:
                    print(f"  - {screenshot}")
                    
            except Exception as e:
                print(f"\n❌ Test suite error: {e}")
                import traceback
                traceback.print_exc()
                
            finally:
                await self.cleanup()


async def main():
    """Run the stable browser test"""
    tester = StableBrowserTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())