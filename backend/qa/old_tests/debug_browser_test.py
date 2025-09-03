#!/usr/bin/env python3
"""
Debug browser test to see what's actually on the page
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_pages():
    """Debug what's actually on the pages"""
    
    print("=" * 60)
    print("DEBUG BROWSER TEST")
    print("=" * 60)
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Enable verbose console output
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda error: print(f"Page error: {error}"))
        
        print("🔍 Checking what's on the chat page...")
        
        try:
            # Navigate to chat page
            response = await page.goto("http://localhost:3001/chat.html", wait_until="networkidle")
            print(f"Response status: {response.status}")
            
            # Get page content
            content = await page.content()
            print(f"Page content length: {len(content)} characters")
            
            # Get page title
            title = await page.title()
            print(f"Page title: '{title}'")
            
            # Try different selectors
            selectors_to_check = [
                "#chatForm",
                "form",
                "#userMessage",
                "textarea",
                "input",
                "button",
                ".chat-form",
                "[data-chat]",
                "#messagesContainer",
                ".messages",
                "#chat-form"  # Different casing
            ]
            
            print("\nChecking for elements:")
            for selector in selectors_to_check:
                element = await page.query_selector(selector)
                if element:
                    print(f"  ✅ Found: {selector}")
                    # Get some info about the element
                    tag = await element.evaluate("el => el.tagName")
                    id_attr = await element.evaluate("el => el.id")
                    class_attr = await element.evaluate("el => el.className")
                    print(f"     Tag: {tag}, ID: '{id_attr}', Class: '{class_attr}'")
                else:
                    print(f"  ❌ Not found: {selector}")
            
            # Get all forms on page
            forms = await page.query_selector_all("form")
            print(f"\nTotal forms on page: {len(forms)}")
            for i, form in enumerate(forms):
                form_id = await form.evaluate("el => el.id")
                form_class = await form.evaluate("el => el.className")
                print(f"  Form {i+1}: ID='{form_id}', Class='{form_class}'")
            
            # Get all textareas
            textareas = await page.query_selector_all("textarea")
            print(f"\nTotal textareas on page: {len(textareas)}")
            for i, textarea in enumerate(textareas):
                textarea_name = await textarea.evaluate("el => el.name")
                textarea_id = await textarea.evaluate("el => el.id")
                print(f"  Textarea {i+1}: Name='{textarea_name}', ID='{textarea_id}'")
            
            # Get all buttons
            buttons = await page.query_selector_all("button")
            print(f"\nTotal buttons on page: {len(buttons)}")
            for i, button in enumerate(buttons[:5]):  # First 5 buttons
                button_text = await button.evaluate("el => el.textContent")
                button_type = await button.evaluate("el => el.type")
                print(f"  Button {i+1}: Text='{button_text.strip()}', Type='{button_type}'")
            
            # Check if there are any error messages
            print("\nChecking for errors or issues:")
            
            # Check for 404 or error pages
            if "404" in content or "not found" in content.lower():
                print("  ⚠️  Page might be 404")
            
            # Check for JavaScript errors
            errors = await page.query_selector_all(".error, .alert-danger")
            if errors:
                print(f"  ⚠️  Found {len(errors)} error messages on page")
            
            # Take a screenshot for manual inspection
            await page.screenshot(path="/tmp/debug_chat_page.png")
            print("\n📸 Screenshot saved to /tmp/debug_chat_page.png")
            
            # Also check admin page
            print("\n" + "=" * 40)
            print("Checking admin page...")
            
            await page.goto("http://localhost:3001/admin.html", wait_until="networkidle")
            
            admin_selectors = [
                "#documentsSection",
                ".documents-container",
                "#documents-list",
                "input[type='file']",
                ".upload-form",
                ".file-upload"
            ]
            
            print("\nChecking admin page elements:")
            for selector in admin_selectors:
                element = await page.query_selector(selector)
                if element:
                    print(f"  ✅ Found: {selector}")
                else:
                    print(f"  ❌ Not found: {selector}")
            
            await page.screenshot(path="/tmp/debug_admin_page.png")
            print("\n📸 Screenshot saved to /tmp/debug_admin_page.png")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("Check the screenshots in /tmp/ to see what's on the pages")

if __name__ == "__main__":
    asyncio.run(debug_pages())