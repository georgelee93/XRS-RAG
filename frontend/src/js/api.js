/**
 * API Service Module
 */

import { API_CONFIG, MESSAGES } from './config.js';
import { parseApiError } from './utils.js';
import logger from './logger.js';
import { authService } from './auth.js';
import { toFrontendFormat, toBackendFormat } from './utils/transformers.js';

class ApiService {
  constructor() {
    this.baseUrl = API_CONFIG.baseUrl;
    this.timeout = API_CONFIG.timeout;
  }

  /**
   * Make API request with timeout and error handling
   */
  async request(endpoint, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const startTime = Date.now();
    const url = `${this.baseUrl}${endpoint}`;

    // Add auth headers
    const authHeaders = authService.getAuthHeaders();

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          ...authHeaders,  // Include auth token
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const duration = Date.now() - startTime;

      // Log API call
      logger.logAPI(
        options.method || 'GET',
        endpoint,
        options.body,
        { ok: response.ok, status: response.status },
        duration
      );

      // Handle 401 Unauthorized
      if (response.status === 401) {
        await authService.signOut();
        throw new Error('Authentication required');
      }

      if (!response.ok) {
        const errorMessage = await parseApiError(response);
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === 'AbortError') {
        throw new Error(MESSAGES.network.timeout);
      }

      throw error;
    }
  }

  /**
   * Document Management APIs
   */
  async getDocuments() {
    return this.request('/api/documents');
  }

  async uploadDocuments(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.request('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
  }

  async deleteDocument(documentId) {
    return this.request(`/api/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  async downloadDocument(documentId) {
    // Return the download URL
    return `${this.baseUrl}/api/documents/${documentId}/download`;
  }

  /**
   * Chat APIs
   */
  async sendMessage(message, sessionId = null) {
    // Backend expects form data, not JSON
    const formData = new FormData();
    formData.append('message', message);
    if (sessionId) {
      formData.append('session_id', sessionId);
    }

    return this.request('/api/chat', {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
    });
  }

  /**
   * Session Management APIs
   */
  async getSessions(limit = 20, offset = 0) {
    const response = await this.request(`/api/sessions?limit=${limit}&offset=${offset}`);
    // Transform backend snake_case to frontend camelCase
    return toFrontendFormat(response);
  }

  async getSessionDetails(sessionId) {
    const response = await this.request(`/api/sessions/${sessionId}`);
    // Transform backend snake_case to frontend camelCase
    return toFrontendFormat(response);
  }

  async updateSessionTitle(sessionId, title) {
    return this.request(`/api/sessions/${sessionId}/title`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
  }

  async deleteSession(sessionId) {
    return this.request(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Usage & Stats APIs
   */
  async getUsageSummary(days = 7) {
    return this.request(`/api/usage/summary?days=${days}`);
  }

  async getDailyUsage(days = 30) {
    return this.request(`/api/usage/daily?days=${days}`);
  }

  async getStats() {
    return this.request('/api/stats');
  }

  /**
   * Health Check
   */
  async checkHealth() {
    return this.request('/api/health/components');
  }

  /**
   * Logs
   */
  async getLogs(level = null, category = null, limit = 100) {
    const params = new URLSearchParams();
    if (level) params.append('level', level);
    if (category) params.append('category', category);
    params.append('limit', limit);

    return this.request(`/api/logs?${params.toString()}`);
  }

  /**
   * BigQuery APIs
   */
  async getBigQueryStatus() {
    return this.request('/api/bigquery/schemas/status');
  }

  async getBigQueryTables() {
    return this.request('/api/bigquery/tables');
  }

  async refreshBigQuerySchemas() {
    return this.request('/api/bigquery/schemas/refresh', {
      method: 'POST',
    });
  }

  async executeBigQueryQuery(query, language = 'auto') {
    return this.request('/api/bigquery/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, language }),
    });
  }
}

// Export singleton instance
export default new ApiService();