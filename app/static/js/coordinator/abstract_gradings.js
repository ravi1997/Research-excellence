(function () {
  const BASE = "";

  const cycleFilter = document.getElementById("cycleFilter");
  const searchInput = document.getElementById("searchInput");
  const clearSearchBtn = document.getElementById("clearSearch");
  const phaseFilter = document.getElementById("phaseFilter");
  const statusFilter = document.getElementById("statusFilter");
  const refreshButton = document.getElementById("refreshButton");
  const exportButton = document.getElementById("exportButton");
  const abstractList = document.getElementById("abstractList");
  const abstractCount = document.getElementById("abstractCount");
  const gradingPanel = document.getElementById("gradingPanel");
  const prevPageBtn = document.getElementById("prevPage");
  const nextPageBtn = document.getElementById("nextPage");

  const state = {
    page: 1,
    pageSize: 10,
    total: 0,
    pages: 1,
    abstracts: [],
    cycles: new Map(),
    selectedAbstractId: null,
    gradingCache: new Map(),
    isLoading: false,
  };

  init();

  function init() {
    bindEvents();
    fetchCycles().finally(fetchAbstracts);
  }

  function bindEvents() {
    cycleFilter?.addEventListener("change", () => {
      state.page = 1;
      fetchAbstracts();
    });

    phaseFilter?.addEventListener("change", () => {
      state.page = 1;
      fetchAbstracts();
    });

    statusFilter?.addEventListener("change", () => {
      state.page = 1;
      fetchAbstracts();
    });

    if (searchInput) {
      searchInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          state.page = 1;
          fetchAbstracts();
        }
      });
      searchInput.addEventListener("input", () => {
        if (!searchInput.value) {
          state.page = 1;
          fetchAbstracts();
        }
      });
    }

    clearSearchBtn?.addEventListener("click", () => {
      if (!searchInput) return;
      searchInput.value = "";
      searchInput.dispatchEvent(new Event("input"));
    });

    refreshButton?.addEventListener("click", () => fetchAbstracts());
    exportButton?.addEventListener("click", () => exportAbstracts());

    prevPageBtn?.addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        fetchAbstracts();
      }
    });

    nextPageBtn?.addEventListener("click", () => {
      if (state.page < state.pages) {
        state.page += 1;
        fetchAbstracts();
      }
    });

    abstractList?.addEventListener("click", (event) => {
      const row = event.target.closest("[data-abstract-id]");
      if (!row) return;
      const abstractId = row.getAttribute("data-abstract-id");
      selectAbstract(abstractId);
    });
  }

  function authHeaders() {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    return token ? { Authorization: "Bearer " + token } : {};
  }

  async function fetchCycles() {
    if (!cycleFilter) return;
    try {
      const response = await fetch(`${BASE}/api/v1/research/cycles`, { headers: authHeaders() });
      if (!response.ok) {
        throw new Error(`Failed to load cycles ${response.status}`);
      }
      const data = await response.json();
      const cycles = Array.isArray(data) ? data : Array.isArray(data.items) ? data.items : [];
      state.cycles.clear();
      cycleFilter.innerHTML = `<option value="">All cycles</option>`;
      cycles.forEach((cycle) => {
        if (!cycle?.id) return;
        state.cycles.set(String(cycle.id), cycle);
        const option = document.createElement("option");
        option.value = cycle.id;
        option.textContent = `${cycle.name || "Untitled"} (${formatDateRange(cycle.start_date, cycle.end_date)})`;
        cycleFilter.appendChild(option);
      });
    } catch (error) {
      console.error("Unable to load cycles", error);
      cycleFilter.innerHTML = `<option value="">Unable to load cycles</option>`;
    }
  }

  async function fetchAbstracts() {
    if (!abstractList) return;
    state.isLoading = true;
    renderAbstracts();
    try {
      const params = new URLSearchParams({
        page: state.page,
        page_size: state.pageSize,
        sort: "created_at",
        dir: "desc",
      });
      if (searchInput?.value) params.set("q", searchInput.value.trim());
      if (phaseFilter?.value) params.set("review_phase", phaseFilter.value);
      if (statusFilter?.value) params.set("status", statusFilter.value);
      if (cycleFilter?.value) params.set("cycle_id", cycleFilter.value);

      const response = await fetch(`${BASE}/api/v1/research/abstracts?${params.toString()}`, {
        headers: authHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to load abstracts ${response.status}`);
      }
      const data = await response.json();
      const items = Array.isArray(data.items) ? data.items : [];
      state.abstracts = items;
      state.total = data.total ?? items.length ?? 0;
      state.page = data.page ?? state.page;
      state.pages = data.pages ?? 1;
      state.isLoading = false;
      renderAbstracts();
      updatePagination();
    } catch (error) {
      console.error("Unable to load abstracts", error);
      abstractList.innerHTML =
        `<div class="p-5 text-sm text-red-600 dark:text-red-300">Failed to load abstracts. ${escapeHtml(error.message || "")}</div>`;
      state.abstracts = [];
      state.total = 0;
      updatePagination();
    } finally {
      state.isLoading = false;
    }
  }

  async function exportAbstracts() {

    const response = await fetch(`${BASE}/api/v1/research/abstracts/export-with-grades`, {
      method: 'GET',
      headers: authHeaders()
    });

    if (!response.ok) {
      throw new Error(`Failed to load abstracts ${response.status}`);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = 'abstracts_with_gradings.xlsx';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

  }


  function renderAbstracts() {
    if (!abstractList) return;
    if (state.isLoading) {
      abstractList.innerHTML =
        `<div class="p-5 text-sm text-gray-500 dark:text-gray-400 animate-pulse">Loading abstracts...</div>`;
      return;
    }

    if (!state.abstracts.length) {
      abstractList.innerHTML =
        `<div class="p-5 text-sm text-gray-500 dark:text-gray-400">No abstracts match the current filters.</div>`;
      abstractCount && (abstractCount.textContent = "0");
      return;
    }

    abstractCount && (abstractCount.textContent = String(state.total));

    const rows = state.abstracts
      .map((abstract) => {
        const isSelected = state.selectedAbstractId === String(abstract.id);
        const cycleName = state.cycles.get(String(abstract.cycle_id))?.name || "Unassigned";
        const badge = statusBadge(abstract.status);
        const category = abstract.category?.name || "Uncategorized";
        const number = abstract.abstract_number ? `#${abstract.abstract_number}` : "—";
        const reviewers = (abstract.verifiers_count ?? ((abstract.verifiers || []).length)) || 0;
        const phase = abstract.review_phase ?? "—";
        return `
          <button data-abstract-id="${escapeAttr(abstract.id)}" class="w-full text-left transition ${isSelected ? "bg-blue-50 dark:bg-blue-500/10" : "hover:bg-gray-50 dark:hover:bg-gray-800/40"} focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500">
            <div class="px-5 py-4 space-y-2">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">${escapeHtml(number)} · ${escapeHtml(category)}</p>
                  <h3 class="text-base font-semibold text-gray-900 dark:text-white line-clamp-2">${escapeHtml(abstract.title || "Untitled abstract")}</h3>
                </div>
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.class}">${badge.label}</span>
              </div>
              <dl class="grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
                <div>
                  <dt class="font-semibold text-gray-600 dark:text-gray-300">Cycle</dt>
                  <dd>${escapeHtml(cycleName)}</dd>
                </div>
                <div>
                  <dt class="font-semibold text-gray-600 dark:text-gray-300">Review phase</dt>
                  <dd>Phase ${escapeHtml(String(phase))}</dd>
                </div>
                <div>
                  <dt class="font-semibold text-gray-600 dark:text-gray-300">Verifiers</dt>
                  <dd>${escapeHtml(String(reviewers))}</dd>
                </div>
                <div>
                  <dt class="font-semibold text-gray-600 dark:text-gray-300">Updated</dt>
                  <dd>${formatDate(abstract.updated_at) || "—"}</dd>
                </div>
              </dl>
            </div>
          </button>`;
      })
      .join("");

    abstractList.innerHTML = rows;
  }

  function updatePagination() {
    if (prevPageBtn) {
      prevPageBtn.disabled = state.page <= 1;
    }
    if (nextPageBtn) {
      nextPageBtn.disabled = state.page >= state.pages;
    }
  }

  function selectAbstract(abstractId) {
    if (!abstractId) return;
    if (state.selectedAbstractId === abstractId) return;
    state.selectedAbstractId = abstractId;
    renderAbstracts();
    fetchGradings(abstractId);
  }

  async function fetchGradings(abstractId) {
    if (!gradingPanel) return;
    const selected = state.abstracts.find((item) => String(item.id) === String(abstractId));
    gradingPanel.innerHTML = `
      <div class="space-y-3">
        <div>
          <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Abstract</p>
          <p class="text-base font-semibold text-gray-900 dark:text-white">${escapeHtml(selected?.title || "Untitled abstract")}</p>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400">Loading gradings…</p>
      </div>
    `;

    if (state.gradingCache.has(abstractId)) {
      renderGradings(state.gradingCache.get(abstractId), selected);
      return;
    }

    try {
      const response = await fetch(`${BASE}/api/v1/research/abstracts/${abstractId}/gradings`, {
        headers: authHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Failed to load gradings ${response.status}`);
      }
      const gradings = await response.json();
      state.gradingCache.set(abstractId, gradings);
      renderGradings(gradings, selected);
    } catch (error) {
      console.error("Unable to load gradings", error);
      gradingPanel.innerHTML = `<div class="space-y-3">
        <div>
          <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Abstract</p>
          <p class="text-base font-semibold text-gray-900 dark:text-white">${escapeHtml(selected?.title || "Untitled abstract")}</p>
        </div>
        <p class="text-sm text-red-600 dark:text-red-300">Failed to load gradings (${escapeHtml(error.message || "unknown error")}).</p>
      </div>`;
    }
  }

  function renderGradings(gradings, abstract) {
    if (!gradingPanel) return;
    const cycleName = state.cycles.get(String(abstract?.cycle_id))?.name || "Unassigned";
    const summary = buildGradingSummary(gradings || []);

    if (!gradings || !gradings.length) {
      gradingPanel.innerHTML = `
        <div class="space-y-3">
          ${abstractDetailsMarkup(abstract, cycleName)}
          <div class="rounded-2xl border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
            No gradings have been submitted for this abstract yet.
          </div>
        </div>
      `;
      return;
    }

    const phaseTables = buildPhaseTables(gradings || []);
    const tablesMarkup = phaseTables.length
      ? phaseTables.join("")
      : `<div class="rounded-2xl border border-dashed border-gray-300 p-4 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
          No grading details are available.
        </div>`;

    gradingPanel.innerHTML = `
      <div class="space-y-4">
        ${abstractDetailsMarkup(abstract, cycleName)}
        <div class="rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300">
          <p class="font-semibold text-gray-900 dark:text-white">${escapeHtml(summary)}</p>
        </div>
        <div class="space-y-4">${tablesMarkup}</div>
      </div>
    `;
  }

  function buildPhaseTables(gradings) {
    const phaseMap = new Map();

    gradings.forEach((grading) => {
      const phase = grading.review_phase ?? 1;
      const phaseKey = String(phase);
      if (!phaseMap.has(phaseKey)) {
        phaseMap.set(phaseKey, {
          columns: [],
          columnSet: new Set(),
          rows: new Map(),
        });
      }
      const phaseData = phaseMap.get(phaseKey);

      const criteria = grading.grading_type?.criteria || "Unnamed criteria";
      if (!phaseData.columnSet.has(criteria)) {
        phaseData.columnSet.add(criteria);
        phaseData.columns.push(criteria);
      }

      const verifierId = grading.graded_by?.id || `unknown-${phaseData.rows.size}`;
      if (!phaseData.rows.has(verifierId)) {
        phaseData.rows.set(verifierId, {
          verifier: grading.graded_by,
          grades: new Map(),
        });
      }

      phaseData.rows.get(verifierId).grades.set(criteria, grading);
    });

    return Array.from(phaseMap.entries())
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .map(([phaseKey, phaseData]) => renderPhaseTable(phaseKey, phaseData));
  }

  function renderPhaseTable(phaseKey, phaseData) {
    const columns = phaseData.columns;
    const rows = Array.from(phaseData.rows.values());
    const headerCols = columns
      .map(
        (label) => `<th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          ${escapeHtml(label)}
        </th>`
      )
      .join("") + `<th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Total</th>`;

    const bodyRows = rows.length
      ? rows
          .map((row) => {
            const verifierName =
              row.verifier?.full_name ||
              row.verifier?.username ||
              row.verifier?.email ||
              "Unknown verifier";
            const verifierDetail = row.verifier?.email || row.verifier?.username || "";
            const cells = columns
              .map((criteria) => {
                const grade = row.grades.get(criteria);
                if (!grade) {
                  return `<td class="px-3 py-3 text-sm text-gray-500 dark:text-gray-400">—</td>`;
                }
                const scoreMax = grade.grading_type?.max_score;
                const scoreText = `${escapeHtml(String(grade.score))}${
                  scoreMax ? ` / ${escapeHtml(String(scoreMax))}` : ""
                }`;
                const comment = grade.comments
                  ? `<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">${escapeHtml(grade.comments)}</p>`
                  : "";
                const recorded = formatDate(grade.graded_on || grade.created_at);
                return `<td class="px-3 py-3 align-top text-sm text-gray-900 dark:text-gray-100">
                  <div class="font-semibold">${scoreText}</div>
                  ${recorded ? `<p class="text-[11px] text-gray-500 dark:text-gray-400">${escapeHtml(recorded)}</p>` : ""}
                  ${comment}
                </td>`;
              })
              .join("");

            // Calculate total numeric score for this row (sum of available numeric scores)
            let total = 0;
            let hasNumeric = false;
            for (const criteria of columns) {
              const grade = row.grades.get(criteria);
              if (grade && typeof grade.score === 'number') {
                total += Number(grade.score);
                hasNumeric = true;
              }
            }
            const totalCell = `<td class="px-3 py-3 align-top text-sm"><div class="font-semibold">${hasNumeric ? escapeHtml(String(total)) : "—"}</div></td>`;
                return `
              <tr class="border-t border-gray-100 dark:border-gray-800">
                <td class="px-3 py-3 align-top text-sm">
                  <p class="font-semibold text-gray-900 dark:text-white">${escapeHtml(verifierName)}</p>
                  ${verifierDetail ? `<p class="text-xs text-gray-500 dark:text-gray-400">${escapeHtml(verifierDetail)}</p>` : ""}
                </td>
                ${cells}
                ${totalCell}
              </tr>
            `;
          })
          .join("")
      : `<tr><td colspan="${columns.length + 1}" class="px-3 py-3 text-sm text-gray-500 dark:text-gray-400">No gradings recorded for this phase.</td></tr>`;

    return `
      <section class="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950/40">
        <div class="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Review phase</p>
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">Phase ${escapeHtml(phaseKey)}</h3>
          </div>
          <span class="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-500/10 dark:text-blue-200">
            ${rows.length} verifier${rows.length === 1 ? "" : "s"}
          </span>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-100 text-sm dark:divide-gray-800">
            <thead class="bg-gray-50 dark:bg-gray-900/60">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Verifier</th>
                ${headerCols}
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-950/20">
              ${bodyRows}
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  function abstractDetailsMarkup(abstract, cycleName) {
    if (!abstract) return "";
    const category = abstract.category?.name || "Uncategorized";
    const status = statusBadge(abstract.status);
    return `
      <div class="space-y-2">
        <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">${escapeHtml(category)} · ${cycleName ? escapeHtml(cycleName) : "No cycle"}</p>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${escapeHtml(abstract.title || "Untitled abstract")}</h3>
        <div class="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span class="inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold ${status.class}">${status.label}</span>
          <span class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-200">Phase ${escapeHtml(String(abstract.review_phase ?? "—"))}</span>
          <span class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-200">${(abstract.verifiers_count ?? ((abstract.verifiers || []).length)) || 0} verifier(s)</span>
        </div>
      </div>
    `;
  }

  function buildGradingSummary(gradings) {
    if (!gradings.length) return "No gradings recorded.";
    const scores = gradings.map((g) => g.score).filter((s) => typeof s === "number");
    if (!scores.length) return `${gradings.length} gradings recorded.`;
    const total = scores.reduce((sum, value) => sum + value, 0);
    const average = (total / scores.length).toFixed(1);
    const maxScore = Math.max(...scores);
    const minScore = Math.min(...scores);
    return `${gradings.length} grading${gradings.length === 1 ? "" : "s"} · Avg ${average} · High ${maxScore} · Low ${minScore}`;
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  function formatDateRange(start, end) {
    if (!start && !end) return "dates TBD";
    const startDate = start ? new Date(start) : null;
    const endDate = end ? new Date(end) : null;
    const startStr = startDate && !Number.isNaN(startDate.getTime()) ? startDate.toLocaleDateString() : "TBD";
    const endStr = endDate && !Number.isNaN(endDate.getTime()) ? endDate.toLocaleDateString() : "TBD";
    return `${startStr} – ${endStr}`;
  }

  function statusBadge(status) {
    const normalized = String(status || "").toUpperCase();
    switch (normalized) {
      case "STATUS.ACCEPTED":
        return { label: "Accepted", class: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200" };
      case "STATUS.REJECTED":
        return { label: "Rejected", class: "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-200" };
      case "STATUS.UNDER_REVIEW":
        return { label: "Under review", class: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-200" };
      default:
        return { label: "Pending", class: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200" };
    }
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }
})();
