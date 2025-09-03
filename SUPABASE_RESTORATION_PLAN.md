# Supabase Integration Restoration Plan

## Overview
During the migration to OpenAI Assistant API v2, we removed most Supabase integration logic but left broken references. This document outlines the complete restoration plan for proper data persistence, user management, and analytics.

## Current State Analysis

### ✅ What Still Works
- OpenAI Assistant v2 file uploads and chat
- Basic FastAPI endpoints  
- Frontend functionality

### ❌ What's Broken
- **All Supabase connections** - Invalid URL/credentials
- **Chat message persistence** - No history saved
- **Document metadata tracking** - Files uploaded but not tracked
- **User session management** - No user association
- **Usage analytics** - No cost/token tracking
- **Method mismatches** - Called methods don't exist

### 🔧 Root Causes
1. **Invalid Supabase configuration** - Placeholder URL/keys
2. **Missing method implementations** - `insert_document_record()`, `get_user_documents()`
3. **Broken error handling** - Fails silently, continues without data
4. **Missing ERD implementation** - Tables may not exist or be outdated

## Restoration Tasks

### Phase 1: Database Schema & Connection Setup

#### Task 1.1: Verify/Update Supabase Configuration
- [ ] **Get current Supabase project details from user**
- [ ] **Update environment variables**:
  ```bash
  SUPABASE_URL=https://your-actual-project.supabase.co
  SUPABASE_ANON_KEY=your-actual-anon-key
  SUPABASE_SERVICE_KEY=your-actual-service-key  # For admin operations
  SUPABASE_JWT_SECRET=your-jwt-secret
  ```
- [ ] **Test connection** with simple query
- [ ] **Update both local and Cloud Run environments**

#### Task 1.2: Database Schema Implementation
- [ ] **Get current ERD from user** or design new one
- [ ] **Create/verify core tables**:
  - `user_profiles` - User information and roles
  - `documents` - Document metadata and OpenAI file mapping
  - `chat_sessions` - Chat session tracking
  - `chat_messages` - Message history with full content
  - `usage_logs` - API usage and cost tracking
  - `document_access` - User-document permissions (if needed)

#### Task 1.3: Indexes and Views
- [ ] **Create performance indexes**:
  - `chat_messages(session_id, created_at)`
  - `documents(user_id, status, created_at)`
  - `usage_logs(user_id, service, created_at)`
- [ ] **Create summary views**:
  - `chat_sessions_summary` - Sessions with message counts
  - `user_usage_summary` - User usage statistics

### Phase 2: Backend Integration Fixes

#### Task 2.1: Fix Supabase Client Methods
- [ ] **Fix method naming mismatches**:
  - `insert_document_record()` → `create_document()`
  - `get_user_documents()` → Add proper implementation
- [ ] **Add missing methods**:
  ```python
  async def create_document(self, document_data: Dict) -> Dict
  async def get_user_documents(self, user_id: str) -> List[Dict]
  async def update_document_status(self, file_id: str, status: str) -> bool
  ```
- [ ] **Improve error handling** - Don't fail silently
- [ ] **Add connection health checks**

#### Task 2.2: Document Management Integration
- [ ] **Fix upload flow**:
  - Upload to OpenAI ✅ (working)
  - Save metadata to Supabase ❌ (fix)
  - Update assistant file registry ❌ (fix)
- [ ] **Fix document listing**:
  - Get from OpenAI as primary source
  - Enrich with Supabase metadata
  - Filter by user permissions
- [ ] **Fix document deletion**:
  - Delete from OpenAI
  - Update status in Supabase
  - Remove from assistant file registry

#### Task 2.3: Chat Session Management
- [ ] **Fix session creation**:
  - Create OpenAI thread ✅
  - Save to Supabase ❌ (fix)
  - Link to user properly
- [ ] **Fix message persistence**:
  - Save user messages
  - Save assistant responses
  - Track token usage
  - Store OpenAI message IDs for reference
- [ ] **Fix session listing**:
  - Get user's sessions
  - Include message counts
  - Sort by last activity

#### Task 2.4: Usage Tracking Integration  
- [ ] **Fix usage logger**:
  - Track OpenAI API calls
  - Calculate costs accurately
  - Batch insert to database
  - Link to user sessions
- [ ] **Add usage endpoints**:
  - User usage summary
  - Admin usage analytics
  - Cost reports

### Phase 3: File Registry Synchronization Fix

#### Task 3.1: Assistant File Registry Issues
- [ ] **Problem**: `file_registry` only populated at startup
- [ ] **Solution**: Dynamic registry updates
  ```python
  async def refresh_file_registry(self):
      """Refresh file registry from OpenAI"""
      files = await self.client.files.list(purpose="assistants")
      self.file_registry = {f.id: {...} for f in files.data}
  ```
- [ ] **Call after every upload**
- [ ] **Add periodic refresh** (every 5 minutes)
- [ ] **Integrate with Supabase** - get file metadata from DB

#### Task 3.2: Chat File Attachment Fix
- [ ] **Ensure uploaded files are available for search**:
  - Refresh registry after upload
  - Verify files are attached to messages
  - Test document search functionality
- [ ] **Add file usage tracking**:
  - Which files were used in responses
  - Citation tracking from OpenAI responses

### Phase 4: Authentication & Authorization

#### Task 4.1: User Management
- [ ] **Fix user profile creation**:
  - Create profile on first login
  - Set default role
  - Track registration source
- [ ] **Fix role-based access**:
  - Admin vs regular user permissions
  - Document access controls
  - Usage limit enforcement

#### Task 4.2: Session Security
- [ ] **Fix JWT token validation**
- [ ] **Add session expiration**
- [ ] **Secure admin endpoints**

### Phase 5: Admin Panel Integration

#### Task 5.1: Document Management
- [ ] **Fix document listing** in admin panel
- [ ] **Add user document associations**
- [ ] **Fix document deletion** from admin

#### Task 5.2: User Analytics
- [ ] **User activity dashboards**
- [ ] **Usage cost tracking**  
- [ ] **Session management**

#### Task 5.3: System Health
- [ ] **Database health checks**
- [ ] **OpenAI integration status**
- [ ] **Error monitoring**

## Implementation Priority

### 🚨 Critical (Fix First)
1. **Supabase connection setup** - Nothing works without this
2. **Document upload tracking** - Users losing uploaded files
3. **File registry synchronization** - Documents not found in chat

### ⚠️ High Priority  
4. **Chat message persistence** - No conversation history
5. **User session management** - Can't track user activity
6. **Method name fixes** - Remove error logs

### 📊 Medium Priority
7. **Usage tracking** - Cost monitoring
8. **Admin panel integration** - Management features
9. **Performance optimizations** - Indexes, caching

### 🔧 Low Priority
10. **Advanced features** - Role-based access, advanced analytics

## Testing Strategy

### Phase 1: Connection Testing
- [ ] **Basic Supabase connection test**
- [ ] **Table existence verification**
- [ ] **Insert/select operations**

### Phase 2: Integration Testing  
- [ ] **Document upload → storage flow**
- [ ] **Chat message → persistence flow**
- [ ] **User session → tracking flow**

### Phase 3: End-to-End Testing
- [ ] **Upload document → ask questions → get results**
- [ ] **Admin panel → view user data**
- [ ] **Usage tracking → cost calculations**

## Rollout Plan

### Development Environment
1. **Setup local Supabase connection**
2. **Implement and test fixes**
3. **Verify all flows working**

### Production Deployment
1. **Update Cloud Run environment variables**
2. **Deploy backend with fixes**
3. **Monitor logs for errors**
4. **Test with real users**

### Monitoring
1. **Setup Supabase usage alerts**
2. **Monitor error rates**
3. **Track database performance**

## Questions for User

1. **Can you provide the current Supabase project details?**
   - Project URL
   - Database schema/ERD
   - Current table structure

2. **Do you want to keep the existing schema or redesign it?**

3. **What's the priority for user management features?**
   - Role-based access
   - Usage limits
   - Admin controls

4. **Any specific analytics/reporting requirements?**

## Next Steps

1. **Get Supabase project details from user**
2. **Start with Phase 1: Database Schema & Connection Setup**
3. **Implement fixes incrementally**
4. **Test thoroughly before production deployment**

---

**Estimated Timeline**: 2-3 days for critical fixes, 1 week for full restoration
**Risk Level**: Medium - System works without Supabase but lacks persistence
**Impact**: High - Proper data tracking, user management, and analytics