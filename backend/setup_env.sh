#!/bin/bash

# Environment setup script for deployment
# Source this file before running deploy.sh: source setup_env.sh

echo "🔧 Setting up deployment environment variables"
echo ""
echo "Please enter the required configuration values:"
echo ""

# Required variables
read -p "Enter your OpenAI API Key (sk-...): " OPENAI_API_KEY
export OPENAI_API_KEY

# Optional variables
read -p "Enter JWT Secret (press Enter to skip): " JWT_SECRET
if [ -n "$JWT_SECRET" ]; then
    export JWT_SECRET
fi

read -p "Enter OpenAI Assistant ID (press Enter to auto-create): " OPENAI_ASSISTANT_ID
if [ -n "$OPENAI_ASSISTANT_ID" ]; then
    export OPENAI_ASSISTANT_ID
fi

read -p "Enter frontend domain for CORS (e.g., https://your-app.web.app): " CORS_ORIGINS
if [ -n "$CORS_ORIGINS" ]; then
    export CORS_ORIGINS
fi

read -p "Enter GCP Project ID (default: rag-chatbot-20250806): " GCP_PROJECT_ID
if [ -z "$GCP_PROJECT_ID" ]; then
    GCP_PROJECT_ID="rag-chatbot-20250806"
fi
export GCP_PROJECT_ID

read -p "Enter GCP Region (default: us-central1): " GCP_REGION
if [ -z "$GCP_REGION" ]; then
    GCP_REGION="us-central1"
fi
export GCP_REGION

# BigQuery setup
read -p "Do you want to enable BigQuery? (y/n): " ENABLE_BQ
if [ "$ENABLE_BQ" = "y" ] || [ "$ENABLE_BQ" = "Y" ]; then
    read -p "Enter path to BigQuery service account JSON: " BQ_SA_PATH
    if [ -f "$BQ_SA_PATH" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$BQ_SA_PATH"
        
        read -p "Enter BigQuery dataset name (default: ca_stats): " BIGQUERY_DATASET
        if [ -z "$BIGQUERY_DATASET" ]; then
            BIGQUERY_DATASET="ca_stats"
        fi
        export BIGQUERY_DATASET
    else
        echo "⚠️  Service account file not found: $BQ_SA_PATH"
    fi
fi

echo ""
echo "✅ Environment variables set:"
echo "   OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
[ -n "$JWT_SECRET" ] && echo "   JWT_SECRET: ***"
[ -n "$OPENAI_ASSISTANT_ID" ] && echo "   OPENAI_ASSISTANT_ID: $OPENAI_ASSISTANT_ID"
[ -n "$CORS_ORIGINS" ] && echo "   CORS_ORIGINS: $CORS_ORIGINS"
echo "   GCP_PROJECT_ID: $GCP_PROJECT_ID"
echo "   GCP_REGION: $GCP_REGION"
[ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && echo "   BigQuery: Enabled"
[ -n "$BIGQUERY_DATASET" ] && echo "   BIGQUERY_DATASET: $BIGQUERY_DATASET"
echo ""
echo "Now run: ./deploy.sh"