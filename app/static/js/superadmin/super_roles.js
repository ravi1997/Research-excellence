(function () {
  const BASE = "";
  const tableBody = document.querySelector("#roles-table-body");
  if (!tableBody) return;

 const state = {
    currentPage: 1,
    totalPages: 1,
    totalRoles: 0,
    rawItems: [],
    sortField: null,
    sortDirection: "asc",
    pageSize: 10,
  };

 const selected = new Set();

  // Element references
  const loadingIndicator = document.getElementById("loading-indicator");
  const emptyState = document.getElementById("empty-state");
  const searchInput = document.getElementById("role-search");
  const clearSearchBtn = document.getElementById("clear-search");
  const statusFilter = document.getElementById("status-filter");
  const searchBtn = document.getElementById("search-btn");
  const resetFiltersBtn = document.getElementById("reset-filters");
  const emptyAddRoleBtn = document.getElementById("empty-add-role");
 const bulkBtn = document.getElementById("bulk-actions-btn");
  const bulkModal = document.getElementById("bulk-confirm-modal");
  const bulkConfirmBtn = document.getElementById("bulk-confirm");
  const bulkCancelBtn = document.getElementById("bulk-cancel");
  const bulkSelectionCount = document.getElementById("bulk-selection-count");
  const selectedCount = document.getElementById("selected-count");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const startItem = document.getElementById("start-item");
  const endItem = document.getElementById("end-item");
  const totalCount = document.getElementById("total-count");
  const currentPageEl = document.getElementById("current-page");
  const totalPagesEl = document.getElementById("total-pages");
  const visibleCountEl = document.getElementById("visible-count");
  const metricTotalEl = document.getElementById("metric-total-roles");
  const metricDocumentedEl = document.getElementById("metric-documented-roles");
  const metricProtectedEl = document.getElementById("metric-protected-roles");
  const metricLastSyncEl = document.getElementById("metric-last-sync");
  const selectAllCheckbox = document.getElementById("select-all-roles");
  const addRoleBtn = document.getElementById("add-role-btn");
  const roleModal = document.getElementById("role-modal");
  const modalCloseBtn = document.getElementById("modal-close");
  const cancelRoleBtn = document.getElementById("cancel-role-btn");
  const roleForm = document.getElementById("role-form");
  const modalTitle = document.getElementById("modal-title");
  const statusLabelMap = {
    active: { label: "Active", badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200" },
    protected: { label: "Protected", badge: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200" },
  };

  const sortButtons = document.querySelectorAll("[data-sort]");

  const metricFallback = (el) => el && (el.textContent = "0");
  const getRoleInputs = () => [];

  // Utilities
 const debounce = (fn, delay = 300) => {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
 };

  function authHeader() {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    return token ? { Authorization: "Bearer " + token } : {};
  }

  function jsonHeaders() {
    return { "Content-Type": "application/json", ...authHeader() };
 }

  function showLoading() {
    loadingIndicator?.classList.remove("hidden");
  }

  function hideLoading() {
    loadingIndicator?.classList.add("hidden");
  }

 const toggleBodyScroll = (lock) => {
    document.body.classList.toggle("overflow-hidden", Boolean(lock));
  };

  const toggleEmptyState = (show) => {
    emptyState?.classList.toggle("hidden", !show);
  };

 const toggleClearButton = () => {
    if (!clearSearchBtn) return;
    clearSearchBtn.classList.toggle("hidden", !(searchInput?.value?.length));
  };

 const setMetric = (el, value) => {
    if (!el) return;
    const formatted = Number.isFinite(value) ? value : 0;
    el.textContent = new Intl.NumberFormat().format(formatted);
  };

  const safeDate = (value) => {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  };

  function escapeHtml(str) {
    if (str == null) return "";
    // Properly escape HTML special characters
    var escaped = String(str);
    escaped = escaped.replace(/&/g, "&");
    escaped = escaped.replace(/</g, "<");
    escaped = escaped.replace(/>/g, ">");
    escaped = escaped.replace(/"/g, "\"");
    escaped = escaped.replace(/'/g, "'");
    return escaped;
  }

  // Fetch & transform
  async function fetchRoles(page = 1) {
    showLoading();
    const params = new URLSearchParams();
    params.set("page", page);

    const search = searchInput?.value?.trim();
    if (search) params.set("search", search);

    const status = statusFilter?.value;
    if (status && status !== "all") params.set("status", status);

    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/available?${params.toString()}`, { headers: authHeader() });
      if (!response.ok) {
        console.error("Failed to load roles", response.status);
        hideLoading();
        return;
      }

      const data = await response.json();
      state.currentPage = data.current_page || page;
      state.totalPages = data.total_pages || 1;
      state.totalRoles = data.total_count ?? data.total ?? 0;
      if (Number.isFinite(data.per_page)) {
        state.pageSize = data.per_page;
      } else if (Array.isArray(data.items) && data.items.length) {
        state.pageSize = data.items.length;
      }

      updateMetricsFromResponse(data);

      selected.clear();
      updateBulkUI();
      clearSelectAll();

      state.rawItems = Array.isArray(data.items) ? [...data.items] : [];
      renderRoles();
      renderPagination();
    } catch (error) {
      console.error("Unable to load roles", error);
    } finally {
      toggleClearButton();
      hideLoading();
    }
  }

 function updateMetricsFromResponse(data) {
    const items = Array.isArray(data.items) ? data.items : [];
    const metrics = data.metrics || data.stats || {};

    const documentedCount = Number.isFinite(metrics.documented) ? metrics.documented : 
      items.reduce((acc, role) => {
        const meta = data.metadata?.[role.value] || {};
        return meta.label?.trim() || meta.description?.trim() ? acc + 1 : acc;
      }, 0);

    const protectedCount = Number.isFinite(metrics.protected) ? metrics.protected : 
      items.reduce((acc, role) => role.protected ? acc + 1 : acc, 0);

    setMetric(metricTotalEl, data.total_count ?? data.total ?? items.length);
    setMetric(metricDocumentedEl, documentedCount);
    setMetric(metricProtectedEl, protectedCount);
    metricLastSyncEl && (metricLastSyncEl.textContent = new Date().toLocaleString());
  }

 function applyFilters(items) {
    const status = statusFilter?.value || "all";
    if (status === "all") return [...items];

    return items.filter((role) => {
      if (status === "protected") return Boolean(role.protected);
      if (status === "active") return !role.protected;
      return true;
    });
  }

 function resolveSortValue(role, field) {
    switch (field) {
      case "identifier":
        return role.value || "";
      case "label":
        return role.label || role.value || "";
      case "description":
        return role.description || "";
      case "status":
        return role.protected ? 1 : 0;
      default:
        return "";
    }
 }

  function applySort(items) {
    const { sortField, sortDirection } = state;
    if (!sortField) return [...items];

    const factor = sortDirection === "desc" ? -1 : 1;
    return [...items].sort((a, b) => {
      const aVal = resolveSortValue(a, sortField);
      const bVal = resolveSortValue(b, sortField);

      if (aVal instanceof Date && bVal instanceof Date) {
        return (aVal.getTime() - bVal.getTime()) * factor;
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return (aVal - bVal) * factor;
      }
      return String(aVal).localeCompare(String(bVal), undefined, { sensitivity: "base" }) * factor;
    });
  }

 function renderRoles() {
    const filteredItems = applyFilters(state.rawItems);
    const items = applySort(filteredItems);

    tableBody.innerHTML = "";
    visibleCountEl && (visibleCountEl.textContent = items.length);
    toggleEmptyState(items.length === 0);

    items.forEach((role) => {
      const tr = document.createElement("tr");
      const isSelected = selected.has(role.value);
      const isProtected = Boolean(role.protected);
      const statusKey = isProtected ? "protected" : "active";
      const statusMeta = statusLabelMap[statusKey];
      const statusLabel = statusMeta.label;
      const statusBadgeClass = statusMeta.badge;

      const meta = state.metadata?.[role.value] || {};
      const displayLabel = meta.label || role.value || "";
      const displayDescription = meta.description || "";

      tr.className = [
        "bg-white dark:bg-gray-900/40",
        "hover:bg-gray-50 dark:hover:bg-gray-800/60 transition",
        isSelected ? "ring-1 ring-blue-500/50" : "",
      ].join(" ");

      tr.innerHTML = `
        <td class="px-6 py-4 align-middle">
          <input type="checkbox" class="row-select h-4 w-4 rounded border-gray-30 text-blue-60 focus:ring-blue-500 dark:border-gray-700" value="\${escapeHtml(role.value)}" ${isSelected ? "checked" : ""} aria-label="Select ${escapeHtml(role.value || "role")}">
        </td>
        <td class="px-6 py-4 align-middle">
          <div class="flex flex-col">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(role.value || "")}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">${role.enum ? `Enum: ${escapeHtml(role.enum)}` : ""}</span>
          </div>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-30">${escapeHtml(displayLabel)}</td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">${escapeHtml(displayDescription)}</td>
        <td class="px-6 py-4 align-middle">
          <span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadgeClass}">
            <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
            ${statusLabel}
          </span>
        </td>
        <td class="px-6 py-4 align-middle text-right">
          <div class="flex items-center justify-end gap-2 text-sm">
            <button class="edit-role-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 text-blue-60 transition hover:bg-blue-50 dark:text-blue-30 dark:hover:bg-blue-500/10" data-id="${escapeHtml(role.value)}" title="Edit role">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 17.5V20h2.5L17.81 8.69l-2.5L4 17.5zM19.71 7.04a1 0 000-1.41l-1.34-1.34a1 1 0 00-1.41 0l-1.6 1.59 2.5 1.85-1.34z"/>
              </svg>
              Edit
            </button>
            <button class="protect-role-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 \${isProtected ? "text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10" : "text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10"}" data-id="\${escapeHtml(role.value)}" title="\${isProtected ? "Unprotect role" : "Protect role"}">
              ${isProtected ? "Unprotect" : "Protect"}
            </button>
          </div>
        </td>
      `;
      tableBody.appendChild(tr);
    });

    updateBulkUI();
    updateSortIndicators();
  }

  function renderPagination() {
    const page = state.currentPage;
    const pages = state.totalPages;
    const total = state.totalRoles;
    const pageSize = state.pageSize || 10;

    if (startItem) startItem.textContent = total === 0 ? 0 : (page - 1) * pageSize + 1;
    if (endItem) endItem.textContent = Math.min(page * pageSize, total);
    if (totalCount) totalCount.textContent = total;
    if (currentPageEl) currentPageEl.textContent = page;
    if (totalPagesEl) totalPagesEl.textContent = pages;

    if (prevBtn) prevBtn.disabled = page <= 1;
    if (nextBtn) nextBtn.disabled = page >= pages;
  }

  function updateBulkUI() {
    const count = selected.size;
    bulkBtn && (bulkBtn.disabled = count === 0);
    selectedCount && (selectedCount.textContent = count);
    bulkSelectionCount && (bulkSelectionCount.textContent = count);

    if (!selectAllCheckbox) return;
    const rowCheckboxes = tableBody.querySelectorAll(".row-select");
    const totalRows = rowCheckboxes.length;
    if (!totalRows) {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = false;
      return;
    }
    selectAllCheckbox.checked = count === totalRows;
    selectAllCheckbox.indeterminate = count > 0 && count < totalRows;
 }

  function clearSelectAll() {
    if (!selectAllCheckbox) return;
    selectAllCheckbox.checked = false;
    selectAllCheckbox.indeterminate = false;
 }

  // Bulk modal helpers
  function openBulkModal() {
    if (!bulkModal) return;
    bulkSelectionCount && (bulkSelectionCount.textContent = selected.size);
    bulkModal.classList.remove("hidden");
    toggleBodyScroll(true);
  }

 function closeBulkModal() {
    if (!bulkModal) return;
    bulkModal.classList.add("hidden");
    toggleBodyScroll(false);
  }

 // Role modal helpers
  function openRoleModal(roleId) {
    if (!roleModal) return;
    console.log("Opening role modal for", roleId);

    if (roleId) {
      modalTitle && (modalTitle.textContent = "Edit role");
      loadRoleData(roleId);
    } else {
      modalTitle && (modalTitle.textContent = "Add new role");
      resetRoleForm();
    }

    console.log("Opening role modal");
    roleModal.classList.remove("hidden");
    console.log("role modal visible:", !roleModal.classList.contains("hidden"));
    toggleBodyScroll(true);
 }

 function closeRoleModal() {
    if (!roleModal) return;
    roleModal.classList.add("hidden");
    toggleBodyScroll(false);
 }

  function resetRoleForm() {
    const fields = ["role-id", "role-identifier", "role-label", "role-description"];
    fields.forEach((field) => {
      const input = document.getElementById(field);
      if (!input) return;
      if (field === "role-id") input.value = "";
      else input.value = "";
    });

    const statusSelect = document.getElementById("role-status");
    if (statusSelect) statusSelect.value = "active";
  }

  async function loadRoleData(roleId) {
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/available/${roleId}`, { headers: authHeader() });
      if (!response.ok) {
        console.error("Failed to load role data");
        return;
      }
      const { role } = await response.json();
      if (!role) return;

      const map = {
        "role-id": role.value,
        "role-identifier": role.value || "",
        "role-label": role.label || "",
        "role-description": role.description || "",
      };
      Object.entries(map).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.value = value;
      });

      const statusSelect = document.getElementById("role-status");
      if (statusSelect) statusSelect.value = role.protected ? "protected" : "active";
    } catch (error) {
      console.error("Failed to load role details", error);
    }
 }

 async function saveRole() {
    const roleId = document.getElementById("role-id")?.value;
    const payload = {
      identifier: document.getElementById("role-identifier")?.value || "",
      label: document.getElementById("role-label")?.value || "",
      description: document.getElementById("role-description")?.value || "",
      protected: (document.getElementById("role-status")?.value || "active") === "protected",
    };

    const method = roleId ? "PUT" : "POST";
    const endpoint = roleId ? `${BASE}/api/v1/user_roles/manage` : `${BASE}/api/v1/user_roles/manage`;

    const response = await fetch(endpoint, {
      method,
      headers: jsonHeaders(),
      body: JSON.stringify({
        action: roleId ? "update" : "add",
        identifier: payload.identifier,
        metadata: {
          label: payload.label,
          description: payload.description
        },
        protected: payload.protected
      }),
    });

    if (response.ok) {
      closeRoleModal();
      fetchRoles(state.currentPage);
    } else {
      const message = await response.text();
      console.error("Failed to save role", message);
      alert("Failed to save role: " + message);
    }
  }

  // Role actions
  async function protectRole(roleId) {
    const response = await fetch(`${BASE}/api/v1/user_roles/manage`, { 
      method: "POST", 
      headers: jsonHeaders(),
      body: JSON.stringify({ action: "protect", identifier: roleId })
    });
    return response.ok;
  }

 async function unprotectRole(roleId) {
    const response = await fetch(`${BASE}/api/v1/user_roles/manage`, { 
      method: "POST", 
      headers: jsonHeaders(),
      body: JSON.stringify({ action: "unprotect", identifier: roleId })
    });
    return response.ok;
  }

 // Event wiring
 searchBtn?.addEventListener("click", () => fetchRoles(1));

  const debouncedSearch = debounce(() => fetchRoles(1), 300);
  searchInput?.addEventListener("input", () => {
    toggleClearButton();
    debouncedSearch();
  });
  searchInput?.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      fetchRoles(1);
    }
  });

 clearSearchBtn?.addEventListener("click", () => {
    if (!searchInput) return;
    searchInput.value = "";
    toggleClearButton();
    fetchRoles(1);
  });

  statusFilter?.addEventListener("change", () => fetchRoles(1));

  resetFiltersBtn?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    if (statusFilter) statusFilter.value = "all";
    toggleClearButton();
    fetchRoles(1);
  });

  emptyAddRoleBtn?.addEventListener("click", () => openRoleModal(null));

  prevBtn?.addEventListener("click", () => {
    if (state.currentPage > 1) fetchRoles(state.currentPage - 1);
  });
  nextBtn?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) fetchRoles(state.currentPage + 1);
  });

  selectAllCheckbox?.addEventListener("change", (event) => {
    const on = event.target.checked;
    selected.clear();
    tableBody.querySelectorAll(".row-select").forEach((checkbox) => {
      checkbox.checked = on;
      if (on) selected.add(checkbox.value);
    });
    updateBulkUI();
 });

  tableBody.addEventListener("change", (event) => {
    const checkbox = event.target.closest(".row-select");
    if (!checkbox) return;
    if (checkbox.checked) selected.add(checkbox.value);
    else selected.delete(checkbox.value);
    updateBulkUI();
  });

 tableBody.addEventListener("click", async (event) => {
    const editBtn = event.target.closest(".edit-role-btn");
    const protectBtn = event.target.closest(".protect-role-btn");

    if (editBtn) {
      openRoleModal(editBtn.getAttribute("data-id"));
      return;
    }

    if (protectBtn) {
      const roleId = protectBtn.getAttribute("data-id");
      const row = protectBtn.closest("tr");
      const isProtected = row?.querySelector(".protect-role-btn")?.textContent.trim() === "Unprotect";
      const ok = isProtected ? await unprotectRole(roleId) : await protectRole(roleId);
      if (ok) fetchRoles(state.currentPage);
      return;
    }
 });

 bulkBtn?.addEventListener("click", () => {
    if (selected.size === 0) return;
    openBulkModal();
  });
 bulkCancelBtn?.addEventListener("click", closeBulkModal);
  bulkConfirmBtn?.addEventListener("click", () => {
    const action = document.getElementById("bulk-action-select")?.value || "activate";
    console.info("Requested bulk " + action + " for", Array.from(selected));
    closeBulkModal();
  });

  addRoleBtn?.addEventListener("click", () => openRoleModal(null));
  modalCloseBtn?.addEventListener("click", closeRoleModal);
  cancelRoleBtn?.addEventListener("click", closeRoleModal);
  roleModal?.addEventListener("click", (event) => {
    if (event.target === roleModal) closeRoleModal();
  });
  bulkModal?.addEventListener("click", (event) => {
    if (event.target === bulkModal) closeBulkModal();
  });

  roleForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveRole();
  });

  sortButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const field = button.getAttribute("data-sort");
      if (!field) return;
      if (state.sortField === field) {
        state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
      } else {
        state.sortField = field;
        state.sortDirection = "asc";
      }
      updateSortIndicators();
      renderRoles();
    });
  });

  function updateSortIndicators() {
    sortButtons.forEach((button) => {
      const field = button.getAttribute("data-sort");
      const icon = button.querySelector(".sort-icon");
      const isActive = state.sortField === field;
      const direction = isActive ? state.sortDirection : null;

      button.setAttribute("aria-sort", direction ? (direction === "asc" ? "ascending" : "descending") : "none");
      if (!icon) return;
      icon.style.opacity = isActive ? "1" : "0.35";
      icon.innerHTML = direction === "desc" ? "<span>▼</span><span>▲</span>" : "<span>▲</span><span>▼</span>";
    });
  }

 window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeRoleModal();
      closeBulkModal();
    }
 });

 // Initialise
 toggleClearButton();
  updateSortIndicators();
  metricFallback(metricTotalEl);
  metricFallback(metricDocumentedEl);
  metricFallback(metricProtectedEl);
  metricFallback(metricLastSyncEl);

 fetchRoles(1);
})();
