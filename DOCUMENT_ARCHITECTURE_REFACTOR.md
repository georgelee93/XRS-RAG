# Document Architecture Refactor Plan

## Current Problems
1. **Admin panel uses dual sources** - OpenAI + Supabase causing inconsistencies
2. **Supabase metadata used for display** - Can show deleted/stale files
3. **No backup storage** - Files only in OpenAI, no recovery option
4. **Analytics mixed with display logic** - Complex queries for simple displays

## New Architecture

### **Document Display (Admin Panel)**
**Single Source**: OpenAI files API
- Show only files that actually exist and work
- Get metadata from OpenAI upload metadata
- Clean, fast, always accurate

### **Analytics & Tracking (Supabase)**
**Dual Purpose**: 
1. **Usage Analytics** - API calls, user activity, costs
2. **Document History** - Full audit trail including deleted files

### **File Storage Strategy**
**Dual Storage**:
1. **Primary**: OpenAI (for AI processing)
2. **Backup**: Supabase Storage (for maintenance/recovery)

## Implementation Tasks

### 1. Refactor Document Listing
```python
# OLD: complex dual-source logic
async def list_documents(self, user_id):
    openai_docs = await self.assistant.list_documents()  # Primary
    supabase_docs = await self.supabase.get_user_documents(user_id)  # Secondary
    # Complex merge logic...

# NEW: OpenAI only for display
async def list_documents(self):
    files = await self.client.files.list(purpose="assistants")
    return [{
        "file_id": f.id,
        "filename": f.filename,
        "size": format_size(f.bytes),
        "uploaded_at": datetime.fromtimestamp(f.created_at).isoformat(),
        "uploaded_by": f.metadata.get("uploaded_by", "unknown"),
        "user_id": f.metadata.get("user_id"),
        "status": "active"  # If in OpenAI, it's active
    } for f in files.data]
```

### 2. Enhanced Upload Process
```python
async def upload_document(self, file_content, filename, user_id, user_email):
    # 1. Upload to OpenAI (primary)
    openai_result = await self.assistant.upload_document(
        file_content=file_content,
        filename=filename,
        metadata={
            "user_id": user_id,
            "uploaded_by": user_email,
            "uploaded_at": datetime.now().isoformat()
        }
    )
    
    # 2. Backup to Supabase Storage
    storage_path = f"documents/{user_id}/{openai_result['file_id']}/{filename}"
    backup_url = await self.supabase.upload_file(
        bucket="documents",
        file_path=storage_path,
        file_content=file_content,
        content_type=content_type
    )
    
    # 3. Log for analytics/history
    await self.supabase.log_document_event({
        "action": "upload",
        "file_id": openai_result["file_id"],
        "filename": filename,
        "user_id": user_id,
        "uploaded_by": user_email,
        "size": len(file_content),
        "storage_path": storage_path,
        "backup_url": backup_url,
        "created_at": datetime.now().isoformat()
    })
    
    return openai_result
```

### 3. Enhanced Delete Process
```python
async def delete_document(self, file_id, user_id):
    # 1. Get file info before deletion
    file_info = await self.get_file_info(file_id)
    
    # 2. Delete from OpenAI (primary)
    success = await self.assistant.delete_document(file_id)
    
    if success:
        # 3. Log deletion for history
        await self.supabase.log_document_event({
            "action": "delete",
            "file_id": file_id,
            "filename": file_info.get("filename"),
            "user_id": user_id,
            "deleted_at": datetime.now().isoformat(),
            "deleted_by": user_id
        })
        
        # Note: Keep backup in Supabase Storage for recovery
        # Don't delete from storage, just mark as deleted in logs
```

### 4. Separate Analytics Queries
```python
class DocumentAnalytics:
    async def get_user_upload_stats(self, user_id):
        """Get user's upload history and statistics"""
        return await self.supabase.client.table("document_events").select("*").eq(
            "user_id", user_id
        ).eq("action", "upload").execute()
    
    async def get_deleted_files_history(self):
        """Get history of all deleted files"""
        return await self.supabase.client.table("document_events").select("*").eq(
            "action", "delete"
        ).execute()
    
    async def get_storage_usage_by_user(self):
        """Calculate storage usage per user"""
        # Query upload events minus delete events
        pass
```

### 5. File Recovery System
```python
class DocumentRecovery:
    async def list_recoverable_files(self, user_id):
        """List files that can be recovered from backup"""
        # Get deleted files that still have backup storage
        deleted = await self.supabase.client.table("document_events").select(
            "*"
        ).eq("action", "delete").eq("user_id", user_id).execute()
        
        return [d for d in deleted.data if d.get("backup_url")]
    
    async def recover_file(self, file_id, user_id):
        """Restore file from backup to OpenAI"""
        # Download from Supabase Storage backup
        # Re-upload to OpenAI
        # Log recovery event
        pass
```

## New Database Schema

### Keep Existing Tables:
- `user_profiles` - User management
- `chat_sessions` - Chat history  
- `chat_messages` - Messages
- `usage_logs` - API usage tracking

### New Simplified Table:
```sql
-- Replace complex 'documents' table with simple event log
CREATE TABLE document_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action VARCHAR(20) NOT NULL, -- 'upload', 'delete', 'recover'
  file_id VARCHAR(255) NOT NULL, -- OpenAI file ID
  filename VARCHAR(255) NOT NULL,
  user_id UUID REFERENCES user_profiles(id),
  uploaded_by VARCHAR(255),
  size_bytes BIGINT,
  content_type VARCHAR(100),
  storage_path TEXT, -- Supabase storage path for backup
  backup_url TEXT, -- Supabase storage URL
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- Index for fast queries
  INDEX idx_document_events_file_id ON document_events(file_id),
  INDEX idx_document_events_user_action ON document_events(user_id, action),
  INDEX idx_document_events_created_at ON document_events(created_at)
);
```

## Benefits of New Architecture

### ✅ **Simplified Document Display**
- Admin panel always shows current, working files
- No data inconsistency issues
- Faster queries (single source)

### ✅ **Comprehensive Analytics**
- Full audit trail of all document operations
- User activity tracking
- Storage usage calculations
- Recovery capabilities

### ✅ **Backup & Recovery**
- All files backed up to Supabase Storage
- Can recover deleted files
- Maintenance and compliance ready

### ✅ **Performance**
- Admin panel: Fast OpenAI-only queries
- Analytics: Separate optimized queries
- No complex joins between sources

## Migration Plan

### Phase 1: Refactor Document Listing
1. Update `list_documents` to use OpenAI only
2. Test admin panel with new logic
3. Verify all metadata shows correctly

### Phase 2: Add Backup Storage
1. Add Supabase Storage upload to upload flow
2. Create `document_events` table
3. Log all document operations

### Phase 3: Analytics Dashboard
1. Create separate analytics queries
2. Add recovery functionality
3. Historical reporting features

### Phase 4: Cleanup
1. Remove old `documents` table logic
2. Clean up unused Supabase methods
3. Update documentation

## Questions for Implementation

1. **Supabase Storage bucket structure**: 
   - `documents/{user_id}/{file_id}/{filename}` ?
   - Or organize by date: `documents/{year}/{month}/{user_id}/` ?

2. **Retention policy**: 
   - Keep deleted file backups forever?
   - Auto-delete backups after X months?

3. **Analytics scope**:
   - What specific metrics do you need?
   - User quotas/limits implementation?

4. **Recovery workflow**:
   - Admin-only recovery?
   - Self-service user recovery?
   - Automatic recovery options?