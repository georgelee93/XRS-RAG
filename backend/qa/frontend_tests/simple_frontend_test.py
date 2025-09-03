#!/usr/bin/env python3
"""
Simple Frontend Test without Playwright
Tests the frontend by checking HTML content and JavaScript execution
"""

import requests
import json
from datetime import datetime
import time

class SimpleFrontendTester:
    def __init__(self):
        self.frontend_url = "http://localhost:3000"
        self.backend_url = "http://localhost:8080"
        self.test_results = []
        
    def record_test(self, test_name: str, passed: bool, details: str):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {details}")
    
    def test_frontend_accessible(self):
        """Test if frontend is accessible"""
        try:
            response = requests.get(f"{self.frontend_url}/public/admin.html")
            
            if response.status_code == 200:
                self.record_test("Frontend Accessible", True, f"Status {response.status_code}")
                return True
            else:
                self.record_test("Frontend Accessible", False, f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.record_test("Frontend Accessible", False, str(e))
            return False
    
    def test_admin_html_structure(self):
        """Test if admin HTML has correct structure"""
        try:
            response = requests.get(f"{self.frontend_url}/public/admin.html")
            html = response.text
            
            # Check for essential elements
            checks = {
                "Admin App Container": '<div id="adminApp"' in html,
                "Document Table": 'id="documentTableBody"' in html,
                "Upload Button": 'uploadBtn' in html or 'upload' in html.lower(),
                "JavaScript Import": 'src="/src/js/admin.js"' in html,
                "API Config": 'localhost:8080' in html or 'API_CONFIG' in html
            }
            
            all_passed = True
            for check_name, check_result in checks.items():
                self.record_test(f"HTML Check: {check_name}", check_result, 
                               "Found" if check_result else "Not found")
                if not check_result:
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.record_test("Admin HTML Structure", False, str(e))
            return False
    
    def test_backend_api(self):
        """Test if backend API returns documents"""
        try:
            response = requests.get(f"{self.backend_url}/api/documents")
            
            if response.status_code != 200:
                self.record_test("Backend API", False, f"Status {response.status_code}")
                return False, 0
            
            data = response.json()
            
            if isinstance(data, dict) and "documents" in data:
                doc_count = len(data["documents"])
                self.record_test("Backend API", True, f"Returns {doc_count} documents")
                return True, doc_count
            else:
                self.record_test("Backend API", False, "Unexpected response format")
                return False, 0
                
        except Exception as e:
            self.record_test("Backend API", False, str(e))
            return False, 0
    
    def test_cors_headers(self):
        """Test if CORS is properly configured"""
        try:
            # Simulate a CORS request from frontend
            headers = {
                "Origin": self.frontend_url,
                "Referer": f"{self.frontend_url}/public/admin.html"
            }
            
            response = requests.get(f"{self.backend_url}/api/documents", headers=headers)
            
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            
            if cors_header:
                if cors_header == "*" or self.frontend_url in cors_header:
                    self.record_test("CORS Configuration", True, f"Allow-Origin: {cors_header}")
                    return True
                else:
                    self.record_test("CORS Configuration", False, 
                                   f"Allow-Origin doesn't match: {cors_header}")
                    return False
            else:
                self.record_test("CORS Configuration", False, "No CORS headers")
                return False
                
        except Exception as e:
            self.record_test("CORS Configuration", False, str(e))
            return False
    
    def test_javascript_files(self):
        """Test if JavaScript files are accessible"""
        try:
            js_files = [
                "/src/js/admin.js",
                "/src/js/api.js",
                "/src/js/config.js",
                "/src/js/utils.js"
            ]
            
            all_accessible = True
            for js_file in js_files:
                try:
                    response = requests.get(f"{self.frontend_url}{js_file}")
                    
                    if response.status_code == 200:
                        # Check if it's actually JavaScript
                        is_js = "function" in response.text or "const" in response.text or "import" in response.text
                        
                        if is_js:
                            self.record_test(f"JS File: {js_file}", True, "Accessible and valid")
                        else:
                            self.record_test(f"JS File: {js_file}", False, "Not JavaScript content")
                            all_accessible = False
                    else:
                        self.record_test(f"JS File: {js_file}", False, f"Status {response.status_code}")
                        all_accessible = False
                        
                except Exception as e:
                    self.record_test(f"JS File: {js_file}", False, str(e))
                    all_accessible = False
            
            return all_accessible
            
        except Exception as e:
            self.record_test("JavaScript Files", False, str(e))
            return False
    
    def test_api_integration(self):
        """Test if the frontend can potentially connect to the backend"""
        try:
            # Check if config.js has correct backend URL
            response = requests.get(f"{self.frontend_url}/src/js/config.js")
            
            if response.status_code == 200:
                config_content = response.text
                
                if "8080" in config_content:
                    self.record_test("API Integration Config", True, 
                                   "Config has correct backend port (8080)")
                    return True
                elif "8000" in config_content:
                    self.record_test("API Integration Config", False, 
                                   "Config has wrong port (8000 instead of 8080)")
                    return False
                else:
                    self.record_test("API Integration Config", False, 
                                   "Could not find backend URL in config")
                    return False
            else:
                self.record_test("API Integration Config", False, 
                               f"Could not access config.js: {response.status_code}")
                return False
                
        except Exception as e:
            self.record_test("API Integration Config", False, str(e))
            return False
    
    def run_tests(self):
        """Run all frontend tests"""
        print("="*60)
        print("SIMPLE FRONTEND TEST (No Browser)")
        print("="*60)
        
        # Test 1: Frontend accessible
        print("\n🔍 Test 1: Frontend Accessibility")
        self.test_frontend_accessible()
        
        # Test 2: HTML structure
        print("\n🔍 Test 2: Admin HTML Structure")
        self.test_admin_html_structure()
        
        # Test 3: Backend API
        print("\n🔍 Test 3: Backend API")
        api_ok, doc_count = self.test_backend_api()
        
        # Test 4: CORS
        print("\n🔍 Test 4: CORS Configuration")
        self.test_cors_headers()
        
        # Test 5: JavaScript files
        print("\n🔍 Test 5: JavaScript Files")
        self.test_javascript_files()
        
        # Test 6: API Integration
        print("\n🔍 Test 6: API Integration")
        self.test_api_integration()
        
        # Analysis
        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60)
        
        if api_ok and doc_count > 0:
            print(f"\n📊 Backend has {doc_count} documents")
            print("If these aren't showing in the admin page, the issue is likely:")
            print("  1. JavaScript execution error (check browser console)")
            print("  2. Authentication/authorization issue")
            print("  3. DOM manipulation error in admin.js")
            print("  4. Timing issue (page loads before API call completes)")
            
            print("\n🔧 Debugging Steps:")
            print("  1. Open http://localhost:3002/public/admin.html")
            print("  2. Open browser console (F12)")
            print("  3. Look for red error messages")
            print("  4. In console, type: app.documents")
            print("  5. If undefined, type: api.getDocuments().then(console.log)")
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {total-passed} ({(total-passed)/total*100:.1f}%)")
        
        if passed < total:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        # Save results
        with open("qa/simple_frontend_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
            print(f"\nResults saved to: qa/simple_frontend_test_results.json")
        
        return self.test_results


def main():
    tester = SimpleFrontendTester()
    tester.run_tests()


if __name__ == "__main__":
    main()