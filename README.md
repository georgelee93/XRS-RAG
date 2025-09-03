# 청암 챗봇 - OpenAI Assistant v2

청암 내부 사용을 위한 문서 Q&A 챗봇 (Document Q&A chatbot using OpenAI Assistant API v2)

## 🚀 Overview

A simplified chatbot system using OpenAI Assistant API v2 with built-in file search capabilities. No complex RAG implementation needed.

### Key Features
- 📄 **Document Management** - Upload, store, and manage various document types
- 💬 **AI Chat** - Context-aware conversations using OpenAI Assistant API v2
- 🗄️ **Supabase Integration** - Secure cloud storage and database
- 📊 **Usage Tracking** - Monitor API usage and costs
- 🔐 **Session Management** - Persistent chat sessions
- 🌐 **Modern UI** - Responsive web interface with Korean language support

## 🏗️ Architecture

```
RAG-Project/
├── backend/              # FastAPI backend application
│   ├── api/             # API routes and endpoints
│   ├── core/            # Business logic and services
│   │   ├── chat_interface.py      # OpenAI chat integration
│   │   ├── document_manager_supabase.py  # Document management
│   │   ├── supabase_client.py     # Supabase integration
│   │   └── retrieval_client.py    # OpenAI retrieval
│   ├── database/        # Database schemas and migrations
│   ├── docs/            # Backend documentation
│   └── main.py          # Application entry point
│
├── frontend/            # Web interface (Vanilla JS + Tailwind)
│   ├── public/          # Static HTML files
│   │   ├── index.html   # Landing page
│   │   ├── admin.html   # Admin dashboard
│   │   └── chat.html    # Chat interface
│   ├── src/             # JavaScript and CSS
│   │   ├── js/          # Modular JavaScript
│   │   └── styles/      # Tailwind CSS
│   └── package.json     # Frontend dependencies
│
└── README.md           # This file
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **OpenAI Assistant API v2** - Advanced AI with file search capabilities
- **Supabase** - PostgreSQL database and file storage
- **Python 3.9+** - Modern Python features

### Frontend
- **Vanilla JavaScript** - No framework dependencies
- **Tailwind CSS** - Utility-first styling
- **Vite** - Lightning-fast build tool
- **ES6 Modules** - Modern JavaScript architecture

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+
- Supabase account
- OpenAI API key

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd RAG-Project
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY
# - SUPABASE_URL
# - SUPABASE_ANON_KEY

# Set up Supabase database
# 1. Create a new Supabase project
# 2. Run backend/database/schema.sql in Supabase SQL editor
# 3. Create a storage bucket named "documents"

# Run the backend
python main.py
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Update VITE_API_URL if needed (default: http://localhost:8000/api)

# Run development server
npm run dev
```

### 4. Access the Application
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔑 Environment Variables

### Backend Environment Variables
```env
# Required
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional
PORT=8000
APP_ENV=development
DEBUG=True
LOG_LEVEL=INFO
```

### Frontend Environment Variables
```env
# API endpoint
VITE_API_URL=http://localhost:8000/api

# Feature flags
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG_LOGS=true
```

## 📦 Deployment

### Backend Deployment

The backend includes configurations for multiple platforms:

- **Railway**: `railway.toml`
- **Render**: `render.yaml`
- **Fly.io**: `fly.toml`
- **Docker**: `Dockerfile`

Example Railway deployment:
```bash
cd backend
railway up
```

### Frontend Deployment

Build and deploy the frontend:
```bash
cd frontend
npm run build

# Deploy to Vercel
vercel

# Or deploy to Netlify
netlify deploy --dir=dist --prod
```

## 🔒 Security

- **API Keys**: Never commit `.env` files
- **CORS**: Configure allowed origins in production
- **RLS**: Enable Row Level Security in Supabase
- **HTTPS**: Always use HTTPS in production
- **Authentication**: Implement user authentication for production use

## 📚 API Documentation

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload documents |
| GET | `/api/documents` | List all documents |
| DELETE | `/api/documents/{id}` | Delete a document |
| GET | `/api/documents/{id}/download` | Download a document |
| POST | `/api/chat` | Send chat message |
| GET | `/api/sessions` | List chat sessions |
| GET | `/api/usage/summary` | Get usage statistics |
| GET | `/api/health/components` | System health check |

Full API documentation available at `/docs` when running the backend.

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend linting
cd frontend
npm run lint
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential.