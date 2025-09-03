#!/bin/bash

echo "=========================================="
echo "RAG Chatbot Frontend UI Test Runner"
echo "=========================================="
echo

# Run comprehensive setup check
echo "🔍 Running comprehensive setup check..."
if python3 check_ui_setup.py; then
    echo "✅ Setup check passed"
else
    echo "❌ Setup check failed"
    exit 1
fi

echo
echo "🚀 Starting Frontend UI Tests..."
echo "This will:"
echo "  1. Launch Chrome browser (visible)"
echo "  2. Navigate through the web interface"
echo "  3. Test document upload functionality"
echo "  4. Test chat interactions"
echo "  5. Verify UI responsiveness"
echo "  6. Take screenshots for verification"
echo

# Change to the QA directory
cd "$(dirname "$0")"

# Install dependencies if needed
echo "📦 Installing required dependencies..."
python3 -m pip install playwright aiohttp python-dotenv supabase &> /dev/null
python3 -m playwright install &> /dev/null

echo "🎭 Running Playwright UI tests..."
echo

# Run the test suite
python3 frontend_ui_test.py

echo
echo "📸 Screenshots saved to /tmp/"
echo "📄 Test report saved to frontend_ui_test_report.json"
echo
echo "✅ Frontend UI testing complete!"