#!/usr/bin/env python3
"""
Enhanced Browser Tests with Console Error Detection
Captures and validates browser console errors to catch API issues
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Test credentials
TEST_EMAIL = "test11@ca1996.co.kr"
TEST_PASSWORD = "Qq123456"

async def run_enhanced_browser_tests():
    """Run browser tests with console error detection"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Run: python3 -m playwright install chromium")
        return False
    
    print("\n" + "="*60)
    print("ENHANCED BROWSER TEST SUITE WITH ERROR DETECTION")
    print("="*60)
    
    results = []
    console_errors = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # Test 1: Chat Functionality with Console Monitoring
        print("\n💬 TEST 1: Chat with Console Error Detection")
        print("-"*40)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set up console error listener
            console_logs = []
            page.on("console", lambda msg: console_logs.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            }))
            
            # Set up request/response interceptors
            request_logs = []
            response_logs = []
            
            page.on("request", lambda request: request_logs.append({
                "url": request.url,
                "method": request.method,
                "headers": request.headers
            }))
            
            page.on("response", lambda response: response_logs.append({
                "url": response.url,
                "status": response.status,
                "headers": response.headers
            }))
            
            # Login
            await page.goto("http://localhost:3001/login.html")
            await page.fill('input[type="email"]', TEST_EMAIL)
            await page.fill('input[type="password"]', TEST_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Navigate to chat
            await page.goto("http://localhost:3001/chat.html", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Send a test message
            message_input = await page.query_selector('#messageInput')
            if message_input:
                await message_input.fill("Test message for error detection")
                print("✅ Entered test message")
                
                # Clear logs before sending
                console_logs.clear()
                request_logs.clear()
                response_logs.clear()
                
                # Submit message
                submit_button = await page.query_selector('#chatForm button[type="submit"]')
                if submit_button:
                    await submit_button.click()
                    print("✅ Sent message")
                    
                    # Wait for response
                    await page.wait_for_timeout(5000)
                    
                    # Check for console errors
                    errors = [log for log in console_logs if log["type"] == "error"]
                    if errors:
                        print(f"❌ Console errors detected: {len(errors)}")
                        for error in errors:
                            print(f"   - {error['text']}")
                            console_errors.append(error)
                        results.append(("Chat Console Errors", "FAIL", errors))
                    else:
                        print("✅ No console errors")
                        results.append(("Chat Console Errors", "PASS", None))
                    
                    # Check for failed API requests
                    failed_requests = [
                        resp for resp in response_logs 
                        if resp["status"] >= 400 and "/api/" in resp["url"]
                    ]
                    if failed_requests:
                        print(f"❌ Failed API requests: {len(failed_requests)}")
                        for req in failed_requests:
                            print(f"   - {req['status']} {req['url']}")
                        results.append(("API Requests", "FAIL", failed_requests))
                    else:
                        print("✅ All API requests successful")
                        results.append(("API Requests", "PASS", None))
                    
                    # Check content-type of chat request
                    chat_requests = [
                        req for req in request_logs 
                        if "/api/chat" in req["url"] and req["method"] == "POST"
                    ]
                    if chat_requests:
                        for req in chat_requests:
                            content_type = req["headers"].get("content-type", "")
                            if "multipart/form-data" in content_type:
                                print("✅ Chat request using correct FormData")
                                results.append(("Chat Content-Type", "PASS", None))
                            elif "application/json" in content_type:
                                print("❌ Chat request using JSON (should be FormData)")
                                results.append(("Chat Content-Type", "FAIL", "Using JSON instead of FormData"))
                            else:
                                print(f"⚠️ Chat request content-type: {content_type}")
                                results.append(("Chat Content-Type", "WARN", content_type))
                    
            await page.screenshot(path="/tmp/enhanced_test_chat.png")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error in chat test: {e}")
            results.append(("Chat Test", "ERROR", str(e)))
        
        # Test 2: Document Upload with Error Detection
        print("\n📄 TEST 2: Document Upload with Error Detection")
        print("-"*40)
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # Set up console error listener
            console_logs = []
            page.on("console", lambda msg: console_logs.append({
                "type": msg.type,
                "text": msg.text
            }))
            
            response_logs = []
            page.on("response", lambda response: response_logs.append({
                "url": response.url,
                "status": response.status
            }))
            
            # Login and go to admin
            await page.goto("http://localhost:3001/login.html")
            await page.fill('input[type="email"]', TEST_EMAIL)
            await page.fill('input[type="password"]', TEST_PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            
            # Check if redirected to admin
            if "admin.html" in page.url:
                print("✅ Admin page accessible")
                
                # Check for console errors on admin page
                errors = [log for log in console_logs if log["type"] == "error"]
                if errors:
                    print(f"❌ Admin page console errors: {len(errors)}")
                    results.append(("Admin Console Errors", "FAIL", errors))
                else:
                    print("✅ No console errors on admin page")
                    results.append(("Admin Console Errors", "PASS", None))
                
                # Check for failed document API calls
                doc_requests = [
                    resp for resp in response_logs 
                    if "/api/documents" in resp["url"]
                ]
                failed_doc_requests = [
                    req for req in doc_requests 
                    if req["status"] >= 400
                ]
                if failed_doc_requests:
                    print(f"❌ Failed document API requests: {len(failed_doc_requests)}")
                    results.append(("Document API", "FAIL", failed_doc_requests))
                else:
                    print(f"✅ Document API requests successful ({len(doc_requests)} total)")
                    results.append(("Document API", "PASS", None))
            
            await page.screenshot(path="/tmp/enhanced_test_admin.png")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error in admin test: {e}")
            results.append(("Admin Test", "ERROR", str(e)))
        
        await browser.close()
    
    # Summary
    print("\n" + "="*60)
    print("ENHANCED TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status in ["FAIL", "ERROR"])
    warned = sum(1 for _, status, _ in results if status == "WARN")
    
    for test_name, status, details in results:
        icon = "✅" if status == "PASS" else "❌" if status in ["FAIL", "ERROR"] else "⚠️"
        print(f"{icon} {test_name}: {status}")
        if details and status != "PASS":
            if isinstance(details, list):
                for detail in details[:3]:  # Show first 3 details
                    print(f"   - {detail}")
            else:
                print(f"   - {details}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}, Failed: {failed}, Warnings: {warned}")
    
    # Save detailed report
    report_file = f"reports/enhanced_browser_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("reports").mkdir(exist_ok=True)
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "warnings": warned
        },
        "results": [
            {"test": name, "status": status, "details": details}
            for name, status, details in results
        ],
        "console_errors": console_errors
    }
    
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    print("📸 Screenshots saved to /tmp/")
    
    if console_errors:
        print(f"\n⚠️ Found {len(console_errors)} console errors during testing")
        print("These indicate potential frontend-backend integration issues")
    
    return failed == 0

async def main():
    """Main test runner"""
    success = await run_enhanced_browser_tests()
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