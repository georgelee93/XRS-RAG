#!/usr/bin/env python3
"""
Main QA Test Runner
Runs all QA test suites and provides a comprehensive report
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test_module(module_name: str, test_class: str, test_method: str = "run_all_tests") -> Tuple[bool, str]:
    """Run a test module and return results"""
    try:
        print(f"\n🔄 Running {module_name}...")
        
        # Import and run the test
        module = __import__(module_name, fromlist=[test_class])
        test_suite = getattr(module, test_class)()
        
        # Run the tests
        if hasattr(test_suite, test_method):
            result = getattr(test_suite, test_method)()
            return (result, "Completed successfully")
        else:
            return (False, f"Test method {test_method} not found")
            
    except ImportError as e:
        return (False, f"Import error: {e}")
    except Exception as e:
        return (False, f"Error: {e}")

def main():
    """Main QA runner"""
    print("\n" + "="*70)
    print(" "*20 + "RAG CHATBOT COMPREHENSIVE QA TEST SUITE")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test suites
    test_suites = [
        {
            "name": "Authentication & Authorization",
            "module": "test_auth_qa",
            "class": "AuthQA",
            "description": "Tests login, JWT tokens, and access control"
        },
        {
            "name": "Assistant Configuration",
            "module": "test_assistant_qa",
            "class": "AssistantQA",
            "description": "Tests OpenAI assistant and vector store management"
        },
        {
            "name": "Chat History",
            "module": "test_chat_history_qa",
            "class": "ChatHistoryQA",
            "description": "Tests session creation, retrieval, and user association"
        },
        {
            "name": "Document Management",
            "module": "test_document_qa",
            "class": "DocumentQA",
            "description": "Tests document upload, storage, and retrieval"
        },
        {
            "name": "Chat Functionality",
            "module": "test_chat_qa",
            "class": "ChatQA",
            "description": "Tests chat API, message processing, and responses"
        },
        {
            "name": "API Endpoints",
            "module": "test_api_qa",
            "class": "ApiQA",
            "description": "Tests all REST API endpoints and responses"
        },
        {
            "name": "Frontend Integration",
            "module": "test_frontend_qa",
            "class": "FrontendQA",
            "description": "Tests frontend-backend communication"
        }
    ]
    
    # Track results
    results = []
    total_tests = len(test_suites)
    passed_tests = 0
    
    # Run each test suite
    for suite in test_suites:
        print(f"\n{'='*70}")
        print(f"📋 Test Suite: {suite['name']}")
        print(f"   Description: {suite['description']}")
        print(f"{'='*70}")
        
        start_time = time.time()
        
        # Check if module exists
        module_path = os.path.join(os.path.dirname(__file__), f"{suite['module']}.py")
        if not os.path.exists(module_path):
            print(f"⚠️  Skipping - Test file not found: {suite['module']}.py")
            results.append({
                "suite": suite['name'],
                "status": "SKIPPED",
                "message": "Test file not found",
                "duration": 0
            })
            continue
        
        # Run the test
        success, message = run_test_module(suite['module'], suite['class'])
        duration = time.time() - start_time
        
        # Record result
        status = "PASSED" if success else "FAILED"
        results.append({
            "suite": suite['name'],
            "status": status,
            "message": message,
            "duration": duration
        })
        
        if success:
            passed_tests += 1
            print(f"✅ {suite['name']}: PASSED ({duration:.2f}s)")
        else:
            print(f"❌ {suite['name']}: FAILED - {message} ({duration:.2f}s)")
    
    # Generate summary report
    print("\n" + "="*70)
    print(" "*25 + "QA TEST SUMMARY REPORT")
    print("="*70)
    
    print(f"\nTest Execution Summary:")
    print(f"  Total Test Suites: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {total_tests - passed_tests - sum(1 for r in results if r['status'] == 'SKIPPED')}")
    print(f"  Skipped: {sum(1 for r in results if r['status'] == 'SKIPPED')}")
    
    # Calculate pass rate (excluding skipped tests)
    executed_tests = [r for r in results if r['status'] != 'SKIPPED']
    if executed_tests:
        pass_rate = (sum(1 for r in executed_tests if r['status'] == 'PASSED') / len(executed_tests)) * 100
        print(f"  Pass Rate: {pass_rate:.1f}%")
    else:
        pass_rate = 0
        print(f"  Pass Rate: N/A (no tests executed)")
    
    # Detailed results
    print(f"\nDetailed Results:")
    for result in results:
        status_icon = "✅" if result['status'] == "PASSED" else "❌" if result['status'] == "FAILED" else "⚠️"
        print(f"  {status_icon} {result['suite']}: {result['status']}")
        if result['status'] == "FAILED":
            print(f"      Error: {result['message']}")
    
    # Overall assessment
    print("\n" + "="*70)
    if pass_rate == 100:
        print("🎉 EXCELLENT! All QA tests passed successfully!")
        print("The system is ready for production.")
    elif pass_rate >= 80:
        print("⚠️  GOOD: Most tests passed, but some issues need attention.")
        print("Review failed tests before deployment.")
    elif pass_rate >= 60:
        print("⚠️  FAIR: Several tests failed. System needs improvements.")
        print("Fix critical issues before proceeding.")
    else:
        print("❌ CRITICAL: Many tests failed. System has significant issues.")
        print("Major fixes required before deployment.")
    
    print("="*70)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return exit code based on results
    return 0 if pass_rate == 100 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)