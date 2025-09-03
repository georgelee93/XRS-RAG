#!/usr/bin/env python3
"""
Test if Playwright browser setup is working
"""

import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    """Quick test to verify browser can launch"""
    print("Testing Playwright browser setup...")
    
    try:
        playwright = await async_playwright().start()
        print("✅ Playwright started")
        
        browser = await playwright.chromium.launch(
            headless=True  # Run headless for quick test
        )
        print("✅ Browser launched")
        
        page = await browser.new_page()
        print("✅ Page created")
        
        await page.goto("http://localhost:3001")
        print("✅ Navigated to localhost:3001")
        
        title = await page.title()
        print(f"✅ Page title: {title}")
        
        await browser.close()
        await playwright.stop()
        
        print("\n🎉 Browser setup is working! Ready for UI tests.")
        return True
        
    except Exception as e:
        print(f"\n❌ Browser setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Playwright is installed: pip3 install playwright")
        print("2. Install browsers: python3 -m playwright install chromium")
        print("3. Check if frontend is running on port 3001")
        return False

if __name__ == "__main__":
    asyncio.run(test_browser())