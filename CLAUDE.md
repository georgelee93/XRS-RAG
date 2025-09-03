# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) chatbot system called "청암 챗봇" (Cheongam Chatbot) - an AI-powered document retrieval and chat system using OpenAI Assistant API v2 and Supabase.

## High-level Architecture

The system follows a client-server architecture with:
- **Backend**: FastAPI application serving REST APIs, integrating with OpenAI Assistant API for chat functionality and Supabase for data storage
- **Frontend**: Vanilla JavaScript + Tailwind CSS web interface with multiple pages (admin, chat, login)
- **Storage**: Supabase for PostgreSQL database and file storage, OpenAI vector stores for document retrieval
- **Optional**: BigQuery integration for analytics (can be disabled via BIGQUERY_ENABLED env var)

Key architectural decisions:
- Uses OpenAI Assistant API v2 with file search capabilities for document-aware conversations
- Session management maintains chat context across conversations
- Document processing supports PDF, TXT, MD, DOCX formats
- Modular service architecture with clear separation of concerns

## Development Commands

### Backend
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Run tests
pytest

# Deploy to Google Cloud Run
gcloud run deploy rag-backend --source . --region us-central1 --platform managed --allow-unauthenticated
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run development server (port 3000)
npm run dev

# Build for production
npm run build

# Deploy to Firebase
firebase deploy --only hosting
```

## Project Structure

- `backend/` - FastAPI backend
  - `api/routes.py` - API endpoint definitions
  - `core/` - Business logic and services
    - `chat_interface.py` - OpenAI chat integration
    - `document_manager_supabase.py` - Document management
    - `supabase_client.py` - Supabase client wrapper
    - `retrieval_client.py` - OpenAI retrieval operations
    - `config.py` - Configuration management with Pydantic
  - `main.py` - Application entry point

- `frontend/` - Web interface
  - `public/` - Static HTML files (admin.html, chat.html, login.html)
  - `src/js/` - Modular JavaScript (api.js, auth.js, chat.js)
  - `src/styles/` - Tailwind CSS configuration
  - `vite.config.js` - Vite build configuration

## Environment Configuration

Required environment variables for backend:
- `OPENAI_API_KEY` - OpenAI API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key

Optional:
- `BIGQUERY_ENABLED` - Enable/disable BigQuery integration (default: false)
- `GCP_PROJECT_ID` - Google Cloud project ID (if using BigQuery)
- `PORT` - Server port (default: 8080)
- `CORS_ORIGINS` - Allowed CORS origins list

## API Endpoints

Key endpoints (all prefixed with `/api`):
- `POST /documents/upload` - Upload documents to vector store
- `GET /documents` - List all documents
- `DELETE /documents/{id}` - Delete a document
- `POST /chat` - Send chat message with document context
- `GET /sessions` - List chat sessions
- `GET /usage/summary` - Get usage statistics
- `GET /health/components` - System health check

## Deployment

The project includes deployment configurations for:
- **Google Cloud Run** - Backend deployment (`cloudbuild.yaml`, `Dockerfile`)
- **Firebase Hosting** - Frontend deployment (`firebase.json`)

Production URLs:
- Frontend: https://rag-chatbot-20250806.web.app
- Backend: https://rag-backend-223940753124.us-central1.run.app