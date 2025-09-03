/**
 * Admin Dashboard - Refactored Version
 */

import { createIcon, showToast } from './components.js';
import { 
  formatFileSize, 
  formatDate, 
  getDocumentType, 
  getStatusBadge,
  debounce,
  createLoadingSpinner,
  createEmptyState
} from './utils.js';
import { FILE_UPLOAD, PAGINATION, MESSAGES } from './config.js';
import api from './api.js';
import logger from './logger.js';
import { AuthGuard } from './authGuard.js';

// Application State
class AdminApp {
  constructor() {
    this.documents = [];
    this.filteredDocuments = [];
    this.currentPage = 1;
    this.itemsPerPage = PAGINATION.itemsPerPage;
    this.searchQuery = '';
    this.selectedFilter = 'all';
    this.selectedDocs = new Set();
    this.isLoading = false;
  }

  async init() {
    logger.info('ADMIN', 'Initializing admin dashboard');
    
    try {
      console.log('Setting up event listeners...');
      this.setupEventListeners();
      
      console.log('Setting up section navigation...');
      try {
        this.setupSectionNavigation();
      } catch (navError) {
        console.error('Error in setupSectionNavigation:', navError);
      }
      
      console.log('Setting up BigQuery listeners...');
      this.setupBigQueryListeners();
      
      // Initialize filter select value
      const filterSelect = document.getElementById('filterSelect');
      if (filterSelect) {
        filterSelect.value = this.selectedFilter;
      }
      
      await this.loadDocuments();
      this.render();
      
      // BigQuery status will be loaded when user navigates to that section
    } catch (error) {
      logger.error('ADMIN', 'Initialization error', { error: error.message });
      console.error('Full error:', error);
      showToast('초기화 중 오류가 발생했습니다', 'error');
    }
  }

  setupEventListeners() {
    // Search
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', debounce(() => {
        this.searchQuery = searchInput.value;
        this.filterDocuments();
        this.render();
      }, 300));
    }

    // Filter
    const filterSelect = document.getElementById('filterSelect');
    if (filterSelect) {
      filterSelect.addEventListener('change', (e) => {
        this.selectedFilter = e.target.value;
        this.filterDocuments();
        this.render();
      });
    }

    // Upload button
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
      uploadBtn.addEventListener('click', () => this.showUploadModal());
    }

    // File input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    // Upload confirm button
    const uploadConfirmBtn = document.getElementById('uploadConfirmBtn');
    if (uploadConfirmBtn) {
      uploadConfirmBtn.addEventListener('click', () => this.uploadFiles());
    }

    // Modal close buttons
    document.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', () => this.closeModals());
    });

    // Select all checkbox
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
    }

    // Bulk delete button
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    if (bulkDeleteBtn) {
      bulkDeleteBtn.addEventListener('click', () => this.bulkDelete());
    }

    // Pagination
    document.getElementById('prevPage')?.addEventListener('click', () => this.changePage(-1));
    document.getElementById('nextPage')?.addEventListener('click', () => this.changePage(1));
  }

  setupSectionNavigation() {
    const navButtons = document.querySelectorAll('[data-section]');
    console.log('Found nav buttons:', navButtons.length);
    navButtons.forEach(button => {
      console.log('Setting up button for section:', button.dataset.section);
      button.addEventListener('click', () => {
        const targetSection = button.dataset.section;
        console.log('Button clicked for section:', targetSection);
        this.showSection(targetSection);
        
        // Update active state
        navButtons.forEach(btn => {
          btn.classList.remove('nav-btn-active');
        });
        button.classList.add('nav-btn-active');
      });
    });
  }

  showSection(sectionId) {
    console.log('Switching to section:', sectionId);
    document.querySelectorAll('.section-content').forEach(section => {
      section.classList.add('hidden');
    });
    document.getElementById(sectionId)?.classList.remove('hidden');
    
    // Load BigQuery data when switching to BigQuery section
    if (sectionId === 'bigquery') {
      console.log('Loading BigQuery data...');
      this.loadBigQueryStatus();
    }
  }

  async loadDocuments() {
    this.setLoading(true);
    
    try {
      const response = await api.getDocuments();
      
      if (response.success && response.documents) {
        this.documents = response.documents.map(doc => ({
          // Use clear naming convention
          supabaseId: doc.supabase_id,         // Database record ID
          openaiFileId: doc.openai_file_id,    // OpenAI file ID
          displayName: doc.display_name,       // User-visible filename
          storagePath: doc.storage_path,       // Storage bucket path
          fileSize: doc.file_size,             // Human-readable size
          fileSizeBytes: doc.file_size_bytes,  // Size in bytes
          fileType: doc.file_type,             // File extension
          status: doc.status,
          uploadedAt: doc.uploaded_at,
          uploadedById: doc.uploaded_by_id,
          uploadedByEmail: doc.uploaded_by_email
        }));
        
        this.filterDocuments();
        logger.info('ADMIN', `Loaded ${this.documents.length} documents`);
      }
    } catch (error) {
      logger.error('ADMIN', 'Failed to load documents', { error: error.message });
      showToast('문서 목록을 불러오는데 실패했습니다', 'error');
    } finally {
      this.setLoading(false);
    }
  }

  filterDocuments() {
    console.log('Filtering documents:', this.documents);
    console.log('Selected filter:', this.selectedFilter);
    console.log('Search query:', this.searchQuery);
    
    this.filteredDocuments = this.documents.filter(doc => {
      // Search filter
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        if (!doc.displayName.toLowerCase().includes(query)) {
          return false;
        }
      }

      // Status filter
      console.log(`Document ${doc.displayName} status: ${doc.status}, filter: ${this.selectedFilter}`);
      if (this.selectedFilter !== 'all' && doc.status !== this.selectedFilter) {
        return false;
      }

      return true;
    });

    console.log('Filtered documents:', this.filteredDocuments);
    // Reset to first page when filtering
    this.currentPage = 1;
  }

  render() {
    this.renderDocumentTable();
    this.renderPagination();
    this.updateStats();
  }

  renderDocumentTable() {
    const tbody = document.getElementById('documentTableBody');
    if (!tbody) return;

    if (this.isLoading) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-8">
            ${createLoadingSpinner()}
          </td>
        </tr>
      `;
      return;
    }

    if (this.filteredDocuments.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="text-center py-8">
            ${createEmptyState('문서가 없습니다')}
          </td>
        </tr>
      `;
      return;
    }

    // Calculate pagination
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    const pageDocuments = this.filteredDocuments.slice(startIndex, endIndex);

    tbody.innerHTML = pageDocuments.map(doc => `
      <tr class="hover:bg-neutral-50 transition-colors">
        <td class="px-6 py-4 whitespace-nowrap">
          <input type="checkbox" 
                 class="doc-checkbox rounded border-neutral-300" 
                 data-doc-id="${doc.supabaseId}"
                 ${this.selectedDocs.has(doc.supabaseId) ? 'checked' : ''}>
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
          <div class="flex items-center">
            <span class="text-2xl mr-3">${getDocumentType(doc.displayName).icon}</span>
            <div>
              <div class="text-sm font-medium text-neutral-900">${doc.displayName}</div>
              <div class="text-sm text-neutral-500">${doc.fileSize}</div>
            </div>
          </div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
          ${doc.fileType ? doc.fileType.toUpperCase() : ''}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
          ${formatDate(doc.uploadedAt)}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
          ${getStatusBadge(doc.status)}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <button onclick="app.downloadDocument('${doc.supabaseId}')" 
                  class="text-neutral-600 hover:text-neutral-900 mr-3"
                  title="다운로드"
                  ${!doc.openaiFileId ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
            ${createIcon('download', 20)}
          </button>
          <button onclick="app.deleteDocument('${doc.supabaseId}')" 
                  class="text-red-600 hover:text-red-900"
                  title="삭제">
            ${createIcon('trash', 20)}
          </button>
        </td>
      </tr>
    `).join('');

    // Re-attach checkbox listeners
    tbody.querySelectorAll('.doc-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const docId = e.target.dataset.docId;
        if (e.target.checked) {
          this.selectedDocs.add(docId);
        } else {
          this.selectedDocs.delete(docId);
        }
        this.updateBulkActions();
      });
    });
  }

  renderPagination() {
    const totalPages = Math.ceil(this.filteredDocuments.length / this.itemsPerPage);
    
    // Update text
    const startIndex = (this.currentPage - 1) * this.itemsPerPage + 1;
    const endIndex = Math.min(startIndex + this.itemsPerPage - 1, this.filteredDocuments.length);
    
    document.getElementById('showingStart').textContent = this.filteredDocuments.length > 0 ? startIndex : 0;
    document.getElementById('showingEnd').textContent = endIndex;
    document.getElementById('totalDocs').textContent = this.filteredDocuments.length;

    // Update buttons
    document.getElementById('prevPage').disabled = this.currentPage === 1;
    document.getElementById('nextPage').disabled = this.currentPage === totalPages || totalPages === 0;

    // Update page numbers
    const pageNumbers = document.getElementById('pageNumbers');
    if (pageNumbers) {
      pageNumbers.innerHTML = this.generatePageNumbers(totalPages);
    }
  }

  generatePageNumbers(totalPages) {
    if (totalPages <= 1) return '';

    const pages = [];
    const maxButtons = PAGINATION.maxPageButtons;
    let startPage = Math.max(1, this.currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage + 1 < maxButtons) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(`
        <button onclick="app.goToPage(${i})" 
                class="px-3 py-2 text-sm leading-tight rounded-lg ${
                  i === this.currentPage
                    ? 'text-white bg-neutral-900 border border-neutral-900'
                    : 'text-neutral-600 bg-white border border-neutral-300 hover:bg-neutral-50'
                }">
          ${i}
        </button>
      `);
    }

    return pages.join('');
  }

  changePage(direction) {
    const totalPages = Math.ceil(this.filteredDocuments.length / this.itemsPerPage);
    const newPage = this.currentPage + direction;
    
    if (newPage >= 1 && newPage <= totalPages) {
      this.currentPage = newPage;
      this.render();
    }
  }

  goToPage(page) {
    this.currentPage = page;
    this.render();
  }

  updateStats() {
    const totalDocs = this.documents.length;
    const activeDocs = this.documents.filter(d => d.status === 'active').length;
    const totalSize = this.documents.reduce((sum, doc) => {
      // Use the new fileSize property
      if (doc.fileSize) {
        const sizeMatch = doc.fileSize.match(/[\d.]+/);
        return sum + (sizeMatch ? parseFloat(sizeMatch[0]) : 0);
      }
      return sum;
    }, 0);

    const totalDocsElement = document.getElementById('totalDocuments');
    if (totalDocsElement) {
      totalDocsElement.textContent = totalDocs;
    }
  }

  // File Upload Methods
  showUploadModal() {
    document.getElementById('uploadModal').classList.remove('hidden');
    document.getElementById('fileInput').value = '';
    document.getElementById('fileList').innerHTML = '';
    document.getElementById('fileList').classList.add('hidden');
  }

  closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
      modal.classList.add('hidden');
    });
  }

  handleFileSelect(event) {
    const files = Array.from(event.target.files);
    const fileList = document.getElementById('fileList');
    
    if (files.length === 0) {
      fileList.classList.add('hidden');
      return;
    }

    // Validate files
    const validFiles = files.filter(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      if (!FILE_UPLOAD.allowedTypes.includes(ext)) {
        showToast(`${file.name}: ${MESSAGES.upload.invalidType}`, 'error');
        return false;
      }
      if (file.size > FILE_UPLOAD.maxFileSize) {
        showToast(`${file.name}: ${MESSAGES.upload.tooLarge}`, 'error');
        return false;
      }
      return true;
    });

    // Display file list
    fileList.innerHTML = `
      <h3 class="font-medium text-gray-900 mb-2">선택된 파일 (${validFiles.length}개)</h3>
      <ul class="space-y-2">
        ${validFiles.map(file => {
          const type = getDocumentType(file.name);
          return `
            <li class="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div class="flex items-center">
                <span class="text-2xl mr-2">${type.icon}</span>
                <span class="text-sm text-gray-900">${file.name}</span>
              </div>
              <span class="text-sm text-gray-500">${formatFileSize(file.size)}</span>
            </li>
          `;
        }).join('')}
      </ul>
    `;
    
    fileList.classList.remove('hidden');
  }

  async uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const files = Array.from(fileInput.files);
    
    if (files.length === 0) {
      showToast('파일을 선택해주세요', 'error');
      return;
    }

    this.setLoading(true, '파일 업로드 중...');
    
    try {
      const response = await api.uploadDocuments(files);
      
      // DEBUG: Log the full response
      console.log('Upload response:', response);
      if (response.documents) {
        console.log('Documents in response:', response.documents);
        response.documents.forEach((doc, index) => {
          console.log(`Document ${index}:`, doc);
        });
      }
      
      if (response.success) {
        showToast(MESSAGES.upload.success, 'success');
        this.closeModals();
        await this.loadDocuments();
        this.render();  // Re-render the UI after loading documents
      } else {
        // Show specific error message
        const errorMsg = response.message || 'Upload failed';
        const failedFiles = response.documents && Array.isArray(response.documents)
          ? response.documents
              .filter(doc => doc.status === 'error')
              .map(doc => `${doc.filename}: ${doc.error}`)
              .join('\n')
          : '';
        
        showToast(`${errorMsg}\n${failedFiles}`, 'error');
      }
    } catch (error) {
      logger.error('ADMIN', 'Upload failed', { error: error.message });
      showToast(MESSAGES.upload.error, 'error');
    } finally {
      this.setLoading(false);
    }
  }

  // Document Actions
  async downloadDocument(docId) {
    try {
      const url = await api.downloadDocument(docId);
      window.open(url, '_blank');
      logger.info('ADMIN', `Download initiated for document: ${docId}`);
    } catch (error) {
      logger.error('ADMIN', 'Download failed', { error: error.message });
      showToast('다운로드 중 오류가 발생했습니다', 'error');
    }
  }

  async deleteDocument(docId) {
    if (!confirm(MESSAGES.delete.confirm)) {
      return;
    }

    this.setLoading(true, '문서 삭제 중...');

    try {
      const result = await api.deleteDocument(docId);
      logger.info('ADMIN', `Delete API response:`, result);
      
      if (result.success) {
        showToast(MESSAGES.delete.success, 'success');
        
        // Immediately remove from local state using supabaseId
        this.documents = this.documents.filter(doc => doc.supabaseId !== docId);
        this.filterDocuments();
        this.render();
        
        logger.info('ADMIN', `Document deleted: ${docId}`);
        
        // Optionally reload from server in background to sync
        this.loadDocuments().catch(err => {
          logger.error('ADMIN', 'Failed to sync after delete', { error: err.message });
        });
      } else {
        throw new Error(result.error || 'Delete failed');
      }
    } catch (error) {
      logger.error('ADMIN', 'Delete failed', { error: error.message });
      showToast(MESSAGES.delete.error, 'error');
      // Reload to ensure UI is in sync with server state
      await this.loadDocuments();
      this.render();
    } finally {
      this.setLoading(false);
    }
  }

  // Bulk Actions
  toggleSelectAll(checked) {
    const checkboxes = document.querySelectorAll('.doc-checkbox');
    checkboxes.forEach(checkbox => {
      checkbox.checked = checked;
      const docId = checkbox.dataset.docId;
      if (checked) {
        this.selectedDocs.add(docId);
      } else {
        this.selectedDocs.delete(docId);
      }
    });
    this.updateBulkActions();
  }

  updateBulkActions() {
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const selectedCount = this.selectedDocs.size;
    
    if (bulkDeleteBtn) {
      bulkDeleteBtn.disabled = selectedCount === 0;
      bulkDeleteBtn.textContent = selectedCount > 0 
        ? `선택 삭제 (${selectedCount})` 
        : '선택 삭제';
    }
  }

  async bulkDelete() {
    const count = this.selectedDocs.size;
    if (count === 0) return;

    if (!confirm(`선택한 ${count}개의 문서를 삭제하시겠습니까?`)) {
      return;
    }

    this.setLoading(true, '문서 삭제 중...');
    
    try {
      // Map selected doc IDs to their OpenAI file IDs for deletion
      const deletePromises = Array.from(this.selectedDocs).map(supabaseId => {
        const doc = this.documents.find(d => d.supabaseId === supabaseId);
        if (!doc || !doc.openaiFileId) {
          return { error: 'File ID not found', supabaseId };
        }
        return api.deleteDocument(doc.openaiFileId).catch(err => ({ error: err, supabaseId }));
      });
      
      const results = await Promise.all(deletePromises);
      const failures = results.filter(r => r.error);
      const successfulDeletes = results.filter(r => !r.error && r.success);
      
      if (failures.length > 0) {
        showToast(`${failures.length}개 문서 삭제 실패`, 'error');
      } else {
        showToast(`${count}개 문서가 삭제되었습니다`, 'success');
      }
      
      // Immediately remove successfully deleted documents from local state
      const deletedIds = new Set(Array.from(this.selectedDocs));
      failures.forEach(f => deletedIds.delete(f.supabaseId));
      
      this.documents = this.documents.filter(doc => !deletedIds.has(doc.supabaseId));
      this.selectedDocs.clear();
      this.filterDocuments();
      this.render();
      
      // Sync with server in background
      this.loadDocuments().catch(err => {
        logger.error('ADMIN', 'Failed to sync after bulk delete', { error: err.message });
      });
    } catch (error) {
      logger.error('ADMIN', 'Bulk delete failed', { error: error.message });
      showToast('일괄 삭제 중 오류가 발생했습니다', 'error');
      // Reload to ensure UI is in sync
      await this.loadDocuments();
      this.render();
    } finally {
      this.setLoading(false);
    }
  }

  // Utility Methods
  setLoading(loading, message = '로딩 중...') {
    this.isLoading = loading;
    
    // Update UI loading state
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
      if (loading) {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.querySelector('.loading-message').textContent = message;
      } else {
        loadingOverlay.classList.add('hidden');
      }
    }
  }

  // BigQuery Integration Methods
  setupBigQueryListeners() {
    const refreshBtn = document.getElementById('refreshSchemasBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshBigQuerySchemas());
    }
  }

  async loadBigQueryStatus() {
    try {
      const response = await api.getBigQueryStatus();
      logger.info('ADMIN', 'BigQuery status response:', response);
      
      // Update status (response doesn't have 'success' field)
      const isEnabled = response.enabled === true;
      logger.info('ADMIN', `BigQuery enabled: ${isEnabled}`);
      
      document.getElementById('bigqueryStatus').textContent = isEnabled ? '활성' : '비활성';
      document.getElementById('bigqueryStatus').className = isEnabled 
        ? 'text-2xl font-bold text-green-600' 
        : 'text-2xl font-bold text-gray-400';
      
      // Update dataset
      document.getElementById('datasetId').textContent = response.dataset_id || response.project_id || '-';
      
      // Update table count
      document.getElementById('tableCount').textContent = response.table_count || 0;
      
      // Update last refresh
      if (response.last_updated) {
        const date = new Date(response.last_updated);
        document.getElementById('lastRefresh').textContent = formatDate(date);
      } else {
        document.getElementById('lastRefresh').textContent = '없음';
      }
      
      // Load table list
      if (isEnabled) {
        logger.info('ADMIN', 'BigQuery is enabled, loading tables...');
        await this.loadBigQueryTables();
      } else {
        logger.info('ADMIN', 'BigQuery is disabled, showing disabled message');
        this.showBigQueryDisabled();
      }
    } catch (error) {
      logger.error('ADMIN', 'Failed to load BigQuery status', { error: error.message });
      this.showBigQueryError();
    }
  }

  async loadBigQueryTables() {
    try {
      logger.info('ADMIN', 'Loading BigQuery tables...');
      const response = await api.getBigQueryTables();
      logger.info('ADMIN', `Received ${response.tables ? response.tables.length : 0} tables`);
      
      if (response.success && response.tables) {
        this.renderBigQueryTables(response.tables);
      } else {
        logger.warn('ADMIN', 'No tables in response or success=false', response);
      }
    } catch (error) {
      logger.error('ADMIN', 'Failed to load BigQuery tables', { error: error.message });
    }
  }

  renderBigQueryTables(tables) {
    logger.info('ADMIN', `Rendering ${tables.length} BigQuery tables`);
    console.log('Tables to render:', tables); // Debug log
    
    const tbody = document.getElementById('tableListBody');
    if (!tbody) {
      logger.error('ADMIN', 'tableListBody element not found!');
      return;
    }
    
    console.log('Found tbody element:', tbody); // Debug log

    if (tables.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-8 text-gray-500">
            테이블이 없습니다. 스키마를 갱신해주세요.
          </td>
        </tr>
      `;
      return;
    }

    // Log first table for debugging
    console.log('First table:', tables[0]);
    
    const html = tables.map(table => `
      <tr class="hover:bg-gray-50 transition-colors">
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
          ${table.table_name || table.table_id}
        </td>
        <td class="px-6 py-4 text-sm text-gray-500">
          ${table.description || '-'}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          ${table.column_count || 0}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          ${table.row_count ? table.row_count.toLocaleString() : '-'}
        </td>
      </tr>
    `).join('');
    
    console.log('Generated HTML length:', html.length); // Debug log
    tbody.innerHTML = html;
    console.log('Tables rendered successfully'); // Debug log
  }

  showBigQueryDisabled() {
    const schemaInfo = document.getElementById('schemaInfo');
    if (schemaInfo) {
      schemaInfo.innerHTML = `
        <div class="text-center py-8">
          <svg class="w-16 h-16 text-gray-400 mx-auto mb-4" fill="currentColor" viewBox="0 0 256 256">
            <path d="M224,177.32V78.68a8,8,0,0,0-4.07-7L134.07,24.21a8,8,0,0,0-7.93,0L40.21,71.68a8,8,0,0,0-4.07,7v98.64a8,8,0,0,0,4.07,7l85.86,47.47a8,8,0,0,0,7.93,0l85.86-47.47A8,8,0,0,0,224,177.32Z"></path>
          </svg>
          <p class="text-gray-600 mb-4">BigQuery 연동이 비활성화되어 있습니다</p>
          <p class="text-sm text-gray-500">BigQuery 서비스 계정 키를 설정하고<br>환경 변수를 구성해주세요</p>
        </div>
      `;
    }

    const tbody = document.getElementById('tableListBody');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center py-8 text-gray-500">
            BigQuery가 연동되지 않았습니다
          </td>
        </tr>
      `;
    }
  }

  showBigQueryError() {
    const schemaInfo = document.getElementById('schemaInfo');
    if (schemaInfo) {
      schemaInfo.innerHTML = `
        <div class="text-center py-8">
          <p class="text-red-600">BigQuery 상태를 불러올 수 없습니다</p>
        </div>
      `;
    }
  }

  async refreshBigQuerySchemas() {
    const confirmRefresh = confirm('BigQuery 테이블 목록을 새로고침하시겠습니까?');
    if (!confirmRefresh) return;

    this.setLoading(true, 'BigQuery 테이블 목록 새로고침 중...');

    try {
      const response = await api.refreshBigQuerySchemas();
      
      if (response.success) {
        showToast(`${response.count}개 테이블을 찾았습니다`, 'success');
        
        // Reload status and tables
        await this.loadBigQueryStatus();
      } else {
        throw new Error(response.error || 'Table refresh failed');
      }
    } catch (error) {
      logger.error('ADMIN', 'Failed to refresh table list', { error: error.message });
      showToast('테이블 목록 새로고침 중 오류가 발생했습니다', 'error');
    } finally {
      this.setLoading(false);
    }
  }
}

// Initialize app when DOM is ready
const app = new AdminApp();
window.app = app; // Make available globally for onclick handlers

// Add debug function for testing
window.testBigQuery = async function() {
  console.log('Testing BigQuery table loading...');
  await app.loadBigQueryStatus();
  console.log('Done loading BigQuery status');
};

// Require admin role before initializing
document.addEventListener('DOMContentLoaded', async () => {
  // Check auth and require admin role
  const isAuthorized = await AuthGuard.requireAuth('admin');
  
  if (isAuthorized) {
    // Setup auth UI
    AuthGuard.setupLogoutButton();
    AuthGuard.updateUIForAuth();
    
    // Initialize admin app
    app.init();
  }
});