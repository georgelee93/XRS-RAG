#!/usr/bin/env python3
"""
Quick setup check for Frontend UI Testing
Validates that all required services are running before UI tests
"""

import asyncio
import aiohttp
import sys

class UISetupChecker:
    def __init__(self):
        self.frontend_url = "http://localhost:3001"
        self.backend_url = "http://localhost:8080"
        
    async def check_frontend(self):
        """Check if frontend is serving pages"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check main pages
                pages_to_check = [
                    "/chat.html",
                    "/admin.html", 
                    "/index.html"
                ]
                
                results = {}
                for page in pages_to_check:
                    try:
                        async with session.get(f"{self.frontend_url}{page}") as response:
                            results[page] = response.status == 200
                    except:
                        results[page] = False
                
                all_good = all(results.values())
                print(f"Frontend ({self.frontend_url}):")
                for page, status in results.items():
                    icon = "✅" if status else "❌" 
                    print(f"  {icon} {page}")
                
                return all_good
                
        except Exception as e:
            print(f"❌ Frontend check failed: {e}")
            return False
    
    async def check_backend(self):
        """Check if backend APIs are responding"""
        try:
            async with aiohttp.ClientSession() as session:
                endpoints_to_check = [
                    "/api/health",
                    "/api/documents",
                    "/api/chat"
                ]
                
                results = {}
                for endpoint in endpoints_to_check:
                    try:
                        if endpoint == "/api/chat":
                            # POST request for chat
                            payload = {
                                "message": "test",
                                "session_id": "setup_check"
                            }
                            async with session.post(f"{self.backend_url}{endpoint}", json=payload) as response:
                                results[endpoint] = response.status in [200, 422]  # 422 might be validation error but API is responding
                        else:
                            # GET request for others
                            async with session.get(f"{self.backend_url}{endpoint}") as response:
                                results[endpoint] = response.status == 200
                    except Exception as e:
                        results[endpoint] = False
                
                all_good = all(results.values())
                print(f"\nBackend ({self.backend_url}):")
                for endpoint, status in results.items():
                    icon = "✅" if status else "❌"
                    print(f"  {icon} {endpoint}")
                
                return all_good
                
        except Exception as e:
            print(f"❌ Backend check failed: {e}")
            return False
    
    async def check_dependencies(self):
        """Check if required Python packages are available"""
        print("\nPython Dependencies:")
        dependencies = [
            "playwright",
            "aiohttp", 
            "supabase",
            "dotenv"
        ]
        
        all_good = True
        for dep in dependencies:
            try:
                if dep == "playwright":
                    import playwright
                elif dep == "aiohttp":
                    import aiohttp
                elif dep == "supabase":
                    import supabase
                elif dep == "dotenv":
                    import dotenv
                print(f"  ✅ {dep}")
            except ImportError:
                print(f"  ❌ {dep} (run: pip install {dep})")
                all_good = False
        
        return all_good
    
    async def run_setup_check(self):
        """Run complete setup validation"""
        print("=" * 60)
        print("UI TESTING SETUP CHECK")
        print("=" * 60)
        
        frontend_ok = await self.check_frontend()
        backend_ok = await self.check_backend()
        deps_ok = await self.check_dependencies()
        
        print("\n" + "=" * 60)
        print("SETUP STATUS")
        print("=" * 60)
        
        if frontend_ok and backend_ok and deps_ok:
            print("🎉 All checks passed! Ready to run UI tests.")
            print("\nTo run UI tests:")
            print("  ./run_ui_tests.sh")
            print("  OR")
            print("  python3 frontend_ui_test.py")
            return True
        else:
            print("❌ Setup issues found. Fix the following:")
            
            if not frontend_ok:
                print("\n📱 Frontend Issues:")
                print("  - Make sure frontend server is running")
                print("  - cd frontend && npm run dev")
                
            if not backend_ok:
                print("\n🔧 Backend Issues:")
                print("  - Make sure backend server is running")
                print("  - cd backend && python3 main.py")
                
            if not deps_ok:
                print("\n📦 Dependency Issues:")
                print("  - Install missing Python packages")
                print("  - pip install playwright aiohttp python-dotenv supabase")
                print("  - playwright install")
            
            return False


async def main():
    checker = UISetupChecker()
    success = await checker.run_setup_check()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())