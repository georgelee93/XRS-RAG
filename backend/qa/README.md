# RAG Chatbot QA Testing Suite

## 📁 Directory Structure

```
qa/
├── config.py           # Multi-environment configuration
├── api_tests/          # API endpoint tests
│   ├── quick_test.py   # Basic health checks
│   ├── comprehensive_test.py  # Full API testing (local only)
│   ├── deployable_test.py     # Multi-environment testing
│   └── test_flow_demo.py      # Demo/educational
│
├── browser_tests/      # Browser UI automation
│   └── final_browser_test.py  # Working browser tests
│
├── docs/              # Documentation
│   ├── HOW_TESTS_WORK.md
│   ├── TESTING_APPROACHES.md
│   └── ...
│
├── reports/           # Test results
│   └── *.json         # Test reports
│
├── old_tests/         # Previous test versions
│   └── ...            # Archived for reference
│
└── run_all_tests.py   # Master test runner
```

## 🚀 Quick Start

### Run All Tests
```bash
cd backend/qa
python3 run_all_tests.py
```

### Test Different Environments

**Local Testing:**
```bash
# Comprehensive local test
python3 api_tests/comprehensive_test.py

# Deployable test for local
python3 api_tests/deployable_test.py --env local
```

**Production Testing (Read-Only):**
```bash
# Safe production test
./test_production.sh

# Or directly
python3 api_tests/deployable_test.py --env production
```

**Custom Environment:**
```bash
export QA_BACKEND_URL="https://your-backend.com"
export QA_FRONTEND_URL="https://your-frontend.com"
python3 api_tests/deployable_test.py --env staging
```

### Run Specific Tests

**API Tests Only:**
```bash
cd api_tests
python3 quick_test.py          # Quick validation (< 10 seconds)
python3 comprehensive_test.py  # Full API testing (local only)
python3 deployable_test.py     # Multi-environment testing
```

**Browser Tests Only:**
```bash
cd browser_tests
python3 final_browser_test.py  # UI automation tests
```

## ✅ Current Test Status

### API Tests (4/4 Passing) ✅
- **Backend Health** - ✅ Working
- **Document List** - ✅ Working
- **Chat API** - ✅ Working
- **Frontend Access** - ✅ Working

### Browser Tests (2/4 Passing) ⚠️
- **Login Page** - ❌ Login flow issue
- **Chat Message** - ❌ Response timing issue
- **Admin Page** - ✅ Working
- **Responsive Design** - ✅ Working

## 📋 Test Scenarios

### 1. Document Upload Flow
- Upload file via API
- Verify in OpenAI Storage
- Check Vector Store indexing
- Confirm Supabase storage
- Validate database record

### 2. Chat Functionality
- Send message with session ID
- Receive AI response
- Verify response time < 10s
- Check message logging

### 3. Document Retrieval
- Upload test document
- Ask questions about content
- Verify AI retrieves correct info
- No hallucination of documents

### 4. Vector Store Integrity
- Single assistant (no duplicates)
- Connected to vector store
- No orphaned "untitled" stores
- All files properly indexed

### 5. Usage Tracking
- Messages saved with UUID
- Timestamps recorded
- Usage metrics tracked
- Document access logged

## 🛡️ Deployment Safety

### Production Safety Features
- **Read-Only Tests**: No document uploads in production
- **No Data Modification**: Skip cleanup in production
- **Environment Detection**: Automatic safety based on environment
- **CI/CD Integration**: GitHub Actions workflow included

### Environment URLs

| Environment | Backend URL | Frontend URL |
|------------|-------------|--------------|
| Local | http://localhost:8080 | http://localhost:3000 |
| Production | https://rag-backend-pkp7h5g2eq-uc.a.run.app | https://rag-chatbot-20250806.web.app |
| Staging | Configure via env vars | Configure via env vars |

## 🔧 Test Configuration

### Prerequisites
- Python 3.9+
- Backend running on port 8080
- Frontend running on port 3001
- Test credentials: `test@cheongahm.com` / `1234`

### Required Packages
```bash
pip3 install aiohttp playwright python-dotenv openai supabase
python3 -m playwright install chromium
```

### Environment Variables
Create `.env` file in backend directory with:
```
OPENAI_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_ANON_KEY=your_key
```

## 📊 Test Reports

Reports are generated in `reports/` directory as JSON files:
- `test_report_YYYYMMDD_HHMMSS.json`

Each report includes:
- Timestamp
- Individual test results
- Pass/fail status
- Error messages if any
- Overall summary

## 🐛 Known Issues

### Browser Tests
1. **Login Flow** - Page title doesn't change after login
2. **Chat Response** - AI responses not captured (timing issue)

### Workarounds
- API tests provide backend validation
- Manual testing can verify UI functionality
- Screenshots capture current state

## 📸 Screenshots

Browser tests create screenshots in `/tmp/`:
- `test1_initial_page.png` - Login page
- `test2_chat_conversation.png` - Chat interface
- `test3_admin_page.png` - Admin panel
- `test4_responsive_*.png` - Different viewports

## 🎯 Test Coverage

| Component | API Test | Browser Test | Coverage |
|-----------|----------|--------------|----------|
| Backend Health | ✅ | ❌ | 100% |
| Document Upload | ✅ | ⚠️ | 80% |
| Chat Function | ✅ | ⚠️ | 75% |
| Vector Store | ✅ | ❌ | 100% |
| UI Elements | ❌ | ✅ | 50% |
| Responsive | ❌ | ✅ | 100% |
| Database | ✅ | ❌ | 100% |

**Overall Coverage: ~75%**

## 🔄 Continuous Testing

For CI/CD integration:
```bash
# Run tests and exit with proper code
python3 run_all_tests.py
echo $?  # 0 if passed, 1 if failed
```

## 📝 Adding New Tests

1. Create test file in appropriate directory
2. Follow existing test patterns
3. Update this README
4. Add to `run_all_tests.py` if needed

## 💡 Tips

- Run API tests first (faster, more stable)
- Browser tests may need Playwright reinstall
- Check screenshots for visual verification
- Review JSON reports for detailed results