/**
 * Super Admin Audit Logs Management
 * Comprehensive audit trail functionality with modern design patterns
 */

// Initialize the audit logs module
class AuditLogsManager {
  constructor() {
    // Configuration
    this.config = {
      api: {
        base: '',
        endpoints: {
          list: '/api/v1/super/audit/list',
          export: '/api/v1/super/audit/export'
        }
      },
      pagination: {
        defaultLimit: 50,
        maxLimit: 200
      }
    };
    
    // DOM elements
    this.elements = {
      exportBtn: document.getElementById('exportAudit'),
      refreshBtn: document.getElementById('refreshAudit'),
      auditForm: document.getElementById('auditFilter'),
      resetBtn: document.getElementById('resetAudit'),
      auditTable: document.getElementById('auditTable'),
      tableBody: document.getElementById('auditTableBody'),
      loadMoreBtn: document.getElementById('loadMoreAudit'),
      summaryNode: document.getElementById('auditSummary'),
      paginationInfo: document.getElementById('paginationInfo'),
      endNode: document.getElementById('auditEnd'),
      prevPageBtn: document.getElementById('prevPage'),
      nextPageBtn: document.getElementById('nextPage'),
      currentPageSpan: document.getElementById('currentPage'),
      totalPagesSpan: document.getElementById('totalPages'),
      auditStatus: document.getElementById('auditStatus')
    };
    
    // State variables
    this.state = {
      currentPage: 1,
      totalPages: 1,
      hasNextPage: false,
      hasPrevPage: false,
      activeParams: { limit: this.config.pagination.defaultLimit },
      loading: false,
      error: null,
      allAuditData: [] // Store all data for charts
    };
    
    // Chart instances
    this.charts = {
      eventTypeChart: null,
      activityChart: null
    };
    
    // Bind event handlers
    this.bindEvents();
    
    // Initial load
    this.initialize();
  }
  
  /**
   * Initialize the audit logs manager
   */
  async initialize() {
    this.updateAuditStatus('active');
    await this.fetchAudit(this.state.activeParams);
    
    // Initialize charts after a short delay to ensure DOM is fully loaded
    setTimeout(() => {
      this.initializeCharts();
    }, 500);
  }
  
  /**
   * Bind event handlers to DOM elements
   */
  bindEvents() {
    // Form submission handler
    if (this.elements.auditForm) {
      this.elements.auditForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleFormSubmit();
      });
    }
    
    // Reset button handler
    if (this.elements.resetBtn) {
      this.elements.resetBtn.addEventListener('click', () => {
        this.handleReset();
      });
    }
    
    // Refresh button handler
    if (this.elements.refreshBtn) {
      this.elements.refreshBtn.addEventListener('click', () => {
        this.handleRefresh();
      });
    }
    
    // Previous page button handler
    if (this.elements.prevPageBtn) {
      this.elements.prevPageBtn.addEventListener('click', () => {
        this.handlePrevPage();
      });
    }
    
    // Next page button handler
    if (this.elements.nextPageBtn) {
      this.elements.nextPageBtn.addEventListener('click', () => {
        this.handleNextPage();
      });
    }
    
    // Export button handler
    if (this.elements.exportBtn) {
      this.elements.exportBtn.addEventListener('click', () => {
        this.handleExport();
      });
    }
 }
  
  /**
   * Handle form submission
   */
  handleFormSubmit() {
    const formData = new FormData(this.elements.auditForm);
    
    // Build active parameters from form data
    this.state.activeParams = { 
      limit: formData.get('limit') || this.config.pagination.defaultLimit 
    };
    
    for (const [key, value] of formData.entries()) {
      if (value && key !== 'limit' && key !== 'page') {
        this.state.activeParams[key] = value;
      }
    }
    
    // Reset to first page and fetch data
    this.state.currentPage = 1;
    this.fetchAudit(this.state.activeParams);
  }
  
  /**
   * Handle reset action
   */
  handleReset() {
    this.elements.auditForm.reset();
    this.state.activeParams = { limit: this.config.pagination.defaultLimit };
    this.state.currentPage = 1;
    this.fetchAudit(this.state.activeParams);
  }
  
  /**
   * Handle refresh action
   */
  handleRefresh() {
    this.fetchAudit(this.state.activeParams);
  }
  
  /**
   * Handle previous page navigation
   */
  handlePrevPage() {
    if (this.state.hasPrevPage) {
      this.state.currentPage--;
      this.fetchAudit(this.state.activeParams);
    }
  }
  
  /**
   * Handle next page navigation
   */
  handleNextPage() {
    if (this.state.hasNextPage) {
      this.state.currentPage++;
      this.fetchAudit(this.state.activeParams);
    }
  }
  
  /**
   * Handle export functionality
   */
  async handleExport() {
    if (!this.elements.exportBtn) return;
    
    this.elements.exportBtn.disabled = true;
    this.elements.exportBtn.textContent = 'Exporting...';
    
    try {
      const params = { ...this.state.activeParams };
      // Remove pagination specific params for export
      delete params.page; // server will use its own export logic
      
      const qs = new URLSearchParams(params).toString();
      const response = await fetch(`${this.config.api.base}${this.config.api.endpoints.export}${qs ? ('?' + qs) : ''}`);
      
      if (!response.ok) {
        throw new Error(`Export failed with status ${response.status}`);
      }
      
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      // Create and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      
      // Clean up object URL
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      
      this.showNotification('Audit logs exported successfully', 'success');
    } catch (error) {
      console.error('Export error:', error);
      this.showNotification('Error exporting audit logs. Please try again.', 'error');
    } finally {
      if (this.elements.exportBtn) {
        this.elements.exportBtn.disabled = false;
        this.elements.exportBtn.textContent = 'Export (JSON)';
      }
    }
  }
  
  /**
   * Fetch audit logs from the API with pagination
   * @param {Object} params - Query parameters for the API request
   */
  async fetchAudit(params) {
    if (this.state.loading) return;
    
    this.state.loading = true;
    this.updateLoadingState(true);
    
    try {
      // Add pagination parameters
      const p = { ...params, page: this.state.currentPage };
      const qs = new URLSearchParams(p).toString();
      const response = await fetch(`${this.config.api.base}${this.config.api.endpoints.list}?${qs}`);
      
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update UI with new data
      this.renderRows(data.items || []);
      
      // Update pagination info
      this.state.currentPage = data.current_page || 1;
      this.state.totalPages = data.total_pages || 1;
      this.state.hasNextPage = data.has_next || false;
      this.state.hasPrevPage = data.has_prev || false;
      
      // Update pagination UI
      this.updatePaginationUI();
      
      // Update load more button visibility (hide since we're using page-based pagination)
      if (this.elements.loadMoreBtn) {
        this.elements.loadMoreBtn.style.display = 'none';
      }
      
      // Update end marker visibility
      if (this.elements.endNode) {
        this.elements.endNode.style.display = this.state.hasNextPage ? 'none' : 'inline';
      }
      
      // Update summary text
      if (this.elements.summaryNode) {
        const totalRecords = data.total_count || 0;
        this.elements.summaryNode.textContent = `${totalRecords} records`;
      }
      
      if (this.elements.paginationInfo) {
        const totalShown = data.items ? data.items.length : 0;
        const totalRecords = data.total_count || 0;
        this.elements.paginationInfo.textContent = `${totalShown} of ${totalRecords} records`;
      }
      
      // Store all data for charts (only when on first page or doing a fresh search)
      if (this.state.currentPage === 1) {
        this.state.allAuditData = data.items || [];
        this.updateCharts();
      } else {
        // For pagination, we'd need to fetch all data separately for charts
        // For now, just update with current page data
        this.state.allAuditData = [...this.state.allAuditData, ...(data.items || [])];
        // Only update charts if they exist to avoid initialization issues
        if (this.charts.eventTypeChart && this.charts.activityChart) {
          this.updateCharts();
        }
      }
      
      this.state.error = null;
      this.updateAuditStatus('active');
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      this.state.error = error.message;
      this.showError(error.message);
      this.updateAuditStatus('error');
    } finally {
      this.state.loading = false;
      this.updateLoadingState(false);
    }
  }
  
 /**
   * Render audit log rows in the table
   * @param {Array} items - Array of audit log objects
   */
  renderRows(items) {
    if (!this.elements.tableBody) return;
    
    // Clear existing content
    this.elements.tableBody.innerHTML = '';
    
    if (items.length === 0) {
      // Show empty state
      this.elements.tableBody.innerHTML = `
        <tr>
          <td colspan="8" class="px-6 py-12 text-center text-gray-500">
            <div class="flex flex-col items-center justify-center">
              <svg class="w-12 h-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <p class="text-lg font-medium">No audit logs found</p>
              <p class="mt-1">Apply filters to see audit logs</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }
    
    // Process each item and create table rows
    items.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'bg-white border-b hover:bg-gray-50 transition-colors duration-150';
      
      // Format the row with audit log data
      tr.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${item.id || ''}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium 
            ${this.getEventBadgeClass(item.event || '')}">
            ${this.formatEventName(item.event || '')}
          </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.user_id || ''}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.target_user_id || ''}</td>
        <td class="px-6 py-4 text-sm text-gray-500 max-w-xs">
          ${this.formatDetails(item)}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.ip_address || ''}</td>
        <td class="px-6 py-4 text-sm text-gray-500 max-w-xs truncate" title="${this.formatUserAgent(item.user_agent || '')}">
          ${this.formatUserAgent(item.user_agent || '').substring(0, 30)}${(item.user_agent || '').length > 30 ? '...' : ''}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          <div class="flex flex-col">
            <span>${new Date(item.created_at).toLocaleString()}</span>
            <span class="text-xs text-gray-400">${this.getTimeAgo(new Date(item.created_at))}</span>
          </div>
        </td>
      `;
      
      this.elements.tableBody.appendChild(tr);
    });
    
    // Bind event listeners to view details buttons after they're added to the DOM
    this.bindDetailsEventListeners();
  }
  
  /**
   * Get CSS class for event badge based on event type
   * @param {string} event - Event type
   * @returns {string} CSS class name
   */
  getEventBadgeClass(event) {
    const eventTypes = {
      'login': 'bg-green-100 text-green-800',
      'logout': 'bg-red-100 text-red-800',
      'user_create': 'bg-blue-100 text-blue-800',
      'user_update': 'bg-blue-100 text-blue-800',
      'user_delete': 'bg-red-100 text-red-800',
      'admin_action': 'bg-purple-100 text-purple-800',
      'security_event': 'bg-yellow-100 text-yellow-800'
    };
    
    // Default to security event if specific type not found
    return eventTypes[event] || 'bg-gray-100 text-gray-800';
  }
  
  /**
   * Format event name for display
   * @param {string} event - Event type
   * @returns {string} Formatted event name
   */
  formatEventName(event) {
    const eventNames = {
      'login': 'Login',
      'logout': 'Logout',
      'user_create': 'User Create',
      'user_update': 'User Update',
      'user_delete': 'User Delete',
      'admin_action': 'Admin Action',
      'security_event': 'Security Event'
    };
    
    return eventNames[event] || event.charAt(0).toUpperCase() + event.slice(1);
  }
  
  /**
   * Format details for display - handles structured data
   * @param {Object} item - The full audit log item containing details
   * @returns {string} Formatted HTML for details column
   */
  formatDetails(item) {
    // Extract details from the item
    let details = item.detail || {};
    
    // If details is a string, try to parse it as JSON
    if (typeof details === 'string') {
      try {
        details = JSON.parse(details);
      } catch (e) {
        // If it's not valid JSON, return as is but truncated
        return `<span title="${details}">${details.substring(0, 120)}${details.length > 120 ? '...' : ''}</span>`;
      }
    }
    
    // If details is an object, format it nicely
    if (typeof details === 'object' && details !== null) {
      const keys = Object.keys(details);
      
      if (keys.length === 0) {
        return '<span class="text-gray-400">No details</span>';
      }
      
      // For objects with few keys, show them inline
      if (keys.length <= 3) {
        return keys.map(key => {
          const value = details[key];
          const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
          return `<span class="inline-block mr-2 mb-1 px-2 py-1 bg-gray-100 rounded text-xs" title="${key}: ${displayValue}">${key}: ${displayValue}</span>`;
        }).join('');
      }
      
      // For objects with many keys, show a summary with a view details button
      // Properly encode the item for the data attribute
      const itemString = JSON.stringify(item);
      const encodedItem = encodeURIComponent(itemString);
      
      // Build the HTML string manually to avoid template literal issues
      let html = '<div class="details-summary">';
      html += '<div class="details-preview">';
      
      // Add first 2 key-value pairs
      for (let i = 0; i < Math.min(2, keys.length); i++) {
        const key = keys[i];
        const value = details[key];
        const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
        html += `<div class="detail-item"><span class="font-medium">${key}:</span> ${displayValue}</div>`;
      }
      
      // Add "more" indicator if there are more than 2 keys
      if (keys.length > 2) {
        html += `<div class="text-gray-500 text-xs mt-1">+${keys.length - 2} more</div>`;
      }
      
      html += '</div>';
      html += '<div class="details-full hidden">';
      
      // Add all key-value pairs to the full details
      for (let i = 0; i < keys.length; i++) {
        const key = keys[i];
        const value = details[key];
        const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
        html += `<div class="detail-item"><span class="font-medium">${key}:</span> ${displayValue}</div>`;
      }
      
      html += '</div>';
      html += `<button class="view-details-btn text-xs text-blue-600 hover:text-blue-800 mt-1" type="button" data-item="${encodedItem}">View details</button>`;
      html += '</div>';
      
      return html;
    }
    
    // For other types, return as string
    return String(details);
 }
  
  /**
   * Format user agent for display
   * @param {string} userAgent - User agent string
   * @returns {string} Formatted user agent
   */
  formatUserAgent(userAgent) {
    if (!userAgent) return 'Unknown';
    
    // Try to parse user agent to extract useful information
    try {
      // This is a simplified version - in a real application you might use a library like ua-parser-js
      const browserMatch = userAgent.match(/(Chrome|Firefox|Safari|Edge|Opera|MSIE|Trident)/i);
      const osMatch = userAgent.match(/(Windows|Mac|Linux|Android|iOS|iPhone|iPad)/i);
      
      if (browserMatch && osMatch) {
        return `${browserMatch[0]} on ${osMatch[0]}`;
      }
      
      return userAgent;
    } catch (e) {
      return userAgent;
    }
  }
  
  /**
   * Calculate time ago string
   * @param {Date} date - Date object
   * @returns {string} Time ago string
   */
  getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  }
  
  /**
   * Update pagination UI elements
   */
  updatePaginationUI() {
    if (this.elements.currentPageSpan) {
      this.elements.currentPageSpan.textContent = this.state.currentPage;
    }
    
    if (this.elements.totalPagesSpan) {
      this.elements.totalPagesSpan.textContent = this.state.totalPages;
    }
    
    if (this.elements.prevPageBtn) {
      this.elements.prevPageBtn.disabled = !this.state.hasPrevPage;
      this.elements.prevPageBtn.classList.toggle('opacity-50', !this.state.hasPrevPage);
      this.elements.prevPageBtn.classList.toggle('cursor-not-allowed', !this.state.hasPrevPage);
    }
    
    if (this.elements.nextPageBtn) {
      this.elements.nextPageBtn.disabled = !this.state.hasNextPage;
      this.elements.nextPageBtn.classList.toggle('opacity-50', !this.state.hasNextPage);
      this.elements.nextPageBtn.classList.toggle('cursor-not-allowed', !this.state.hasNextPage);
    }
 }
  
  /**
   * Update loading state UI
   * @param {boolean} isLoading - Whether loading state is active
   */
  updateLoadingState(isLoading) {
    const table = document.querySelector('#auditTable tbody');
    if (table) {
      if (isLoading) {
        table.innerHTML = `
          <tr>
            <td colspan="8" class="px-6 py-12 text-center">
              <div class="flex flex-col items-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2"></div>
                <span class="text-gray-500">Loading audit logs...</span>
              </div>
            </td>
          </tr>
        `;
      }
    }
  }
  
  /**
   * Update audit status indicator
   * @param {string} status - Status ('active', 'error', etc.)
   */
  updateAuditStatus(status) {
    if (!this.elements.auditStatus) return;
    
    const statusClasses = {
      'active': 'bg-green-100 text-green-800',
      'error': 'bg-red-100 text-red-800',
      'warning': 'bg-yellow-100 text-yellow-800'
    };
    
    const statusText = {
      'active': 'Active',
      'error': 'Error',
      'warning': 'Warning'
    };
    
    this.elements.auditStatus.className = 'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ' + 
                                          (statusClasses[status] || statusClasses.active);
    
    this.elements.auditStatus.innerHTML = `
      <span class="w-2 h-2 rounded-full ${status === 'active' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-yellow-50'} mr-2"></span>
      ${statusText[status] || statusText.active}
    `;
  }
  
  /**
   * Show error message
   * @param {string} message - Error message
   */
  showError(message) {
    // Create error notification
    this.showNotification(message, 'error');
  }
  
  /**
   * Show notification message
   * @param {string} message - Message to show
   * @param {string} type - Type of notification ('success', 'error', 'warning', 'info')
   */
  showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.notification-toast');
    existingNotifications.forEach(notification => notification.remove());
    
    // Create notification container
    const notification = document.createElement('div');
    notification.className = `notification-toast fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white ${
      type === 'success' ? 'bg-green-500' : 
      type === 'error' ? 'bg-red-500' : 
      type === 'warning' ? 'bg-yellow-500' : 'bg-blue-50'
    } transition-opacity duration-300`;
    notification.innerHTML = `
      <div class="flex items-center">
        <span>${message}</span>
        <button class="ml-4 text-white hover:text-gray-200 focus:outline-none close-btn">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Add close event
    const closeBtn = notification.querySelector('.close-btn');
    closeBtn.addEventListener('click', () => {
      notification.style.opacity = '0';
      setTimeout(() => {
        notification.remove();
      }, 300);
    });
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (notification.parentNode) {
        notification.style.opacity = '0';
        setTimeout(() => {
          notification.remove();
        }, 300);
      }
    }, 5000);
  }
  
  /**
   * Initialize charts
   */
  async initializeCharts() {
    // Wait for DOM to be ready
    if (!document.getElementById('eventTypeChart') || !document.getElementById('activityChart')) {
      // If elements don't exist yet, wait a bit and try again
      await new Promise(resolve => setTimeout(resolve, 100));
      if (!document.getElementById('eventTypeChart') || !document.getElementById('activityChart')) {
        return; // Charts not available
      }
    }
    
    // Destroy existing charts if they exist to avoid canvas reuse errors
    if (this.charts.eventTypeChart) {
      this.charts.eventTypeChart.destroy();
    }
    
    if (this.charts.activityChart) {
      this.charts.activityChart.destroy();
    }
    
    // Initialize event type chart
    const eventTypeCtx = document.getElementById('eventTypeChart').getContext('2d');
    this.charts.eventTypeChart = new Chart(eventTypeCtx, {
      type: 'doughnut',
      data: {
        labels: [],
        datasets: [{
          data: [],
          backgroundColor: [
            '#36A2EB', // Blue
            '#FF6384', // Red
            '#FFCE56', // Yellow
            '#4BC0C0', // Teal
            '#9966FF', // Purple
            '#FF9F40', // Orange
            '#8AC926', // Green
            '#1982C4'  // Dark Blue
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || 0;
                return `${label}: ${value}`;
              }
            }
          }
        }
      }
    });
    
    // Initialize activity chart
    const activityCtx = document.getElementById('activityChart').getContext('2d');
    this.charts.activityChart = new Chart(activityCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Audit Events',
          data: [],
          borderColor: '#36A2EB',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          }
        }
      }
    });
    
    // Update charts with existing data if available
    if (this.state.allAuditData.length > 0) {
      this.updateCharts();
    }
  }
  
  /**
   * Bind event listeners to view details buttons
   */
  bindDetailsEventListeners() {
    // Remove existing listeners to avoid duplicates
    const buttons = document.querySelectorAll('.view-details-btn');
    buttons.forEach(button => {
      // Get the item data from the button's data attribute
      const itemData = button.getAttribute('data-item');
      if (itemData) {
        try {
          // First decode the URI component, then parse the JSON
          const decodedItemData = decodeURIComponent(itemData);
          const item = JSON.parse(decodedItemData);
          
          // Remove previous listeners if any
          const newButton = button.cloneNode(true);
          button.parentNode.replaceChild(newButton, button);
          
          // Add new event listener
          newButton.addEventListener('click', (e) => {
            e.preventDefault();
            // Create a modal to display the full details
            this.createModalForDetails(item);
          });
        } catch (e) {
          console.error('Error parsing audit log item data:', e);
          console.log('Problematic data:', itemData);
          
          // If parsing fails, try to handle it more gracefully
          try {
            // Attempt to decode and parse again with additional error handling
            const decodedItemData = decodeURIComponent(itemData);
            // Try to fix common JSON issues before parsing
            const sanitizedData = decodedItemData
              .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // Remove control characters
              .replace(/\\'/g, "'"); // Fix escaped quotes
            
            const item = JSON.parse(sanitizedData);
            
            // Remove previous listeners if any
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            // Add new event listener
            newButton.addEventListener('click', (e) => {
              e.preventDefault();
              // Create a modal to display the full details
              this.createModalForDetails(item);
            });
          } catch (e2) {
            console.error('Second attempt to parse audit log item data also failed:', e2);
          }
        }
      }
    });
  }
  
  /**
   * Create a modal for detailed view of audit log
   * @param {Object} item - The audit log item containing all the data
   */
  createModalForDetails(item) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
    overlay.id = 'audit-details-modal-overlay';
    
    // Parse the details if it's a string
    let details = item.detail || {};
    if (typeof details === 'string') {
      try {
        details = JSON.parse(details);
      } catch (e) {
        // If it's not valid JSON, keep as string but sanitize it for HTML
        details = this.sanitizeHtml(details);
      }
    }
    
    // Format details for display in the modal
    let detailsHtml = '<p class="text-gray-500 italic">No details available</p>';
    if (typeof details === 'object' && details !== null) {
      const keys = Object.keys(details);
      if (keys.length > 0) {
        detailsHtml = '<ul class="space-y-2">';
        keys.forEach(key => {
          const value = details[key];
          const displayValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : this.sanitizeHtml(String(value));
          detailsHtml += `<li class="flex"><span class="font-medium w-32 flex-shrink-0">${this.sanitizeHtml(key)}:</span> <span class="break-words">${displayValue}</span></li>`;
        });
        detailsHtml += '</ul>';
      }
    } else if (typeof details === 'string') {
      detailsHtml = `<pre class="whitespace-pre-wrap break-words">${details}</pre>`;
    }
    
    // Sanitize other fields that will be inserted into HTML
    const sanitizedId = this.sanitizeHtml((item.id || 'N/A').toString());
    const sanitizedEvent = this.sanitizeHtml((item.event ? this.formatEventName(item.event) : 'N/A').toString());
    const sanitizedUserId = this.sanitizeHtml((item.user_id || 'N/A').toString());
    const sanitizedTargetUserId = this.sanitizeHtml((item.target_user_id || 'N/A').toString());
    const sanitizedIpAddress = this.sanitizeHtml((item.ip_address || 'N/A').toString());
    const sanitizedUserAgent = this.sanitizeHtml(this.formatUserAgent(item.user_agent || ''));
    const sanitizedTimestamp = this.sanitizeHtml(new Date(item.created_at).toLocaleString());
    
    // Create modal content
    const modal = document.createElement('div');
    modal.className = 'bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto';
    
    // Format the modal content
    modal.innerHTML = `
      <div class="p-6">
        <div class="flex justify-between items-start mb-4">
          <h3 class="text-xl font-bold text-gray-900">Audit Log Details</h3>
          <button id="close-modal-btn" class="text-gray-500 hover:text-gray-700">
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="space-y-6 max-h-[70vh] overflow-y-auto pr-2">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">ID</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedId}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">Event</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedEvent}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">User ID</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedUserId}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">Target User ID</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedTargetUserId}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg md:col-span-2">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">Details</h4>
              <div class="mt-1 text-sm text-gray-900 bg-white p-3 rounded max-h-60 overflow-y-auto">
                ${detailsHtml}
              </div>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">IP Address</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedIpAddress}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">User Agent</h4>
              <p class="mt-1 text-sm font-medium text-gray-900 break-words">${sanitizedUserAgent}</p>
            </div>
            <div class="bg-gray-50 p-3 rounded-lg md:col-span-2">
              <h4 class="text-xs font-medium text-gray-500 uppercase tracking-wide">Timestamp</h4>
              <p class="mt-1 text-sm font-medium text-gray-900">${sanitizedTimestamp}</p>
            </div>
          </div>
        
        <div class="mt-6 flex justify-end">
          <button id="close-modal-btn-bottom" class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
            Close
          </button>
        </div>
      </div>
    `;
    
    // Add modal to the overlay
    overlay.appendChild(modal);
    
    // Add the overlay to the body
    document.body.appendChild(overlay);
    
    // Add event listeners to close the modal
    const closeModalButtons = overlay.querySelectorAll('[id*="close-modal"]');
    closeModalButtons.forEach(button => {
      button.addEventListener('click', () => {
        document.body.removeChild(overlay);
      });
    });
    
    // Close modal when clicking on the overlay
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });
  }
  
  /**
   * Sanitize HTML to prevent XSS
   * @param {string} str - String to sanitize
   * @returns {string} Sanitized string
   */
  sanitizeHtml(str) {
    if (typeof str !== 'string') {
      str = String(str);
    }
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
  
  /**
   * Update charts with current data
   */
  async updateCharts() {
    if (!this.charts.eventTypeChart || !this.charts.activityChart) {
      // Charts not initialized yet, try to initialize them
      await this.initializeCharts();
    }
    
    // Check again after initialization attempt
    if (!this.charts.eventTypeChart || !this.charts.activityChart) {
      return; // Charts still not available
    }
    
    // Process data for event type chart
    const eventTypeCounts = {};
    this.state.allAuditData.forEach(item => {
      const eventType = item.event || 'unknown';
      eventTypeCounts[eventType] = (eventTypeCounts[eventType] || 0) + 1;
    });
    
    // Update event type chart
    this.charts.eventTypeChart.data.labels = Object.keys(eventTypeCounts);
    this.charts.eventTypeChart.data.datasets[0].data = Object.values(eventTypeCounts);
    this.charts.eventTypeChart.update();
    
    // Process data for activity chart (group by date)
    const activityByDate = {};
    this.state.allAuditData.forEach(item => {
      const date = new Date(item.created_at).toDateString();
      activityByDate[date] = (activityByDate[date] || 0) + 1;
    });
    
    // Sort dates and prepare for chart
    const sortedDates = Object.keys(activityByDate).sort((a, b) => new Date(a) - new Date(b));
    
    // Update activity chart
    this.charts.activityChart.data.labels = sortedDates.map(date => {
      // Format date to be more readable
      return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    this.charts.activityChart.data.datasets[0].data = sortedDates.map(date => activityByDate[date]);
    this.charts.activityChart.update();
  }
}

// Initialize the audit logs manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const auditManager = new AuditLogsManager();
  
  // Initialize charts after a short delay to ensure DOM is fully loaded
  setTimeout(() => {
    auditManager.initializeCharts();
  }, 500);
});

// Export for testing if in Node environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuditLogsManager;
}
