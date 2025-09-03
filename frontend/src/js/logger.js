/**
 * Frontend logging utility for 청암 챗봇
 * Provides centralized logging with different levels and storage
 */

class Logger {
  constructor() {
    this.logs = [];
    this.maxLogs = 1000; // Keep last 1000 logs in memory
    this.logLevels = {
      DEBUG: 0,
      INFO: 1,
      WARN: 2,
      ERROR: 3
    };
    this.currentLevel = this.logLevels.INFO;
    
    // Load persisted logs from localStorage
    this.loadPersistedLogs();
  }

  /**
   * Set the minimum log level
   */
  setLevel(level) {
    if (this.logLevels[level] !== undefined) {
      this.currentLevel = this.logLevels[level];
    }
  }

  /**
   * Core logging method
   */
  log(level, category, message, data = null) {
    const levelValue = this.logLevels[level];
    if (levelValue === undefined || levelValue < this.currentLevel) {
      return;
    }

    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      message,
      data,
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // Add to memory
    this.logs.push(logEntry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Console output with styling
    const styles = {
      DEBUG: 'color: #gray',
      INFO: 'color: #2563eb',
      WARN: 'color: #d97706',
      ERROR: 'color: #dc2626'
    };

    console.log(
      `%c[${level}] [${category}] ${message}`,
      styles[level],
      data ? data : ''
    );

    // Persist important logs
    if (levelValue >= this.logLevels.WARN) {
      this.persistLog(logEntry);
    }

    // Send errors to backend
    if (level === 'ERROR') {
      this.sendToBackend(logEntry);
    }
  }

  /**
   * Convenience methods for different log levels
   */
  debug(category, message, data) {
    this.log('DEBUG', category, message, data);
  }

  info(category, message, data) {
    this.log('INFO', category, message, data);
  }

  warn(category, message, data) {
    this.log('WARN', category, message, data);
  }

  error(category, message, data) {
    this.log('ERROR', category, message, data);
  }

  /**
   * Log API calls with request/response details
   */
  logAPI(method, endpoint, request, response, duration) {
    const status = response?.ok ? 'SUCCESS' : 'FAILED';
    const data = {
      method,
      endpoint,
      request: this.sanitizeData(request),
      response: {
        status: response?.status,
        statusText: response?.statusText,
        data: response?.data
      },
      duration: `${duration}ms`
    };

    if (response?.ok) {
      this.info('API', `${method} ${endpoint} - ${status} (${duration}ms)`, data);
    } else {
      this.error('API', `${method} ${endpoint} - ${status} (${duration}ms)`, data);
    }
  }

  /**
   * Log document operations
   */
  logDocument(operation, documentInfo, result) {
    const data = {
      operation,
      document: {
        id: documentInfo.id,
        name: documentInfo.name,
        type: documentInfo.type,
        size: documentInfo.size
      },
      result,
      timestamp: new Date().toISOString()
    };

    const level = result.success ? 'INFO' : 'ERROR';
    this.log(level, 'DOCUMENT', `${operation} - ${documentInfo.name}`, data);
  }

  /**
   * Log chat interactions
   */
  logChat(event, data) {
    this.info('CHAT', event, {
      ...data,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Sanitize sensitive data before logging
   */
  sanitizeData(data) {
    if (!data) return data;
    
    const sensitiveKeys = ['password', 'token', 'api_key', 'secret'];
    const sanitized = { ...data };

    for (const key in sanitized) {
      if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
        sanitized[key] = '[REDACTED]';
      }
    }

    return sanitized;
  }

  /**
   * Persist log to localStorage
   */
  persistLog(logEntry) {
    try {
      const persistedLogs = JSON.parse(localStorage.getItem('ragLogs') || '[]');
      persistedLogs.push(logEntry);
      
      // Keep only last 100 persisted logs
      if (persistedLogs.length > 100) {
        persistedLogs.splice(0, persistedLogs.length - 100);
      }
      
      localStorage.setItem('ragLogs', JSON.stringify(persistedLogs));
    } catch (error) {
      console.error('Failed to persist log:', error);
    }
  }

  /**
   * Load persisted logs from localStorage
   */
  loadPersistedLogs() {
    try {
      const persistedLogs = JSON.parse(localStorage.getItem('ragLogs') || '[]');
      this.logs = [...persistedLogs, ...this.logs];
    } catch (error) {
      console.error('Failed to load persisted logs:', error);
    }
  }

  /**
   * Send error logs to backend
   */
  async sendToBackend(logEntry) {
    try {
      // TODO: Implement backend logging endpoint
      // await fetch('/api/logs', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(logEntry)
      // });
    } catch (error) {
      console.error('Failed to send log to backend:', error);
    }
  }

  /**
   * Get all logs or filter by criteria
   */
  getLogs(filter = {}) {
    let filtered = [...this.logs];

    if (filter.level) {
      const minLevel = this.logLevels[filter.level];
      filtered = filtered.filter(log => this.logLevels[log.level] >= minLevel);
    }

    if (filter.category) {
      filtered = filtered.filter(log => log.category === filter.category);
    }

    if (filter.startTime) {
      filtered = filtered.filter(log => new Date(log.timestamp) >= new Date(filter.startTime));
    }

    if (filter.endTime) {
      filtered = filtered.filter(log => new Date(log.timestamp) <= new Date(filter.endTime));
    }

    return filtered;
  }

  /**
   * Export logs as JSON
   */
  exportLogs(filter = {}) {
    const logs = this.getLogs(filter);
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rag-logs-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Clear all logs
   */
  clearLogs() {
    this.logs = [];
    localStorage.removeItem('ragLogs');
    this.info('SYSTEM', 'Logs cleared');
  }

  /**
   * Get log statistics
   */
  getStats() {
    const stats = {
      total: this.logs.length,
      byLevel: {},
      byCategory: {},
      errors: []
    };

    for (const level in this.logLevels) {
      stats.byLevel[level] = 0;
    }

    this.logs.forEach(log => {
      stats.byLevel[log.level]++;
      stats.byCategory[log.category] = (stats.byCategory[log.category] || 0) + 1;
      
      if (log.level === 'ERROR') {
        stats.errors.push({
          timestamp: log.timestamp,
          category: log.category,
          message: log.message
        });
      }
    });

    return stats;
  }
}

// Create and export singleton instance
const logger = new Logger();

// Set log level from environment or default to INFO
if (window.location.hostname === 'localhost') {
  logger.setLevel('DEBUG');
}

export default logger;