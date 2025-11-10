
/* submit_list.js - generic reusable list controller
 * Exposes window.SubmitList.{init, Controller, utils}
 */
(function (global) {
    "use strict";

    // ---- tiny utils ----
    const $ = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
    const on = (el, ev, fn, opts) => el && el.addEventListener(ev, fn, opts);
    const debounce = (fn, ms = 250) => {
        let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
    };

    // Console logging utilities (added for debugging)
    function log(message, level = 'info') {
        console.log(`[Submit List] ${level.toUpperCase()}:`, message);
    }

    function logError(message, error = null) {
        console.error(`[Submit List] ERROR: ${message}`, error);
        if (error && error.stack) {
            console.error('Stack trace:', error.stack);
        }
    }

    // ---- fetch helpers ----
    const headers = () => {
        const h = { "Accept": "application/json" };
        const tk = token();
        if (tk) h["Authorization"] = "Bearer " + tk;
        return h;
    };
    const token = () => (localStorage.getItem("token") || "").trim();
    async function fetchJSON(url, params = {}, init = {}) {
        const u = new URL(url, window.location.origin);
        Object.entries(params).forEach(([k, v]) => (v !== undefined && v !== null && v !== "") && u.searchParams.set(k, v));
        const resp = await fetch(u.toString(), { ...init, headers: { ...headers(), ...(init.headers || {}) } });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const ct = resp.headers.get("content-type") || "";
        return ct.includes("application/json") ? resp.json() : resp.text();
    }

    // ---- UI helpers ----
    function escapeHtml(s) { return String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;"); }
    function formatDate(iso) { if (!iso) return ""; const d = new Date(iso); if (isNaN(d)) return String(iso); return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" }); }
    function createToastContainer() {
        let c = document.getElementById("toast-container");
        if (!c) {
            c = document.createElement("div");
            c.id = "toast-container";
            c.className = "fixed top-3 right-3 z-50 space-y-2";
            document.body.appendChild(c);
        }
        return c;
    }
    function toast(msg, cls = "bg-blue-600 text-white") {
        const c = createToastContainer();
        const d = document.createElement("div");
        d.className = `px-3 py-2 rounded shadow ${cls}`;
        d.textContent = msg;
        c.appendChild(d);
        setTimeout(() => d.remove(), 2500);
    }

    function getStatusClass(status) {
        const s = String(status || "").toLowerCase();
        if (s.includes("accept")) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
        if (s.includes("reject")) return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100";
        if (s.includes("review")) return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100";
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
    }

    function applySortStyles(groupEl, key) {
        if (!groupEl) return;
        $$(".sort-btn", groupEl).forEach(b => b.classList.toggle("font-semibold", b.getAttribute("data-key") === key));
    }
    function activateSeg(groupEl, btn) { if (!groupEl || !btn) return; $$(".seg", groupEl).forEach(b => b.classList.remove("active")); btn.classList.add("active"); }

    function highlightSelection(root, li) {
        if (!root || !li) return;
        $$("li[data-id]", root).forEach(n => n.classList.remove("ring", "ring-blue-400"));
        li.classList.add("ring", "ring-blue-400");
    }

    function wireSegmentedControls(groupEl, onChange) {
        if (!groupEl) return;
        on(groupEl, "click", (e) => {
            const btn = e.target.closest("[data-val]");
            if (!btn) return;
            activateSeg(groupEl, btn);
            onChange(btn.getAttribute("data-val") || "");
        });
    }
    function wireSortGroups(groupEl, onChange) {
        if (!groupEl) return;
        on(groupEl, "click", (e) => {
            const btn = e.target.closest("[data-key]");
            if (!btn) return;
            onChange(btn.getAttribute("data-key"));
            applySortStyles(groupEl, btn.getAttribute("data-key"));
        });
    }

    // ---- PDF preview hooks (no-op here; feature modules can import pdf.js and call) ----
    async function renderVerifierPdfPreview() { /* placeholder: implement in feature if needed */ }
    async function generatePreview() { /* placeholder */ }

    // ---- Controller ----
    class Controller {
        /**
         * Required options:
         *  listEl, searchInputEl, searchBtnEl, statusGroupEl, sortGroupEl,
         *  prevBtnEl, nextBtnEl, pageInfoEl, statsEl, pageSizeGroupEl, globalLoadingEl
         *  fetchPage({page,pageSize,sortKey,sortDir,filter,query}) => {items,total,totalPages,meta?}
         *  renderItem(item,state) => HTMLElement
         * Optional:
         *  details: {containerEl,noSelectedEl,contentEl,previewEl,titleEl,categoryEl,statusEl,numberEl,authorEl,dateEl}
         *  onSelect(item, ctx)
         *  statsMap: { total?: nodeOrSel, pending?:..., ... }
         */
        constructor(opts) {
            this.o = { ...opts };
            this.state = { page: 1, pageSize: 20, sortKey: null, sortDir: "desc", filter: "", query: "", total: 0, totalPages: 1, items: [], selectedId: null };

            // resolve selectors
            ["listEl", "searchInputEl", "searchBtnEl", "statusGroupEl", "sortGroupEl", "prevBtnEl", "nextBtnEl", "pageInfoEl", "statsEl", "pageSizeGroupEl", "globalLoadingEl"]
                .forEach(k => { if (typeof this.o[k] === "string") this.o[k] = $(this.o[k]); });
            if (this.o.details) {
                Object.keys(this.o.details).forEach(k => { if (typeof this.o.details[k] === "string") this.o.details[k] = $(this.o.details[k]); });
            }
            this._bind();
        }

        init() { this.refresh(); return this; }

        _bind() {
            const o = this.o, s = this.state;

            // search
            if (o.searchInputEl) on(o.searchInputEl, "input", debounce(() => { s.query = o.searchInputEl.value.trim(); s.page = 1; this.refresh(); }, 300));
            if (o.searchBtnEl) on(o.searchBtnEl, "click", () => { s.query = (o.searchInputEl?.value || "").trim(); s.page = 1; this.refresh(); });

            // filter + sort
            wireSegmentedControls(o.statusGroupEl, (val) => { s.filter = val; s.page = 1; this.refresh(); });
            wireSortGroups(o.sortGroupEl, (key) => { if (s.sortKey === key) s.sortDir = s.sortDir === "asc" ? "desc" : "asc"; else { s.sortKey = key; s.sortDir = "asc"; } s.page = 1; this.refresh(); });

            // page size
            if (o.pageSizeGroupEl) on(o.pageSizeGroupEl, "click", (e) => {
                const btn = e.target.closest("[data-size]"); if (!btn) return;
                activateSeg(o.pageSizeGroupEl, btn);
                const sz = parseInt(btn.getAttribute("data-size"), 10);
                if (!Number.isNaN(sz)) { s.pageSize = sz; s.page = 1; this.refresh(); }
            });

            // pager
            if (o.prevBtnEl) on(o.prevBtnEl, "click", () => { if (s.page > 1) { s.page--; this.refresh(); } });
            if (o.nextBtnEl) on(o.nextBtnEl, "click", () => { if (s.page < s.totalPages) { s.page++; this.refresh(); } });

            // select item
            if (o.listEl) on(o.listEl, "click", (e) => {
                const li = e.target.closest("li[data-id]"); if (!li) return;
                const id = li.getAttribute("data-id");
                const item = this.state.items.find(x => String(x.id) === String(id));
                if (!item) return;
                highlightSelection(o.listEl, li);
                this._select(item);
            });
        }

        _setLoading(onoff) { const el = this.o.globalLoadingEl; if (el) el.classList.toggle("hidden", !onoff); }

        async refresh() {
            const s = this.state;
            log(`Refreshing list: page=${s.page}, pageSize=${s.pageSize}, sortKey=${s.sortKey}, filter=${s.filter}, query=${s.query}`, 'info');
            this._setLoading(true);
            try {
                const res = await this.o.fetchPage({ page: s.page, pageSize: s.pageSize, sortKey: s.sortKey, sortDir: s.sortDir, filter: s.filter, query: s.query });
                log(`Received ${res.items?.length || 0} items, total=${res.total}, totalPages=${res.totalPages}`, 'info');
                s.items = res.items || [];
                s.total = res.total ?? s.items.length;
                s.totalPages = res.totalPages ?? Math.max(1, Math.ceil((s.total || 0) / s.pageSize));
                this._renderList();
                this._updateMeta(res.meta || {}, { total: s.total });
                this._updatePager();
                // auto select first
                if (!s.selectedId && s.items.length > 0 && this.o.listEl) {
                    const firstId = String(s.items[0].id);
                    const li = this.o.listEl.querySelector(`li[data-id="${firstId}"]`) || this.o.listEl.querySelector("li[data-id]");
                    if (li) { 
                        highlightSelection(this.o.listEl, li); 
                        this._select(s.items[0]); 
                        log(`Auto-selected first item ID: ${firstId}`, 'info');
                    }
                }
            } catch (e) {
                logError("refresh error:", e);
                if (this.o.statsEl) this.o.statsEl.textContent = "Failed to load.";
                toast("Failed to load list", "bg-red-600 text-white");
            } finally {
                this._setLoading(false);
                log('List refresh completed', 'info');
            }
        }

        _renderList() {
            const root = this.o.listEl; 
            if (!root) {
                log('List element not found, cannot render', 'warn');
                return;
            }
            log(`Rendering ${this.state.items.length} items`, 'info');
            root.innerHTML = "";
            const frag = document.createDocumentFragment();
            for (const it of this.state.items) {
                const li = this.o.renderItem(it, this.state);
                if (!(li instanceof HTMLElement)) {
                    log(`renderItem did not return an HTMLElement for item ${it.id}`, 'warn');
                    continue;
                }
                li.setAttribute("data-id", String(it.id));
                frag.appendChild(li);
            }
            root.appendChild(frag);
            log(`List rendering completed with ${this.state.items.length} items`, 'info');
        }

        _updatePager() {
            const s = this.state, o = this.o;
            if (o.pageInfoEl) {
                const start = (s.page - 1) * s.pageSize + 1;
                const end = Math.min(s.page * s.pageSize, s.total);
                o.pageInfoEl.textContent = s.total ? `${start}–${end} of ${s.total}` : "0";
                log(`Pager updated: ${start}–${end} of ${s.total}`, 'info');
            }
            if (o.prevBtnEl) {
                o.prevBtnEl.disabled = s.page <= 1;
                log(`Previous button ${o.prevBtnEl.disabled ? 'disabled' : 'enabled'}`, 'info');
            }
            if (o.nextBtnEl) {
                o.nextBtnEl.disabled = s.page >= s.totalPages;
                log(`Next button ${o.nextBtnEl.disabled ? 'disabled' : 'enabled'}`, 'info');
            }
            if (o.statsEl && !o.pageInfoEl) o.statsEl.textContent = `${s.total} item(s)`;
        }

        

        _updateMeta(meta, base) {
            const o = this.o;
            const total = base.total ?? meta.total;
            if (o.statsEl) o.statsEl.textContent = total != null ? `${total} item(s)` : "";
            if (o.statsMap) {
                Object.entries(o.statsMap).forEach(([key, sel]) => {
                    const el = typeof sel === "string" ? $(sel) : sel;
                    const val = meta[key];
                    if (el && val != null) el.textContent = String(val);
                });
            }
        }

        _select(item) {
            log(`Selecting item with ID: ${item.id}`, 'info');
            this.state.selectedId = item.id;
            if (this.o.details) {
                this.o.details.noSelectedEl?.classList.add("hidden");
                this.o.details.contentEl?.classList.remove("hidden");
            }
            const ctx = {
                setDetails: (fields) => {
                    const d = this.o.details || {};
                    if (fields.title !== undefined && d.titleEl) d.titleEl.textContent = fields.title || "";
                    if (fields.category !== undefined && d.categoryEl) d.categoryEl.textContent = fields.category?.name || "";
                    if (fields.status !== undefined && d.statusEl) d.statusEl.textContent = fields.status || "";
                    if (fields.number !== undefined && d.numberEl) d.numberEl.textContent = fields.number || "";
                    if (fields.author !== undefined && d.authorEl) d.authorEl.textContent = fields.author || "";
                    if (fields.date !== undefined && d.dateEl) d.dateEl.textContent = fields.date || "";
                    if (fields.previewHtml !== undefined && d.previewEl) d.previewEl.innerHTML = fields.previewHtml || "";
                },
                previewEl: this.o.details?.previewEl || null,
                detailsEl: this.o.details?.containerEl || null,
                utils: { escapeHtml, formatDate, getStatusClass, toast }
            };
            if (typeof this.o.onSelect === "function") {
                log(`Calling onSelect for item ID: ${item.id}`, 'info');
                this.o.onSelect(item, ctx);
            }
        }
    }

    function init(opts) { return new Controller(opts).init(); }

    // Additional API endpoints for abstract relationships
    async function addAuthorToAbstract(abstractId, authorData) {
        try {
            const response = await fetch(`${BASE}/abstracts/${abstractId}/authors`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(authorData)
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text() || response.statusText}`);
            return response.json();
        } catch (error) {
            logError(`Error adding author to abstract ${abstractId}:`, error);
            throw error;
        }
    }

    async function removeAuthorFromAbstract(abstractId, authorId) {
        try {
            const response = await fetch(`${BASE}/abstracts/${abstractId}/authors/${authorId}`, {
                method: 'DELETE',
                headers: headers()
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text() || response.statusText}`);
            return response.json();
        } catch (error) {
            logError(`Error removing author ${authorId} from abstract ${abstractId}:`, error);
            throw error;
        }
    }

    async function assignVerifiersToAbstract(abstractId, userIds) {
        try {
            const response = await fetch(`${BASE}/abstracts/${abstractId}/verifiers`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_ids: userIds })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text() || response.statusText}`);
            return response.json();
        } catch (error) {
            logError(`Error assigning verifiers to abstract ${abstractId}:`, error);
            throw error;
        }
    }

    async function removeVerifierFromAbstract(abstractId, userId) {
        try {
            const response = await fetch(`${BASE}/abstracts/${abstractId}/verifiers/${userId}`, {
                method: 'DELETE',
                headers: headers()
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text() || response.statusText}`);
            return response.json();
        } catch (error) {
            logError(`Error removing verifier ${userId} from abstract ${abstractId}:`, error);
            throw error;
        }
    }

    // Function to handle download functionality
    async function handleDownload(downloadUrl, fileName = 'data.zip') {
        try {
            const downloadBtn = document.getElementById('DownloadBtn');
            if (downloadBtn) {
                // Show loading state
                const originalText = downloadBtn.textContent;
                downloadBtn.textContent = 'Downloading...';
                downloadBtn.disabled = true;
                
                // Make API call to download endpoint
                const response = await fetch(downloadUrl, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token()}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                // Create a blob from the response and trigger download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                toast('Download started successfully', 'bg-green-600 text-white');
            }
        } catch (error) {
            logError('Download failed:', error);
            toast('Download failed. Please try again.', 'bg-red-600 text-white');
        } finally {
            // Restore button state
            const downloadBtn = document.getElementById('DownloadBtn');
            if (downloadBtn) {
                downloadBtn.textContent = 'Download Data';
                downloadBtn.disabled = false;
            }
        }
    }

    global.SubmitList = {
        init, Controller,
        utils: {
            $, $$, on, debounce, fetchJSON, escapeHtml, formatDate, headers, token, toast, getStatusClass,
            wireSegmentedControls, wireSortGroups, applySortStyles, highlightSelection,
            // Additional utilities for abstract relationships
            addAuthorToAbstract, removeAuthorFromAbstract, assignVerifiersToAbstract, removeVerifierFromAbstract
        },
        // Export the download function for use in specific page implementations
        handleDownload
    };
})(window);