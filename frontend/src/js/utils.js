/**
 * Utility Functions
 */

import { DOCUMENT_TYPES, DOCUMENT_STATUS } from './config.js';

/**
 * Format file size to human readable format
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
}

/**
 * Format date to locale string
 */
export function formatDate(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Get file extension from filename
 */
export function getFileExtension(filename) {
  if (!filename) return '';
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
}

/**
 * Get document type info
 */
export function getDocumentType(filename) {
  const ext = getFileExtension(filename);
  return DOCUMENT_TYPES[ext] || { icon: '📄', color: 'gray' };
}

/**
 * Get status badge HTML
 */
export function getStatusBadge(status) {
  const statusInfo = DOCUMENT_STATUS[status] || DOCUMENT_STATUS.processing;
  
  // Define color classes explicitly to avoid Tailwind purging
  const colorClasses = {
    green: 'bg-green-50 text-green-700 border border-green-200',
    blue: 'bg-blue-50 text-blue-700 border border-blue-200',
    red: 'bg-red-50 text-red-700 border border-red-200',
    gray: 'bg-neutral-100 text-neutral-700 border border-neutral-300'
  };
  
  return `
    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses[statusInfo.color] || colorClasses.gray}">
      <span class="mr-1">${statusInfo.icon}</span>
      ${statusInfo.label}
    </span>
  `;
}

/**
 * Debounce function for search
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Parse API error response
 */
export async function parseApiError(response) {
  try {
    const data = await response.json();
    return data.detail || data.error || '알 수 없는 오류가 발생했습니다';
  } catch {
    return `HTTP ${response.status}: ${response.statusText}`;
  }
}

/**
 * Create loading spinner
 */
export function createLoadingSpinner() {
  return `
    <div class="flex justify-center items-center p-4">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-neutral-900"></div>
    </div>
  `;
}

/**
 * Create empty state message
 */
export function createEmptyState(message = '데이터가 없습니다') {
  return `
    <div class="text-center py-12">
      <svg class="mx-auto h-12 w-12 text-neutral-400" fill="currentColor" viewBox="0 0 256 256">
        <path d="M213.66,82.34l-56-56A8,8,0,0,0,152,24H56A16,16,0,0,0,40,40V216a16,16,0,0,0,16,16H200a16,16,0,0,0,16-16V88A8,8,0,0,0,213.66,82.34ZM152,88V44l44,44ZM56,216V40h80V88a8,8,0,0,0,8,8h48V216Z"/>
      </svg>
      <h3 class="mt-2 text-sm font-medium text-neutral-900">${message}</h3>
    </div>
  `;
}