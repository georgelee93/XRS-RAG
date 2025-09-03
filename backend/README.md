# RAG Chatbot Backend v2.0

A robust, production-ready backend service for document-based AI chatbot using OpenAI's Assistants API v2.

## 🚀 What's New in v2.0

- **Refactored Architecture**: Clean separation of concerns
- **Robust Delete**: Handles edge cases properly
- **Standardized Errors**: Consistent error handling
- **Better Naming**: Clear, unambiguous variable names
- **Improved Logging**: Comprehensive debugging support

## Features

- 📄 **Document Management**: Upload, list, delete documents with dual storage
- 💬 **Intelligent Chat**: AI responses based on uploaded documents
- 🗄️ **Dual Storage**: OpenAI for AI, Supabase for downloads
- 📊 **BigQuery Integration**: Optional analytics support
- 🔐 **Authentication**: Supabase Auth integration
- 🌏 **Korean Support**: Full support for Korean documents
- ⏰ **KST Timezone**: All timestamps in Korea Standard Time
- 🔍 **Session Management**: Persistent conversations
- 📈 **Usage Tracking**: Monitor API usage and costs
- ❤️ **Health Monitoring**: Component health checks

## Tech Stack

- **Framework**: FastAPI
- **AI**: OpenAI Assistant API v2 with File Search
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase Storage
- **Deployment**: Google Cloud Run
- **Language**: Python 3.11+

## Project Structure

```
backend/
├── api/              # API routes and endpoints
├── core/             # Core business logic
│   ├── chat_interface.py           # Chat functionality
│   ├── document_manager_supabase.py # Document management
│   ├── retrieval_client.py         # OpenAI integration
│   ├── supabase_client.py          # Supabase client
│   ├── session_manager.py          # Session management
│   └── usage_tracker.py            # Usage monitoring
├── main.py           # Application entry point
└── requirements.txt  # Python dependencies
```

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file with:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ORG_ID=your_openai_org_id
   
   # Supabase Configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   
   # Optional: Google Cloud (for BigQuery)
   GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
   GCP_PROJECT_ID=your_project_id
   ```

5. **Set up Supabase**
   - Create a Supabase project
   - Run the SQL schema: `supabase_schema.sql`
   - Create a storage bucket named "documents"
   - Configure RLS policies as needed

6. **Run the application**
   ```bash
   python main.py
   ```

## API Endpoints

### Document Management
- `POST /api/documents/upload` - Upload documents
- `GET /api/documents` - List all documents
- `DELETE /api/documents/{doc_id}` - Delete a document
- `GET /api/documents/{doc_id}/download` - Download a document

### Chat
- `POST /api/chat` - Send a chat message
- `POST /api/search` - Search through documents

### Session Management
- `GET /api/sessions` - List chat sessions
- `GET /api/sessions/{session_id}` - Get session details
- `DELETE /api/sessions/{session_id}` - Delete a session

### Usage & Monitoring
- `GET /api/usage/summary` - Get usage summary
- `GET /api/usage/daily` - Get daily usage statistics
- `GET /api/health/components` - System health check

## Document Upload Flow

1. File uploaded to Supabase Storage
2. File uploaded to OpenAI for AI processing
3. Metadata saved to Supabase database
4. File becomes available for chat queries

## Deployment

The backend is configured for deployment on:
- **Railway**: Use `railway.toml`
- **Render**: Use `render.yaml`
- **Fly.io**: Use `fly.toml`
- **Docker**: Use `Dockerfile`

See `DEPLOYMENT_GUIDE.md` for detailed deployment instructions.

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
The project follows PEP 8 style guidelines. Use `black` for formatting:
```bash
black .
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `PORT` | Server port (default: 8000) | No |
| `ENV` | Environment (development/production) | No |

## License

[Your License Here]