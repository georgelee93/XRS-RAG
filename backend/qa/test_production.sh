#!/bin/bash
# Test production deployment (read-only tests)

echo "=================================="
echo "PRODUCTION DEPLOYMENT TEST"
echo "=================================="
echo ""
echo "This will run READ-ONLY tests against production."
echo "No data will be created or modified."
echo ""

# Set production URLs
export QA_ENV="production"
export QA_BACKEND_URL="https://rag-backend-pkp7h5g2eq-uc.a.run.app"
export QA_FRONTEND_URL="https://rag-chatbot-20250806.web.app"

# Run the test
python3 qa/api_tests/deployable_test.py --env production

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Production tests passed!"
else
    echo ""
    echo "❌ Production tests failed!"
    exit 1
fi