(function(){
  // Base URL for API endpoints (empty string means relative to current domain)
  const BASE = '';
  
  // Get DOM elements
  const exportBtn = document.getElementById('exportAudit');
  const auditForm = document.getElementById('auditFilter');
  const resetBtn = document.getElementById('resetAudit');
  const auditTable = document.getElementById('auditTable');
  const loadMoreBtn = document.getElementById('loadMoreAudit');
  const summaryNode = document.getElementById('auditSummary');
  const endNode = document.getElementById('auditEnd');
  const prevPageBtn = document.getElementById('prevPage');
  const nextPageBtn = document.getElementById('nextPage');
  const currentPageSpan = document.getElementById('currentPage');
  const totalPagesSpan = document.getElementById('totalPages');

  // State variables
  let currentPage = 1;
  let totalPages = 1;
  let hasNextPage = false;
  let hasPrevPage = false;
  let activeParams = {};
  let loading = false;

  /**
   * Render audit log rows in the table
   * @param {Array} items - Array of audit log objects
   */
  function renderRows(items) {
    if (!auditTable) return;
    
    const tbody = auditTable.querySelector('tbody');
    tbody.innerHTML = '';
    
    items.forEach(item => {
      const tr = document.createElement('tr');
      tr.className = 'bg-white border-b hover:bg-gray-50';
      
      // Format the row with audit log data
      tr.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${item.id}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.event || ''}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.user_id || ''}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.target_user_id || ''}</td>
        <td class="px-6 py-4 text-sm text-gray-500 max-w-xs truncate" title="${item.detail || ''}">${(item.detail || '').substring(0, 120)}${item.detail && item.detail.length > 120 ? '...' : ''}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(item.created_at).toLocaleString()}</td>
      `;
      
      tbody.appendChild(tr);
    });
  }

  /**
   * Update pagination UI elements
   */
  function updatePaginationUI() {
    if (currentPageSpan) currentPageSpan.textContent = currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
    
    if (prevPageBtn) {
      prevPageBtn.disabled = !hasPrevPage;
      prevPageBtn.classList.toggle('opacity-50', !hasPrevPage);
      prevPageBtn.classList.toggle('cursor-not-allowed', !hasPrevPage);
    }
    
    if (nextPageBtn) {
      nextPageBtn.disabled = !hasNextPage;
      nextPageBtn.classList.toggle('opacity-50', !hasNextPage);
      nextPageBtn.classList.toggle('cursor-not-allowed', !hasNextPage);
    }
  }

  /**
   * Fetch audit logs from the API with pagination
   * @param {Object} params - Query parameters for the API request
   */
  async function fetchAudit(params) {
    if (loading) return;
    loading = true;
    
    try {
      // Add pagination parameters
      const p = { ...params, page: currentPage };
      const qs = new URLSearchParams(p).toString();
      const response = await fetch(`${BASE}/api/v1/super/audit/list?${qs}`);
      
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
      
      const data = await response.json();
      
      // Update UI with new data
      renderRows(data.items || []);
      
      // Update pagination info
      currentPage = data.current_page || 1;
      totalPages = data.total_pages || 1;
      hasNextPage = data.has_next || false;
      hasPrevPage = data.has_prev || false;
      
      // Update pagination UI
      updatePaginationUI();
      
      // Update load more button visibility (hide since we're using page-based pagination)
      if (loadMoreBtn) {
        loadMoreBtn.style.display = 'none';
      }
      
      // Update end marker visibility
      if (endNode) {
        endNode.style.display = hasNextPage ? 'none' : 'inline';
      }
      
      // Update summary text
      if (summaryNode) {
        const totalShown = data.items ? data.items.length : 0;
        const totalRecords = data.total_count || 0;
        summaryNode.textContent = `${totalShown} of ${totalRecords} row(s) shown`;
      }
    } catch (error) {
      console.error('Error fetching audit logs:', error);
      alert('Error loading audit logs. Please try again.');
    } finally {
      loading = false;
    }
  }

  // Set up form submission handler
  if (auditForm) {
    auditForm.addEventListener('submit', e => {
      e.preventDefault();
      const formData = new FormData(auditForm);
      
      // Build active parameters from form data
      activeParams = { limit: formData.get('limit') || 50 };
      for (const [key, value] of formData.entries()) {
        if (value && key !== 'limit' && key !== 'page') activeParams[key] = value;
      }
      
      // Reset to first page and fetch data
      currentPage = 1;
      fetchAudit(activeParams);
    });
  }
  
  // Set up reset button handler
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      auditForm.reset();
      activeParams = { limit: 50 };
      currentPage = 1;
      fetchAudit(activeParams);
    });
  }
  
  // Set up previous page button handler
  if (prevPageBtn) {
    prevPageBtn.addEventListener('click', () => {
      if (hasPrevPage) {
        currentPage--;
        fetchAudit(activeParams);
      }
    });
  }
  
  // Set up next page button handler
  if (nextPageBtn) {
    nextPageBtn.addEventListener('click', () => {
      if (hasNextPage) {
        currentPage++;
        fetchAudit(activeParams);
      }
    });
  }
  
  // Set up export button handler
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      exportBtn.disabled = true;
      exportBtn.textContent = 'Exporting...';
      
      try {
        const params = {...activeParams};
        // Remove pagination specific params for export
        delete params.page; // server will use its own export logic
        
        const qs = new URLSearchParams(params).toString();
        const response = await fetch(`${BASE}/api/v1/super/audit/export${qs ? ('?' + qs) : ''}`);
        
        if (!response.ok) {
          throw new Error(`Export failed with status ${response.status}`);
        }
        
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create and trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = 'audit_logs.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
        
        // Clean up object URL
        setTimeout(() => URL.revokeObjectURL(url), 5000);
      } catch (error) {
        console.error('Export error:', error);
        alert('Error exporting audit logs. Please try again.');
      } finally {
        exportBtn.disabled = false;
        exportBtn.textContent = 'Export (JSON)';
      }
    });
  }

  // Initial load of audit logs when page loads
  if (auditTable) {
    activeParams = { limit: 50 };
    fetchAudit(activeParams);
  }
})();
