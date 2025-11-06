(function () {
  "use strict";

  const BASE = "";
  const loadingBanner = document.getElementById("roles-loading");
  const errorBanner = document.getElementById("roles-error");
  const errorMessageEl = document.getElementById("roles-error-message");
  const retryBtn = document.getElementById("roles-retry");
  const form = document.getElementById("role-form");
  const listContainer = document.getElementById("role-list");
  const saveBtn = document.getElementById("roles-save");
  const resetBtn = document.getElementById("roles-reset");
  const identifierInput = document.getElementById("role-identifier");
  const labelInput = document.getElementById("role-label");
  const descriptionInput = document.getElementById("role-description");
  const addBtn = document.getElementById("role-add");
  const deleteBtn = document.getElementById("role-delete");
  const totalMetric = document.getElementById("metric-total-roles");
  const documentedMetric = document.getElementById("metric-documented-roles");
  const lastSyncMetric = document.getElementById("metric-last-sync");
  const searchInput = document.getElementById("role-search");
  const sortSelect = document.getElementById("role-sort");
  const resultsCount = document.getElementById("role-results-count");
  const dirtyIndicator = document.getElementById("roles-dirty-indicator");

  if (!listContainer || !loadingBanner) return;

  const toast =
    window.researchPortal?.showToast ||
    ((message, type = "info") => {
      (type === "error" ? console.error : console.log)(`[RoleCatalogue] ${message}`);
    });

  const state = {
    roles: [],
    metadata: {},
    drafts: {},
    dirty: false,
    search: "",
    sort: "asc",
    lastSync: null,
  };

  let searchDebounce;

  const cssEscape = (function () {
    if (typeof window !== "undefined" && window.CSS && typeof window.CSS.escape === "function") {
      return (value) => window.CSS.escape(String(value));
    }
    return (value) =>
      String(value).replace(/[\0-\x1f\x20\x7f]|^-?\d|^-|[^0-9a-zA-Z_-]/g, (match) => {
        if (match === "\0") return "\uFFFD";
        return `\\${match}`;
      });
  })();

  function authHeader() {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    return token ? { Authorization: "Bearer " + token } : {};
  }

  function jsonHeaders() {
    return { "Content-Type": "application/json", ...authHeader() };
  }

  function showLoading(show) {
    loadingBanner.classList.toggle("hidden", !show);
    if (show) loadingBanner.classList.add("flex");
    else loadingBanner.classList.remove("flex");
  }

  function showError(message) {
    if (errorMessageEl) {
      errorMessageEl.textContent = message || "Unexpected error occurred.";
    }
    errorBanner?.classList.remove("hidden");
  }

  function hideError() {
    errorBanner?.classList.add("hidden");
  }

  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function prettifyIdentifier(identifier) {
    return (identifier || "")
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function setDirty(value) {
    state.dirty = Boolean(value);
    if (dirtyIndicator) {
      dirtyIndicator.classList.toggle("hidden", !state.dirty);
    }
  }

  function refreshDirtyIndicator() {
    setDirty(Object.keys(state.drafts).length > 0);
  }

  function formatCount(value, singular) {
    const count = Number(value) || 0;
    const label = singular || "item";
    return `${count.toLocaleString()} ${count === 1 ? label : `${label}s`}`;
  }

  function fallbackLabel(role) {
    if (role?.label && role.label.trim()) return role.label.trim();
    return prettifyIdentifier(role?.value || "");
  }

  function fallbackDescription(role) {
    return role?.description && role.description.trim() ? role.description.trim() : "";
  }

  function getBaseValues(roleValue) {
    const role = state.roles.find((item) => item.value === roleValue) || {};
    const meta = state.metadata[roleValue] || {};
    const label =
      meta.label && meta.label.trim()
        ? meta.label.trim()
        : fallbackLabel(role);
    const description =
      meta.description && meta.description.trim()
        ? meta.description.trim()
        : fallbackDescription(role);
    return { label, description };
  }

  function getDisplayValues(role) {
    const base = getBaseValues(role.value);
    const draft = state.drafts[role.value];
    if (!draft) {
      return { ...base, baseLabel: base.label, baseDescription: base.description };
    }

    return {
      label: draft.label ?? "",
      description: draft.description ?? "",
      baseLabel: base.label,
      baseDescription: base.description,
    };
  }

  function captureDrafts() {
    if (!listContainer) return;
    const rows = listContainer.querySelectorAll("tr[data-role-row]");
    if (!rows.length) {
      refreshDirtyIndicator();
      return;
    }

    rows.forEach((row) => {
      const roleValue = row.getAttribute("data-role-row");
      if (!roleValue) return;
      const inputs = row.querySelectorAll(`[data-role="${cssEscape(roleValue)}"]`);
      if (!inputs.length) return;
      const entry = { label: "", description: "" };
      inputs.forEach((input) => {
        if (input.name === "label") entry.label = input.value;
        if (input.name === "description") entry.description = input.value;
      });
      const base = getBaseValues(roleValue);
      if (entry.label === base.label && entry.description === base.description) {
        delete state.drafts[roleValue];
      } else {
        state.drafts[roleValue] = entry;
      }
    });
    refreshDirtyIndicator();
  }

  function getRenderableRoles() {
    let roles = Array.isArray(state.roles) ? state.roles.slice() : [];
    if (state.search) {
      const query = state.search.toLowerCase();
      roles = roles.filter((role) => {
        const value = (role.value || "").toLowerCase();
        const { label, description } = getDisplayValues(role);
        return (
          value.includes(query) ||
          (label || "").toLowerCase().includes(query) ||
          (description || "").toLowerCase().includes(query)
        );
      });
    }

    if (state.sort === "desc") {
      roles
        .sort((a, b) => (a.value || "").localeCompare(b.value || "", undefined, { sensitivity: "base" }))
        .reverse();
    } else if (state.sort === "label") {
      roles.sort((a, b) => {
        const aLabel = (getDisplayValues(a).label || "").toLowerCase();
        const bLabel = (getDisplayValues(b).label || "").toLowerCase();
        return aLabel.localeCompare(bLabel, undefined, { sensitivity: "base" });
      });
    } else {
      roles.sort((a, b) => (a.value || "").localeCompare(b.value || "", undefined, { sensitivity: "base" }));
    }
    return roles;
  }

  function updateMetrics() {
    const total = state.roles.length;
    if (totalMetric) totalMetric.textContent = formatCount(total, "role");

    let documented = 0;
    state.roles.forEach((role) => {
      const meta = state.metadata[role.value] || {};
      if ((meta.label && meta.label.trim()) || (meta.description && meta.description.trim())) {
        documented += 1;
      }
    });
    if (documentedMetric) documentedMetric.textContent = formatCount(documented, "role");

    if (lastSyncMetric) {
      lastSyncMetric.textContent = state.lastSync
        ? state.lastSync.toLocaleString()
        : "Awaiting refresh…";
    }

    if (resultsCount) {
      const filtered = getRenderableRoles().length;
      if (!total) {
        resultsCount.textContent = "0 roles";
      } else if (filtered === total) {
        resultsCount.textContent = formatCount(total, "role");
      } else {
        resultsCount.textContent = `Showing ${filtered.toLocaleString()} of ${total.toLocaleString()} roles`;
      }
    }
  }

  function renderRoles(options = {}) {
    const { skipCapture = false } = options;
    if (!skipCapture) {
      captureDrafts();
    }

    listContainer.innerHTML = "";
    const roles = getRenderableRoles();
    if (!state.roles.length) {
      listContainer.innerHTML =
        '<tr><td colspan="4" class="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-300">No system roles were returned.</td></tr>';
      updateMetrics();
      return;
    }

    if (!roles.length) {
      listContainer.innerHTML =
        '<tr><td colspan="4" class="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-300">No roles match the current filters.</td></tr>';
      updateMetrics();
      return;
    }

    const fragment = document.createDocumentFragment();
    roles.forEach((role) => {
      const { label, description, baseLabel, baseDescription } = getDisplayValues(role);
      const persistedMeta = state.metadata[role.value] || {};
      const hasPersistedMetadata =
        (persistedMeta.label && persistedMeta.label.trim()) ||
        (persistedMeta.description && persistedMeta.description.trim());
      const hasDraftChanges = label !== baseLabel || description !== baseDescription;

      const row = document.createElement("tr");
      row.setAttribute("data-role-row", role.value);
      row.className = "align-top";
      row.innerHTML = `
        <td class="whitespace-nowrap px-4 py-4 align-top">
          <div class="flex items-start gap-3">
            <span class="mt-1 inline-flex h-2.5 w-2.5 flex-shrink-0 rounded-full ${
              hasPersistedMetadata || hasDraftChanges ? "bg-blue-500" : "bg-gray-400 dark:bg-gray-600"
            }" data-role-indicator="${escapeHtml(role.value)}"></span>
            <div>
              <div class="font-mono text-sm font-semibold text-gray-900 dark:text-gray-100">${escapeHtml(
                role.value
              )}</div>
              <div class="mt-1 text-xs text-gray-500 dark:text-gray-400">Enum: ${escapeHtml(
                role.enum || role.value
              )}</div>
            </div>
          </div>
        </td>
        <td class="px-4 py-4 align-top">
          <label class="block text-sm font-semibold text-gray-800 dark:text-gray-100">
            <span class="sr-only">Display label</span>
            <input type="text" class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100" name="label" value="${escapeHtml(
              label
            )}" data-role="${escapeHtml(role.value)}" autocomplete="off">
          </label>
        </td>
        <td class="px-4 py-4 align-top">
          <label class="block text-sm font-semibold text-gray-800 dark:text-gray-100">
            <span class="sr-only">Description</span>
            <textarea class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100" name="description" rows="3" data-role="${escapeHtml(
              role.value
            )}" autocomplete="off">${escapeHtml(description)}</textarea>
          </label>
        </td>
        <td class="px-4 py-4 align-top text-right">
          <div class="inline-flex flex-col gap-2 sm:flex-row sm:justify-end">
            <button type="button" class="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300" data-action="reset" data-role="${escapeHtml(
              role.value
            )}" title="Restore stored metadata">
              Reset
            </button>
            <button type="button" class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900" data-action="copy" data-role="${escapeHtml(
              role.value
            )}" title="Copy role identifier">
              Copy ID
            </button>
          </div>
        </td>`;
      fragment.appendChild(row);
    });

    listContainer.appendChild(fragment);
    updateMetrics();
  }

  function applyMetadata(meta) {
    if (meta && typeof meta === "object") {
      state.metadata = { ...meta };
    } else {
      state.metadata = {};
    }
    state.drafts = {};
    refreshDirtyIndicator();
  }

  async function loadMetadata() {
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/metadata`, { headers: authHeader() });
      if (!response.ok) throw new Error(`Failed with status ${response.status}`);
      const data = await response.json();
      applyMetadata(data.items || {});
      renderRoles({ skipCapture: true });
    } catch (error) {
      console.error("Failed to load role metadata", error);
      toast("Unable to load role metadata. Using defaults.", "warn");
      applyMetadata({});
      renderRoles({ skipCapture: true });
    }
  }

  async function loadRoles() {
    hideError();
    showLoading(true);
    state.drafts = {};
    refreshDirtyIndicator();
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/available`, { headers: authHeader() });
      if (!response.ok) throw new Error(`Failed with status ${response.status}`);
      const data = await response.json();
      state.roles = Array.isArray(data.items) ? data.items : [];
      form?.classList.remove("hidden");
      renderRoles({ skipCapture: true });
      showLoading(false);
      await loadMetadata();
      state.lastSync = new Date();
      updateMetrics();
    } catch (error) {
      console.error("Failed to load roles", error);
      showLoading(false);
      showError("Unable to load role definitions.");
    }
  }

  async function saveMetadata(evt) {
    evt?.preventDefault();
    captureDrafts();

    const snapshot = {};
    state.roles.forEach((role) => {
      const inputs = listContainer.querySelectorAll(`[data-role="${cssEscape(role.value)}"]`);
      const entry = { label: "", description: "" };
      inputs.forEach((input) => {
        if (input.name === "label") entry.label = input.value.trim();
        if (input.name === "description") entry.description = input.value.trim();
      });
      snapshot[role.value] = entry;
    });

    saveBtn?.classList.add("opacity-60", "pointer-events-none");
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/metadata`, {
        method: "PUT",
        headers: jsonHeaders(),
        body: JSON.stringify({ items: snapshot }),
      });
      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Failed with status ${response.status}`);
      }
      const data = await response.json();
      applyMetadata(data.items || {});
      renderRoles({ skipCapture: true });
      toast("Role metadata saved.", "success");
      state.lastSync = new Date();
      updateMetrics();
    } catch (error) {
      console.error("Failed to save metadata", error);
      toast("Unable to save role metadata.", "error");
    } finally {
      saveBtn?.classList.remove("opacity-60", "pointer-events-none");
    }
  }

  function resetAllMetadata() {
    state.drafts = {};
    refreshDirtyIndicator();
    renderRoles({ skipCapture: true });
  }

  async function copyRoleIdentifier(roleValue) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(roleValue);
      } else {
        const tempInput = document.createElement("input");
        tempInput.value = roleValue;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
      }
      toast(`Copied '${roleValue}' to clipboard.`, "success");
    } catch (error) {
      console.error("Failed to copy identifier", error);
      toast("Unable to copy role identifier.", "error");
    }
  }

  function resetRoleRow(roleValue) {
    const base = getBaseValues(roleValue);
    const inputs = listContainer.querySelectorAll(`[data-role="${cssEscape(roleValue)}"]`);
    inputs.forEach((input) => {
      if (input.name === "label") input.value = base.label;
      if (input.name === "description") input.value = base.description;
    });
    delete state.drafts[roleValue];
    refreshDirtyIndicator();
    renderRoles({ skipCapture: true });
  }

  function updateDraftForRole(roleValue) {
    const inputs = listContainer.querySelectorAll(`[data-role="${cssEscape(roleValue)}"]`);
    if (!inputs.length) return;
    const entry = { label: "", description: "" };
    inputs.forEach((input) => {
      if (input.name === "label") entry.label = input.value;
      if (input.name === "description") entry.description = input.value;
    });
    const base = getBaseValues(roleValue);
    if (entry.label === base.label && entry.description === base.description) {
      delete state.drafts[roleValue];
    } else {
      state.drafts[roleValue] = entry;
    }
    refreshDirtyIndicator();

    const indicator = listContainer.querySelector(`[data-role-indicator="${cssEscape(roleValue)}"]`);
    if (indicator) {
      const persistedMeta = state.metadata[roleValue] || {};
      const hasPersisted =
        (persistedMeta.label && persistedMeta.label.trim()) ||
        (persistedMeta.description && persistedMeta.description.trim());
      const hasDraftChanges = entry.label !== base.label || entry.description !== base.description;
      indicator.classList.remove("bg-blue-500", "bg-gray-400", "dark:bg-gray-600");
      if (hasPersisted || hasDraftChanges) {
        indicator.classList.add("bg-blue-500");
      } else {
        indicator.classList.add("bg-gray-400", "dark:bg-gray-600");
      }
    }
  }

  form?.addEventListener("submit", saveMetadata);

  form?.addEventListener("input", (evt) => {
    const target = evt.target;
    if (!target) return;
    if (target.id === "role-search" || target.id === "role-sort") return;
    const roleValue = target.dataset.role;
    if (!roleValue) return;
    updateDraftForRole(roleValue);
  });

  resetBtn?.addEventListener("click", (evt) => {
    evt.preventDefault();
    resetAllMetadata();
  });

  retryBtn?.addEventListener("click", () => {
    hideError();
    loadRoles();
  });

  addBtn?.addEventListener("click", async () => {
    const identifier = identifierInput?.value.trim();
    if (!identifier) {
      toast("Provide a role identifier.", "warn");
      return;
    }
    if (state.dirty) {
      toast("Save or reset metadata changes before adding a new role.", "warn");
      return;
    }

    const payload = {
      action: "add",
      identifier,
      metadata: {
        label: labelInput?.value || "",
        description: descriptionInput?.value || "",
      },
    };

    addBtn.classList.add("opacity-60", "pointer-events-none");
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/manage`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Failed with status ${response.status}`);
      toast("Role added successfully.", "success");
      identifierInput && (identifierInput.value = "");
      labelInput && (labelInput.value = "");
      descriptionInput && (descriptionInput.value = "");
      await loadRoles();
    } catch (error) {
      console.error("Failed to add role", error);
      toast(error.message || "Unable to add role.", "error");
    } finally {
      addBtn.classList.remove("opacity-60", "pointer-events-none");
    }
  });

  deleteBtn?.addEventListener("click", async () => {
    const identifier = identifierInput?.value.trim();
    if (!identifier) {
      toast("Provide a role identifier to delete.", "warn");
      return;
    }
    if (state.dirty) {
      toast("Save or reset metadata changes before deleting a role.", "warn");
      return;
    }

    if (!confirm(`Are you sure you want to delete the role '${identifier}'?`)) {
      return;
    }

    const payload = { action: "delete", identifier };

    deleteBtn.classList.add("opacity-60", "pointer-events-none");
    try {
      const response = await fetch(`${BASE}/api/v1/user_roles/manage`, {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Failed with status ${response.status}`);
      toast("Role removed successfully.", "success");
      identifierInput && (identifierInput.value = "");
      labelInput && (labelInput.value = "");
      descriptionInput && (descriptionInput.value = "");
      await loadRoles();
    } catch (error) {
      console.error("Failed to delete role", error);
      toast(error.message || "Unable to delete role.", "error");
    } finally {
      deleteBtn.classList.remove("opacity-60", "pointer-events-none");
    }
  });

  listContainer?.addEventListener("click", (evt) => {
    const target = evt.target.closest("button[data-action]");
    if (!target) return;
    const roleValue = target.dataset.role;
    if (!roleValue) return;
    const action = target.dataset.action;
    if (action === "reset") {
      evt.preventDefault();
      resetRoleRow(roleValue);
    } else if (action === "copy") {
      evt.preventDefault();
      copyRoleIdentifier(roleValue);
    }
  });

  searchInput?.addEventListener("input", (evt) => {
    const value = evt.target.value;
    state.search = value.trim();
    if (searchDebounce) window.clearTimeout(searchDebounce);
    searchDebounce = window.setTimeout(() => {
      renderRoles();
    }, 150);
  });

  sortSelect?.addEventListener("change", (evt) => {
    state.sort = evt.target.value || "asc";
    renderRoles();
  });

  window.addEventListener("beforeunload", (evt) => {
    if (!state.dirty) return;
    evt.preventDefault();
    evt.returnValue = "";
  });

  loadRoles();
})();
