
/* abstract_submit_list.js - abstract page adapter using SubmitList
 * This version preserves previous function names/behaviors:
 *   - window.searchAbstracts(query?)
 *   - window.changeAbstractPage(deltaOrNumber)
 *   - window.updateAbstractMeta()
 */
(function () {
    "use strict";
    const { utils, init } = window.SubmitList;
    const { fetchJSON, escapeHtml, formatDate, getStatusClass, toast } = utils;

    // ---- Endpoints (adjust if needed) ----
    const API_LIST = "/api/v1/research/abstracts";
    const API_ONE = (id) => `/api/v1/research/abstracts/${encodeURIComponent(id)}`;
    const API_META1 = "/api/v1/research/abstracts/meta";        // preferred
    const API_META2 = "/api/v1/research/abstracts/status";      // alternate
    // Fallback strategy: try META1 -> META2 -> derive from list(meta)

    // ---- Render each list item ----
    function renderItem(item) {
        const li = document.createElement("li");
        li.className = "p-3 hover:bg-white/60 dark:hover:bg-gray-800/60 cursor-pointer flex items-start gap-3";
        li.innerHTML = `
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-3">
          <h4 class="font-semibold truncate">${escapeHtml(item.title || "Untitled")}</h4>
          <span class="badge text-xs px-2 py-0.5 ${getStatusClass(item.status)}">${escapeHtml(item.status || "")}</span>
        </div>
        <div class="text-xs muted mt-1 truncate">
          #${escapeHtml(item.id)} · ${escapeHtml(item.category || "-")} · ${escapeHtml(item.author || "-")}
        </div>
      </div>
      <div class="text-xs whitespace-nowrap ml-2">${escapeHtml(formatDate(item.created_at))}</div>
    `;
        return li;
    }

    // ---- Fetch a page (server params kept compatible) ----
    async function fetchPage({ page, pageSize, sortKey, sortDir, filter, query }) {
        const data = await fetchJSON(API_LIST, {
            q: query, status: filter, sort: sortKey || "created_at", dir: sortDir || "desc", page, size: pageSize
        });
        return { items: data.items || [], total: data.total ?? 0, totalPages: data.total_pages ?? 1, meta: data.meta || {} };
    }

    // ---- Fill details on select ----
    async function onSelect(item, ctx) {
        try {
            const full = await fetchJSON(API_ONE(item.id));
            ctx.setDetails({
                title: full.title || item.title,
                category: full.category || item.category || "",
                status: full.status || item.status || "",
                number: full.abstract_number || full.number || item.number || "",
                author: full.author || item.author || "",
                date: formatDate(full.created_at || item.created_at),
                previewHtml: `<div class="p-3 text-sm muted">Loading preview…</div>`
            });

            // Prefer embedded iframe preview to avoid worker wiring; switch to pdf.js if needed.
            const pdfUrl = full.pdf_url || full.file_url || item.pdf_url;
            if (pdfUrl) {
                ctx.previewEl.innerHTML = `<iframe class="w-full h-[70vh]" src="${pdfUrl}" loading="lazy"></iframe>`;
            } else {
                ctx.previewEl.innerHTML = `<div class="p-3 text-sm muted">No PDF attached.</div>`;
            }
        } catch (e) {
            console.error("Detail load error:", e);
            ctx.setDetails({ previewHtml: `<div class="p-3 text-sm text-red-600 dark:text-red-400">Failed to load details.</div>` });
        }
    }

    // ---- Initialize controller ----
    const ctrl = init({
        listEl: "#List",
        searchInputEl: "#abstractSearch",
        searchBtnEl: "#SearchBtn",
        statusGroupEl: "#StatusGroup",
        sortGroupEl: "#SortGroup",
        prevBtnEl: "#Prev",
        nextBtnEl: "#Next",
        pageInfoEl: "#PageInfo",
        statsEl: "#Stats",
        pageSizeGroupEl: "#PageSizeGroup",
        globalLoadingEl: "#globalLoading",
        details: {
            containerEl: "#Details",
            noSelectedEl: "#noSelected",
            contentEl: "#Content",
            previewEl: "#preview-content",
            titleEl: "#summaryTitle",
            categoryEl: "#summaryCategory",
            statusEl: "#summaryStatus",
            numberEl: "#summaryNumber",
            authorEl: "#summaryAuthor",
            dateEl: "#summaryDate",
        },
        // Keep the counters identical to old page
        statsMap: { total: "#statTotal", pending: "#statPending", accepted: "#statAccepted", rejected: "#statRejected" },
        fetchPage,
        renderItem,
        onSelect
    });

    // ---- Backward-compatible function names ----

    // searchAbstracts(query?) — keeps old external triggers working
    window.searchAbstracts = function (query) {
        if (typeof query === "string") {
            const input = document.querySelector("#abstractSearch");
            if (input) input.value = query;
            ctrl.state.query = query.trim();
            ctrl.state.page = 1;
            ctrl.refresh();
            return;
        }
        // If no arg, read from input
        const input = document.querySelector("#abstractSearch");
        ctrl.state.query = (input?.value || "").trim();
        ctrl.state.page = 1;
        ctrl.refresh();
    };

    // changeAbstractPage(deltaOrNumber) — accepts +1/-1 or absolute number
    window.changeAbstractPage = function (deltaOrNumber) {
        const s = ctrl.state;
        if (typeof deltaOrNumber === "number") {
            if (Number.isInteger(deltaOrNumber) && Math.abs(deltaOrNumber) <= 2 && deltaOrNumber !== 0) {
                // treat small ints like delta for compatibility
                s.page = Math.min(Math.max(1, s.page + deltaOrNumber), s.totalPages);
            } else {
                s.page = Math.min(Math.max(1, deltaOrNumber), s.totalPages);
            }
        } else if (typeof deltaOrNumber === "string") {
            if (deltaOrNumber === "next") s.page = Math.min(s.page + 1, s.totalPages);
            else if (deltaOrNumber === "prev") s.page = Math.max(s.page - 1, 1);
        }
        ctrl.refresh();
    };

    // updateAbstractMeta() — tries dedicated endpoints, then list(meta) fallback
    window.updateAbstractMeta = async function () {
        try {
            // preferred
            try {
                const m = await fetchJSON(API_META1);
                applyMeta(m);
                return;
            } catch (_) { }

            // alternate
            try {
                const m = await fetchJSON(API_META2);
                applyMeta(m);
                return;
            } catch (_) { }

            // fallback: hit list API with tiny page to get meta
            const data = await fetchJSON(API_LIST, { page: 1, size: 1 });
            applyMeta(data.meta || {});
        } catch (e) {
            console.error("updateAbstractMeta failed", e);
            toast("Failed to refresh counters", "bg-red-600 text-white");
        }
    };

    function applyMeta(meta) {
        const map = {
            total: "#statTotal",
            pending: "#statPending",
            accepted: "#statAccepted",
            rejected: "#statRejected",
        };
        Object.entries(map).forEach(([k, sel]) => {
            const el = document.querySelector(sel);
            if (el && meta[k] != null) el.textContent = String(meta[k]);
        });
        const stats = document.querySelector("#Stats");
        if (stats && meta.total != null) stats.textContent = `${meta.total} item(s)`;
    }

    // Expose controller for debugging (optional)
    window.__abstractListCtrl = ctrl;

    // Initial meta refresh (optional; safe if your page used to do it)
    window.updateAbstractMeta();
})();


/* --- Compatibility shim: expose previous function names so old code keeps working --- */
(function () {
    try {
        const u = (window.SubmitList && window.SubmitList.utils) || {};
        const ctrl = window.__abstractListCtrl;

        // Map utils directly
        window.escapeHtml = u.escapeHtml;
        window.formatDate = u.formatDate;
        window.fetchJSON = u.fetchJSON;
        window.headers = u.headers;
        window.token = u.token;
        window.toast = u.toast;
        window.getStatusClass = u.getStatusClass;
        window.applySortStyles = u.applySortStyles;
        window.highlightSelection = u.highlightSelection;
        window.wireSegmentedControls = u.wireSegmentedControls;
        window.wireSortGroups = u.wireSortGroups;

        // activateSeg existed earlier; export it if available
        if (u.activateSeg) window.activateSeg = u.activateSeg;

        // Previously present higher-level helpers — provide safe fallbacks
        window.generatePreview = window.generatePreview || (async function () { /* no-op */ });
        window.renderVerifierPdfPreview = window.renderVerifierPdfPreview || (async function (url, el) {
            if (!el) return;
            if (url) el.innerHTML = `<iframe class="w-full h-[70vh]" src="${url}" loading="lazy"></iframe>`;
            else el.innerHTML = `<div class="p-3 text-sm muted">No PDF.</div>`;
        });

        // Page update helpers used by older code
        window.updatePanel = window.updatePanel || function () { if (ctrl) ctrl.refresh(); };
        window.updateStatsBar = window.updateStatsBar || function () { if (window.updateAbstractMeta) window.updateAbstractMeta(); };

        // Layout helpers that were page-specific; keep as no-ops to avoid errors
        window.adjust = window.adjust || function () { };
        window.apply = window.apply || function () { };
        window.renderList = window.renderList || function () { if (ctrl) ctrl.refresh(); };
        window.initCriteriaFilter = window.initCriteriaFilter || function () { };
        window.initSidePanelCollapse = window.initSidePanelCollapse || function () { };

    } catch (e) { console.warn("Compat shim init error", e); }
})();