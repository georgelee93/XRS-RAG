import { createIcon, showToast } from './components.js';
import logger from './logger.js';
import { AuthGuard } from './authGuard.js';
import { authService } from './auth.js';
import { API_CONFIG } from './config.js';
import api from './api.js';

// State management
const state = {
  messages: [],
  loadedDocuments: [],
  currentConversationId: null,
  isLoading: false,
  sessionId: null,
};

// Initialize the app
document.addEventListener('DOMContentLoaded', async () => {
  // Check auth first
  const isAuthenticated = await AuthGuard.requireAuth();
  
  if (isAuthenticated) {
    // Setup auth UI
    AuthGuard.setupLogoutButton();
    AuthGuard.updateUIForAuth();
    
    // Initialize chat app
    initializeEventListeners();
    loadSavedConversations();
    adjustTextareaHeight();
    initializeSession();
    loadSystemInfo();
  }
});

function initializeEventListeners() {
  // Chat form
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (message && !state.isLoading) {
      await sendMessage(message);
      messageInput.value = '';
      adjustTextareaHeight();
    }
  });

  // Auto-resize textarea
  messageInput.addEventListener('input', adjustTextareaHeight);
  
  // Handle Enter key
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });

  // New chat button
  const newChatBtn = document.getElementById('newChatBtn');
  if (newChatBtn) {
    newChatBtn.addEventListener('click', startNewChat);
  }

  // Attachment button
  document.getElementById('attachBtn').addEventListener('click', () => {
    showToast('파일 첨부 기능은 곧 준비 중입니다', 'info');
  });
}

function adjustTextareaHeight() {
  const textarea = document.getElementById('messageInput');
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
}

async function sendMessage(message) {
  state.isLoading = true;
  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;
  
  logger.logChat('MESSAGE_SENT', { 
    message: message.substring(0, 100), // Log first 100 chars for privacy
    sessionId: state.sessionId,
    messageLength: message.length
  });
  
  // Hide welcome message
  document.getElementById('welcomeMessage').classList.add('hidden');
  
  // Add user message
  addMessage('user', message);
  
  // Show typing indicator
  const typingId = addMessage('assistant', '', true);
  const startTime = Date.now();
  
  try {
    // Call backend API using centralized service
    const data = await api.sendMessage(message, state.sessionId);
    
    const duration = Date.now() - startTime;
    
    // Remove typing indicator and add response
    removeMessage(typingId);
    
    // Debug: log the actual data structure
    console.log('Chat API Response:', data);
    
    const responseText = data.response || data.message || data.text || '응답을 받지 못했습니다.';
    const responseId = addMessage('assistant', responseText);
    
    logger.logChat('RESPONSE_RECEIVED', { 
      responseLength: responseText.length,
      sessionId: state.sessionId,
      duration: `${duration}ms`,
      usage: data.usage
    });
    
    // References are no longer supported without retrieval API
    
    // Update session ID if provided
    if (data.session_id) {
      state.sessionId = data.session_id;
    }
    
    // Save conversation
    saveConversation();
    
  } catch (error) {
    logger.error('CHAT', 'Failed to send message', { 
      error: error.message,
      sessionId: state.sessionId,
      duration: `${Date.now() - startTime}ms`
    });
    
    console.error('Chat error:', error);
    removeMessage(typingId);
    
    // Check if it's a timeout error and show appropriate message
    if (error.message === '요청 시간이 초과되었습니다') {
      addMessage('assistant', '요청 시간이 초과되었습니다. 더 간단한 질문으로 다시 시도해주세요.');
      showToast('요청 시간 초과', 'error');
    } else {
      addMessage('assistant', '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.');
      showToast('응답을 받지 못했습니다', 'error');
    }
  } finally {
    state.isLoading = false;
    sendBtn.disabled = false;
  }
}

function addMessage(role, text, isTyping = false) {
  const messageId = Date.now();
  const message = { id: messageId, role, text, timestamp: new Date() };
  state.messages.push(message);
  
  const messagesList = document.getElementById('messagesList');
  const messageDiv = document.createElement('div');
  messageDiv.id = `message-${messageId}`;
  messageDiv.className = 'flex gap-4';
  
  if (role === 'user') {
    messageDiv.classList.add('justify-end');
    messageDiv.innerHTML = `
      <div class="order-2">
        <div class="chat-bubble-user">
          ${escapeHtml(text)}
        </div>
        <div class="text-xs text-neutral-500 mt-1 text-right">
          ${formatTime(message.timestamp)}
        </div>
      </div>
      <div class="w-8 h-8 bg-neutral-900 rounded-full flex items-center justify-center flex-shrink-0 order-1">
        <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 256 256">
          <path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z"></path>
        </svg>
      </div>
    `;
  } else {
    messageDiv.innerHTML = `
      <div class="w-8 h-8 bg-neutral-100 rounded-full flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4 text-neutral-600" fill="currentColor" viewBox="0 0 256 256">
          <path d="M197.58,129.06l-51.61-19-19-51.65a15.92,15.92,0,0,0-29.88,0L78.07,110l-51.65,19a15.92,15.92,0,0,0,0,29.88L78,178l19,51.62a15.92,15.92,0,0,0,29.88,0L146,178l51.65-19a15.92,15.92,0,0,0,0-29.88ZM140.39,163a8,8,0,0,0-4.42,4.42L120,215.45,104,167.38a8,8,0,0,0-4.42-4.42L51.55,147l48.06-15.93a8,8,0,0,0,4.42-4.42L120,78.55l15.97,48.06a8,8,0,0,0,4.42,4.42L188.45,147Z"></path>
        </svg>
      </div>
      <div>
        <div class="chat-bubble-model">
          ${isTyping ? getTypingIndicator() : formatMessage(text)}
        </div>
        ${!isTyping ? `
          <div class="text-xs text-neutral-500 mt-1">
            ${formatTime(message.timestamp)}
          </div>
        ` : ''}
      </div>
    `;
  }
  
  messagesList.appendChild(messageDiv);
  messageDiv.scrollIntoView({ behavior: 'smooth' });
  
  return messageId;
}

function removeMessage(messageId) {
  const messageEl = document.getElementById(`message-${messageId}`);
  if (messageEl) {
    messageEl.remove();
  }
  state.messages = state.messages.filter(m => m.id !== messageId);
}

function getTypingIndicator() {
  return `
    <div class="flex gap-1">
      <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
      <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
      <div class="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
    </div>
  `;
}

function formatMessage(text) {
  // Handle undefined or null text
  if (!text) {
    return '';
  }
  
  // Simple markdown-like formatting
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-neutral-100 px-1 py-0.5 rounded text-sm">$1</code>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(date) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: 'numeric',
    hour12: true
  }).format(date);
}

// References functionality removed - no longer using retrieval API


function saveConversation() {
  if (state.messages.length === 0) return;
  
  const conversations = JSON.parse(localStorage.getItem('ragConversations') || '[]');
  const conversation = {
    id: state.currentConversationId || Date.now(),
    title: state.messages[0]?.text.substring(0, 50) + '...',
    messages: state.messages,
    timestamp: new Date(),
  };
  
  const existingIndex = conversations.findIndex(c => c.id === conversation.id);
  if (existingIndex >= 0) {
    conversations[existingIndex] = conversation;
  } else {
    conversations.unshift(conversation);
  }
  
  // Keep only last 10 conversations
  conversations.splice(10);
  
  localStorage.setItem('ragConversations', JSON.stringify(conversations));
  state.currentConversationId = conversation.id;
  
  loadSavedConversations();
}

async function loadSavedConversations() {
  const conversationsList = document.getElementById('conversationsList');
  
  try {
    // Try to load from backend first
    const response = await api.getSessions(20, 0);
    
    if (response && response.sessions && response.sessions.length > 0) {
      // Use backend sessions (now transformed to camelCase)
      conversationsList.innerHTML = response.sessions.map(session => {
        const sessionId = session.sessionId;  // Now using camelCase after transformation
        const lastMessage = session.lastMessage || session.sessionTitle || '새 대화';
        const timestamp = session.updatedAt || session.createdAt;
        const isActive = sessionId === state.currentConversationId || sessionId === state.sessionId;
        
        return `
          <button class="w-full text-left p-2 hover:bg-neutral-50 rounded-lg transition-colors ${isActive ? 'bg-neutral-50' : ''}" 
                  onclick="loadSessionFromBackend('${sessionId}')">
            <p class="text-sm font-medium text-neutral-900 truncate">${lastMessage}</p>
            <p class="text-xs text-neutral-500">${formatRelativeTime(new Date(timestamp))}</p>
          </button>
        `;
      }).join('');
    } else {
      // Fallback to localStorage if no backend sessions
      const localConversations = JSON.parse(localStorage.getItem('ragConversations') || '[]');
      
      if (localConversations.length === 0) {
        conversationsList.innerHTML = '<div class="text-sm text-neutral-500">No recent conversations</div>';
        return;
      }
      
      conversationsList.innerHTML = localConversations.map(conv => `
        <button class="w-full text-left p-2 hover:bg-neutral-50 rounded-lg transition-colors ${conv.id === state.currentConversationId ? 'bg-neutral-50' : ''}" 
                onclick="loadConversation(${conv.id})">
          <p class="text-sm font-medium text-neutral-900 truncate">${conv.title}</p>
          <p class="text-xs text-neutral-500">${formatRelativeTime(new Date(conv.timestamp))}</p>
        </button>
      `).join('');
    }
  } catch (error) {
    console.error('Failed to load sessions from backend:', error);
    
    // Fallback to localStorage on error
    const conversations = JSON.parse(localStorage.getItem('ragConversations') || '[]');
    
    if (conversations.length === 0) {
      conversationsList.innerHTML = '<div class="text-sm text-neutral-500">No recent conversations</div>';
      return;
    }
    
    conversationsList.innerHTML = conversations.map(conv => `
      <button class="w-full text-left p-2 hover:bg-neutral-50 rounded-lg transition-colors ${conv.id === state.currentConversationId ? 'bg-neutral-50' : ''}" 
              onclick="loadConversation(${conv.id})">
        <p class="text-sm font-medium text-neutral-900 truncate">${conv.title}</p>
        <p class="text-xs text-neutral-500">${formatRelativeTime(new Date(conv.timestamp))}</p>
      </button>
    `).join('');
  }
}

function formatRelativeTime(date) {
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  
  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  if (hours < 24) return `${hours}시간 전`;
  if (days < 7) return `${days}일 전`;
  return date.toLocaleDateString('ko-KR');
}

// New functions for API integration
function initializeSession() {
  // Generate a unique session ID for this chat session
  state.sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  logger.info('CHAT', 'New session initialized', { sessionId: state.sessionId });
}

async function loadSystemInfo() {
  const startTime = Date.now();
  
  try {
    // Load total documents count using API service
    const data = await api.getDocuments();
    const totalDocs = data.documents ? data.documents.length : 0;
    const docsElement = document.getElementById('totalDocsCount');
    if (docsElement) {
      docsElement.textContent = `전체 문서: ${totalDocs}개`;
    }
    logger.debug('SYSTEM', `Loaded document count: ${totalDocs}`);
    
    // Check system status using API service
    const healthData = await api.checkHealth();
    const statusElement = document.getElementById('systemStatus');
    if (statusElement) {
      const isHealthy = healthData.healthy === true;  // Fixed: check 'healthy' field, not 'status'
      statusElement.textContent = isHealthy ? '상태: 정상' : '상태: 점검 필요';
      statusElement.className = isHealthy ? 'mt-1 text-green-600' : 'mt-1 text-red-600';
    }
    
    logger.info('SYSTEM', 'System health check completed', {
      status: healthData.status,
      components: healthData.components,
      duration: `${Date.now() - startTime}ms`
    });
  } catch (error) {
    logger.error('SYSTEM', 'Failed to load system info', { 
      error: error.message,
      duration: `${Date.now() - startTime}ms`
    });
    
    console.error('Failed to load system info:', error);
    const statusElement = document.getElementById('systemStatus');
    if (statusElement) {
      statusElement.textContent = '상태: 오프라인';
      statusElement.className = 'mt-1 text-red-600';
    }
  }
}

function startNewChat() {
  // Clear current conversation
  state.messages = [];
  state.currentConversationId = null;
  state.sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  
  // Clear UI
  document.getElementById('messagesList').innerHTML = '';
  document.getElementById('welcomeMessage').classList.remove('hidden');
  
  // Update conversation list
  loadSavedConversations();
  
  showToast('새 대화를 시작합니다', 'success');
}

// Global functions
window.sendSampleQuestion = function(question) {
  document.getElementById('messageInput').value = question;
  document.getElementById('chatForm').dispatchEvent(new Event('submit'));
};


window.loadConversation = function(conversationId) {
  const conversations = JSON.parse(localStorage.getItem('ragConversations') || '[]');
  const conversation = conversations.find(c => c.id === conversationId);
  
  if (conversation) {
    state.messages = [];
    state.currentConversationId = conversationId;
    document.getElementById('messagesList').innerHTML = '';
    document.getElementById('welcomeMessage').classList.add('hidden');
    
    conversation.messages.forEach(msg => {
      addMessage(msg.role, msg.text);
    });
    
    loadSavedConversations();
  }
};

window.loadSessionFromBackend = async function(sessionId) {
  try {
    // Show loading state
    const messagesList = document.getElementById('messagesList');
    messagesList.innerHTML = '<div class="text-center text-neutral-500 mt-8">대화를 불러오는 중...</div>';
    document.getElementById('welcomeMessage').classList.add('hidden');
    
    // Get session details from backend
    const sessionData = await api.getSessionDetails(sessionId);
    
    if (sessionData && sessionData.messages) {
      // Clear current state
      state.messages = [];
      state.currentConversationId = sessionId;
      state.sessionId = sessionId;
      messagesList.innerHTML = '';
      
      // Add messages from session history
      sessionData.messages.forEach(msg => {
        // Convert backend message format to frontend format
        const role = msg.role === 'user' ? 'user' : 'assistant';
        const text = msg.content || msg.text || '';
        addMessage(role, text);
      });
      
      // Update conversation list to highlight selected
      loadSavedConversations();
      
      showToast('대화를 불러왔습니다', 'success');
    } else {
      throw new Error('세션 데이터를 찾을 수 없습니다');
    }
  } catch (error) {
    console.error('Failed to load session from backend:', error);
    showToast('대화를 불러오는데 실패했습니다', 'error');
    
    // Clear the messages area on error
    document.getElementById('messagesList').innerHTML = '';
    document.getElementById('welcomeMessage').classList.remove('hidden');
  }
};