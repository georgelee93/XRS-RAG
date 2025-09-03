# QA Testing Guide for RAG Chatbot

## Overview
This guide documents the comprehensive QA testing process for the RAG Chatbot system to ensure all components work correctly and integration issues are caught early.

## Test Suites

### 1. API Tests (`api_tests/`)
Tests backend API endpoints with proper authentication.

#### Basic API Test
```bash
python3 api_tests/quick_test.py
```
- Tests health endpoint
- Tests document list
- Tests chat functionality
- Tests frontend accessibility

#### Authenticated API Test
```bash
python3 api_tests/authenticated_test.py
```
- Uses test credentials: test11@ca1996.co.kr / Qq123456
- Tests all endpoints with Bearer token authentication
- Validates response structures

#### Content-Type Validation Test ⭐ NEW
```bash
python3 api_tests/content_type_test.py
```
- **CRITICAL**: Tests that chat API correctly expects FormData, not JSON
- Validates content-type handling for all endpoints
- Catches frontend-backend format mismatches

### 2. Browser Tests (`browser_tests/`)
Tests UI functionality using Playwright.

#### Standard Browser Test
```bash
python3 browser_tests/authenticated_browser_test.py
```
- Tests login flow
- Tests chat interface
- Tests document management
- Tests responsive design

#### Enhanced Browser Test ⭐ NEW
```bash
python3 browser_tests/enhanced_browser_test.py
```
- **CRITICAL**: Captures browser console errors
- Monitors API request/response status codes
- Validates content-type headers in actual browser requests
- Detects JavaScript errors that API tests miss

### 3. Integration Tests (`integration_tests/`) ⭐ NEW

#### Frontend-Backend Integration Test
```bash
python3 integration_tests/frontend_backend_test.py
```
- Tests actual data flow between frontend and backend
- Validates response format matches frontend expectations
- Tests error handling scenarios
- Ensures consistency between what frontend sends and backend expects

### 4. Complete Test Suite
```bash
python3 run_all_tests.py
```
Runs all test suites and generates comprehensive report.

## Critical Test Points

### 1. Content-Type Validation
**Why it matters**: Frontend and backend must agree on data format.

**What went wrong before**:
- Frontend was sending `application/json`
- Backend expected `multipart/form-data`
- Result: 422 Unprocessable Entity errors

**How we catch it now**:
- Content-type test explicitly checks both formats
- Enhanced browser test monitors actual browser requests
- Integration test validates the complete flow

### 2. Response Format Validation
**Why it matters**: Frontend expects specific field names.

**What went wrong before**:
- Frontend checked `healthData.status === 'healthy'`
- Backend returned `healthy: true`
- Result: System incorrectly showed "점검 필요" (Needs Inspection)

**How we catch it now**:
- Integration tests validate exact response structure
- Tests check for expected field names
- Documentation of expected formats

### 3. Console Error Detection
**Why it matters**: API errors may not cause test failures but break user experience.

**How we catch it now**:
- Enhanced browser tests capture all console errors
- Monitor network requests for 4xx/5xx responses
- Validate that errors are properly handled

## Test Credentials

```
Email: test11@ca1996.co.kr
Password: Qq123456
Role: Admin (has access to document management)
```

## Running Tests

### Quick Validation
```bash
# Run these for quick validation
cd backend/qa
python3 api_tests/content_type_test.py  # Check API formats
python3 integration_tests/frontend_backend_test.py  # Check integration
```

### Full Test Suite
```bash
cd backend/qa
python3 run_all_tests.py  # Complete test suite
```

### Before Deployment Checklist
1. ✅ Run content-type validation test
2. ✅ Run integration test
3. ✅ Run enhanced browser test with console monitoring
4. ✅ Check for any 4xx/5xx responses
5. ✅ Verify no console errors in browser tests
6. ✅ Confirm system status shows "정상" not "점검 필요"

## Expected Test Results

### Success Criteria
- API Tests: 100% pass rate
- Browser Tests: 75%+ pass rate (chat response timing can be partial)
- Content-Type Tests: 100% pass rate
- Integration Tests: 100% pass rate
- No console errors in browser tests
- No 422 errors in API calls

### Known Issues
1. **Chat Response Display Timing**: Browser tests may show partial success due to async response rendering - this is acceptable if API returns 200.

2. **Admin Redirect**: Test user has admin privileges, so login redirects to admin.html instead of chat.html - this is expected behavior.

## Adding New Tests

When adding new features:

1. **Update API Tests**: Add test for new endpoint
2. **Update Content-Type Test**: Ensure correct format validation
3. **Update Integration Test**: Validate frontend-backend consistency
4. **Update Browser Test**: Add UI interaction test
5. **Check Console Errors**: Ensure no new JavaScript errors

## Common Issues and Solutions

### Issue: 422 Unprocessable Entity
**Cause**: Wrong content-type (JSON vs FormData)
**Solution**: Check api.js matches backend Form() expectations

### Issue: System shows "점검 필요"
**Cause**: Frontend checking wrong field name
**Solution**: Verify response field names match frontend expectations

### Issue: Tests pass but UI broken
**Cause**: Tests not checking actual browser behavior
**Solution**: Run enhanced browser tests with console monitoring

## Test Reports

Reports are saved in `backend/qa/reports/` directory:
- `authenticated_test_*.json` - API test results
- `content_type_test_*.json` - Content validation results
- `integration_test_*.json` - Integration test results
- `enhanced_browser_test_*.json` - Browser test with console errors
- `final_qa_summary_*.txt` - Overall QA summary

## Continuous Improvement

After each bug found in production:
1. Add a test that would have caught it
2. Update this guide with the scenario
3. Ensure all similar issues are covered

## Contact

For test failures or questions:
- Check error logs in `reports/` directory
- Verify test credentials are still valid
- Ensure backend and frontend are running on correct ports