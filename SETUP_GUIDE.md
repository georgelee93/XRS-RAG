# Complete Setup Guide for RAG Chatbot

## Prerequisites
- Supabase account with a new project
- OpenAI API key with access to GPT-4 and Assistants API
- Python 3.9+ installed
- Node.js 16+ installed

## Step 1: Get Your API Keys

### 1.1 OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Copy the key (starts with `sk-...`)
4. Save it securely - you won't be able to see it again!

### 1.2 Supabase Credentials
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the following:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **Anon/Public Key**: `eyJhbGc...` (long string)
   - **Service Role Key**: `eyJhbGc...` (different long string)
4. Get the JWT Secret:
   - Still in Settings → API
   - Scroll down to find **JWT Secret**
   - Click reveal and copy it

## Step 2: Update Environment Variables

Edit the `/backend/.env` file and replace with your actual keys:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Keep these as is for now (will be auto-created)
# OPENAI_ASSISTANT_ID=
# OPENAI_VECTOR_STORE_ID=
```

## Step 3: Set Up Supabase Database

### 3.1 Create Database Tables
1. Go to your Supabase dashboard
2. Click on **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy the entire contents of `/backend/database_schema.sql`
5. Paste it into the SQL editor
6. Click **Run** (or press Ctrl/Cmd + Enter)
7. You should see "Success. No rows returned"

### 3.2 Verify Tables Were Created
Run this query to verify:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- documents
- chat_sessions
- chat_messages
- usage_tracking
- users

## Step 4: Create Storage Bucket

### 4.1 Create Documents Bucket
1. In Supabase dashboard, go to **Storage** in the left sidebar
2. Click **Create a new bucket**
3. Name it: `documents`
4. Set privacy: **Public** (or Private if you prefer more security)
5. Click **Create bucket**

### 4.2 Configure Storage Policies (Optional)
If you created a private bucket:
1. Click on the `documents` bucket
2. Go to **Policies** tab
3. Click **New Policy**
4. Choose **For full customization**
5. Give it a name: "Allow all operations"
6. Policy definition:
   ```sql
   (auth.role() = 'authenticated') OR (auth.role() = 'anon')
   ```
7. Check all operations: SELECT, INSERT, UPDATE, DELETE
8. Click **Review** then **Save policy**

## Step 5: Start the Backend

### 5.1 Activate Virtual Environment & Start Server
```bash
cd backend
source venv_test/bin/activate  # On Windows: venv_test\Scripts\activate
python main.py
```

### 5.2 First Run - Assistant Creation
On first run, the backend will automatically:
1. Create an OpenAI Assistant
2. Create a Vector Store
3. Save these IDs to `assistant_config.json`

Watch the console output for:
```
INFO | Created new assistant: asst_xxxxx
INFO | Created new vector store: vs_xxxxx
```

### 5.3 Verify Everything is Working
1. Check health endpoint:
   ```bash
   curl http://localhost:8080/api/health
   ```

2. Check component health:
   ```bash
   curl http://localhost:8080/api/health/components
   ```

   All components should show "healthy":
   - database: healthy
   - openai: healthy
   - assistant: healthy

## Step 6: Test Document Upload

### 6.1 Using the API directly
```bash
# Upload a test document
curl -X POST http://localhost:8080/api/documents/upload \
  -F "file=@test_doc.txt"
```

### 6.2 Using the Admin Interface
1. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Navigate to http://localhost:3000/admin.html
3. Upload a document using the interface

## Step 7: Test Chat Functionality

### 7.1 Create a Chat Session
```bash
curl -X POST http://localhost:8080/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}'
```

### 7.2 Send a Chat Message
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, can you help me?",
    "session_id": "your-session-id-from-above"
  }'
```

## Troubleshooting

### Database Connection Issues
- Error: "column documents.id does not exist"
  - **Solution**: Run the database schema SQL in Supabase SQL editor

### OpenAI API Issues
- Error: "Invalid API key"
  - **Solution**: Check your OPENAI_API_KEY in .env file
  - Make sure there are no extra spaces or newlines

### Supabase Connection Issues
- Error: "Invalid Supabase credentials"
  - **Solution**: Verify all Supabase keys in .env
  - Check that your Supabase project is active (not paused)

### CORS Issues
- Error: "CORS policy blocked"
  - **Solution**: Add your frontend URL to CORS_ORIGINS in .env:
    ```
    CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
    ```

### Port Already in Use
- Error: "Address already in use"
  - **Solution**: 
    ```bash
    # Find and kill the process
    lsof -i :8080
    kill -9 <PID>
    # Or change the port in .env
    PORT=8001
    ```

## Next Steps

1. **Set up authentication** (optional):
   - Implement user login/signup
   - Add JWT token validation

2. **Customize the Assistant**:
   - Edit the system prompt in `core/chat_interface.py`
   - Adjust model parameters (temperature, max_tokens)

3. **Deploy to production**:
   - See DEPLOYMENT.md for cloud deployment instructions

## Support

If you encounter issues:
1. Check the logs in `/backend/logs/`
2. Verify all environment variables are set correctly
3. Ensure all services (Supabase, OpenAI) are accessible
4. Check the API documentation at http://localhost:8080/docs