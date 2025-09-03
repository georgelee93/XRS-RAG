# Naming Convention for RAG Chatbot Project

## ID Fields Naming Convention

### Database / Supabase
- `id` - Primary key in Supabase database (UUID)
- `supabase_id` - When referencing Supabase ID from other contexts

### OpenAI
- `openai_file_id` - File ID from OpenAI (format: `file-xxxxx`)
- `openai_assistant_id` - Assistant ID from OpenAI (format: `asst-xxxxx`)
- `openai_thread_id` - Thread ID from OpenAI (format: `thread-xxxxx`)
- `openai_vector_store_id` - Vector store ID (format: `vs-xxxxx`)

### Storage
- `storage_path` - Path in Supabase Storage bucket
- `storage_url` - Full URL to access file from storage

### Display/User-facing
- `display_name` - Original filename as uploaded by user
- `file_type` - File extension/type (pdf, docx, etc.)
- `file_size` - Human-readable size
- `file_size_bytes` - Size in bytes

### Timestamps (all in KST)
- `created_at` - When record was created in database
- `uploaded_at` - When file was uploaded to OpenAI
- `updated_at` - Last modification time
- `deleted_at` - Soft delete timestamp

### User Information
- `user_id` - Supabase auth user ID
- `user_email` - User's email address
- `uploaded_by` - User ID who uploaded the file

## API Response Structure

### Document Object
```json
{
  "supabase_id": "uuid",           // Database record ID
  "openai_file_id": "file-xxx",    // OpenAI file ID
  "display_name": "파일명.pdf",     // Original filename
  "storage_path": "2024_hash.pdf",  // Storage bucket path
  "storage_url": "https://...",     // Download URL
  "file_type": "pdf",
  "file_size": "1.2 MB",            // Human-readable
  "file_size_bytes": 1234567,       // Bytes
  "status": "active",
  "uploaded_at": "2024-01-01T12:00:00+09:00",
  "uploaded_by": "user-uuid",
  "user_email": "user@example.com"
}
```

## Frontend Variable Names

### Document List Item
```javascript
{
  supabaseId: 'uuid',           // Database ID
  openaiFileId: 'file-xxx',     // OpenAI file ID  
  displayName: '파일명.pdf',     // Show to user
  storageUrl: 'https://...',    // For downloads
  fileType: 'pdf',
  fileSize: '1.2 MB',
  status: 'active',
  uploadedAt: '2024-01-01',
  userEmail: 'user@example.com'
}
```

## Database Table Columns

### documents table
- `id` (UUID) - Primary key
- `openai_file_id` (TEXT) - OpenAI file reference
- `display_name` (TEXT) - Original filename
- `storage_path` (TEXT) - Path in storage bucket
- `file_type` (TEXT) - Extension
- `file_size_bytes` (BIGINT) - Size in bytes
- `status` (TEXT) - active/deleted
- `uploaded_by` (UUID) - User ID reference
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)
- `deleted_at` (TIMESTAMPTZ)

## Function Parameter Names

### Upload
```python
async def upload_document(
    file_content: bytes,
    display_name: str,  # Original filename
    user_id: str
) -> Dict
```

### Delete
```python
async def delete_document(
    openai_file_id: str  # Always use OpenAI ID for deletion
) -> bool
```

### Download
```python
async def download_document(
    openai_file_id: str  # Use OpenAI ID to find storage_path
) -> bytes
```

## Principles

1. **Be Explicit**: Always prefix IDs with their source system
2. **Avoid Ambiguity**: Never use generic names like `id`, `file_id`, `doc_id`
3. **Consistency**: Same field should have same name across all layers
4. **User-Facing**: Use `display_name` for what users see, not `filename`
5. **Technical**: Use specific technical terms internally (openai_file_id, storage_path)