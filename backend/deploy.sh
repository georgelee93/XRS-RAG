#!/bin/bash

# Deploy script for RAG Chatbot Backend
# This script handles environment variables and deployment to Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-rag-chatbot-20250806}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-rag-backend}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying RAG Chatbot Backend to Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"

# Check if required environment variables are set
check_env() {
    if [ -z "${!1}" ]; then
        echo "❌ Error: $1 is not set"
        echo "Please set it with: export $1=your-value"
        exit 1
    else
        echo "✅ $1 is set"
    fi
}

# Check required variables
echo ""
echo "Checking environment variables..."
check_env "OPENAI_API_KEY"

# Optional variables
if [ -n "$JWT_SECRET" ]; then
    echo "✅ JWT_SECRET is set"
else
    echo "⚠️  JWT_SECRET not set (using default - not recommended for production)"
fi

if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "✅ BigQuery service account found"
    BIGQUERY_ENABLED="true"
else
    echo "ℹ️  BigQuery service account not found (BigQuery features disabled)"
    BIGQUERY_ENABLED="false"
fi

# Create secrets in Secret Manager
echo ""
echo "Setting up secrets in Secret Manager..."

# Create or update OpenAI API key secret
echo -n "${OPENAI_API_KEY}" | gcloud secrets create OPENAI_API_KEY --data-file=- 2>/dev/null || \
echo -n "${OPENAI_API_KEY}" | gcloud secrets versions add OPENAI_API_KEY --data-file=-

# Create or update JWT secret if provided
if [ -n "$JWT_SECRET" ]; then
    echo -n "${JWT_SECRET}" | gcloud secrets create JWT_SECRET --data-file=- 2>/dev/null || \
    echo -n "${JWT_SECRET}" | gcloud secrets versions add JWT_SECRET --data-file=-
fi

# Create or update BigQuery credentials if provided
if [ "$BIGQUERY_ENABLED" == "true" ]; then
    gcloud secrets create GOOGLE_APPLICATION_CREDENTIALS --data-file="${GOOGLE_APPLICATION_CREDENTIALS}" 2>/dev/null || \
    gcloud secrets versions add GOOGLE_APPLICATION_CREDENTIALS --data-file="${GOOGLE_APPLICATION_CREDENTIALS}"
fi

# Build the Docker image
echo ""
echo "Building Docker image..."
docker build -t ${IMAGE_NAME} .

# Push to Container Registry
echo ""
echo "Pushing image to Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."

DEPLOY_COMMAND="gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production"

# Add CORS origins if provided
if [ -n "$CORS_ORIGINS" ]; then
    DEPLOY_COMMAND="${DEPLOY_COMMAND},CORS_ORIGINS=${CORS_ORIGINS}"
fi

# Add BigQuery dataset if provided
if [ -n "$BIGQUERY_DATASET" ]; then
    DEPLOY_COMMAND="${DEPLOY_COMMAND},BIGQUERY_DATASET=${BIGQUERY_DATASET}"
fi

# Add project ID
DEPLOY_COMMAND="${DEPLOY_COMMAND},GCP_PROJECT_ID=${PROJECT_ID}"

# Add OpenAI Assistant ID if provided
if [ -n "$OPENAI_ASSISTANT_ID" ]; then
    DEPLOY_COMMAND="${DEPLOY_COMMAND},OPENAI_ASSISTANT_ID=${OPENAI_ASSISTANT_ID}"
fi

# Add secrets
DEPLOY_COMMAND="${DEPLOY_COMMAND} \
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest"

if [ -n "$JWT_SECRET" ]; then
    DEPLOY_COMMAND="${DEPLOY_COMMAND},JWT_SECRET=JWT_SECRET:latest"
fi

if [ "$BIGQUERY_ENABLED" == "true" ]; then
    # We'll mount the secret as a file
    DEPLOY_COMMAND="${DEPLOY_COMMAND} \
      --set-secrets /tmp/gcp-key.json=GOOGLE_APPLICATION_CREDENTIALS:latest \
      --set-env-vars GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json"
fi

# Execute deployment
eval ${DEPLOY_COMMAND}

# Get the service URL
echo ""
echo "Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌍 Service URL: ${SERVICE_URL}"
echo ""
echo "📝 Next steps:"
echo "1. Update your frontend configuration with the backend URL:"
echo "   ${SERVICE_URL}/api"
echo "2. Test the health endpoint:"
echo "   curl ${SERVICE_URL}/api/health"
echo "3. Monitor logs:"
echo "   gcloud run services logs tail ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "⚠️  Important: Make sure to update CORS_ORIGINS with your frontend domain:"
echo "   export CORS_ORIGINS=https://your-frontend-domain.com"
echo "   ./deploy.sh"