/* submit_list_paper.js — page adapter for BEST PAPERS (mirrors award list integration) */
(function () {
    "use strict";

    if (!window.SubmitList || typeof window.SubmitList.init !== "function") {
        console.error("[Best Paper List] SubmitList helpers not available. Cannot initialise list controller.");
        return;
    }

    const { utils, init } = window.SubmitList;
    const { fetchJSON, escapeHtml, formatDate, getStatusClass } = utils;

    function log(message, level = "info") {
        console.log(`[Best Paper List] ${level.toUpperCase()}:`, message);
    }

    function logError(message, error = null) {
        console.error(`[Best Paper List] ERROR: ${message}`, error);
        if (error && error.stack) {
            console.error("Stack trace:", error.stack);
        }
    }

    const API_LIST = "/api/v1/research/best-papers";
    const API_DETAIL = (id) => `/api/v1/research/best-papers/${encodeURIComponent(id)}`;
    const API_META = "/api/v1/research/best-papers/status";

    const token = () => (localStorage.getItem("token") || "").trim();
    const BASE = window.API_BASE || `${location.origin}/api/v1/research`;

    function sQ(id) {
        return document.getElementById(id);
    }

    // ===== Generated preview =====
    window.generatePreview = function (selPaper) {
        const previewContent = sQ("preview-content");
        if (!previewContent || !selPaper) return;

        const categoryName = selPaper.paper_category?.name || selPaper.paper_category || "No Category";

        if (sQ("summaryTitle")) sQ("summaryTitle").textContent = selPaper.title || "Untitled Best Paper";
        if (sQ("summaryCategory")) sQ("summaryCategory").textContent = categoryName;
        const paperNumber =
            selPaper.bestpaper_number ||
            selPaper.paper_number ||
            selPaper.paperNumber ||
            selPaper.id ||
            "Unknown ID";
        if (sQ("summaryNumber")) sQ("summaryNumber").textContent = paperNumber;

        if (sQ("summaryStatus")) {
            sQ("summaryStatus").textContent = selPaper.status || "PENDING";
            sQ("summaryStatus").className = "badge " + getStatusClass(selPaper.status);
        }
        if (sQ("summaryAuthor")) {
            const authorName =
                selPaper.created_by?.username ||
                selPaper.author?.name ||
                selPaper.author_name ||
                "Unknown User";
            sQ("summaryAuthor").textContent = authorName;
        }
        if (sQ("summaryDate")) {
            sQ("summaryDate").textContent = formatDate(selPaper.created_at);
        }

        let authorsHTML = "";
        if (selPaper.author) {
            const author = selPaper.author;
            const roles = [];
            if (author.is_presenter) roles.push("Presenter");
            if (author.is_corresponding) roles.push("Corresponding");
            authorsHTML = `
                <div class="border-l-4 border-blue-400 dark:border-blue-600 pl-4 py-2">
                    <div class="flex flex-wrap justify-between gap-2">
                        <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(author.name || "")}</p>
                        ${
                            roles.length
                                ? `<div class="flex flex-wrap gap-1">
                                        ${roles
                                            .map(
                                                (role) => `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">${escapeHtml(role)}</span>`
                                            )
                                            .join("")}
                                   </div>`
                                : ""
                        }
                    </div>
                    ${
                        author.email
                            ? `<p class="text-sm text-blue-600 dark:text-blue-400 mt-1">${escapeHtml(author.email)}</p>`
                            : ""
                    }
                    ${
                        author.affiliation
                            ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${escapeHtml(author.affiliation)}</p>`
                            : ""
                    }
                </div>
            `;
        } else {
            authorsHTML = `<p class="text-gray-500 dark:text-gray-400 italic">No authors listed</p>`;
        }

        const aiimsAnswer = selPaper.is_aiims_work ? "Yes" : "No";
        const aiimsDescription = selPaper.is_aiims_work
            ? "The work was primarily conducted at AIIMS."
            : "The work was not primarily conducted at AIIMS.";

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

                <!-- AIIMS & Covering Letter Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17V7a2 2 0 012-2h6a2 2 0 012 2v10m-2 4h-4a2 2 0 01-2-2V7a2 2 0 012-2h4a2 2 0 012 2v10a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Project Context</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">AIIMS involvement & Covering Letter</p>
                        </div>
                    </div>
                    <div class="ml-2 space-y-4">
                        <div class="rounded-lg bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 px-4 py-3">
                            <div class="flex items-center gap-2">
                                <span class="font-medium text-blue-700 dark:text-blue-200">Work primarily done at AIIMS?</span>
                                <span class="badge bg-white/80 dark:bg-blue-950/40 text-blue-700 dark:text-blue-200">${aiimsAnswer}</span>
                            </div>
                            <p class="text-sm text-blue-600 dark:text-blue-300 mt-1">${aiimsDescription}</p>
                        </div>
                        ${
                            selPaper.forwarding_letter_path
                                ? `
                            <div id="forwarding-pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-400">Loading covering letter…</span>
                                    </div>
                                </div>
                            </div>
                        `
                                : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No covering letter uploaded for this best paper.</p>`
                        }
                    </div>
                </div>

                <!-- PDF Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17V7a2 2 0 012-2h6a2 2 0 012 2v10m-2 4h-4a2 2 0 01-2-2V7a2 2 0 012-2h4a2 2 0 012 2v10a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Full Paper PDF</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Uploaded manuscript for review</p>
                        </div>
                    </div>
                    <div class="ml-2">
                        ${
                            selPaper.full_paper_path
                                ? `
                            <div id="pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-400">Loading PDF…</span>
                                    </div>
                                </div>
                            </div>
                        `
                                : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No PDF uploaded for this best paper.</p>`
                        }
                    </div>
                </div>
            </div>
        `;

        previewContent.innerHTML = previewHTML;

        if (selPaper.full_paper_path) {
            window.renderVerifierPdfPreview(selPaper.id);
        }

        if (selPaper.forwarding_letter_path) {
            window.renderVerifierforwardingPdfPreview(selPaper.id);
        }
    };

    // PDF.js rendering for main PDF
    window.renderVerifierPdfPreview = function (bestPaperId) {
        const container = document.getElementById("pdf-preview-container");

        if (typeof pdfjsLib === "undefined") {
            if (container)
                container.innerHTML =
                    '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/js/vendor/pdf.worker.min.js";

        fetch(`${BASE}/best-papers/${encodeURIComponent(bestPaperId)}/pdf`, {
            headers: { Authorization: `Bearer ${token()}` },
        })
            .then((response) => {
                if (!response.ok) throw new Error("Network response was not ok");
                return response.arrayBuffer();
            })
            .then((buffer) => {
                const typedarray = new Uint8Array(buffer);
                const loadingTask = pdfjsLib.getDocument({ data: typedarray, password: "" });
                return loadingTask.promise.then((pdf) => ({ pdf }));
            })
            .then(({ pdf }) => {
                if (!container) return;
                container.innerHTML = "";
                const scale = 1.5;
                const tasks = [];
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                    tasks.push(
                        pdf.getPage(pageNum).then((page) => {
                            const viewport = page.getViewport({ scale });
                            const canvas = document.createElement("canvas");
                            canvas.className = "w-full mb-4 rounded shadow";
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            container.appendChild(canvas);
                            const context = canvas.getContext("2d");
                            return page.render({ canvasContext: context, viewport }).promise;
                        })
                    );
                }
                return Promise.all(tasks);
            })
            .catch((err) => {
                if (container)
                    container.innerHTML = `<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to load/render PDF: ${escapeHtml(
                        err?.message || "Unknown error"
                    )}</p>`;
            });
    };

    // PDF.js rendering for forwarding letter PDF
    window.renderVerifierforwardingPdfPreview = function (bestPaperId) {
        const container = document.getElementById("forwarding-pdf-preview-container");

        if (typeof pdfjsLib === "undefined") {
            if (container)
                container.innerHTML =
                    '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/js/vendor/pdf.worker.min.js";

        fetch(`${BASE}/best-papers/${encodeURIComponent(bestPaperId)}/forwarding_pdf`, {
            headers: { Authorization: `Bearer ${token()}` },
        })
            .then((response) => {
                if (!response.ok) throw new Error("Network response was not ok");
                return response.arrayBuffer();
            })
            .then((buffer) => {
                const typedarray = new Uint8Array(buffer);
                const loadingTask = pdfjsLib.getDocument({ data: typedarray, password: "" });
                return loadingTask.promise.then((pdf) => ({ pdf }));
            })
            .then(({ pdf }) => {
                if (!container) return;
                container.innerHTML = "";
                const scale = 1.5;
                const tasks = [];
                for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                    tasks.push(
                        pdf.getPage(pageNum).then((page) => {
                            const viewport = page.getViewport({ scale });
                            const canvas = document.createElement("canvas");
                            canvas.className = "w-full mb-4 rounded shadow";
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            container.appendChild(canvas);
                            const context = canvas.getContext("2d");
                            return page.render({ canvasContext: context, viewport }).promise;
                        })
                    );
                }
                return Promise.all(tasks);
            })
            .catch((err) => {
                if (container)
                    container.innerHTML = `<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to load/render PDF: ${escapeHtml(
                        err?.message || "Unknown error"
                    )}</p>`;
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
                    #${escapeHtml(
                        item.bestpaper_number ||
                            item.paper_number ||
                            item.paperNumber ||
                            item.id ||
                            "-"
                    )} · ${escapeHtml(item.paper_category?.name || "-")} · ${escapeHtml(
            item.created_by?.username || item.author?.name || "-"
        )}
                </div>
            </div>
            <div class="text-xs whitespace-nowrap ml-2">${escapeHtml(formatDate(item.created_at))}</div>
        `;
        return li;
    }

    async function fetchPage({ page, pageSize, sortKey, sortDir, filter, query }) {
        log(
            `Fetching page ${page} with filter: ${filter || "all"}, query: ${query || "none"}, sort=${sortKey || "created_at"}:${sortDir || "desc"}`,
            "info"
        );
        try {
            const data = await fetchJSON(API_LIST, {
                q: query,
                status: filter ? filter.toUpperCase() : "",
                sort_by: sortKey || "created_at",
                sort_dir: sortDir || "desc",
                page,
                page_size: pageSize,
            });
            return {
                items: data.items || [],
                total: data.total ?? data.items?.length ?? 0,
                totalPages: data.pages ?? 1,
                meta: data.meta || {},
            };
        } catch (error) {
            logError("Error fetching best paper list", error);
            throw error;
        }
    }

    async function onSelect(item, ctx) {
        log(`Selecting best paper with ID: ${item.id}`, "info");
        try {
            const full = await fetchJSON(API_DETAIL(item.id));
            log(`Fetched full best paper details for ID: ${item.id}`, "info");

            ctx.setDetails({
                title: full.title || item.title || "",
                category: full.paper_category || item.paper_category || (full.paper_category?.name && { name: full.paper_category.name }) || "",
                status: full.status || item.status || "",
                number: full.bestpaper_number || full.paper_number || item.bestpaper_number || item.paper_number || "",
                author:
                    full.created_by?.username ||
                    full.author?.name ||
                    item.created_by?.username ||
                    item.author?.name ||
                    "",
                date: formatDate(full.created_at || item.created_at),
                previewHtml: `<div class="p-3 text-sm muted">Loading preview…</div>`,
            });

            window.generatePreview(full);
        } catch (error) {
            logError(`Error selecting best paper with ID: ${item.id}`, error);
            throw error;
        }
    }

    const pickEl = (...selectors) => {
        for (const sel of selectors) {
            if (!sel) continue;
            const el = typeof sel === "string" ? document.querySelector(sel) : sel;
            if (el) return el;
        }
        return null;
    };

    // -----------------------
    // Controller wiring
    // -----------------------
    let __bestPaperListCtrl = null;

    document.addEventListener("DOMContentLoaded", function () {
        try {
            const ctrl = init({
                listEl: pickEl("#List", "#paperList"),
                searchInputEl: pickEl("#abstractSearch", "#paperSearch"),
                searchBtnEl: pickEl("#SearchBtn", "#paperSearchBtn"),
                statusGroupEl: pickEl("#StatusGroup", "#paperStatusGroup"),
                sortGroupEl: pickEl("#SortGroup", "#paperSortGroup"),
                prevBtnEl: pickEl("#Prev", "#paperPrev"),
                nextBtnEl: pickEl("#Next", "#paperNext"),
                pageInfoEl: pickEl("#PageInfo", "#paperPageInfo"),
                statsEl: pickEl("#Stats", "#paperStats"),
                pageSizeGroupEl: pickEl("#PageSizeGroup", "#paperPageSizeGroup"),
                globalLoadingEl: pickEl("#globalLoading"),
                details: {
                    containerEl: pickEl("#Details", "#paperDetails"),
                    noSelectedEl: pickEl("#noSelected", "#noPaperSelected"),
                    contentEl: pickEl("#Content", "#paperContent"),
                    previewEl: pickEl("#preview-content"),
                    titleEl: pickEl("#summaryTitle"),
                    categoryEl: pickEl("#summaryCategory"),
                    statusEl: pickEl("#summaryStatus"),
                    numberEl: pickEl("#summaryNumber", "#summaryPaperNumber"),
                    authorEl: pickEl("#summaryAuthor"),
                    dateEl: pickEl("#summaryDate"),
                },
                statsMap: {
                    total: "#statTotal",
                    pending: "#statPending",
                    accepted: "#statAccepted",
                    rejected: "#statRejected",
                },
                fetchPage,
                renderItem,
                onSelect,
            });

            __bestPaperListCtrl = ctrl;
            window.__bestPaperListCtrl = __bestPaperListCtrl;

            window.searchBestPapers = function (q) {
                if (!__bestPaperListCtrl) return;
                const s = __bestPaperListCtrl.state;
                const input = pickEl("#abstractSearch", "#paperSearch");
                if (typeof q === "string") {
                    if (input) input.value = q;
                    s.query = q.trim();
                } else {
                    s.query = (input?.value || "").trim();
                }
                s.page = 1;
                __bestPaperListCtrl.refresh();
            };

            window.changeBestPaperPage = function (deltaOrNumber) {
                if (!__bestPaperListCtrl) return;
                const s = __bestPaperListCtrl.state;
                if (typeof deltaOrNumber === "number") {
                    if (Number.isInteger(deltaOrNumber) && Math.abs(deltaOrNumber) <= 2 && deltaOrNumber !== 0) {
                        s.page = Math.min(Math.max(1, s.page + deltaOrNumber), s.totalPages);
                    } else {
                        s.page = Math.min(Math.max(1, deltaOrNumber), s.totalPages);
                    }
                } else if (deltaOrNumber === "next") {
                    s.page = Math.min(s.page + 1, s.totalPages);
                } else if (deltaOrNumber === "prev") {
                    s.page = Math.max(s.page - 1, 1);
                }
                __bestPaperListCtrl.refresh();
            };

            window.updateBestPaperMeta = async function () {
                try {
                    const meta = await fetchJSON(API_META);
                    const pendingCount = (meta.pending || 0) + (meta.under_review || 0);
                    const acceptedCount = meta.accepted || 0;
                    const rejectedCount = meta.rejected || 0;
                    const totalCount = meta.total != null ? meta.total : pendingCount + acceptedCount + rejectedCount;

                    const totalEl = document.querySelector("#statTotal");
                    if (totalEl) totalEl.textContent = String(totalCount);

                    const pendingEl = document.querySelector("#statPending");
                    if (pendingEl) pendingEl.textContent = String(pendingCount);

                    const acceptedEl = document.querySelector("#statAccepted");
                    if (acceptedEl) acceptedEl.textContent = String(acceptedCount);

                    const rejectedEl = document.querySelector("#statRejected");
                    if (rejectedEl) rejectedEl.textContent = String(rejectedCount);

                    const statsLabel = pickEl("#paperStats", "#Stats");
                    if (statsLabel) {
                        statsLabel.textContent = `${totalCount} item(s)`;
                    }
                } catch (e) {
                    console.warn("updateBestPaperMeta failed", e);
                }
            };

            const nextBtn = pickEl("#Next", "#paperNext");
            const prevBtn = pickEl("#Prev", "#paperPrev");

            if (nextBtn) {
                nextBtn.addEventListener("click", function () {
                    if (__bestPaperListCtrl && __bestPaperListCtrl.state.page < __bestPaperListCtrl.state.totalPages) {
                        __bestPaperListCtrl.state.page++;
                        __bestPaperListCtrl.refresh();
                    }
                });
            }

            if (prevBtn) {
                prevBtn.addEventListener("click", function () {
                    if (__bestPaperListCtrl && __bestPaperListCtrl.state.page > 1) {
                        __bestPaperListCtrl.state.page--;
                        __bestPaperListCtrl.refresh();
                    }
                });
            }

            // Attempt to load status counts on first paint
            window.updateBestPaperMeta();
        } catch (error) {
            logError("Error initializing best paper list controller", error);
            const statsEl = pickEl("#paperStats", "#Stats");
            if (statsEl) {
                statsEl.textContent = "Error loading best paper list. Please refresh the page.";
                statsEl.className = "text-red-600 dark:text-red-400";
            }
        }
    });

    // Define global helpers for pagination controls that might be referenced elsewhere
    window.nextBestPaperPage = function () {
        if (window.__bestPaperListCtrl && window.__bestPaperListCtrl.state.page < window.__bestPaperListCtrl.state.totalPages) {
            window.__bestPaperListCtrl.state.page++;
            window.__bestPaperListCtrl.refresh();
        } else {
            console.warn("Best paper list controller not ready or already on last page");
        }
    };

    window.prevBestPaperPage = function () {
        if (window.__bestPaperListCtrl && window.__bestPaperListCtrl.state.page > 1) {
            window.__bestPaperListCtrl.state.page--;
            window.__bestPaperListCtrl.refresh();
        } else {
            console.warn("Best paper list controller not ready or already on first page");
        }
    };
})();
