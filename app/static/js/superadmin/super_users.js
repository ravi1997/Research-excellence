// Superadmin User Management page logic (externalized for CSP compliance)
(function(){
  const BASE = '';
  const tableBody = document.querySelector('#users-table-body');
  if(!tableBody) return; // page not present
  let currentPage = 1;
  let totalPages = 1;  // Track total pages
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

  async function fetchUsers(page=1){
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
      return; 
    }
    const data = await res.json();
    renderUsers(data.items);
    renderPagination(data.current_page, data.total_pages, data.total_count);
  }

  function updateBulkUI(){
    const count = selected.size;
    const bulkBtn = document.getElementById('bulk-actions-btn');
    if(bulkBtn) {
      bulkBtn.textContent = `Bulk Actions (${count})`;
      bulkBtn.disabled = count === 0;
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
      const rolesArr = (u.roles||[]);
      const roles = rolesArr.map(r=>`<span class=\"inline-block px-2 py-0.5 text-[10px] font-medium rounded-full border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200\">${escapeHtml(r)}</span>`).join(' ');
      const isSelected = selected.has(u.id);
      const status = u.is_active ? 'Active' : 'Inactive';
      const locked = u.locked ? 'Locked' : 'Unlocked';
      const lastLogin = u.last_login ? new Date(u.last_login).toLocaleString() : 'Never';
      
      tr.innerHTML = `
        <td><input type="checkbox" class="row-select" value="${u.id}" ${isSelected?'checked':''}></td>
        <td>${escapeHtml(u.username||'')}</td>
        <td>${escapeHtml(u.email||'')}</td>
        <td>${escapeHtml(u.employee_id||'')}</td>
        <td class="space-x-1">${roles}</td>
        <td>${status}</td>
        <td>${locked}</td>
        <td>${lastLogin}</td>
        <td class="whitespace-nowrap px-2 py-1 space-x-1">
          <button class="edit-user-btn px-2 py-1 text-xs border rounded border-blue-500 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900" data-id="${u.id}">Edit</button>
          <button class="activate-user-btn px-2 py-1 text-xs border rounded border-green-500 text-green-600 hover:bg-green-50 dark:hover:bg-green-900" data-id="${u.id}">${u.is_active ? 'Deactivate' : 'Activate'}</button>
          <button class="lock-user-btn px-2 py-1 text-xs border rounded border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-900" data-id="${u.id}">${locked === 'Locked' ? 'Unlock' : 'Lock'}</button>
        </td>`;
      tableBody.appendChild(tr);
    }
    updateBulkUI();
  }

  function renderPagination(page, pages, total){
    currentPage = page;
    totalPages = pages; // Store total pages for reference
    const pageInfo = document.getElementById('page-info');
    if(pageInfo) pageInfo.textContent = `Page ${page} of ${pages}`;
    
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
      const currentStatus = userRow.querySelector('td:nth-child(6)').textContent; // status column
      
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
        if(userData.user.locked) {
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
  const closeModalBtn = document.querySelector('#user-modal .close');
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
    
    userModal.classList.remove('hidden');
  }
  
  function closeUserModal() {
    if(userModal) userModal.classList.add('hidden');
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
    }
  }
  
  closeModalBtn.addEventListener('click', closeUserModal);
  cancelBtn.addEventListener('click', closeUserModal);
  userForm.addEventListener('submit', (e) => {
    e.preventDefault();
    saveUser();
  });
  
  // Close modal when clicking outside
  window.addEventListener('click', (e) => {
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
