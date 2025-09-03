/**
 * Frontend Configuration
 */

// API Configuration
export const API_CONFIG = {
  baseUrl: window.location.hostname === 'localhost' 
    ? 'http://localhost:8080'
    : 'https://rag-backend-223940753124.asia-northeast3.run.app', // Seoul Cloud Run URL
  timeout: 120000, // 120 seconds (2 minutes) - increased for complex document searches
};

// Supabase Configuration - Updated with new project
export const SUPABASE_CONFIG = {
  url: 'https://utowhepyocvkjqtxdsnj.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV0b3doZXB5b2N2a2pxdHhkc25qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY3ODQyMjAsImV4cCI6MjA3MjM2MDIyMH0.K6SXf_2Wn3yPD813HrX2h2py50G_fW5Put3s3ymOC1M'
};

// Document Types
// Only file types supported by OpenAI Assistant API
export const DOCUMENT_TYPES = {
  pdf: { icon: '📄', color: 'red' },
  docx: { icon: '📝', color: 'blue' },
  txt: { icon: '📃', color: 'gray' },
  md: { icon: '📋', color: 'purple' },
};

// Unsupported types kept for reference (can be shown as disabled)
export const UNSUPPORTED_TYPES = {
  doc: { icon: '📝', color: 'blue' },
  ppt: { icon: '📊', color: 'orange' },
  pptx: { icon: '📊', color: 'orange' },
  xls: { icon: '📈', color: 'green' },
  xlsx: { icon: '📈', color: 'green' },
  csv: { icon: '📊', color: 'teal' },
  json: { icon: '{}', color: 'indigo' },
  xml: { icon: '📰', color: 'yellow' },
  html: { icon: '🌐', color: 'pink' },
};

// Status Configuration
export const DOCUMENT_STATUS = {
  active: { label: '활성', color: 'green', icon: '✅' },
  processing: { label: '처리 중', color: 'blue', icon: '⏳' },
  deleted: { label: '삭제됨', color: 'gray', icon: '🗑️' },
  error: { label: '오류', color: 'red', icon: '❌' },
};

// Pagination
export const PAGINATION = {
  itemsPerPage: 10,
  maxPageButtons: 5,
};

// File Upload
export const FILE_UPLOAD = {
  maxFileSize: 30 * 1024 * 1024, // 30 MB (Cloud Run limit)
  allowedTypes: Object.keys(DOCUMENT_TYPES),
  maxFiles: 10,
};

// UI Messages
export const MESSAGES = {
  upload: {
    success: '파일이 성공적으로 업로드되었습니다',
    error: '파일 업로드 중 오류가 발생했습니다',
    tooLarge: '파일 크기가 너무 큽니다',
    invalidType: '지원하지 않는 파일 형식입니다. PDF, DOCX, TXT, MD 파일만 지원됩니다.',
  },
  delete: {
    confirm: '정말로 이 문서를 삭제하시겠습니까?',
    success: '문서가 삭제되었습니다',
    error: '문서 삭제 중 오류가 발생했습니다',
  },
  network: {
    error: '네트워크 오류가 발생했습니다',
    timeout: '요청 시간이 초과되었습니다',
  },
};