/* award_submit_list.js — page adapter for AWARDS (preserves old globals) */
(function () {
    "use strict";
    const { utils, init } = window.SubmitList;
    const { fetchJSON, escapeHtml, formatDate, getStatusClass } = utils;

    // Console logging utilities
    function log(message, level = 'info') {
        console.log(`[Award List] ${level.toUpperCase()}:`, message);
    }

    function logError(message, error = null) {
        console.error(`[Award List] ERROR: ${message}`, error);
        if (error && error.stack) {
            console.error('Stack trace:', error.stack);
        }
    }

    const API_LIST = "/api/v1/research/awards";
    const API_DETAIL = (id) => `/api/v1/research/awards/${encodeURIComponent(id)}`;
    const API_META = "/api/v1/research/awards/status";

    // -----------------------
    // Helpers for preview code
    // -----------------------
    const token = () => (localStorage.getItem("token") || "").trim();
    const BASE = window.API_BASE || `${location.origin}/api/v1/research`; // used by PDF fetch

    function sQ(id) { return document.getElementById(id); }

    // ===== Generated preview (drop-in) =====
    window.generatePreview = function (selAward) {
        const previewContent = sQ('preview-content');
        if (!previewContent || !selAward) return;

        const categoryName = selAward.paper_category?.name || selAward.paper_category || 'No Category';

        // Update summary card info (top badges)
        if (sQ('summaryTitle')) sQ('summaryTitle').textContent = selAward.title || 'Untitled Award';
        if (sQ('summaryCategory')) sQ('summaryCategory').textContent = categoryName;
        if (sQ('summaryAwardNumber')) sQ('summaryAwardNumber').textContent = selAward.award_number || 'Unknown ID';

        if (sQ('summaryStatus')) {
            sQ('summaryStatus').textContent = selAward.status || 'PENDING';
            sQ('summaryStatus').className = 'badge ' + getStatusClass(selAward.status);
        }
        if (sQ('summaryAuthor')) sQ('summaryAuthor').textContent = selAward.created_by?.username || selAward.author || 'Unknown User';
        if (sQ('summaryDate')) sQ('summaryDate').textContent = formatDate(selAward.created_at);

        // Build Authors block
        let authorsHTML = '';
        if (selAward.author) {
            const author = selAward.author;
            const roles = [];
            if (author.is_presenter) roles.push('Presenter');
            if (author.is_corresponding) roles.push('Corresponding');
            authorsHTML = `
                <div class="border-l-4 border-blue-400 dark:border-blue-600 pl-4 py-2">
                    <div class="flex flex-wrap justify-between gap-2">
                        <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(author.name || '')}</p>
                        ${roles.length ? `<div class="flex flex-wrap gap-1">
                            ${roles.map(r => `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-80 dark:text-blue-100">${r}</span>`).join('')}
                        </div>` : ''}
                    </div>
                    ${author.email ? `<p class="text-sm text-blue-600 dark:text-blue-400 mt-1">${escapeHtml(author.email)}</p>` : ''}
                    ${author.affiliation ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${escapeHtml(author.affiliation)}</p>` : ''}
                </div>`;
        } else {
            authorsHTML = `<p class="text-gray-500 dark:text-gray-400 italic">No authors listed</p>`;
        }

        const previewHTML = `
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
                <!-- Authors Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.28 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Authors</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">List of contributing authors</p>
                        </div>
                    </div>
                    <div class="ml-2 space-y-4">
                        ${authorsHTML}
                    </div>
                </div>

                <!-- AIIMS & Forwarding Letter Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17V7a2 2 0 012-2h6a2 2 0 012 2v10m-2 4h-4a2 2 0 01-2-2V7a2 2 0 012-2h4a2 2 0 012 2v10a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Covering Letter</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">AIIMS involvement and covering letter</p>
                        </div>
                    </div>
                    <div class="ml-2">
                        ${selAward.forwarding_letter_path ? `
                            <div id="forwarding-pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-400">Loading PDF...</span>
                                    </div>
                                </div>
                            </div>
                        ` : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No Forwarding Letter PDF uploaded for this award.</p>`}
                    </div>
                </div>

                <!-- PDF Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17V7a2 2 0 012-2h6a2 2 0 012 2v10m-2 4h-4a2 2 0 01-2V7a2 2 0 012-2h4a2 2 0 012 2v10a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">PDF Document</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Uploaded award PDF</p>
                        </div>
                    </div>
                    <div class="ml-2">
                        ${selAward.full_paper_path ? `
                            <div id="pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-40">Loading PDF...</span>
                                    </div>
                                </div>
                            </div>
                        ` : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No PDF uploaded for this award.</p>`}
                    </div>
                </div>
            </div>
        `;

        previewContent.innerHTML = previewHTML;

        // After rendering, if PDF exists, render preview using PDF.js
        if (selAward.full_paper_path) {
            window.renderVerifierPdfPreview(selAward.id);
        }

        if (selAward.forwarding_letter_path) {
            window.renderVerifierforwardingPdfPreview(selAward.id);
        }
    };

    // PDF.js rendering for main PDF
    window.renderVerifierPdfPreview = function (awardId) {
        const container = document.getElementById('pdf-preview-container');

        if (typeof pdfjsLib === 'undefined') {
            if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.worker.min.js';

        fetch(`${BASE}/awards/${encodeURIComponent(awardId)}/pdf`, {
            headers: { 'Authorization': `Bearer ${token()}` }
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.arrayBuffer();
            })
            .then(buffer => {
                const typedarray = new Uint8Array(buffer);
                const loadingTask = pdfjsLib.getDocument({ data: typedarray, password: '' });
                return loadingTask.promise.then(pdf => ({ pdf }));
            })
            .then(({ pdf }) => {
                if (!container) return;
                container.innerHTML = '';
                const scale = 1.5;
                const tasks = [];
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                    tasks.push(
                        pdf.getPage(pageNum).then(page => {
                            const viewport = page.getViewport({ scale });
                            const canvas = document.createElement('canvas');
                            canvas.className = 'w-full mb-4 rounded shadow';
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            container.appendChild(canvas);
                            const context = canvas.getContext('2d');
                            return page.render({ canvasContext: context, viewport }).promise;
                        })
                    );
                }
                return Promise.all(tasks);
            })
            .catch(err => {
                if (container) container.innerHTML = `<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to load/render PDF: ${escapeHtml(err?.message || 'Unknown error')}</p>`;
            });
    };

    // PDF.js rendering for forwarding letter PDF
    window.renderVerifierforwardingPdfPreview = function (awardId) {
        const container = document.getElementById('forwarding-pdf-preview-container');

        if (typeof pdfjsLib === 'undefined') {
            if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.worker.min.js';

        fetch(`${BASE}/awards/${encodeURIComponent(awardId)}/forwarding_pdf`, {
            headers: { 'Authorization': `Bearer ${token()}` }
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.arrayBuffer();
            })
            .then(buffer => {
                const typedarray = new Uint8Array(buffer);
                const loadingTask = pdfjsLib.getDocument({ data: typedarray, password: '' });
                return loadingTask.promise.then(pdf => ({ pdf }));
            })
            .then(({ pdf }) => {
                if (!container) return;
                container.innerHTML = '';
                const scale = 1.5;
                const tasks = [];
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                    tasks.push(
                        pdf.getPage(pageNum).then(page => {
                            const viewport = page.getViewport({ scale });
                            const canvas = document.createElement('canvas');
                            canvas.className = 'w-full mb-4 rounded shadow';
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            container.appendChild(canvas);
                            const context = canvas.getContext('2d');
                            return page.render({ canvasContext: context, viewport }).promise;
                        })
                    );
                }
                return Promise.all(tasks);
            })
            .catch(err => {
                if (container) container.innerHTML = `<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to load/render PDF: ${escapeHtml(err?.message || 'Unknown error')}</p>`;
            });
    };

    // -----------------------
    // List render
    // -----------------------
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
                    #${escapeHtml(item.id)} · ${escapeHtml(item.paper_category?.name || "-")} · ${escapeHtml(item.created_by?.username || "-")}
                </div>
            </div>
            <div class="text-xs whitespace-nowrap ml-2">${escapeHtml(formatDate(item.created_at))}</div>
        `;
        return li;
    }

    async function fetchPage({ page, pageSize, sortKey, sortDir, filter, query }) {
        log(`Fetching page ${page} with filter: ${filter || 'all'}, query: ${query || 'none'}`, 'info');
        try {
            const data = await fetchJSON(API_LIST, {
                q: query, status: filter, sort: sortKey || "created_at", dir: sortDir || "desc", page, size: pageSize
            });
            log(`Received ${data.items?.length || 0} items for page ${page}`, 'info');
            return { items: data.items || [], total: data.total ?? 0, totalPages: data.pages ?? 1, meta: data.meta || {} };
        } catch (error) {
            logError('Error fetching page data:', error);
            throw error;
        }
    }

    // Use generated preview inside selection handler
    async function onSelect(item, ctx) {
        log(`Selecting award with ID: ${item.id}`, 'info');
        try {
            const full = await fetchJSON(API_DETAIL(item.id));
            log(`Fetched full award details for ID: ${item.id}`, 'info');

            // Update summary badges via controller so they also reflect in UI elements
            ctx.setDetails({
                title: full.title || item.title || "",
                category: full.paper_category || item.paper_category || (full.paper_category?.name) || "",
                status: full.status || item.status || "",
                number: full.award_number || full.number || item.number || "",
                author: (full.created_by?.username) || full.author || item.author || "",
                date: formatDate(full.created_at || item.created_at),
                previewHtml: `<div class="p-3 text-sm muted">Loading preview…</div>`
            });

            // Now render the rich details + authors + PDF using the generated function
            window.generatePreview(full);
        } catch (error) {
            logError(`Error selecting award with ID: ${item.id}`, error);
            throw error;
        }
    }

    // -----------------------
    // Controller wiring
    // -----------------------
    let __awardListCtrl = null;

    document.addEventListener('DOMContentLoaded', function() {
        try {
            const ctrl = init({
                listEl: "#List",
                searchInputEl: "#awardSearch",
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
                statsMap: { total: "#statTotal", pending: "#statPending", accepted: "#statAccepted", rejected: "#statRejected" },
                fetchPage, renderItem, onSelect
            });
            
            __awardListCtrl = ctrl;
            
            // ---- Old global names preserved ----
            window.searchAwards = function (q) {
                const s = __awardListCtrl.state;
                if (typeof q === "string") { const input = document.querySelector("#awardSearch"); if (input) input.value = q; s.query = q.trim(); }
                else { const input = document.querySelector("#awardSearch"); s.query = (input?.value || "").trim(); }
                s.page = 1; __awardListCtrl.refresh();
            };
            window.changeAwardPage = function (deltaOrNumber) {
                const s = __awardListCtrl.state;
                if (typeof deltaOrNumber === "number") {
                    if (Number.isInteger(deltaOrNumber) && Math.abs(deltaOrNumber) <= 2 && deltaOrNumber !== 0)
                        s.page = Math.min(Math.max(1, s.page + deltaOrNumber), s.totalPages);
                    else
                        s.page = Math.min(Math.max(1, deltaOrNumber), s.totalPages);
                } else if (deltaOrNumber === "next") s.page = Math.min(s.page + 1, s.totalPages);
                else if (deltaOrNumber === "prev") s.page = Math.max(s.page - 1, 1);
                __awardListCtrl.refresh();
            };
            window.updateAwardMeta = async function () {
                try {
                    const m = await fetchJSON(API_META);
                    const map = { total: "#statTotal", pending: "#statPending", accepted: "#statAccepted", rejected: "#statRejected" };
                    for (const [k, sel] of Object.entries(map)) {
                        const el = document.querySelector(sel);
                        if (el && m[k] != null) el.textContent = String(m[k]);
                    }
                    const stats = document.querySelector("#Stats");
                    if (stats && m.total != null) stats.textContent = `${m.total} item(s)`;
                } catch (e) { console.warn("updateAwardMeta failed", e); }
            };

            // Ensure global controller reference is accessible
            window.__awardListCtrl = __awardListCtrl;
            
            // Add explicit event handlers for next/prev buttons to ensure they work
            const nextBtn = document.querySelector("#Next");
            const prevBtn = document.querySelector("#Prev");
            
            if (nextBtn) {
                nextBtn.addEventListener('click', function() {
                    if (__awardListCtrl && __awardListCtrl.state.page < __awardListCtrl.state.totalPages) {
                        __awardListCtrl.state.page++;
                        __awardListCtrl.refresh();
                    }
                });
            }
            
            if (prevBtn) {
                prevBtn.addEventListener('click', function() {
                    if (__awardListCtrl && __awardListCtrl.state.page > 1) {
                        __awardListCtrl.state.page--;
                        __awardListCtrl.refresh();
                    }
                });
            }
        } catch (error) {
            console.error("Error initializing award list controller:", error);
            // Show an error message to the user
            const statsEl = document.querySelector("#Stats");
            if (statsEl) {
                statsEl.textContent = "Error loading award list. Please refresh the page.";
                statsEl.className = "text-red-600 dark:text-red-40";
            }
        }
    });
    
    // Define global functions outside DOMContentLoaded but with checks to ensure controller is ready
    window.nextAwardPage = function() {
        if (window.__awardListCtrl && window.__awardListCtrl.state.page < window.__awardListCtrl.state.totalPages) {
            window.__awardListCtrl.state.page++;
            window.__awardListCtrl.refresh();
        } else {
            console.warn("Award list controller not ready or already on last page");
        }
    };
    
    window.prevAwardPage = function() {
        if (window.__awardListCtrl && window.__awardListCtrl.state.page > 1) {
            window.__awardListCtrl.state.page--;
            window.__awardListCtrl.refresh();
        } else {
            console.warn("Award list controller not ready or already on first page");
        }
    };

})();