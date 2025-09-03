#!/bin/bash

# Update Cloud Run service with environment variables from .env file

echo "📦 Updating Cloud Run environment variables..."

# Load environment variables from .env file
if [ -f .env ]; then
    # Extract only the needed variables more carefully
    while IFS='=' read -r key value; do
        case "$key" in
            OPENAI_API_KEY|SUPABASE_URL|SUPABASE_ANON_KEY|ENVIRONMENT|GCP_PROJECT_ID)
                # Remove quotes and trailing comments
                value="${value%\"}"
                value="${value#\"}"
                value="${value%%#*}"
                export "$key=$value"
                ;;
        esac
    done < <(grep -E '^(OPENAI_API_KEY|SUPABASE_URL|SUPABASE_ANON_KEY|ENVIRONMENT|GCP_PROJECT_ID)=' .env)
else
    echo "Error: .env file not found!"
    exit 1
fi

# Service configuration
SERVICE_NAME="rag-backend"
REGION="us-central1"
PROJECT_ID="rag-chatbot-20250806"

# Update Cloud Run service with environment variables
echo "🚀 Updating Cloud Run service..."

/Applications/google-cloud-sdk/bin/gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --update-env-vars="OPENAI_API_KEY=$OPENAI_API_KEY" \
    --update-env-vars="SUPABASE_URL=$SUPABASE_URL" \
    --update-env-vars="SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
    --update-env-vars="ENVIRONMENT=production" \
    --update-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
    --update-env-vars="CORS_ORIGINS=https://rag-chatbot-20250806.web.app,https://rag-chatbot-20250806.firebaseapp.com,http://localhost:3000"

if [ $? -eq 0 ]; then
    echo "✅ Cloud Run service updated successfully!"
    echo ""
    echo "Service URL: https://rag-backend-drmq5dg22q-uc.a.run.app"
else
    echo "❌ Failed to update Cloud Run service"
    exit 1
fi