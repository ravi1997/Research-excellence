(function () {
  "use strict";

  class RoleStudioPage {
    constructor() {
      this.basePath = "";

      // Core nodes
      this.tableBody = document.getElementById("roleTable");
      if (!this.tableBody) return;

      this.form = document.getElementById("roleForm");
      this.loadingBanner = document.getElementById("roleLoading");
      this.errorBanner = document.getElementById("roleError");
      this.errorMessage = document.getElementById("roleErrorMessage");
      this.retryBtn = document.getElementById("roleRetry");

      // Filters
      this.searchInput = document.getElementById("roleSearch");
      this.sortSelect = document.getElementById("roleSort");
      this.resultBadge = document.getElementById("roleResultBadge");

      // Metrics
      this.metricTotal = document.getElementById("roleMetricTotal");
      this.metricDocumented = document.getElementById("roleMetricDocumented");
      this.metricSync = document.getElementById("roleMetricSync");

      // Metadata actions
      this.saveBtn = document.getElementById("roleSave");
      this.resetBtn = document.getElementById("roleReset");
      this.dirtyIndicator = document.getElementById("roleDirty");

      // Creation panel
      this.newIdInput = document.getElementById("roleNewId");
      this.newLabelInput = document.getElementById("roleNewLabel");
      this.newDescriptionInput = document.getElementById("roleNewDescription");
      this.createBtn = document.getElementById("roleCreate");
      this.removeBtn = document.getElementById("roleRemove");

      // Toast helper
      this.toast =
        window.researchPortal?.showToast ||
        ((message, type = "info") => {
          const log = type === "error" ? console.error : console.log;
          log(`[RoleStudio] ${message}`);
        });

      this.searchDebounce = null;
      this.state = {
        roles: [],
        metadata: {},
        drafts: {},
        search: "",
        sort: "identifier-asc",
        lastSync: null,
        dirty: false,
      };

      this.init();
    }

    init() {
      this.bindEvents();
      this.loadRoles();
    }

    bindEvents() {
      this.retryBtn?.addEventListener("click", () => {
        this.hideError();
        this.loadRoles();
      });

      this.form?.addEventListener("submit", (evt) => {
        evt.preventDefault();
        this.saveMetadata();
      });

      this.tableBody.addEventListener("input", (evt) => {
        const target = evt.target;
        if (!target) return;
        const roleValue = target.closest("[data-role-row]")?.dataset.roleRow;
        const field = target.dataset.roleField;
        if (!roleValue || !field) return;
        this.captureDraftForRole(roleValue);
      });

      this.tableBody.addEventListener("click", (evt) => {
        const actionBtn = evt.target.closest("button[data-role-action]");
        if (!actionBtn) return;
        evt.preventDefault();
        const { roleAction: action, roleValue } = actionBtn.dataset;
        if (!roleValue) return;
        if (action === "reset") {
          this.resetRow(roleValue);
        } else if (action === "copy") {
          this.copyIdentifier(roleValue);
        }
      });

      this.resetBtn?.addEventListener("click", (evt) => {
        evt.preventDefault();
        this.resetAllMetadata();
      });

      this.searchInput?.addEventListener("input", (evt) => {
        const value = evt.target.value || "";
        this.state.search = value.trim();
        if (this.searchDebounce) window.clearTimeout(this.searchDebounce);
        this.searchDebounce = window.setTimeout(() => this.renderTable(), 180);
      });

      this.sortSelect?.addEventListener("change", (evt) => {
        this.state.sort = evt.target.value || "identifier-asc";
        this.renderTable();
      });

      this.createBtn?.addEventListener("click", () => this.createRole());
      this.removeBtn?.addEventListener("click", () => this.deleteRole());

      window.addEventListener("beforeunload", (evt) => {
        if (!this.state.dirty) return;
        evt.preventDefault();
        evt.returnValue = "";
      });
    }

    /* ---------- Helpers ---------- */

    authHeader() {
      const token =
        localStorage.getItem("access_token") ||
        localStorage.getItem("token") ||
        sessionStorage.getItem("authToken") ||
        "";
      return token ? { Authorization: `Bearer ${token}` } : {};
    }

    jsonHeaders() {
      return { "Content-Type": "application/json", ...this.authHeader() };
    }

    showLoading(show) {
      if (!this.loadingBanner) return;
      this.loadingBanner.classList.toggle("hidden", !show);
    }

    showError(message) {
      if (!this.errorBanner) return;
      if (this.errorMessage) this.errorMessage.textContent = message || "Unexpected error encountered.";
      this.errorBanner.classList.remove("hidden");
    }

    hideError() {
      this.errorBanner?.classList.add("hidden");
    }

    setDirty(isDirty) {
      this.state.dirty = Boolean(isDirty);
      this.dirtyIndicator?.classList.toggle("hidden", !this.state.dirty);
    }

    /* ---------- Data fetching ---------- */

    async loadRoles() {
      this.hideError();
      this.showLoading(true);
      this.form?.classList.add("hidden");
      this.state.drafts = {};
      this.setDirty(false);

      try {
        const response = await fetch(`${this.basePath}/api/v1/user_roles/available`, {
          headers: this.authHeader(),
        });
        if (!response.ok) throw new Error(`Failed with status ${response.status}`);
        const data = await response.json();
        this.state.roles = Array.isArray(data.items) ? data.items : [];
        this.form?.classList.remove("hidden");
        this.renderTable({ skipDraftCapture: true });
        await this.loadMetadata();
        this.state.lastSync = new Date();
        this.updateMetrics();
      } catch (error) {
        console.error("Failed to load roles", error);
        this.showError("Unable to load role catalogue. Try again shortly.");
      } finally {
        this.showLoading(false);
      }
    }

    async loadMetadata() {
      try {
        const response = await fetch(`${this.basePath}/api/v1/user_roles/metadata`, {
          headers: this.authHeader(),
        });
        if (!response.ok) throw new Error(`Failed with status ${response.status}`);
        const data = await response.json();
        this.state.metadata = data.items || {};
      } catch (error) {
        console.error("Failed to load metadata", error);
        this.state.metadata = {};
        this.toast("Unable to load metadata, using defaults.", "warn");
      } finally {
        this.state.drafts = {};
        this.setDirty(false);
        this.renderTable({ skipDraftCapture: true });
      }
    }

    /* ---------- Rendering ---------- */

    renderTable(options = {}) {
      const { skipDraftCapture = false } = options;
      if (!skipDraftCapture) this.captureDrafts();

      this.tableBody.innerHTML = "";
      const roles = this.getRenderableRoles();

      if (!this.state.roles.length) {
        this.tableBody.appendChild(this.emptyRow("No system roles were returned."));
        this.updateMetrics();
        return;
      }

      if (!roles.length) {
        this.tableBody.appendChild(this.emptyRow("No roles match the current filters."));
        this.updateMetrics();
        return;
      }

      const fragment = document.createDocumentFragment();
      roles.forEach((role) => fragment.appendChild(this.buildRow(role)));
      this.tableBody.appendChild(fragment);
      this.updateMetrics();
    }

    buildRow(role) {
      const { value, enum: enumName, protected: locked } = role;
      const displayValues = this.getDisplayValues(value);

      const row = document.createElement("tr");
      row.dataset.roleRow = value;
      row.className = "align-top";

      const indicatorClass =
        displayValues.hasPersisted || displayValues.hasDraftChanges
          ? "bg-blue-500"
          : "bg-gray-400 dark:bg-gray-600";

      row.innerHTML = `
        <td class="px-4 py-4 align-top">
          <div class="flex items-start gap-3">
            <span class="mt-1 inline-flex h-2.5 w-2.5 flex-shrink-0 rounded-full ${indicatorClass}" data-role-indicator="${this.escape(value)}"></span>
            <div>
              <p class="font-mono text-sm font-semibold text-gray-900 dark:text-gray-100">${this.escape(value)}</p>
              <div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400 flex items-center gap-2">
                <span>Enum: ${this.escape(enumName || value)}</span>
                ${locked ? '<span class="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-500/20 dark:text-amber-200">Protected</span>' : ""}
              </div>
            </div>
          </div>
        </td>
        <td class="px-4 py-4 align-top">
          <label class="sr-only" for="label-${this.escape(value)}">Display label</label>
          <input id="label-${this.escape(value)}" type="text" data-role-field="label" value="${this.escape(displayValues.label)}"
            class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100">
        </td>
        <td class="px-4 py-4 align-top">
          <label class="sr-only" for="description-${this.escape(value)}">Description</label>
          <textarea id="description-${this.escape(value)}" rows="3" data-role-field="description"
            class="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100">${this.escape(displayValues.description)}</textarea>
        </td>
        <td class="px-4 py-4 text-right align-top">
          <div class="inline-flex flex-col gap-2 sm:flex-row sm:justify-end">
            <button type="button" data-role-action="reset" data-role-value="${this.escape(value)}"
              class="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
              Reset
            </button>
            <button type="button" data-role-action="copy" data-role-value="${this.escape(value)}"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900">
              Copy ID
            </button>
          </div>
        </td>`;

      return row;
    }

    emptyRow(message) {
      const row = document.createElement("tr");
      row.innerHTML = `<td colspan="4" class="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-300">${message}</td>`;
      return row;
    }

    updateMetrics() {
      const total = this.state.roles.length;
      const documented = this.state.roles.reduce((count, role) => {
        const meta = this.state.metadata[role.value] || {};
        return meta.label?.trim() || meta.description?.trim() ? count + 1 : count;
      }, 0);

      if (this.metricTotal) this.metricTotal.textContent = this.formatCount(total, "role");
      if (this.metricDocumented) this.metricDocumented.textContent = this.formatCount(documented, "role");
      if (this.metricSync) {
        this.metricSync.textContent = this.state.lastSync
          ? this.state.lastSync.toLocaleString()
          : "Awaiting sync…";
      }

      if (this.resultBadge) {
        const filtered = this.getRenderableRoles().length;
        this.resultBadge.textContent =
          total === filtered
            ? this.formatCount(total, "role")
            : `Showing ${filtered.toLocaleString()} of ${total.toLocaleString()} roles`;
      }
    }

    formatCount(value, noun) {
      const count = Number(value) || 0;
      const label = noun || "item";
      return `${count.toLocaleString()} ${count === 1 ? label : `${label}s`}`;
    }

    /* ---------- Draft handling ---------- */

    captureDrafts() {
      const rows = this.tableBody.querySelectorAll("tr[data-role-row]");
      rows.forEach((row) => {
        this.captureDraftForRole(row.dataset.roleRow);
      });
    }

    captureDraftForRole(roleValue) {
      if (!roleValue) return;
      const inputs = this.tableBody.querySelectorAll(
        `tr[data-role-row="${this.cssEscape(roleValue)}"] [data-role-field]`
      );
      if (!inputs.length) return;

      const entry = { label: "", description: "" };
      inputs.forEach((input) => {
        if (input.dataset.roleField === "label") entry.label = input.value;
        if (input.dataset.roleField === "description") entry.description = input.value;
      });

      const base = this.getBaseValues(roleValue);
      if (entry.label === base.label && entry.description === base.description) {
        delete this.state.drafts[roleValue];
      } else {
        this.state.drafts[roleValue] = entry;
      }

      this.setDirty(Object.keys(this.state.drafts).length > 0);
      this.updateIndicator(roleValue, entry, base);
    }

    updateIndicator(roleValue, draftEntry, baseValues) {
      const indicator = this.tableBody.querySelector(
        `[data-role-indicator="${this.cssEscape(roleValue)}"]`
      );
      if (!indicator) return;

      const persisted = this.state.metadata[roleValue] || {};
      const hasPersisted = Boolean(persisted.label?.trim() || persisted.description?.trim());
      const hasDraft =
        (draftEntry?.label ?? baseValues.label) !== baseValues.label ||
        (draftEntry?.description ?? baseValues.description) !== baseValues.description;

      indicator.classList.remove("bg-blue-500", "bg-gray-400", "dark:bg-gray-600");
      indicator.classList.add(hasPersisted || hasDraft ? "bg-blue-500" : "bg-gray-400", "dark:bg-gray-600");
    }

    resetRow(roleValue) {
      const base = this.getBaseValues(roleValue);
      const row = this.tableBody.querySelector(`tr[data-role-row="${this.cssEscape(roleValue)}"]`);
      if (!row) return;
      row.querySelectorAll("[data-role-field]").forEach((input) => {
        if (input.dataset.roleField === "label") input.value = base.label;
        if (input.dataset.roleField === "description") input.value = base.description;
      });
      delete this.state.drafts[roleValue];
      this.setDirty(Object.keys(this.state.drafts).length > 0);
      this.updateIndicator(roleValue, null, base);
    }

    resetAllMetadata() {
      this.state.drafts = {};
      this.setDirty(false);
      this.renderTable({ skipDraftCapture: true });
    }

    /* ---------- Snapshot helpers ---------- */

    getRenderableRoles() {
      let roles = Array.isArray(this.state.roles) ? [...this.state.roles] : [];

      if (this.state.search) {
        const query = this.state.search.toLowerCase();
        roles = roles.filter((role) => {
          const value = (role.value || "").toLowerCase();
          const display = this.getDisplayValues(role.value);
          return (
            value.includes(query) ||
            (display.label || "").toLowerCase().includes(query) ||
            (display.description || "").toLowerCase().includes(query)
          );
        });
      }

      roles.sort((a, b) => this.compareRoles(a, b, this.state.sort));
      return roles;
    }

    compareRoles(a, b, sortKey) {
      const valueA = (a.value || "").toLowerCase();
      const valueB = (b.value || "").toLowerCase();
      const labelA = (this.getDisplayValues(a.value).label || "").toLowerCase();
      const labelB = (this.getDisplayValues(b.value).label || "").toLowerCase();

      switch (sortKey) {
        case "identifier-desc":
          return valueB.localeCompare(valueA, undefined, { sensitivity: "base" });
        case "label-asc":
          return labelA.localeCompare(labelB, undefined, { sensitivity: "base" });
        case "label-desc":
          return labelB.localeCompare(labelA, undefined, { sensitivity: "base" });
        case "identifier-asc":
        default:
          return valueA.localeCompare(valueB, undefined, { sensitivity: "base" });
      }
    }

    getBaseValues(roleValue) {
      const role = this.state.roles.find((item) => item.value === roleValue) || {};
      const meta = this.state.metadata[roleValue] || {};
      const label = meta.label?.trim() || this.prettify(role.value);
      const description = meta.description?.trim() || "";
      return { label, description };
    }

    getDisplayValues(roleValue) {
      const base = this.getBaseValues(roleValue);
      const draft = this.state.drafts[roleValue];
      const label = draft?.label ?? base.label;
      const description = draft?.description ?? base.description;
      return {
        label,
        description,
        hasPersisted: Boolean(
          this.state.metadata[roleValue]?.label?.trim() || this.state.metadata[roleValue]?.description?.trim()
        ),
        hasDraftChanges: label !== base.label || description !== base.description,
      };
    }

    prettify(identifier = "") {
      return identifier
        .split(/[_-]/g)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
    }

    escape(value) {
      if (value == null) return "";
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    cssEscape(value) {
      const str = String(value ?? "");
      if (window.CSS?.escape) return window.CSS.escape(str);
      return str.replace(/[^A-Za-z0-9_-]/g, (char) => {
        if (char === " ") return "\\ ";
        const hex = char.codePointAt(0).toString(16);
        return `\\${hex} `;
      });
    }

    /* ---------- Actions ---------- */

    async saveMetadata() {
      this.captureDrafts();
      const snapshot = {};

      this.state.roles.forEach((role) => {
      const row = this.tableBody.querySelector(`tr[data-role-row="${this.cssEscape(role.value)}"]`);
        if (!row) return;
        const label = row.querySelector('[data-role-field="label"]')?.value.trim() || "";
        const description = row.querySelector('[data-role-field="description"]')?.value.trim() || "";
        snapshot[role.value] = { label, description };
      });

      this.saveBtn?.classList.add("opacity-60", "pointer-events-none");

      try {
        const response = await fetch(`${this.basePath}/api/v1/user_roles/metadata`, {
          method: "PUT",
          headers: this.jsonHeaders(),
          body: JSON.stringify({ items: snapshot }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Failed with status ${response.status}`);
        this.state.metadata = data.items || {};
        this.state.drafts = {};
        this.setDirty(false);
        this.state.lastSync = new Date();
        this.renderTable({ skipDraftCapture: true });
        this.updateMetrics();
        this.toast("Role metadata saved.", "success");
      } catch (error) {
        console.error("Failed to save metadata", error);
        this.toast(error.message || "Unable to save metadata.", "error");
      } finally {
        this.saveBtn?.classList.remove("opacity-60", "pointer-events-none");
      }
    }

    async createRole() {
      const identifier = this.newIdInput?.value.trim();
      if (!identifier) {
        this.toast("Provide a role identifier before continuing.", "warn");
        return;
      }
      if (this.state.dirty) {
        this.toast("Save or reset metadata changes before adding a role.", "warn");
        return;
      }

      const payload = {
        action: "add",
        identifier,
        metadata: {
          label: this.newLabelInput?.value || "",
          description: this.newDescriptionInput?.value || "",
        },
      };

      this.createBtn?.classList.add("opacity-60", "pointer-events-none");
      try {
        const response = await fetch(`${this.basePath}/api/v1/user_roles/manage`, {
          method: "POST",
          headers: this.jsonHeaders(),
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Failed with status ${response.status}`);
        this.toast("Role added successfully.", "success");
        this.clearDesigner();
        await this.loadRoles();
      } catch (error) {
        console.error("Failed to add role", error);
        this.toast(error.message || "Unable to add role.", "error");
      } finally {
        this.createBtn?.classList.remove("opacity-60", "pointer-events-none");
      }
    }

    async deleteRole() {
      const identifier = this.newIdInput?.value.trim();
      if (!identifier) {
        this.toast("Provide a role identifier to delete.", "warn");
        return;
      }
      if (this.state.dirty) {
        this.toast("Save or reset metadata changes before deleting a role.", "warn");
        return;
      }

      if (!window.confirm(`Are you sure you want to delete the role '${identifier}'?`)) {
        return;
      }

      this.removeBtn?.classList.add("opacity-60", "pointer-events-none");
      try {
        const response = await fetch(`${this.basePath}/api/v1/user_roles/manage`, {
          method: "POST",
          headers: this.jsonHeaders(),
          body: JSON.stringify({ action: "delete", identifier }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `Failed with status ${response.status}`);
        this.toast("Role deleted successfully.", "success");
        this.clearDesigner();
        await this.loadRoles();
      } catch (error) {
        console.error("Failed to delete role", error);
        this.toast(error.message || "Unable to delete role.", "error");
      } finally {
        this.removeBtn?.classList.remove("opacity-60", "pointer-events-none");
      }
    }

    clearDesigner() {
      if (this.newIdInput) this.newIdInput.value = "";
      if (this.newLabelInput) this.newLabelInput.value = "";
      if (this.newDescriptionInput) this.newDescriptionInput.value = "";
    }

    async copyIdentifier(roleValue) {
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
        this.toast(`Copied '${roleValue}' to clipboard.`, "success");
      } catch (error) {
        console.error("Failed to copy identifier", error);
        this.toast("Unable to copy role identifier.", "error");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    new RoleStudioPage();
  });
})();
