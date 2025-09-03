# Migration Guide - Backend v2.0

## API Changes

The backend has been refactored for better maintainability and reliability. Here are the key changes:

### Endpoints (No Changes)
All API endpoints remain the same:
- `GET /api/health` - Health check
- `GET /api/health/components` - Component health
- `GET /api/documents` - List documents
- `POST /api/documents/upload` - Upload documents
- `DELETE /api/documents/{openai_file_id}` - Delete document
- `GET /api/documents/{openai_file_id}/download` - Download document
- `POST /api/chat` - Send chat message
- `GET /api/sessions/{session_id}/history` - Get session history
- `GET /api/bigquery/status` - BigQuery status
- `GET /api/bigquery/tables` - List BigQuery tables

### Response Format (Improved)
Documents now return with consistent field names:
```json
{
  "supabase_id": "uuid",
  "openai_file_id": "file-xxx",
  "display_name": "파일명.pdf",
  "storage_path": "20240101_hash.pdf",
  "file_size": "1.2 MB",
  "file_size_bytes": 1234567,
  "file_type": "pdf",
  "status": "active",
  "uploaded_at": "2024-01-01T12:00:00+09:00",
  "uploaded_by_email": "user@example.com"
}
```

### Error Handling (Standardized)
Errors now return consistent format:
```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "value"
  }
}
```

## Key Improvements

1. **Robust Delete Operation**
   - Now properly handles files already deleted from OpenAI
   - Always updates database status
   - Better error recovery

2. **UUID Detection**
   - Automatically detects OpenAI file IDs vs UUIDs
   - No more UUID format errors

3. **Better Logging**
   - Comprehensive logging throughout
   - Easier debugging and monitoring

4. **Cleaner Code Structure**
   - Separated concerns into modules
   - Removed duplicate code
   - Better maintainability

## Frontend Compatibility

The frontend should work without changes, but for best results:

1. **Use consistent field names**:
   - `openai_file_id` instead of `file_id`
   - `display_name` instead of `filename`
   - `file_size_bytes` for numeric size

2. **Handle errors properly**:
   - Check for `error_code` field
   - Display user-friendly messages

3. **Test thoroughly**:
   - Upload documents
   - Delete documents
   - Chat functionality
   - BigQuery integration (if enabled)

## Deployment

The new backend is deployed to the same Cloud Run service. No infrastructure changes required.

## Environment Variables

No changes to environment variables. The same `.env` file works.

## Rollback

If issues occur, the previous version can be restored from Cloud Run console by selecting the previous revision.

## Support

For issues or questions:
- Check logs in Cloud Console
- Review error messages for `error_code`
- Check component health at `/api/health/components`