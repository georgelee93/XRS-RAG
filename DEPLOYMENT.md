# Deployment Guide for RAG Chatbot with OpenAI Assistant API v2

## Overview
This guide covers deploying both the frontend and backend to Google Cloud Platform (GCP).

## Prerequisites
- Google Cloud SDK installed (`gcloud`)
- Docker installed
- Active GCP project with billing enabled
- OpenAI API key
- BigQuery service account (optional)

## Backend Deployment (Cloud Run)

### 1. Set Up GCP Project
```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

### 2. Environment Variables Setup (Recommended Approach)

⚠️ **Important**: We recommend using **direct environment variables** instead of Secret Manager to avoid connection issues.

**Option A: Direct Environment Variables (Recommended)**
```bash
# Set environment variables directly during deployment
gcloud run deploy rag-backend \
  --image gcr.io/$PROJECT_ID/rag-backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars \
    OPENAI_API_KEY="sk-your-openai-api-key",\
    SUPABASE_URL="your-supabase-url",\
    SUPABASE_ANON_KEY="your-supabase-anon-key",\
    ENVIRONMENT=production \
  --memory 2Gi \
  --timeout 300
```

**Option B: Secret Manager (Alternative - may cause connection issues)**
```bash
# Store OpenAI API key (be careful of newline characters)
echo -n "your-openai-api-key" | gcloud secrets create OPENAI_API_KEY --data-file=-

# Store other sensitive data
echo -n "your-supabase-url" | gcloud secrets create SUPABASE_URL --data-file=-
echo -n "your-supabase-anon-key" | gcloud secrets create SUPABASE_ANON_KEY --data-file=-

# If using BigQuery, store the service account key
gcloud secrets create GOOGLE_APPLICATION_CREDENTIALS --data-file=path/to/service-account-key.json
```

**Known Issue with Secret Manager**: Secret Manager may add newline characters to secrets, causing OpenAI API connection failures. If you encounter "Connection error" issues, switch to direct environment variables.

### 3. Create Dockerfile for Backend
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD ["python", "main_assistant_v2.py", "--host", "0.0.0.0", "--port", "8080"]
```

### 4. Create Cloud Build Configuration
```yaml
# backend/cloudbuild.yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/rag-backend', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/rag-backend']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'rag-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/rag-backend'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'ENVIRONMENT=production'
      - '--set-secrets'
      - 'OPENAI_API_KEY=OPENAI_API_KEY:latest'
      - '--set-secrets'
      - 'JWT_SECRET=JWT_SECRET:latest'
      - '--memory'
      - '2Gi'
      - '--timeout'
      - '300'
      - '--max-instances'
      - '10'

images:
  - 'gcr.io/$PROJECT_ID/rag-backend'
```

### 5. Deploy Backend
```bash
cd backend

# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Get the backend URL
gcloud run services describe rag-backend --region us-central1 --format 'value(status.url)'
```

### 6. Set Environment Variables in Cloud Run
```bash
# Set environment variables directly
gcloud run services update rag-backend \
  --region us-central1 \
  --update-env-vars \
    ENVIRONMENT=production,\
    CORS_ORIGINS="https://your-frontend-domain.com",\
    BIGQUERY_DATASET=ca_stats,\
    GCP_PROJECT_ID=$PROJECT_ID,\
    OPENAI_ASSISTANT_ID=your-assistant-id

# For BigQuery with service account
gcloud run services update rag-backend \
  --region us-central1 \
  --set-secrets GOOGLE_APPLICATION_CREDENTIALS=GOOGLE_APPLICATION_CREDENTIALS:latest:env=GOOGLE_APPLICATION_CREDENTIALS_JSON

# Note: You'll need to parse the JSON in your app:
# if os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
#     credentials = json.loads(os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'))
#     client = bigquery.Client.from_service_account_info(credentials)
```

## Frontend Deployment (Firebase Hosting)

### 1. Install Firebase CLI
```bash
npm install -g firebase-tools
firebase login
```

### 2. Initialize Firebase
```bash
cd frontend
firebase init hosting

# Select:
# - Use existing project or create new
# - Public directory: public
# - Single-page app: Yes
# - Automatic builds: No
```

### 3. Update API Configuration
```javascript
// frontend/src/js/config.js
const API_CONFIG = {
  development: {
    baseUrl: 'http://localhost:8000/api',
    websocketUrl: 'ws://localhost:8000/ws'
  },
  production: {
    baseUrl: 'https://rag-backend-xxxxx-uc.a.run.app/api',  // Your Cloud Run URL
    websocketUrl: 'wss://rag-backend-xxxxx-uc.a.run.app/ws'
  }
};

const CONFIG = {
  ...API_CONFIG[window.location.hostname === 'localhost' ? 'development' : 'production'],
  // other config
};

export default CONFIG;
```

### 4. Build and Deploy Frontend
```bash
# Deploy to Firebase
firebase deploy --only hosting

# Get the hosting URL
firebase hosting:sites:list
```

## Alternative: Frontend on Cloud Storage + CDN

### 1. Create Storage Bucket
```bash
gsutil mb -p $PROJECT_ID -c standard -l us-central1 gs://$PROJECT_ID-frontend
gsutil web set -m index.html -e 404.html gs://$PROJECT_ID-frontend
```

### 2. Deploy Frontend Files
```bash
cd frontend
gsutil -m rsync -r -d public/ gs://$PROJECT_ID-frontend/
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" gs://$PROJECT_ID-frontend/**/*.js
gsutil -m setmeta -h "Cache-Control:public, max-age=3600" gs://$PROJECT_ID-frontend/**/*.css
```

### 3. Set up Load Balancer with CDN
```bash
# Create backend bucket
gcloud compute backend-buckets create frontend-bucket \
  --gcs-bucket-name=$PROJECT_ID-frontend

# Create URL map
gcloud compute url-maps create frontend-lb \
  --default-backend-bucket=frontend-bucket

# Create HTTPS proxy
gcloud compute target-https-proxies create frontend-https-proxy \
  --url-map=frontend-lb \
  --ssl-certificates=your-ssl-cert

# Create forwarding rule
gcloud compute forwarding-rules create frontend-https-rule \
  --global \
  --target-https-proxy=frontend-https-proxy \
  --ports=443
```

## Environment Variables Reference

### Backend (.env for local, Secret Manager for production)
```env
# Required
OPENAI_API_KEY=sk-xxx
ENVIRONMENT=production

# Optional but recommended
JWT_SECRET=your-secret-key
CORS_ORIGINS=https://your-frontend.com

# BigQuery (optional)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
BIGQUERY_DATASET=ca_stats
GCP_PROJECT_ID=your-project-id

# OpenAI Assistant (auto-created if not set)
OPENAI_ASSISTANT_ID=asst_xxx
```

### Setting Environment Variables in Cloud Run (One Command)
```bash
# All at once during deployment
gcloud run deploy rag-backend \
  --image gcr.io/$PROJECT_ID/rag-backend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars \
    ENVIRONMENT=production,\
    CORS_ORIGINS="https://your-frontend.com",\
    BIGQUERY_DATASET=ca_stats,\
    GCP_PROJECT_ID=$PROJECT_ID \
  --set-secrets \
    OPENAI_API_KEY=OPENAI_API_KEY:latest,\
    JWT_SECRET=JWT_SECRET:latest \
  --memory 2Gi \
  --timeout 300
```

## Monitoring and Logs

### View Backend Logs
```bash
gcloud run services logs read rag-backend --region us-central1 --limit 50
```

### View Backend Metrics
```bash
# Open in browser
gcloud run services describe rag-backend --region us-central1 --format 'value(status.url)'
# Then append /metrics or check Cloud Console
```

## Troubleshooting

### CORS Issues
1. Check backend CORS_ORIGINS environment variable
2. Ensure frontend is using HTTPS in production
3. Verify API URLs in frontend config

### Authentication Issues
1. Check JWT_SECRET is set in Cloud Run
2. Verify tokens are being sent in headers
3. Check Cloud Run IAM permissions

### BigQuery Connection Issues
1. Verify service account has BigQuery permissions:
   ```bash
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:your-service-account@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/bigquery.dataViewer"
   ```
2. Check GOOGLE_APPLICATION_CREDENTIALS secret is properly mounted
3. Verify BIGQUERY_DATASET exists

### OpenAI API Issues (Common Problem!)
**Problem**: "Connection error" or backend health check fails
**Root Cause**: Secret Manager adding newline characters to API keys

**Solution**:
1. **Switch to direct environment variables** (recommended):
   ```bash
   # Update existing service with direct env vars
   gcloud run services update rag-backend \
     --region us-central1 \
     --set-env-vars OPENAI_API_KEY="sk-your-actual-key"
   ```

2. **Alternative**: Fix Secret Manager secrets:
   ```bash
   # Recreate secret without newlines
   echo -n "sk-your-openai-key" | gcloud secrets versions add OPENAI_API_KEY --data-file=-
   ```

3. **Check API key validity**:
   ```bash
   curl -H "Authorization: Bearer sk-your-key" https://api.openai.com/v1/models
   ```

4. **Verify Cloud Run revision is using latest**:
   ```bash
   # Route all traffic to latest revision
   gcloud run services update-traffic rag-backend --region us-central1 --to-latest
   ```

### Frontend Connection Issues
**Problem**: "상태: 점검 필요" (Status: Needs Check)
**Solution**: Update frontend config with correct backend URL:
1. Get current backend URL:
   ```bash
   gcloud run services describe rag-backend --region us-central1 --format 'value(status.url)'
   ```
2. Update `frontend/src/js/config.js` with the correct URL
3. Rebuild and redeploy frontend

## CI/CD Pipeline (GitHub Actions)

### .github/workflows/deploy.yml
```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

env:
  PROJECT_ID: your-project-id
  REGION: us-central1

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - uses: google-github-actions/setup-gcloud@v1
      
      - name: Build and Deploy Backend
        run: |
          cd backend
          gcloud builds submit --config cloudbuild.yaml
  
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install and Deploy to Firebase
        run: |
          cd frontend
          npm ci
          npm install -g firebase-tools
          firebase deploy --token ${{ secrets.FIREBASE_TOKEN }}
```

## Cost Optimization

1. **Cloud Run**: Set max instances to prevent runaway costs
2. **BigQuery**: Use partitioned tables and query limits
3. **Cloud Storage**: Enable lifecycle policies for old files
4. **Monitoring**: Set up budget alerts

## Security Best Practices

1. **Never commit secrets** to git
2. **Use Secret Manager** for all sensitive data
3. **Enable Cloud Armor** for DDoS protection
4. **Set up Cloud IAP** for admin-only endpoints
5. **Use VPC Service Controls** for BigQuery access
6. **Enable audit logs** for compliance

## Quick Deployment Commands

```bash
# One-liner backend deployment (after initial setup)
cd backend && gcloud builds submit --config cloudbuild.yaml

# One-liner frontend deployment
cd frontend && firebase deploy --only hosting

# Update backend environment variables
gcloud run services update rag-backend --region us-central1 --update-env-vars KEY=value

# View backend logs
gcloud run services logs tail rag-backend --region us-central1
```