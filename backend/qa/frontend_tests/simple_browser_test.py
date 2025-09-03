#!/usr/bin/env python3
"""
Simple browser test using Playwright with minimal configuration
"""

from playwright.sync_api import sync_playwright
import time

def test_admin_page():
    """Test admin page with simple browser automation"""
    
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)  # Set to False to see what happens
        
        print("Creating page...")
        page = browser.new_page()
        
        print("Navigating to admin page...")
        page.goto("http://localhost:3002/public/admin.html")
        
        # Wait for page to load
        print("Waiting for page load...")
        page.wait_for_load_state("networkidle")
        
        # Check if adminApp exists
        admin_app = page.query_selector("#adminApp")
        if admin_app:
            print("✅ Admin app container found")
        else:
            print("❌ Admin app container not found")
        
        # Check if document table exists
        doc_table = page.query_selector("#documentTableBody")
        if doc_table:
            print("✅ Document table found")
        else:
            print("❌ Document table not found")
        
        # Wait a bit for JavaScript to execute
        print("Waiting for JavaScript execution...")
        time.sleep(3)
        
        # Count table rows
        rows = page.query_selector_all("#documentTableBody tr")
        print(f"Found {len(rows)} document rows")
        
        # Check for any console errors
        page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
        
        # Check if app object exists in JavaScript
        try:
            app_exists = page.evaluate("typeof app !== 'undefined'")
            if app_exists:
                print("✅ App object exists in JavaScript")
                
                # Try to get documents from app
                doc_count = page.evaluate("app.documents ? app.documents.length : 0")
                print(f"App has {doc_count} documents loaded")
            else:
                print("❌ App object not found in JavaScript")
        except Exception as e:
            print(f"Error checking app object: {e}")
        
        # Take screenshot
        page.screenshot(path="qa/admin_page_test.png")
        print("Screenshot saved to qa/admin_page_test.png")
        
        # Keep browser open for a moment
        time.sleep(2)
        
        browser.close()
        print("Test completed")

if __name__ == "__main__":
    test_admin_page()