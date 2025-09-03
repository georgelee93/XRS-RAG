# Frontend UI Testing Guide

## Overview

The `frontend_ui_test.py` script provides comprehensive testing of the RAG chatbot's web interface using Playwright automation. It tests the actual user flow through the browser, simulating real user interactions.

## What It Tests

### 1. Page Navigation & Loading
- ✅ Chat page loads at http://localhost:3001/chat.html
- ✅ All essential UI elements are present
- ✅ Form inputs, buttons, and containers load properly

### 2. Document Upload via Admin UI
- ✅ Admin page navigation
- ✅ Upload modal functionality  
- ✅ File input selection
- ✅ Upload confirmation and success feedback
- ✅ File appears in document list

### 3. Chat Interface Interaction
- ✅ Message input and send functionality
- ✅ User message appears in chat
- ✅ AI typing indicator shows
- ✅ AI response is received and displayed
- ✅ Input field clears after sending

### 4. Document List Management
- ✅ Uploaded documents appear in admin panel
- ✅ Document search functionality
- ✅ Document count displays correctly

### 5. Chat History Sidebar
- ✅ Conversations saved to sidebar
- ✅ New chat button functionality
- ✅ Conversation history persistence

### 6. Document Retrieval Through Chat
- ✅ AI can find and reference uploaded documents
- ✅ Specific content from test documents is retrievable
- ✅ Context-aware responses

### 7. UI Responsiveness
- ✅ Mobile view (375x812)
- ✅ Tablet view (768x1024) 
- ✅ Desktop view (1920x1080)
- ✅ Interactive element functionality
- ✅ Hover and focus states

## Prerequisites

### Required Services
1. **Frontend Server**: Must be running at `http://localhost:3001`
   ```bash
   cd frontend && npm run dev
   ```

2. **Backend Server**: Must be running at `http://localhost:8080`
   ```bash
   cd backend && python3 main.py
   ```

### Dependencies
- Python 3.8+
- Playwright
- aiohttp
- python-dotenv
- supabase-py

## Running the Tests

### Easy Method (Recommended)
```bash
cd backend/qa
./run_ui_tests.sh
```

This script will:
- Check if frontend/backend are running
- Install dependencies automatically
- Run the full test suite
- Show test results and screenshot locations

### Manual Method
```bash
cd backend/qa
python3 -m pip install playwright aiohttp python-dotenv supabase
python3 -m playwright install
python3 frontend_ui_test.py
```

## Test Output

### Console Output
The test provides real-time feedback:
```
======================================================================
FRONTEND UI TEST SUITE - PLAYWRIGHT AUTOMATION
======================================================================
Testing frontend at: http://localhost:3001
Test session ID: 12345678-1234-1234-1234-123456789012

🌐 TEST 1: Browser Navigation & Page Load
--------------------------------------------------
✅ Page Navigation: All elements loaded

📝 TEST 2: Document Upload via UI
----------------------------------------
✅ Document Upload UI: Upload completed

💬 TEST 3: Chat Interface Interaction
---------------------------------------------
✅ User Message Display: Message appears in chat
✅ AI Response Received: AI responded
✅ Input Field Cleared: Input cleared after send
...
```

### Screenshots
Visual verification screenshots are saved to `/tmp/`:
- `chat_page_loaded.png` - Initial page load
- `upload_result.png` - After document upload
- `before_send.png` - Before sending chat message
- `after_response.png` - After AI response
- `document_list.png` - Admin document list
- `responsive_*.png` - Different screen sizes

### Test Report
Detailed JSON report saved to `frontend_ui_test_report.json`:
```json
[
  {
    "test": "Page Navigation",
    "passed": true,
    "details": "All elements loaded",
    "timestamp": "2025-08-14T10:30:00.000Z"
  },
  ...
]
```

## Browser Behavior

### Visible Browser
- Tests run in **non-headless mode** (browser window visible)
- This allows you to see exactly what's happening
- Useful for debugging and verification
- Chrome/Chromium browser is used

### Test Flow
1. **Launch Browser** → Opens Chrome
2. **Navigate to Chat** → Loads main interface
3. **Test Elements** → Verifies UI components
4. **Go to Admin** → Tests upload functionality
5. **Upload File** → Creates and uploads test document
6. **Back to Chat** → Tests chat interactions
7. **Send Messages** → Verifies chat flow
8. **Check Responses** → Waits for AI replies
9. **Test Responsive** → Different screen sizes
10. **Cleanup** → Closes browser and temporary files

## Troubleshooting

### Frontend Not Running
```
❌ Frontend is not running at http://localhost:3001
Please start the frontend server first:
cd frontend && npm run dev
```

**Solution**: Start the frontend development server.

### Backend Not Running
```
❌ Backend is not running at http://localhost:8080
Please start the backend server first:
cd backend && python3 main.py
```

**Solution**: Start the backend API server.

### Playwright Installation Issues
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Solution**: 
```bash
python3 -m playwright install
```

### Element Not Found
```
playwright._impl._api_types.TimeoutError: Timeout 10000ms exceeded
```

**Possible causes**:
- Page still loading
- Element selector changed
- JavaScript error preventing load
- Network connectivity issues

### Upload Fails
- Check file permissions
- Verify backend upload endpoint
- Check Supabase storage configuration

## Test Data

### Test Document Content
Each test run creates a unique document:
```
Frontend UI Test Document
=========================

This document was uploaded via UI automation testing.

Test Information:
- Test ID: UI_TEST_2025_0814
- Upload Method: Playwright UI Automation
- Browser: Chromium
- Timestamp: [current time]

The chatbot should be able to find this test document.
```

### Session Management
- Each test run uses a unique session ID
- Test data is created with timestamps
- Cleanup removes temporary files

## Integration with Existing Tests

The UI tests complement the existing backend tests:

- **quick_test.py** → API health checks
- **comprehensive_test.py** → Backend API flows  
- **frontend_ui_test.py** → Web interface flows

Run all tests for complete coverage:
```bash
# Backend tests
python3 quick_test.py
python3 comprehensive_test.py

# Frontend UI tests
./run_ui_tests.sh
```

## Success Criteria

A successful UI test run verifies:
- ✅ All web pages load without errors
- ✅ File upload works through web interface
- ✅ Chat messages send and receive responses
- ✅ UI is responsive across device sizes
- ✅ Navigation and interactive elements work
- ✅ Document retrieval functions through chat
- ✅ Visual elements render correctly

This ensures the complete user experience works as expected.