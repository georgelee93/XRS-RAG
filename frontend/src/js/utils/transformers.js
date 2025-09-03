/**
 * Variable Name Transformation Utilities
 * Converts between snake_case (backend) and camelCase (frontend)
 */

/**
 * Convert snake_case to camelCase
 * @param {string} str - The snake_case string
 * @returns {string} The camelCase string
 */
export function snakeToCamel(str) {
  return str.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
}

/**
 * Convert camelCase to snake_case
 * @param {string} str - The camelCase string
 * @returns {string} The snake_case string
 */
export function camelToSnake(str) {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Transform object keys from snake_case to camelCase
 * @param {Object} obj - Object with snake_case keys
 * @returns {Object} Object with camelCase keys
 */
export function transformResponseToCamelCase(obj) {
  if (obj === null || obj === undefined) {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(transformResponseToCamelCase);
  }
  
  if (typeof obj !== 'object') {
    return obj;
  }
  
  const transformed = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = snakeToCamel(key);
    transformed[camelKey] = transformResponseToCamelCase(value);
  }
  
  return transformed;
}

/**
 * Transform object keys from camelCase to snake_case
 * @param {Object} obj - Object with camelCase keys
 * @returns {Object} Object with snake_case keys
 */
export function transformRequestToSnakeCase(obj) {
  if (obj === null || obj === undefined) {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(transformRequestToSnakeCase);
  }
  
  if (typeof obj !== 'object') {
    return obj;
  }
  
  const transformed = {};
  for (const [key, value] of Object.entries(obj)) {
    const snakeKey = camelToSnake(key);
    transformed[snakeKey] = transformRequestToSnakeCase(value);
  }
  
  return transformed;
}

/**
 * Common key mappings for special cases
 */
const KEY_MAPPINGS = {
  // Backend to Frontend
  session_id: 'sessionId',
  user_id: 'userId',
  created_at: 'createdAt',
  updated_at: 'updatedAt',
  assistant_id: 'assistantId',
  vector_store_id: 'vectorStoreId',
  thread_id: 'threadId',
  message_id: 'messageId',
  file_id: 'fileId',
  last_message: 'lastMessage',
  last_message_at: 'lastMessageAt',
  session_title: 'sessionTitle',
  total_tokens: 'totalTokens',
  total_cost: 'totalCost',
  message_count: 'messageCount',
  
  // Frontend to Backend (reverse mappings)
  sessionId: 'session_id',
  userId: 'user_id',
  createdAt: 'created_at',
  updatedAt: 'updated_at',
  assistantId: 'assistant_id',
  vectorStoreId: 'vector_store_id',
  threadId: 'thread_id',
  messageId: 'message_id',
  fileId: 'file_id',
  lastMessage: 'last_message',
  lastMessageAt: 'last_message_at',
  sessionTitle: 'session_title',
  totalTokens: 'total_tokens',
  totalCost: 'total_cost',
  messageCount: 'message_count',
};

/**
 * Transform keys using predefined mappings
 * @param {Object} obj - Object to transform
 * @param {boolean} toFrontend - If true, converts to frontend format (camelCase), otherwise to backend (snake_case)
 * @returns {Object} Transformed object
 */
export function transformWithMappings(obj, toFrontend = true) {
  if (obj === null || obj === undefined) {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => transformWithMappings(item, toFrontend));
  }
  
  if (typeof obj !== 'object') {
    return obj;
  }
  
  const transformed = {};
  for (const [key, value] of Object.entries(obj)) {
    // Check if we have a specific mapping for this key
    let newKey = key;
    if (toFrontend && KEY_MAPPINGS[key]) {
      newKey = KEY_MAPPINGS[key];
    } else if (!toFrontend) {
      // Find reverse mapping
      const reverseKey = Object.entries(KEY_MAPPINGS).find(([k, v]) => v === key)?.[0];
      if (reverseKey) {
        newKey = reverseKey;
      }
    } else {
      // Use automatic transformation
      newKey = toFrontend ? snakeToCamel(key) : camelToSnake(key);
    }
    
    transformed[newKey] = transformWithMappings(value, toFrontend);
  }
  
  return transformed;
}

// Export convenient aliases
export const toFrontendFormat = (obj) => transformWithMappings(obj, true);
export const toBackendFormat = (obj) => transformWithMappings(obj, false);