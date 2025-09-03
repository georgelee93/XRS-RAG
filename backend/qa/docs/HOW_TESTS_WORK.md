# How RAG Chatbot Tests Work

## Overview

The test suite verifies the complete flow of the RAG Chatbot system, from document upload through AI processing to database logging. Here's how each test scenario works:

## Test Scenarios

### 1. Document Upload & Storage Flow

**What it tests:**
- File upload from web interface → OpenAI API
- Correct filename preservation in OpenAI
- File storage in Supabase storage bucket
- Database record creation in document_registry

**How it works:**
```
1. Create test file with known content
2. Upload via /api/documents/upload endpoint
3. Verify in OpenAI: Check file exists with correct name
4. Verify in Supabase: Check file in storage bucket
5. Verify in Database: Check document_registry table
```

**What can go wrong:**
- File extension missing (causes 422 error)
- OpenAI API key invalid
- Supabase storage permissions
- Database connection issues

### 2. Chat API Connection Test

**What it tests:**
- Chat endpoint is responsive
- Messages are processed
- AI assistant responds
- Response time is acceptable

**How it works:**
```
1. Send test message to /api/chat
2. Include proper session_id (UUID format)
3. Wait for AI response
4. Verify response structure and timing
```

**Success criteria:**
- Status 200 returned
- Response contains success: true
- Response time < 10 seconds
- Valid response text received

### 3. Document Retrieval Through Chat

**What it tests:**
- Assistant can access uploaded documents
- Vector store search is working
- File content is retrievable
- Context is properly used

**How it works:**
```
1. Upload document with specific test content
2. Ask question about that content via chat
3. Verify response contains information from document
4. Check that assistant references the document
```

**Example:**
- Upload: "Test ID: QA_2025_0814"
- Ask: "What is the Test ID?"
- Verify: Response contains "QA_2025_0814"

### 4. Vector Store Integrity

**What it tests:**
- Only one assistant exists (no duplicates)
- Assistant is connected to vector store
- No orphaned "untitled" vector stores
- Vector store contains uploaded files

**How it works:**
```
1. List all assistants from OpenAI
2. Filter for "청암" or "RAG" in name
3. Verify count = 1
4. Get assistant's vector_store_ids
5. List all vector stores
6. Check for "untitled" stores (should be 0)
```

**Previous issue (now fixed):**
- File attachments in messages created new vector stores
- Solution: Removed attachments from send_message

### 5. Usage Tracking & Database Logging

**What it tests:**
- Chat messages saved to database
- Each message has UUID
- Timestamps are recorded
- Usage metrics tracked
- Document access logged

### 6. Frontend UI Testing (New)

**What it tests:**
- Web interface loads properly at http://localhost:3001
- Document upload through admin UI works
- Chat form accepts messages and shows responses
- UI elements are responsive across screen sizes
- Chat history sidebar functions correctly
- Document list displays uploaded files

**How it works:**
```
1. Launch Chrome browser via Playwright
2. Navigate to chat.html and admin.html pages
3. Upload test document through file input UI
4. Send chat messages through web form
5. Wait for AI responses to appear in UI
6. Verify UI elements are present and functional
7. Test responsive design on different screen sizes
8. Take screenshots for visual verification
9. Clean up browser and test data
```

**Test sequence:**
- Page Navigation: Load chat interface
- Document Upload: Use admin panel file upload
- Chat Interaction: Send message and verify response
- Document List: Check uploaded files appear
- Chat History: Verify sidebar conversation storage
- Document Retrieval: Ask AI about uploaded content
- UI Responsiveness: Test mobile/tablet/desktop views

**How it works (Backend Usage Tracking):**
```
1. Send message with known session_id
2. Wait for processing (2 seconds)
3. Query chat_messages table by session_id
4. Verify message exists with:
   - Proper UUID as id
   - Correct session_id
   - Timestamp (created_at)
   - Message content
5. Check usage_tracking table
6. Check document_usage if files involved
```

**Database tables checked:**
- `chat_messages`: Message history
- `usage_tracking`: API usage metrics
- `document_usage`: Document access logs
- `document_registry`: Uploaded documents

## Test Files

### quick_test.py
- Basic health checks
- Simple API verification
- Fast execution (< 10 seconds)
- Good for quick validation

### comprehensive_test.py
- Full end-to-end testing
- Document upload flow
- Vector store verification
- Database logging checks
- Cleanup after testing

### test_flow_demo.py
- Educational demonstration
- Shows each step clearly
- Explains what's happening
- No actual file uploads

### frontend_ui_test.py (Playwright)
- Comprehensive browser-based UI testing
- Tests actual web interface at http://localhost:3001
- Document upload through admin UI
- Chat interactions through web form
- UI responsiveness and element verification
- Screenshot capture for visual verification

### automated_tests.py (Playwright)
- Browser-based UI testing
- Requires Playwright MCP
- Tests actual user interactions
- Currently has setup issues

## Current Test Results

✅ **Passing Tests:**
- Backend health check
- Chat API functionality
- Document list retrieval
- Frontend accessibility

⚠️ **Known Issues:**
- Document upload via test needs proper file format
- Playwright browser automation needs fixing
- Some database UUID constraints

## Running Tests

```bash
# Quick validation
cd backend/qa
python3 quick_test.py

# Demonstration (no uploads)
python3 test_flow_demo.py

# Comprehensive backend testing (with cleanup)
python3 comprehensive_test.py

# Frontend UI testing (requires frontend running at :3001)
./run_ui_tests.sh
# Or directly:
python3 frontend_ui_test.py
```

## Test Data Flow

```
User Action → API Endpoint → Backend Processing → External Services → Database
     ↓             ↓                ↓                    ↓              ↓
  Upload      /api/docs      validate_file         OpenAI API      Supabase
  Chat        /api/chat      process_msg          Vector Store     chat_msgs
  List        /api/docs      get_documents        Storage API      doc_registry
```

## Success Criteria

A fully successful test run verifies:
1. ✅ All APIs respond correctly
2. ✅ Documents upload with proper names
3. ✅ Chat can access document content
4. ✅ No duplicate assistants/vector stores
5. ✅ All interactions logged to database
6. ✅ Response times within thresholds
7. ✅ Error handling works properly

This ensures the system works end-to-end for real users.