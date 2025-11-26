(function () {
  const BASE = "";
  const tableBody = document.querySelector("#users-table-body");
  if (!tableBody) return;

  const state = {
    currentPage: 1,
    totalPages: 1,
    totalUsers: 0,
    rawItems: [],
    sortField: null,
    sortDirection: "asc",
    pageSize: 10,
  };

  const selected = new Set();

  // Element references
  const loadingIndicator = document.getElementById("loading-indicator");
  const emptyState = document.getElementById("empty-state");
  const searchInput = document.getElementById("user-search");
  const clearSearchBtn = document.getElementById("clear-search");
  const roleFilter = document.getElementById("role-filter");
  const statusFilter = document.getElementById("status-filter");
  const searchBtn = document.getElementById("search-btn");
  const resetFiltersBtn = document.getElementById("reset-filters");
  const emptyAddUserBtn = document.getElementById("empty-add-user");
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
  const metricTotalEl = document.getElementById("metric-total-users");
  const metricActiveEl = document.getElementById("metric-active-users");
  const metricLockedEl = document.getElementById("metric-locked-users");
  const metricNewEl = document.getElementById("metric-new-users");
  const selectAllCheckbox = document.getElementById("select-all-users");
  const addUserBtn = document.getElementById("add-user-btn");
  const userModal = document.getElementById("user-modal");
  const modalCloseBtn = document.getElementById("modal-close");
  const cancelUserBtn = document.getElementById("cancel-user-btn");
  const userForm = document.getElementById("user-form");
  const modalTitle = document.getElementById("modal-title");
  const statusLabelMap = {
    active: { label: "Active", badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200" },
    inactive: { label: "Inactive", badge: "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300" },
    locked: { label: "Locked", badge: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200" },
  };

  const sortButtons = document.querySelectorAll("[data-sort]");
  const rolesContainer = document.getElementById("roles");
  const rolesHelpText = document.getElementById("roles-help");
  const categoriesContainer = document.getElementById("categories");
  const categoriesHelpText = document.getElementById("categories-help");
  const paperCategoriesContainer = document.getElementById("paper-categories");
  const awardCategoriesContainer = document.getElementById("award-categories");

  const metricFallback = (el) => el && (el.textContent = "0");
  const getRoleInputs = () =>
    rolesContainer ? rolesContainer.querySelectorAll("input[name='roles']") : [];
  const getCategoryInputs = () =>
    categoriesContainer ? categoriesContainer.querySelectorAll("input[name='category_ids']") : [];
  const getPaperCategoryInputs = () =>
    paperCategoriesContainer ? paperCategoriesContainer.querySelectorAll("input[name='paper_category_ids']") : [];
  const getAwardCategoryInputs = () =>
    awardCategoriesContainer ? awardCategoriesContainer.querySelectorAll("input[name='award_category_ids']") : [];

  let availableRoles = [];
  let rolesReady = false;
  let pendingRoleSelection = [];

  let availableCategories = [];
  let categoriesReady = false;
  let pendingCategorySelection = [];

  let availablePaperCategories = [];
  let paperCategoriesReady = false;
  let pendingPaperCategoryIds = [];
  let pendingAwardCategoryIds = [];

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
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function setRoleSelection(roleValues = []) {
    pendingRoleSelection = Array.isArray(roleValues)
      ? roleValues.map((value) => String(value).trim())
      : [];
    if (!rolesReady) return;
    const selectedSet = new Set(pendingRoleSelection.map((value) => value.toLowerCase()));
    getRoleInputs().forEach((input) => {
      input.checked = selectedSet.has(input.value.toLowerCase());
    });
  }

  function renderRoleOptions() {
    if (!rolesContainer) return;

    if (!availableRoles.length) {
      rolesContainer.innerHTML = `<div class="col-span-full rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
        No roles available. Check role configuration or contact a system administrator.
      </div>`;
      rolesReady = false;
      return;
    }

   rolesContainer.innerHTML = availableRoles
     .map(
        (role) => `
        <label class="flex w-full cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm transition hover:border-blue-400 hover:shadow-md focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-400/60">
          <input
            type="checkbox"
            name="roles"
            value="${escapeHtml(role.value)}"
            class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600"
          >
          <span class="flex flex-col">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(role.label)}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">${escapeHtml(role.description || "")}</span>
          </span>
        </label>`
      )
      .join("");

    rolesReady = true;
    if (rolesHelpText) {
      rolesHelpText.textContent = `Select all roles that should apply to this user. ${availableRoles.length} role option${availableRoles.length === 1 ? '' : 's'} available.`;
    }
    setRoleSelection(pendingRoleSelection);
  }

  async function fetchAvailableRoles() {
    if (!rolesContainer) return;

    rolesReady = false;
    rolesContainer.innerHTML = `<div class="col-span-full flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600 shadow-inner dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
      <svg class="h-4 w-4 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"/>
      </svg>
      Loading available roles…
    </div>`;

    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/available`, {
        headers: authHeader(),
      });
      if (!response.ok) {
        throw new Error(`Failed with status ${response.status}`);
      }
      const data = await response.json();
      availableRoles = Array.isArray(data.items) ? data.items : [];
      renderRoleOptions();
    } catch (error) {
      console.error("Unable to load available roles", error);
      availableRoles = [];
      rolesContainer.innerHTML = `<div class="col-span-full space-y-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 shadow-sm dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
        <p class="font-medium">Unable to load roles</p>
        <p class="text-xs text-red-500 dark:text-red-200">We could not fetch the available role definitions. Please try again.</p>
        <button id="retry-load-roles" type="button" class="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-100 dark:hover:bg-red-500/20">
          Retry
        </button>
      </div>`;
      rolesReady = false;
      if (rolesHelpText) {
        rolesHelpText.textContent = "Role information could not be loaded. Retry or refresh the page.";
      }
      document.getElementById("retry-load-roles")?.addEventListener("click", fetchAvailableRoles);
    }
  }

  function setCategorySelection(categoryValues = []) {
    pendingCategorySelection = Array.isArray(categoryValues)
      ? categoryValues
          .map((value) => String(value).trim())
          .filter((value) => Boolean(value))
      : [];
    if (!categoriesReady) return;
    const selectedSet = new Set(pendingCategorySelection);
    getCategoryInputs().forEach((input) => {
      input.checked = selectedSet.has(input.value);
    });
  }

  function renderCategoryOptions() {
    if (!categoriesContainer) return;

    if (!availableCategories.length) {
      categoriesContainer.innerHTML = `<div class="col-span-full rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
        No categories are currently configured. Create categories first to assign them to users.
      </div>`;
      categoriesReady = true;
      if (categoriesHelpText) {
        categoriesHelpText.textContent = "No categories available.";
      }
      setCategorySelection([]);
      return;
    }

    categoriesContainer.innerHTML = availableCategories
      .map(
        (category) => `
        <label class="flex w-full cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm transition hover:border-emerald-400 hover:shadow-md focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-emerald-400/60">
          <input
            type="checkbox"
            name="category_ids"
            value="${escapeHtml(category.id)}"
            class="mt-1 h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 dark:border-gray-600"
          >
          <span class="flex flex-col">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(category.name || "Untitled category")}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">Assign this user to ${escapeHtml(category.name || "this category")}.</span>
          </span>
        </label>`
      )
      .join("");

    categoriesReady = true;
    if (categoriesHelpText) {
      const count = availableCategories.length;
      categoriesHelpText.textContent = `${count} categor${count === 1 ? "y" : "ies"} available. Select all that apply.`;
    }
    setCategorySelection(pendingCategorySelection);
  }

  async function fetchAvailableCategories() {
    if (!categoriesContainer) return;

    categoriesReady = false;
    categoriesContainer.innerHTML = `<div class="col-span-full flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600 shadow-inner dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
      <svg class="h-4 w-4 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"/>
      </svg>
      Loading available categories…
    </div>`;

    try {
      const response = await fetch(`${BASE}/api/v1/research/categories`, {
        headers: authHeader(),
      });
      if (!response.ok) {
        throw new Error(`Failed with status ${response.status}`);
      }
      const data = await response.json();
      availableCategories = Array.isArray(data)
        ? data
        : Array.isArray(data.items)
        ? data.items
        : [];
      renderCategoryOptions();
    } catch (error) {
      console.error("Unable to load categories", error);
      categoriesContainer.innerHTML = `<div class="col-span-full space-y-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 shadow-sm dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
        <p class="font-medium">Unable to load categories</p>
        <p class="text-xs text-red-500 dark:text-red-200">We could not fetch the available categories. Please try again.</p>
        <button id="retry-load-categories" type="button" class="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-100 dark:hover:bg-red-500/20">
          Retry
        </button>
      </div>`;
      categoriesReady = false;
      if (categoriesHelpText) {
        categoriesHelpText.textContent = "Category information could not be loaded. Retry or refresh the page.";
      }
      document.getElementById("retry-load-categories")?.addEventListener("click", fetchAvailableCategories);
    }
  }

  function setPaperCategorySelection(paperCategoryIds = [], awardCategoryIds = []) {
    pendingPaperCategoryIds = Array.isArray(paperCategoryIds) ? paperCategoryIds.filter(Boolean) : [];
    pendingAwardCategoryIds = Array.isArray(awardCategoryIds) ? awardCategoryIds.filter(Boolean) : [];
    if (!paperCategoriesReady) return;
    const paperSet = new Set(pendingPaperCategoryIds);
    const awardSet = new Set(pendingAwardCategoryIds);
    getPaperCategoryInputs().forEach((input) => {
      input.checked = paperSet.has(input.value);
    });
    getAwardCategoryInputs().forEach((input) => {
      input.checked = awardSet.has(input.value);
    });
  }

  function renderPaperCategoryOptions() {
    const renderInto = (container, type) => {
      if (!container) return;
      if (!availablePaperCategories.length) {
        container.innerHTML = `<div class="col-span-full rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
          No ${type} categories are currently configured.
        </div>`;
        return;
      }

      container.innerHTML = availablePaperCategories
        .map(
          (category) => `
          <label class="flex w-full cursor-pointer items-start gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-sm transition hover:border-emerald-400 hover:shadow-md focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-emerald-400/60">
            <input
              type="checkbox"
              name="${type === "paper" ? "paper_category_ids" : "award_category_ids"}"
              value="${escapeHtml(category.id)}"
              class="mt-1 h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 dark:border-gray-600"
            >
            <span class="flex flex-col">
              <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(category.name || "Untitled category")}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400">Assign this user to ${escapeHtml(category.name || "this category")}.</span>
            </span>
          </label>`
        )
        .join("");
    };

    renderInto(paperCategoriesContainer, "paper");
    renderInto(awardCategoriesContainer, "award");

    paperCategoriesReady = true;
    setPaperCategorySelection(pendingPaperCategoryIds, pendingAwardCategoryIds);
  }

  async function fetchPaperCategories() {
    if (!paperCategoriesContainer && !awardCategoriesContainer) return;

    paperCategoriesReady = false;
    const loadingMarkup = `<div class="col-span-full flex items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600 shadow-inner dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-300">
      <svg class="h-4 w-4 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"/>
      </svg>
      Loading categories…
    </div>`;
    if (paperCategoriesContainer) paperCategoriesContainer.innerHTML = loadingMarkup;
    if (awardCategoriesContainer) awardCategoriesContainer.innerHTML = loadingMarkup;

    try {
      const response = await fetch(`${BASE}/api/v1/research/papercategories`, { headers: authHeader() });
      if (!response.ok) throw new Error(`Failed with status ${response.status}`);
      const data = await response.json();
      availablePaperCategories = Array.isArray(data)
        ? data
        : Array.isArray(data.items)
        ? data.items
        : [];
      renderPaperCategoryOptions();
    } catch (error) {
      console.error("Unable to load paper categories", error);
      const fallback = `<div class="col-span-full space-y-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 shadow-sm dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-100">
        <p class="font-medium">Unable to load categories</p>
        <p class="text-xs text-red-500 dark:text-red-200">We could not fetch the available categories. Please try again.</p>
        <button id="retry-load-paper-categories" type="button" class="inline-flex items-center gap-2 rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 dark:border-red-400/40 dark:bg-red-500/10 dark:text-red-100 dark:hover:bg-red-500/20">
          Retry
        </button>
      </div>`;
      if (paperCategoriesContainer) paperCategoriesContainer.innerHTML = fallback;
      if (awardCategoriesContainer) awardCategoriesContainer.innerHTML = fallback;
      paperCategoriesReady = false;
      document.getElementById("retry-load-paper-categories")?.addEventListener("click", fetchPaperCategories);
    }
  }

  // Fetch & transform
  async function fetchUsers(page = 1) {
    showLoading();
    const params = new URLSearchParams();
    params.set("page", page);

    const search = searchInput?.value?.trim();
    if (search) params.set("search", search);

    const role = roleFilter?.value;
    if (role && role !== "all") params.set("role", role);

    const status = statusFilter?.value;
    if (status && status !== "all") params.set("status", status);

    try {
      const response = await fetch(`${BASE}/api/v1/super/users?${params.toString()}`, { headers: authHeader() });
      if (!response.ok) {
        console.error("Failed to load users", response.status);
        hideLoading();
        return;
      }

      const data = await response.json();
      state.currentPage = data.current_page || page;
      state.totalPages = data.total_pages || 1;
      state.totalUsers = data.total_count ?? data.total ?? 0;
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
      renderUsers();
      renderPagination();
    } catch (error) {
      console.error("Unable to load users", error);
    } finally {
      toggleClearButton();
      hideLoading();
    }
  }

  function updateMetricsFromResponse(data) {
    const items = Array.isArray(data.items) ? data.items : [];
    const metrics = data.metrics || data.stats || {};

    const activeCount = Number.isFinite(metrics.active) ? metrics.active : items.reduce((acc, user) => (user.is_active ? acc + 1 : acc), 0);
    const lockedCount = Number.isFinite(metrics.locked) ? metrics.locked : items.reduce((acc, user) => (user.lock_until ? acc + 1 : acc), 0);

    let newUsers = Number.isFinite(metrics.new) ? metrics.new : 0;
    if (!newUsers && items.length) {
      const cutoff = Date.now() - 1000 * 60 * 60 * 24 * 30;
      newUsers = items.reduce((acc, user) => {
        const created = safeDate(user.created_at);
        return created && created.getTime() >= cutoff ? acc + 1 : acc;
      }, 0);
    }

    setMetric(metricTotalEl, data.total_count ?? data.total ?? items.length);
    setMetric(metricActiveEl, activeCount);
    setMetric(metricLockedEl, lockedCount);
    setMetric(metricNewEl, newUsers);
  }

  function applyFilters(items) {
    const status = statusFilter?.value || "all";
    if (status === "all") return [...items];

    return items.filter((user) => {
      if (status === "locked") return Boolean(user.lock_until);
      if (status === "active") return Boolean(user.is_active) && !user.lock_until;
      if (status === "inactive") return !user.is_active && !user.lock_until;
      return true;
    });
  }

  function resolveSortValue(user, field) {
    switch (field) {
      case "username":
        return user.username || "";
      case "email":
        return user.email || "";
      case "employee_id":
        return user.employee_id || "";
      case "mobile":
        return user.mobile || "";
      case "status":
        return user.is_active ? 1 : 0;
      case "lock":
        return user.lock_until ? 1 : 0;
      case "last_login":
        return safeDate(user.last_login) || new Date(0);
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

  function renderUsers() {
    const filteredItems = applyFilters(state.rawItems);
    const items = applySort(filteredItems);

    tableBody.innerHTML = "";
    visibleCountEl && (visibleCountEl.textContent = items.length);
    toggleEmptyState(items.length === 0);

    const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

    items.forEach((user) => {
      const tr = document.createElement("tr");
      const isSelected = selected.has(user.id);
      const isLocked = Boolean(user.lock_until);
      const isActive = Boolean(user.is_active);
      const statusKey = isLocked ? "locked" : isActive ? "active" : "inactive";
      const statusMeta = statusLabelMap[statusKey];
      const statusLabel = statusMeta.label;
      const statusBadgeClass = statusMeta.badge;

      const lastLoginDate = safeDate(user.last_login);
      const lastLogin = lastLoginDate ? formatter.format(lastLoginDate) : "Never";
      const isVerified = Boolean(user.is_verified);
      
      const roles = (user.roles || []).map((role) => {
        const roleName = String(role || "").toLowerCase();
        let badgeClass = "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";
        if (roleName.includes("admin")) badgeClass = "bg-purple-100 text-purple-700 dark:bg-purple-500/10 dark:text-purple-200";
        if (roleName.includes("super")) badgeClass = "bg-blue-100 text-blue-700 dark:bg-blue-500/10 dark:text-blue-200";
        if (roleName.includes("verifier")) badgeClass = "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200";
        return `<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}">
            ${escapeHtml(role)}
        </span>`;
      }).join("");

      const resolvedCategories = Array.isArray(user.categories) && user.categories.length
        ? user.categories
        : user.category
        ? [user.category]
        : [];
      const categoriesMarkup = resolvedCategories
        .map((cat) => {
          const categoryName = String(cat?.name || "").trim() || "Unassigned";
          const badgeClass = "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";
          return `<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}">
            ${escapeHtml(categoryName)}
          </span>`;
        })
        .join("");

      const paperCats = Array.isArray(user.paper_categories) && user.paper_categories.length
        ? user.paper_categories
        : user.paper_category
        ? [user.paper_category]
        : [];
      const awardCats = Array.isArray(user.award_categories) && user.award_categories.length
        ? user.award_categories
        : user.award_category
        ? [user.award_category]
        : [];

      const paperCatMarkup = paperCats
        .map((cat) => {
          const name = cat?.name || "—";
          const badgeClass = "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";
          return `<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}">
            ${escapeHtml(name)}
          </span>`;
        })
        .join("");

      const awardCatMarkup = awardCats
        .map((cat) => {
          const name = cat?.name || "—";
          const badgeClass = "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";
          return `<span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeClass}">
            ${escapeHtml(name)}
          </span>`;
        })
        .join("");

      tr.className = [
        "bg-white dark:bg-gray-900/40",
        "hover:bg-gray-50 dark:hover:bg-gray-800/60 transition",
        isSelected ? "ring-1 ring-blue-500/50" : "",
      ].join(" ");

      tr.innerHTML = `
        <td class="px-6 py-4 align-middle">
          <input type="checkbox" class="row-select h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-700" value="${user.id}" ${isSelected ? "checked" : ""} aria-label="Select ${escapeHtml(user.username || "user")}">
        </td>
        <td class="px-6 py-4 align-middle">
          <div class="flex flex-col">
            <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(user.username || "")}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400">${escapeHtml(user.display_name || user.full_name || "")}</span>
          </div>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">
          <a href="mailto:${escapeHtml(user.email || "")}" class="transition hover:text-blue-600 dark:hover:text-blue-400">
            ${escapeHtml(user.email || "")}
          </a>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">${escapeHtml(user.employee_id || "—")}</td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300 hidden lg:table-cell">${escapeHtml(user.mobile || "—")}</td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">
          <div class="flex flex-wrap gap-1">${roles || '<span class="text-xs text-gray-400 dark:text-gray-500">No roles</span>'}</div>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">
          <div class="flex flex-wrap gap-1">${categoriesMarkup || '<span class="text-xs text-gray-400 dark:text-gray-500">No category</span>'}</div>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">
          <div class="flex flex-wrap gap-1">${paperCatMarkup || '<span class="text-xs text-gray-400 dark:text-gray-500">No paper category</span>'}</div>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300">
          <div class="flex flex-wrap gap-1">${awardCatMarkup || '<span class="text-xs text-gray-400 dark:text-gray-500">No award category</span>'}</div>
        </td>
        <td class="px-6 py-4 align-middle">
          <span class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadgeClass}">
            <span class="h-1.5 w-1.5 rounded-full bg-current"></span>
            ${statusLabel}
          </span>
        </td>
        <td class="px-6 py-4 align-middle">
          <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${isLocked ? "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-200" : "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200"}">
            ${isLocked ? "Locked" : "Unlocked"}
          </span>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300 hidden md:table-cell">
          <time datetime="${escapeHtml(user.last_login || "")}" title="${escapeHtml(user.last_login || "")}">
            ${escapeHtml(lastLogin)}
          </time>
        </td>
        <td class="px-6 py-4 align-middle text-sm text-gray-600 dark:text-gray-300 md:table-cell">
          ${isVerified ? `<span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200">
              <svg class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Verified
            </span>` : `<span class="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-700 dark:bg-gray-500 dark:text-gray-300">
              Not Verified
            </span>`}
        </td>
        <td class="px-6 py-4 align-middle text-right">
          <div class="flex items-center justify-end gap-2 text-sm">
            <button class="edit-user-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 text-blue-600 transition hover:bg-blue-50 dark:text-blue-300 dark:hover:bg-blue-500/10" data-id="${user.id}" title="Edit user">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 17.5V20h2.5L17.81 8.69l-2.5-2.5L4 17.5zM19.71 7.04a1 1 0 000-1.41l-1.34-1.34a1 1 0 00-1.41 0l-1.6 1.59 2.5 2.5 1.85-1.34z"/>
              </svg>
              Edit
            </button>
            <button class="activate-user-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 ${isActive ? "text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10" : "text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10"}" data-id="${user.id}" title="${isActive ? "Deactivate user" : "Activate user"}">
              ${isActive ? "Deactivate" : "Activate"}
            </button>
            <button class="lock-user-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 ${isLocked ? "text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10" : "text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10"}" data-id="${user.id}" title="${isLocked ? "Unlock user" : "Lock user"}">
              ${isLocked ? "Unlock" : "Lock"}
            </button>
            <button class="verify-user-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 ${isVerified ? "text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-500/10" : "text-red-600 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-500/10"}" data-id="${user.id}" title="${isVerified ? "Unverify user" : "Verify user"}">
              ${isVerified ? "Unverify" : "Verify"}
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
    const total = state.totalUsers;
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

  // User modal helpers
  function openUserModal(userId) {
    if (!userModal) return;

    if (userId) {
      modalTitle && (modalTitle.textContent = "Edit user");
      loadUserData(userId);
    } else {
      modalTitle && (modalTitle.textContent = "Add new user");
      resetUserForm();
    }

    userModal.classList.remove("hidden");
    toggleBodyScroll(true);
  }

  function closeUserModal() {
    if (!userModal) return;
    userModal.classList.add("hidden");
    toggleBodyScroll(false);
  }

  function resetUserForm() {
    const fields = ["user-id", "username", "email", "employee-id", "mobile"];
    fields.forEach((field) => {
      const input = document.getElementById(field);
      if (!input) return;
      if (field === "user-id") input.value = "";
      else input.value = "";
    });

    setRoleSelection([]);
    setCategorySelection([]);
    setPaperCategorySelection([], []);

    const statusSelect = document.getElementById("status");
    if (statusSelect) statusSelect.value = "active";
  }

  async function loadUserData(userId) {
    try {
      const response = await fetch(`${BASE}/api/v1/super/users/${userId}`, { headers: authHeader() });
      if (!response.ok) {
        console.error("Failed to load user data");
        return;
      }
      const { user } = await response.json();
      if (!user) return;

      const map = {
        "user-id": user.id,
        username: user.username || "",
        email: user.email || "",
        "employee-id": user.employee_id || "",
        mobile: user.mobile || "",
      };
      Object.entries(map).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.value = value;
      });

      const roles = Array.isArray(user.roles) ? user.roles.map((r) => String(r)) : [];
      setRoleSelection(roles);

      const categorySource = Array.isArray(user.categories) && user.categories.length
        ? user.categories
        : user.category
        ? [user.category]
        : [];
      const categoryIds = categorySource
        .map((c) => c && (c.id || c.category_id))
        .filter((value) => Boolean(value))
        .map((value) => String(value));
      setCategorySelection(categoryIds);

      const paperCatIds = (Array.isArray(user.paper_categories) ? user.paper_categories : [])
        .map((cat) => cat && (cat.id || cat.paper_category_id || cat.category_id))
        .filter(Boolean)
        .map((val) => String(val));
      if (!paperCatIds.length && user.paper_category_id) {
        paperCatIds.push(String(user.paper_category_id));
      }

    const awardCatIds = (Array.isArray(user.award_categories) ? user.award_categories : [])
      .map((cat) => cat && (cat.id || cat.paper_category_id || cat.category_id))
      .filter(Boolean)
      .map((val) => String(val));
    if (!awardCatIds.length && user.award_category_id) {
      awardCatIds.push(String(user.award_category_id));
    }

    setPaperCategorySelection(paperCatIds, awardCatIds);

      const statusSelect = document.getElementById("status");
      if (statusSelect) statusSelect.value = user.is_active ? "active" : user.lock_until ? "locked" : "inactive";
    } catch (error) {
      console.error("Failed to load user details", error);
    }
  }

  async function saveUser() {
    if (!rolesReady && !availableRoles.length) {
      alert("Roles are still loading. Please wait a moment and try again.");
      return;
    }

    const userId = document.getElementById("user-id")?.value;
    const selectedRoles = Array.from(getRoleInputs()).filter((input) => input.checked).map((input) => input.value);
    if (!selectedRoles.length) {
      alert("Select at least one role for the user.");
      return;
    }
    const payload = {
      username: document.getElementById("username")?.value || "",
      email: document.getElementById("email")?.value || "",
      employee_id: document.getElementById("employee-id")?.value || "",
      mobile: document.getElementById("mobile")?.value || "",
      roles: selectedRoles,
      is_active: (document.getElementById("status")?.value || "active") === "active",
    };

    const selectedCategoryIds = Array.from(getCategoryInputs())
      .filter((input) => input.checked)
      .map((input) => input.value)
      .filter((value, index, arr) => value && arr.indexOf(value) === index);
    payload.category_ids = selectedCategoryIds;
    payload.category_id = selectedCategoryIds[0] || null;
    const paperCategoryIds = Array.from(getPaperCategoryInputs())
      .filter((input) => input.checked)
      .map((input) => input.value);
    const awardCategoryIds = Array.from(getAwardCategoryInputs())
      .filter((input) => input.checked)
      .map((input) => input.value);
    payload.paper_category_ids = paperCategoryIds;
    payload.award_category_ids = awardCategoryIds;
    payload.paper_category_id = paperCategoryIds[0] || null;
    payload.award_category_id = awardCategoryIds[0] || null;

    if (!userId) {
      payload.password = "TempPass123!"; // Platform requires initial password; users prompted to change on first login
    }

    const method = userId ? "PUT" : "POST";
    const endpoint = userId ? `${BASE}/api/v1/super/users/${userId}` : `${BASE}/api/v1/super/users`;

    const response = await fetch(endpoint, {
      method,
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      closeUserModal();
      fetchUsers(state.currentPage);
    } else {
      const message = await response.text();
      console.error("Failed to save user", message);
      alert("Failed to save user: " + message);
    }
  }

  // Account actions
  async function activateUser(userId) {
    const response = await fetch(`${BASE}/api/v1/super/users/${userId}/activate`, { method: "POST", headers: jsonHeaders() });
    return response.ok;
  }

  async function deactivateUser(userId) {
    const response = await fetch(`${BASE}/api/v1/super/users/${userId}/deactivate`, { method: "POST", headers: jsonHeaders() });
    return response.ok;
  }

  async function lockUser(userId) {
    const response = await fetch(`${BASE}/api/v1/super/users/${userId}/lock`, { method: "POST", headers: jsonHeaders() });
    return response.ok;
  }

  async function unlockUser(userId) {
    const response = await fetch(`${BASE}/api/v1/super/users/${userId}/unlock`, { method: "POST", headers: jsonHeaders() });
    return response.ok;
  }

  // Event wiring
  searchBtn?.addEventListener("click", () => fetchUsers(1));

  const debouncedSearch = debounce(() => fetchUsers(1), 300);
  searchInput?.addEventListener("input", () => {
    toggleClearButton();
    debouncedSearch();
  });
  searchInput?.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      fetchUsers(1);
    }
  });

  clearSearchBtn?.addEventListener("click", () => {
    if (!searchInput) return;
    searchInput.value = "";
    toggleClearButton();
    fetchUsers(1);
  });

  roleFilter?.addEventListener("change", () => fetchUsers(1));
  statusFilter?.addEventListener("change", () => fetchUsers(1));

  resetFiltersBtn?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    if (roleFilter) roleFilter.value = "all";
    if (statusFilter) statusFilter.value = "all";
    toggleClearButton();
    fetchUsers(1);
  });

  emptyAddUserBtn?.addEventListener("click", () => openUserModal(null));

  prevBtn?.addEventListener("click", () => {
    if (state.currentPage > 1) fetchUsers(state.currentPage - 1);
  });
  nextBtn?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) fetchUsers(state.currentPage + 1);
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
    const editBtn = event.target.closest(".edit-user-btn");
    const activateBtn = event.target.closest(".activate-user-btn");
    const lockBtn = event.target.closest(".lock-user-btn");
    const verifyBtn = event.target.closest(".verify-user-btn");

    if (editBtn) {
      openUserModal(editBtn.getAttribute("data-id"));
      return;
    }

    if (activateBtn) {
      const userId = activateBtn.getAttribute("data-id");
      const row = activateBtn.closest("tr");
      const isActive = row?.querySelector(".activate-user-btn")?.textContent.trim() === "Deactivate";
      const ok = isActive ? await deactivateUser(userId) : await activateUser(userId);
      if (ok) fetchUsers(state.currentPage);
      return;
    }

    if (lockBtn) {
      const userId = lockBtn.getAttribute("data-id");
      try {
        const response = await fetch(`${BASE}/api/v1/super/users/${userId}`, { headers: authHeader() });
        if (!response.ok) return;
        const { user } = await response.json();
        const ok = user.lock_until ? await unlockUser(userId) : await lockUser(userId);
        if (ok) fetchUsers(state.currentPage);
      } catch (error) {
        console.error("Failed to toggle lock", error);
      }
    }
    if (verifyBtn) {
      const userId = verifyBtn.getAttribute("data-id");
      try {
        const response = await fetch(`${BASE}/api/v1/super/users/${userId}`, { headers: authHeader() });
        if (!response.ok) return;
        const { user } = await response.json();
        const verifyEndpoint = `${BASE}/api/v1/super/users/${userId}/${user.is_verified ? "unverify" : "verify"}`;
        const verifyResponse = await fetch(verifyEndpoint, { method: "POST", headers: jsonHeaders() });
        if (verifyResponse.ok) fetchUsers(state.currentPage);
      } catch (error) {
        console.error("Failed to toggle verification", error);
      }
    }
  });

  bulkBtn?.addEventListener("click", () => {
    if (selected.size === 0) return;
    openBulkModal();
  });
  bulkCancelBtn?.addEventListener("click", closeBulkModal);
  bulkConfirmBtn?.addEventListener("click", () => {
    const action = document.getElementById("bulk-action-select")?.value || "activate";
    console.info(`Requested bulk ${action} for`, Array.from(selected));
    closeBulkModal();
  });

  addUserBtn?.addEventListener("click", () => openUserModal(null));
  modalCloseBtn?.addEventListener("click", closeUserModal);
  cancelUserBtn?.addEventListener("click", closeUserModal);
  userModal?.addEventListener("click", (event) => {
    if (event.target === userModal) closeUserModal();
  });
  bulkModal?.addEventListener("click", (event) => {
    if (event.target === bulkModal) closeBulkModal();
  });

  userForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveUser();
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
      renderUsers();
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
      closeUserModal();
      closeBulkModal();
    }
  });

  // Initialise
  toggleClearButton();
  updateSortIndicators();
  metricFallback(metricTotalEl);
  metricFallback(metricActiveEl);
  metricFallback(metricLockedEl);
  metricFallback(metricNewEl);

  Promise.allSettled([fetchAvailableRoles(), fetchAvailableCategories(), fetchPaperCategories()])
    .finally(() => fetchUsers(1));
})();
