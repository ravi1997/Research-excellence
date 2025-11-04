// Superadmin User Management page logic (externalized for CSP compliance)
(function(){
  const BASE = '';
  const tableBody = document.querySelector('#users-table-body');
  if(!tableBody) return; // page not present
  let currentPage = 1;
  let totalPages = 1;  // Track total pages
  let totalUsers = 0;  // Track total users
  let lastQuery = {};
  const selected = new Set();
  const userModal = document.getElementById('user-modal');
  
  function authHeader(){
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
  }

  function jsonHeaders(){
    return { 'Content-Type':'application/json', ...authHeader() };
  }

  // Show loading indicator
  function showLoading() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if(loadingIndicator) {
      loadingIndicator.classList.remove('hidden');
    }
  }

  // Hide loading indicator
  function hideLoading() {
    const loadingIndicator = document.getElementById('loading-indicator');
    if(loadingIndicator) {
      loadingIndicator.classList.add('hidden');
    }
  }

  async function fetchUsers(page=1){
    showLoading();
    // Get filter values from the actual template elements
    const search = document.getElementById('user-search').value;
    const roleFilter = document.getElementById('role-filter').value;
    
    // Build query parameters
    const params = new URLSearchParams();
    params.set('page', page);
    if(search) params.set('search', search);
    if(roleFilter && roleFilter !== 'all') params.set('role', roleFilter);
    
    const res = await fetch(`${BASE}/api/v1/super/users?${params}`, { headers: { ...authHeader() }});
    if(!res.ok){
      console.error('Failed to load users');
      hideLoading();
      return;
    }
    const data = await res.json();
    renderUsers(data.items);
    renderPagination(data.current_page, data.total_pages, data.total_count);
    hideLoading();
  }

  function updateBulkUI(){
    const count = selected.size;
    const bulkBtn = document.getElementById('bulk-actions-btn');
    const selectedCount = document.getElementById('selected-count');
    if(bulkBtn) {
      bulkBtn.disabled = count === 0;
    }
    if(selectedCount) {
      selectedCount.textContent = count;
    }
    
    const selectAll = document.getElementById('select-all-users');
    if(selectAll){
      const totalRows = document.querySelectorAll('.row-select').length;
      selectAll.checked = count && count === totalRows && totalRows > 0;
      selectAll.indeterminate = count > 0 && count < totalRows && totalRows > 0;
    }
  }

  function renderUsers(items){
    tableBody.innerHTML = '';
    for(const u of items){
      const tr = document.createElement('tr');
      tr.classList.add('bg-white', 'dark:bg-gray-800', 'hover:bg-gray-50', 'dark:hover:bg-gray-700');
      const rolesArr = (u.roles||[]);
      const roles = rolesArr.map(r=>`<span class="inline-block px-2 py-0.5 text-xs font-medium rounded-full border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">${escapeHtml(r)}</span>`).join(' ');
      const isSelected = selected.has(u.id);
      const status = u.is_active ? 'Active' : 'Inactive';
      const locked = u.lock_until ? 'Locked' : 'Unlocked';
      const lastLogin = u.last_login ? new Date(u.last_login).toLocaleString() : 'Never';
      
      tr.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap">
          <input type="checkbox" class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded row-select" value="${u.id}" ${isSelected?'checked':''}>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(u.username||'')}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(u.email||'')}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(u.employee_id||'')}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(u.mobile||'')}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300 space-x-1">${roles}</td>
        <td class="px-6 py-4 whitespace-nowrap">
          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
            ${status}
          </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-30">
          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${u.lock_until ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}">
            ${locked}
          </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${lastLogin}</td>
        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <button class="edit-user-btn text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 mr-3" data-id="${u.id}" title="Edit user">
            <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M1 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
            </svg>
          </button>
          <button class="activate-user-btn ${u.is_active ? 'text-red-600 hover:text-red-900 dark:text-red-40 dark:hover:text-red-300' : 'text-green-60 hover:text-green-900 dark:text-green-40 dark:hover:text-green-300'} mr-3" data-id="${u.id}" title="${u.is_active ? 'Deactivate user' : 'Activate user'}">
            <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 0-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
          </button>
          <button class="lock-user-btn ${u.lock_until ? 'text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300' : 'text-red-600 hover:text-red-900 dark:text-red-40 dark:hover:text-red-300'}" data-id="${u.id}" title="${u.lock_until ? 'Unlock user' : 'Lock user'}">
            <svg class="w-4 h-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 0-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
          </button>
        </td>`;
      tableBody.appendChild(tr);
    }
    updateBulkUI();
  }

  function renderPagination(page, pages, total){
    currentPage = page;
    totalPages = pages; // Store total pages for reference
    totalUsers = total; // Store total users
    
    const startItem = document.getElementById('start-item');
    const endItem = document.getElementById('end-item');
    const totalCount = document.getElementById('total-count');
    const currentPageEl = document.getElementById('current-page');
    const totalPagesEl = document.getElementById('total-pages');
    
    if(startItem) startItem.textContent = ((page - 1) * 10) + 1;
    if(endItem) endItem.textContent = Math.min(page * 10, total);
    if(totalCount) totalCount.textContent = total;
    if(currentPageEl) currentPageEl.textContent = page;
    if(totalPagesEl) totalPagesEl.textContent = pages;
    
    // Enable/disable pagination buttons
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    if(prevBtn) prevBtn.disabled = page <= 1;
    if(nextBtn) nextBtn.disabled = page >= pages;
  }

  // Event listeners for search and filters
  document.getElementById('search-btn').addEventListener('click', ()=>{ fetchUsers(1); });
  document.getElementById('user-search').addEventListener('keypress', (e)=>{
    if(e.key === 'Enter') { fetchUsers(1); }
 });
  
  document.getElementById('prev-page').addEventListener('click', ()=>{
    if(currentPage > 1) fetchUsers(currentPage - 1);
  });
  
  document.getElementById('next-page').addEventListener('click', ()=>{
    if(currentPage < totalPages) fetchUsers(currentPage + 1);
  });

  // Table row interaction
  tableBody.addEventListener('click', async e =>{
    const editBtn = e.target.closest('.edit-user-btn');
    const activateBtn = e.target.closest('.activate-user-btn');
    const lockBtn = e.target.closest('.lock-user-btn');
    
    if(editBtn) {
      openUserModal(editBtn.getAttribute('data-id'));
    }
    else if(activateBtn) {
      const id = activateBtn.getAttribute('data-id');
      const userRow = activateBtn.closest('tr');
      const currentStatus = userRow.querySelector('td:nth-child(7)').textContent.trim(); // status column (now 7th)
      
      if(currentStatus === 'Active') {
        await deactivateUser(id);
      } else {
        await activateUser(id);
      }
      fetchUsers(currentPage);
    }
    else if(lockBtn) {
      const id = lockBtn.getAttribute('data-id');
      
      // For lock/unlock, we need to get the current lock status
      const userRes = await fetch(`${BASE}/api/v1/super/users/${id}`, { headers: authHeader() });
      if(userRes.ok) {
        const userData = await userRes.json();
        if(userData.user.lock_until) {
          await unlockUser(id);
        } else {
          await lockUser(id);
        }
        fetchUsers(currentPage);
      }
    }
 });

  // Checkbox selection
  tableBody.addEventListener('change', e =>{
    const cb = e.target.closest('.row-select');
    if(!cb) return;
    if(cb.checked) selected.add(cb.value);
    else selected.delete(cb.value);
    updateBulkUI();
  });

  document.getElementById('select-all-users').addEventListener('change', e =>{
    const on = e.target.checked;
    selected.clear();
    document.querySelectorAll('.row-select').forEach(cb=>{
      cb.checked = on;
      if(on) selected.add(cb.value);
    });
    updateBulkUI();
  });

  // Add user button
  document.getElementById('add-user-btn').addEventListener('click', ()=>{
    openUserModal(null);
  });

  // User modal functionality
  const cancelBtn = document.getElementById('cancel-user-btn');
  const userForm = document.getElementById('user-form');
  
  function openUserModal(userId) {
    if(!userModal) return;
    
    if(userId) {
      // Edit mode
      document.getElementById('modal-title').textContent = 'Edit User';
      loadUserData(userId);
    } else {
      // Add mode
      document.getElementById('modal-title').textContent = 'Add New User';
      document.getElementById('user-id').value = '';
      document.getElementById('username').value = '';
      document.getElementById('email').value = '';
      document.getElementById('employee-id').value = '';
      document.getElementById('mobile').value = '';
      // Reset roles selection
      const rolesSelect = document.getElementById('roles');
      for(let i = 0; i < rolesSelect.options.length; i++) {
        rolesSelect.options[i].selected = false;
      }
      // Reset status selection
      document.getElementById('status').value = 'active';
    }
    
    // Show modal
    userModal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }
  
  function closeUserModal() {
    if(userModal) {
      userModal.classList.add('hidden');
      document.body.classList.remove('overflow-hidden');
    }
  }
  
  async function loadUserData(userId) {
    const res = await fetch(`${BASE}/api/v1/super/users/${userId}`, { headers: authHeader() });
    if(!res.ok) {
      console.error('Failed to load user data');
      return;
    }
    const data = await res.json();
    const user = data.user;
    
    document.getElementById('user-id').value = user.id;
    document.getElementById('username').value = user.username || '';
    document.getElementById('email').value = user.email || '';
    document.getElementById('employee-id').value = user.employee_id || '';
    document.getElementById('mobile').value = user.mobile || '';
    
    // Set roles
    const rolesSelect = document.getElementById('roles');
    for(let i = 0; i < rolesSelect.options.length; i++) {
      rolesSelect.options[i].selected = user.roles.includes(rolesSelect.options[i].value);
    }
    
    // Set status
    document.getElementById('status').value = user.is_active ? 'active' : 'inactive';
  }
  
  async function saveUser() {
    const userId = document.getElementById('user-id').value;
    const userData = {
      username: document.getElementById('username').value,
      email: document.getElementById('email').value,
      employee_id: document.getElementById('employee-id').value,
      mobile: document.getElementById('mobile').value,
      roles: Array.from(document.getElementById('roles').selectedOptions).map(option => option.value),
      is_active: document.getElementById('status').value === 'active'
    };
    
    // Only add password to create user, not update
    if (!userId) {
      // For create, we can add a temporary password or let the backend generate one
      userData.password = 'TempPass123!'; // This will be changed by the user later
    }
    
    let res;
    if(userId) {
      // Update existing user (don't send password in update)
      res = await fetch(`${BASE}/api/v1/super/users/${userId}`, {
        method: 'PUT',
        headers: jsonHeaders(),
        body: JSON.stringify(userData)
      });
    } else {
      // Create new user
      res = await fetch(`${BASE}/api/v1/super/users`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify(userData)
      });
    }
    
    if(res.ok) {
      closeUserModal();
      fetchUsers(currentPage);
    } else {
      console.error('Failed to save user');
      const errorText = await res.text();
      console.error('Error details:', errorText);
      alert('Failed to save user: ' + errorText);
    }
  }
  
  cancelBtn.addEventListener('click', closeUserModal);
  userForm.addEventListener('submit', (e) => {
    e.preventDefault();
    saveUser();
  });
  
  // Close modal when clicking outside
  userModal.addEventListener('click', (e) => {
    if(e.target === userModal) {
      closeUserModal();
    }
  });

  // API helper functions
  async function activateUser(userId) {
    const res = await fetch(`${BASE}/api/v1/super/users/${userId}/activate`, {
      method: 'POST',
      headers: jsonHeaders()
    });
    return res.ok;
  }
  
  async function deactivateUser(userId) {
    const res = await fetch(`${BASE}/api/v1/super/users/${userId}/deactivate`, {
      method: 'POST',
      headers: jsonHeaders()
    });
    return res.ok;
  }
  
  async function lockUser(userId) {
    const res = await fetch(`${BASE}/api/v1/super/users/${userId}/lock`, {
      method: 'POST',
      headers: jsonHeaders()
    });
    return res.ok;
  }
  
  async function unlockUser(userId) {
    const res = await fetch(`${BASE}/api/v1/super/users/${userId}/unlock`, {
      method: 'POST',
      headers: jsonHeaders()
    });
    return res.ok;
  }

  function escapeHtml(str){
    if (!str) return '';
    return str.replace(/[&<>\"]/g, function(c) {
      switch (c) {
        case '&': return '&';
        case '<': return '<';
        case '>': return '>';
        case '"': return '"';
        default: return c;
      }
    });
 }

  // Initial load
  fetchUsers(1);
})();
