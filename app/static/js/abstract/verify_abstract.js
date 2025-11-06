(() => {
    const BASE = '/api/v1/research';  // Fixed path
    
    // Console logging utilities
    function log(message, level = 'info') {
        console.log(`[Verify Abstract] ${level.toUpperCase()}:`, message);
    }

    function logError(message, error = null) {
        console.error(`[Verify Abstract] ERROR: ${message}`, error);
        if (error && error.stack) {
            console.error('Stack trace:', error.stack);
        }
    }
    
    const token = () => localStorage.getItem('token') || '';
    const headers = () => ({ 'Accept': 'application/json', 'Authorization': `Bearer ${token()}` });
    const sQ = id => document.getElementById(id);
    const abstractList = sQ('abstractList');
    let selAbstract = null;
    const bulk = { abstractIds: new Set() };

    const state = {
        abstracts: { page: 1, pages: 1, pageSize: 20, filter: '', q: '', sort: 'id', dir: 'desc' }
    };

    function activateSeg(group, btn) {
        group.querySelectorAll('.seg').forEach(b => b.classList.remove('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]'));
        btn.classList.add('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
    }

    function wireSegmentedControls() {
        const aStatusGroup = sQ('abstractStatusGroup');
        aStatusGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aStatusGroup, btn);
            state.abstracts.filter = btn.dataset.val || '';
            state.abstracts.page = 1; searchAbstracts();
        });

        const aPageGroup = sQ('abstractPageSizeGroup');
        aPageGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aPageGroup, btn);
            state.abstracts.pageSize = +btn.dataset.size;
            state.abstracts.page = 1; searchAbstracts();
        });
    }
    
    async function updateStatsBar() {
        try {
            const resp = await fetch(`${BASE}/abstracts/status`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` }
            });
            if (!resp.ok) throw new Error('Failed to fetch stats');
            const stats = await resp.json();
            const total = (stats.pending || 0) + (stats.under_review || 0) + (stats.accepted || 0) + (stats.rejected || 0);
            document.getElementById('statTotal').textContent = total;
            document.getElementById('statPending').textContent = stats.pending || 0;
            document.getElementById('statAccepted').textContent = stats.accepted || 0;
            document.getElementById('statRejected').textContent = stats.rejected || 0;
        } catch (e) {
            // fallback: show dashes
            document.getElementById('statTotal').textContent = '-';
            document.getElementById('statPending').textContent = '-';
            document.getElementById('statAccepted').textContent = '-';
            document.getElementById('statRejected').textContent = '-';
        }
    }

    // Hide Accept/Reject buttons if status is not UNDER_REVIEW
    function updateVerifyActionBtns(status) {
        var btns = sQ('verifyActionBtns');
        if (!btns) return;
        if ((status || '').toUpperCase() === 'UNDER_REVIEW') btns.classList.remove('hidden');
        else btns.classList.add('hidden');
    }

    function applySortStyles(groupEl, currentKey, dir) {
        groupEl.querySelectorAll('.sort-btn').forEach(btn => {
            const key = btn.dataset.key;
            const arrow = btn.querySelector('.sort-arrow');
            if (key === currentKey) {
                btn.classList.add('bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
                arrow.classList.remove('opacity-40');
                arrow.textContent = dir === 'asc' ? '↑' : '↓';
            } else {
                btn.classList.remove('bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
                arrow.classList.add('opacity-40');
                arrow.textContent = '↕';
            }
        });
    }

    // Attach sorting behavior to abstract sort button group
    function wireSortGroups() {
        const aGroup = sQ('abstractSortGroup');
        if (aGroup) {
            applySortStyles(aGroup, state.abstracts.sort, state.abstracts.dir);
            aGroup.addEventListener('click', e => {
                const btn = e.target.closest('.sort-btn');
                if (!btn) return;
                const key = btn.dataset.key;
                if (state.abstracts.sort === key) {
                    state.abstracts.dir = state.abstracts.dir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.abstracts.sort = key;
                    state.abstracts.dir = 'asc';
                }
                applySortStyles(aGroup, state.abstracts.sort, state.abstracts.dir);
                searchAbstracts();
            });
        }
    }

    async function fetchJSON(url, opts = {}) {
        log(`Fetching: ${url}`, 'info');
        const bar = document.getElementById('globalLoading');
        bar && bar.classList.remove('hidden');
        try {
            const r = await fetch(url, { headers: headers(), ...opts });
            if (!r.ok) {
                const errorText = await r.text();
                logError(`Fetch error for ${url}: ${r.status}`, new Error(errorText || r.status));
                throw new Error(errorText || r.status);
            }
            const response = await r.json();
            log(`Successfully fetched data from: ${url}`, 'info');
            return response;
        } catch (error) {
            logError(`Error fetching ${url}:`, error);
            throw error;
        } finally {
            setTimeout(() => { bar && bar.classList.add('hidden'); }, 120); // slight delay for smoother perception
        }
    }
    
    function renderList(el, items, type) {
        el.replaceChildren();
        if (!items.length) {
            const empty = document.createElement('li');
            empty.className = 'py-8 text-center text-xs uppercase tracking-wide text-[color:var(--muted)]';
            empty.textContent = type === 'abstract' ? 'No abstracts found' : 'No items found';
            el.appendChild(empty);
            return;
        }
        items.forEach(it => {
            const li = document.createElement('li');
            const selected = bulk.abstractIds.has(it.id) && type === 'abstract';
            li.className = 'group py-3 px-3 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 cursor-pointer flex justify-between items-center transition-colors rounded-lg ' + (selected ? 'bg-[color:var(--brand-100)] dark:bg-[color:var(--brand-900)]' : '');
            li.dataset.id = it.id;
            if (type === 'abstract') {
                li.innerHTML = `
                    <span class="flex items-center gap-3 w-full">
                        <input type="checkbox" class="bulkChk accent-[color:var(--brand-600)] rounded h-5 w-5" data-id="${it.id}" ${selected ? 'checked' : ''}/>
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-900 dark:text-white truncate">${escapeHtml(it.title || 'Untitled Abstract')}</div>
                            <div class="flex flex-wrap gap-2 mt-1">
                                <span class="text-xs text-gray-500 dark:text-gray-400 truncate">(${it.category?.name || 'No Category'})</span>
                                <span class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${getStatusClass(it.status)}">${escapeHtml(it.status || 'PENDING')}</span>
                                <span class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100">Phase: ${it.review_phase || 1}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 p-3 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                            <div class="p-2 rounded-md bg-blue-100 dark:bg-blue-900/30">
                                <svg class="w-5 h-5 text-blue-50" fill="none" viewBox="0 0 24 24"
                                    stroke="currentColor" aria-hidden="true">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </div>
                            <div>
                                <div class="text-xs muted">Submitted By</div>
                                <div id="summaryAuthor" class="font-medium">${escapeHtml(it.created_by?.username || 'Unknown User')}</div>
                            </div>
                            <div class="flex items-center gap-2 p-3 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                            <div class="p-2 rounded-md bg-blue-100 dark:bg-blue-900/30">
                                <svg class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24"
                                    stroke="currentColor" aria-hidden="true">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            </div>
                            <div>
                                <div class="text-xs muted">Submitted On</div>
                                <div id="summaryDate" class="font-medium">${formatDate(it.created_at)}</div>
                            </div>
                        </div>
                    </span>
                `;
                li.addEventListener('click', (e) => { 
                    if (e.target.classList.contains('bulkChk')) return; 
                    selAbstract = it; 
                    updatePanel(); 
                    highlightSelection(); 
                });
            }
            el.appendChild(li);
        });
        if (type === 'abstract') {
            el.querySelectorAll('.bulkChk').forEach(chk => {
                chk.addEventListener('change', e => {
                    const id = e.target.getAttribute('data-id');
                    if (e.target.checked) bulk.abstractIds.add(id); else bulk.abstractIds.delete(id);
                    syncMasterChk();
                    updateBulkStatus();
                });
            });
            syncMasterChk();
        }
    }
    
    function getStatusClass(status) {
        switch ((status || '').toLowerCase()) {
            case 'accepted': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100';
            case 'rejected': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-10';
            case 'under_review': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
            default: return 'bg-blue-100 text-blue-800 dark:bg-blue-90 dark:text-blue-100';
        }
    }
    
    function syncMasterChk() {
        const master = sQ('abstractMasterChk');
        if (!master) return;
        const boxes = abstractList.querySelectorAll('.bulkChk');
        const total = boxes.length;
        const checked = Array.from(boxes).filter(b => b.checked).length;
        master.indeterminate = checked > 0 && checked < total;
        master.checked = total > 0 && checked === total;
    }
    
    function selectAllPage() {
        abstractList.querySelectorAll('.bulkChk').forEach(chk => { chk.checked = true; bulk.abstractIds.add(chk.dataset.id); });
        syncMasterChk(); updateBulkStatus();
    }
    
    function clearAllPage() {
        abstractList.querySelectorAll('.bulkChk').forEach(chk => { chk.checked = false; bulk.abstractIds.delete(chk.dataset.id); });
        syncMasterChk(); updateBulkStatus();
    }
    
    function invertSelection() {
        abstractList.querySelectorAll('.bulkChk').forEach(chk => {
            const id = chk.dataset.id;
            if (chk.checked) { chk.checked = false; bulk.abstractIds.delete(id); }
            else { chk.checked = true; bulk.abstractIds.add(id); }
        });
        syncMasterChk(); updateBulkStatus();
    }
    
    function updateBulkStatus() {
        const el = sQ('bulkStatus');
        if (el) el.textContent = bulk.abstractIds.size ? `${bulk.abstractIds.size} selected` : '';
    }
    
    function highlightSelection() {
        // Clear previous highlight
        Array.from(abstractList.children).forEach(li => li.classList.remove('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]'));
        if (selAbstract) {
            const el = abstractList.querySelector(`[data-id='${selAbstract.id}']`);
            if (el) el.classList.add('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]');
        }
    }
    
    function updatePanel() {
        const noAbstractSelected = sQ('noAbstractSelected');
        const abstractContent = sQ('abstractContent');
        if (selAbstract) {
            noAbstractSelected.classList.add('hidden');
            abstractContent.classList.remove('hidden');
            
            // Generate preview content
            generatePreview();
        } else {
            noAbstractSelected.classList.remove('hidden');
            abstractContent.classList.add('hidden');
        }
    }
    
    // Generate preview of abstract details
    function generatePreview() {
        const previewContent = sQ('preview-content');
        if (!previewContent || !selAbstract) return;
        
        // Get category name
        const categoryName = selAbstract.category?.name || 'No Category';

        updateVerifyActionBtns(selAbstract.status);
        // Update summary card info
        sQ('summaryTitle') && (sQ('summaryTitle').textContent = selAbstract.title || 'Untitled Abstract');
        sQ('summaryCategory') && (sQ('summaryCategory').textContent = categoryName);
        sQ('summaryStatus') && (sQ('summaryStatus').textContent = selAbstract.status || 'PENDING');
        sQ('summaryStatus') && (sQ('summaryStatus').className = 'badge ' + getStatusClass(selAbstract.status));
        sQ('summaryAuthor') && (sQ('summaryAuthor').textContent = selAbstract.created_by?.username || 'Unknown User');
        sQ('summaryDate') && (sQ('summaryDate').textContent = formatDate(selAbstract.created_at));

        // Generate preview HTML with improved styling
        let previewHTML = `
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
               
                <!-- Abstract Content Section -->
                <div class="p-5">
                    <div class="hidden flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h1a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Abstract Content</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Main body of the abstract</p>
                        </div>
                    
                    <div class="ml-2">
                        <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg border border-gray-200 dark:border-gray-600">
                            <p class="whitespace-pre-wrap text-gray-800 dark:text-gray-200">${escapeHtml(selAbstract.content || '')}</p>
                        </div>
                    </div>
                
                <!-- Authors Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Authors</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">List of contributing authors</p>
                        </div>
                    
                    <div class="ml-2 space-y-4">
        `;
        
        if (selAbstract.authors && selAbstract.authors.length > 0) {
            selAbstract.authors.forEach((author) => {
                const roles = [];
                if (author.is_presenter) roles.push('Presenter');
                if (author.is_corresponding) roles.push('Corresponding');
                
                previewHTML += `
                    <div class="border-l-4 border-blue-400 dark:border-blue-600 pl-4 py-2">
                        <div class="flex flex-wrap justify-between gap-2">
                            <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(author.name)}</p>
                            ${roles.length > 0 ? `<div class="flex flex-wrap gap-1">${roles.map(role => 
                                `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                                    ${role}
                                </span>`).join('')}</div>` : ''}
                        </div>
                        ${author.email ? `<p class="text-sm text-blue-600 dark:text-blue-400 mt-1">${escapeHtml(author.email)}</p>` : ''}
                        ${author.affiliation ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${escapeHtml(author.affiliation)}</p>` : ''}
                    </div>
                `;
            });
        } else {
            previewHTML += `
                <p class="text-gray-500 dark:text-gray-400 italic">No authors listed</p>
            `;
        }
        
        previewHTML += `
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
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">PDF Document</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Uploaded abstract PDF</p>
                        </div>
                    <div class="ml-2">
                        ${selAbstract.pdf_path ? `
                            <div id="pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-90/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-400">Loading PDF...</span>
                                    </div>
                                <!-- Canvases for PDF pages will be rendered here -->
                            </div>
                        ` : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No PDF uploaded for this abstract.</p>`}
                    </div>
                
                <!-- Review Phase Information -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 02 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Review Information</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Current review phase and status</p>
                        </div>
                    </div>
                    
                    <div class="ml-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                            <p class="text-sm text-gray-600 dark:text-gray-300">Current Phase</p>
                            <p class="text-xl font-bold text-gray-900 dark:text-white">Phase ${selAbstract.review_phase || 1}</p>
                        </div>
                        <div class="p-4 bg-green-50 dark:bg-green-900/30 rounded-lg">
                            <p class="text-sm text-gray-600 dark:text-gray-300">Status</p>
                            <p class="text-xl font-bold text-gray-900 dark:text-white">${escapeHtml(selAbstract.status || 'PENDING')}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        previewContent.innerHTML = previewHTML;
        // After rendering, if PDF exists, render preview using PDF.js
        if (selAbstract.pdf_path) {
            renderVerifierPdfPreview(selAbstract.id);
        }
    }
    
    // Render PDF preview for verifier using PDF.js
    function renderVerifierPdfPreview(abstractId) {
        if (typeof pdfjsLib === 'undefined') {
            const container = document.getElementById('pdf-preview-container');
            if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/vendor/pdf.worker.min.js';
        fetch(`${BASE}/abstracts/${abstractId}/pdf`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` }
        })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.arrayBuffer();
            })
            .then(buffer => {
                const typedarray = new Uint8Array(buffer);
                const loadingTask = pdfjsLib.getDocument({ data: typedarray, password: '' });
                loadingTask.promise.then(function(pdf) {
                    const container = document.getElementById('pdf-preview-container');
                    if (!container) return;
                    container.innerHTML = '';
                    const scale = 1.5;
                    // Render all pages
                    let pagePromises = [];
                    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                        pagePromises.push(
                            pdf.getPage(pageNum).then(function(page) {
                                const viewport = page.getViewport({ scale: scale });
                                const canvas = document.createElement('canvas');
                                canvas.className = 'w-full mb-4 rounded shadow';
                                canvas.height = viewport.height;
                                canvas.width = viewport.width;
                                container.appendChild(canvas);
                                const context = canvas.getContext('2d');
                                return page.render({ canvasContext: context, viewport: viewport }).promise;
                            })
                        );
                    }
                    Promise.all(pagePromises).catch(function(renderError) {
                        container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">Error rendering PDF pages.</p>';
                    });
                }).catch(function(error) {
                    const container = document.getElementById('pdf-preview-container');
                    if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-40 text-center p-4">Unable to load PDF: ' + (error.message || 'Unknown error') + '</p>';
                });
            })
            .catch(() => {
                const container = document.getElementById('pdf-preview-container');
                if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-40 text-center p-4">Unable to fetch PDF file.</p>';
            });
    }
    
    function formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    async function searchAbstracts() {
        state.abstracts.q = (sQ('abstractSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.abstracts;
        const url = `${BASE}/abstracts?q=${encodeURIComponent(q)}&status=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}&verifier=true`;
        log(`Searching abstracts with URL: ${url}`, 'info');
        try {
            const data = await fetchJSON(url);
            log(`Received ${data.items?.length || 0} abstracts`, 'info');
            renderList(abstractList, data.items || data || [], 'abstract');
            updateAbstractMeta(data);
        } catch (e) {
            logError('Failed to search abstracts:', e);
            toast('Failed to search abstracts: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    // Function to open grading modal
    let gradingModalLastFocus = null; // track focus to restore
    let gradingModalKeyHandler = null;
    async function openGradingModal() {
        if (!selAbstract) {
            toast('Please select an abstract first', 'warn');
            return;
        }

        // Set the abstract title in the modal
        sQ('gradingAbstractTitle').textContent = selAbstract.title || 'Untitled Abstract';
        
        // Fetch grading types for abstracts
        try {
            const gradingTypes = await fetchJSON(`${BASE}/grading-types?grading_for=abstract`);
            populateGradingForm(gradingTypes);

            const modal = sQ('gradingModal');
            if (!modal) return;
            gradingModalLastFocus = document.activeElement;
            modal.classList.remove('hidden');
            setupModalAccessibility(modal);
            // Wire rubric toggle (idempotent)
            const toggle = modal.querySelector('[data-toggle-rubric]');
            const body = modal.querySelector('[data-rubric-body]');
            if (toggle && body && !toggle.__bound) {
                toggle.addEventListener('click', () => {
                    const hidden = body.classList.toggle('hidden');
                    toggle.textContent = hidden ? 'Show' : 'Hide';
                });
                toggle.__bound = true;
            }
        } catch (e) {
            console.error('Error fetching grading types:', e);
            toast('Failed to load grading criteria: ' + (e.message || 'Unknown error'), 'error');
        }
    }

    function setupModalAccessibility(modal){
        // Overlay click closes
        if (!modal.__overlayBound){
            modal.addEventListener('click', e => {
                if (e.target === modal) {
                    closeGradingModal();
                }
            });
            modal.__overlayBound = true;
        }
        // Focus trap
        const focusableSelector = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
        const focusables = Array.from(modal.querySelectorAll(focusableSelector)).filter(el => el.offsetParent !== null);
        if (focusables.length){
            // focus first scoring input if possible
            const firstScore = modal.querySelector('#gradingFieldsContainer input');
            (firstScore || focusables[0]).focus({preventScroll:true});
        } else {
            modal.setAttribute('tabindex', '-1');
            modal.focus({preventScroll:true});
        }
        // Key handler
        gradingModalKeyHandler = function(e){
            if (e.key === 'Escape'){ e.preventDefault(); closeGradingModal(); return; }
            if (e.key === 'Tab'){
                const currentFocusables = Array.from(modal.querySelectorAll(focusableSelector)).filter(el => el.offsetParent !== null);
                if (!currentFocusables.length) return;
                const first = currentFocusables[0];
                const last = currentFocusables[currentFocusables.length -1];
                if (e.shiftKey && document.activeElement === first){
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last){
                    e.preventDefault();
                    first.focus();
                }
            }
        };
        document.addEventListener('keydown', gradingModalKeyHandler, true);
    }

    function closeGradingModal(){
        const modal = sQ('gradingModal');
        sQ('gradingSkeleton').classList.remove('hidden');
        if (modal) modal.classList.add('hidden');
        if (gradingModalKeyHandler){
            document.removeEventListener('keydown', gradingModalKeyHandler, true);
            gradingModalKeyHandler = null;
        }
        if (gradingModalLastFocus && document.contains(gradingModalLastFocus)) {
            try { gradingModalLastFocus.focus({preventScroll:true}); } catch(_){}
        }

    }

    // Function to populate the grading form with grading types
    function populateGradingForm(gradingTypes) {
        const container = sQ('gradingFieldsContainer');
        container.innerHTML = '';  // Clear existing fields

        if (!gradingTypes || gradingTypes.length === 0) {
            container.innerHTML = '<p class="text-gray-500 dark:text-gray-400 p-4 text-center">No grading criteria available.</p>';
            return;
        }

        // Summary footer (will fill live)
        let aggregateFooter = sQ('gradingAggregateSummary');
          if (!aggregateFooter) {
                aggregateFooter = document.createElement('div');
                aggregateFooter.id = 'gradingAggregateSummary';
                aggregateFooter.className = 'mt-6 rounded-xl border border-[color:var(--border)]/60 bg-gray-50 dark:bg-gray-800/60 p-4 text-xs flex flex-col gap-2 relative';
                aggregateFooter.innerHTML = `
                     <div class="flex flex-wrap gap-4">
                         <span><strong>Total:</strong> <span data-total-score>-</span></span>
                         <span><strong>Average:</strong> <span data-average-score>-</span></span>
                         <span><strong>Filled:</strong> <span data-filled-count>0</span>/<span data-total-count>0</span></span>
                     </div>
                     <div class="relative h-2 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
                         <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-[color:var(--brand-600)] to-[color:var(--brand-40)] transition-all" data-filled-bar style="width:0%"></div>
                     </div>
                     <div id="gradingAggregateLive" role="status" aria-live="polite" class="absolute w-px h-px -m-px overflow-hidden whitespace-nowrap border-0 p-0">No scores yet.</div>`;
          }

        const gradingStateKey = selAbstract ? `grading_state_${selAbstract.id}` : null;
        let persistedState = {};
        if (gradingStateKey) {
            try { persistedState = JSON.parse(localStorage.getItem(gradingStateKey) || '{}'); } catch (_) { persistedState = {}; }
        }

        const fieldsMeta = []; // track for summary

        // Create input fields for each grading type with enhanced UI (numeric + synchronized range slider + scale + validation badge + tooltip)
        gradingTypes.forEach(type => {
                        const min = Number(type.min_score);
                        const max = Number(type.max_score);
                        const span = max - min;
                        const safeId = `grading_${type.id}`;
                        const fieldDiv = document.createElement('div');
                        fieldDiv.className = 'mb-4 p-4 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-[color:var(--border)]/60 shadow-sm hover:shadow transition-shadow';
                        fieldDiv.innerHTML = `
                                <div class="flex items-start justify-between gap-3 mb-2">
                                    <label for="${safeId}_number" class="group block text-sm font-semibold text-gray-80 dark:text-gray-200 relative">
                                        <span class="inline-flex items-center gap-1">
                                          <span>${escapeHtml(type.criteria)}</span>
                                          <span class="ml-1 text-[color:var(--text-muted)] font-normal">(${min} - ${max})</span>
                                          <span class="inline-flex items-center justify-center w-4 h-4 text-[10px] rounded-full bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 cursor-help" data-tooltip="Score range: ${min}-${max}. Use consistent rubric.">i</span>
                                          <span class="ml-1" data-validity-badge aria-hidden="true"></span>
                                        </span>
                                        <span class="invisible opacity-0 group-hover:opacity-100 group-hover:visible transition pointer-events-none absolute z-10 top-full left-0 mt-1 w-48 text-[10px] leading-snug bg-black/80 text-white rounded px-2 py-1" role="tooltip">${escapeHtml(type.description || 'Provide a fair score based on the rubric.')}</span>
                                    </label>
                                    <div class="text-[10px] uppercase tracking-wide rounded-full px-2 py-0.5 bg-[color:var(--brand-50)] dark:bg-[color:var(--brand-900)]/40 text-[color:var(--brand-600)] dark:text-[color:var(--brand-300)] font-medium" data-range-pill>${span} range</div>
                                </div>
                                <div class="grid grid-cols-5 gap-3 items-center">
                                     <div class="col-span-2 flex flex-col gap-1">
                                            <input 
                                                id="${safeId}_number"
                                                type="number" 
                                                name="${safeId}" 
                                                min="${min}" 
                                                max="${max}" 
                                                inputmode="numeric"
                                                class="input w-full text-sm font-medium" 
                                                placeholder="${min} - ${max}"
                                                aria-describedby="${safeId}_help"
                                                required
                                            />
                                            <div class="relative h-2 mt-1 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden" aria-hidden="true">
                                                <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-[color:var(--brand-500)] to-[color:var(--brand-300)] transition-all" data-progress style="width:0%"></div>
                                                <div class="absolute inset-0 flex justify-between text-[8px] leading-none text-gray-500 dark:text-gray-400 pt-2 select-none">
                                                    <span>${min}</span><span>${Math.round(min + span * 0.25)}</span><span>${Math.round(min + span * 0.5)}</span><span>${Math.round(min + span * 0.75)}</span><span>${max}</span>
                                                </div>
                                            </div>
                                     <div class="col-span-3 flex flex-col gap-1">
                                            <input 
                                                id="${safeId}_range"
                                                type="range" 
                                                min="${min}" 
                                                max="${max}" 
                                                step="1" 
                                                class="w-full accent-[color:var(--brand-600)] cursor-pointer" 
                                                aria-label="${escapeHtml(type.criteria)} score slider"
                                            />
                                            <div class="flex justify-between text-[10px] text-gray-500 dark:text-gray-400 font-medium">
                                                <span>Low</span><span class="text-[color:var(--brand-600)] dark:text-[color:var(--brand-400)]">Score</span><span>High</span>
                                            </div>
                                     </div>
                                <button type="button" data-toggle-comment class="mt-3 text-[11px] font-medium inline-flex items-center gap-1 text-[color:var(--brand-600)] hover:underline focus:outline-none">
                                     <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg>
                                     Add Comment
                                </button>
                                <textarea 
                                        name="comment_${type.id}" 
                                        class="hidden mt-2 input w-full text-xs" 
                                        placeholder="Comment on ${escapeHtml(type.criteria)} (optional)..." 
                                        rows="2"
                                        data-comment-box
                                ></textarea>
                                <p id="${safeId}_help" class="mt-2 text-[10px] leading-relaxed text-gray-500 dark:text-gray-400">
                                     Use either the number box or slider. Progress bar shows relative score.
                                </p>
                        `;
                        container.appendChild(fieldDiv);

                        // Metadata for summary & validation
                        fieldsMeta.push({ id: safeId, min, max, numberSelector: `#${safeId}_number` });

                        // Wiring interactions & validation
                        const numberInput = fieldDiv.querySelector(`#${safeId}_number`);
                        const rangeInput = fieldDiv.querySelector(`#${safeId}_range`);
                        const progress = fieldDiv.querySelector('[data-progress]');
                        const toggleBtn = fieldDiv.querySelector('[data-toggle-comment]');
                        const commentBox = fieldDiv.querySelector('[data-comment-box]');
                        const validityBadge = fieldDiv.querySelector('[data-validity-badge]');

                        // Restore persisted value if exists
                        if (persistedState[safeId]?.score != null) {
                            const v = persistedState[safeId].score;
                            numberInput.value = v;
                            rangeInput.value = v;
                        }
                        if (persistedState[safeId]?.comment) {
                            commentBox.classList.remove('hidden');
                            commentBox.value = persistedState[safeId].comment;
                            toggleBtn.innerHTML = '<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18 12H6" /></svg> Remove Comment';
                        }

                        function updateProgress(val) {
                                const num = Number(val);
                                if (isNaN(num)) { progress.style.width = '0%'; return; }
                                const pct = ((num - min) / (max - min)) * 10;
                                progress.style.width = `${Math.min(Math.max(pct, 0), 100)}%`;
                                updateValidity();
                                updateAggregate();
                                persist();
                        }

                        function updateValidity() {
                            const val = Number(numberInput.value);
                            if (!isNaN(val) && val >= min && val <= max) {
                                validityBadge.innerHTML = '<svg class="w-4 h-4 text-green-600 dark:text-green-40" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>';
                            } else if (numberInput.value !== '') {
                                validityBadge.innerHTML = '<svg class="w-4 h-4 text-red-600 dark:text-red-40" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>';
                            } else {
                                validityBadge.innerHTML = '';
                            }
                        }

                        numberInput.addEventListener('input', (e) => {
                                let val = numberInput.value;
                                if (val === '') { updateProgress(null); return; }
                                let num = Number(val);
                                if (num < min) num = min; if (num > max) num = max;
                                numberInput.value = String(num);
                                rangeInput.value = String(num);
                                updateProgress(num);
                        });
                        rangeInput.addEventListener('input', () => {
                            numberInput.value = rangeInput.value;
                            updateProgress(rangeInput.value);
                        });

                        // Keyboard shortcuts (Up/Down) on number or range
                        function stepValue(delta) {
                            let current = numberInput.value === '' ? min : Number(numberInput.value);
                            if (isNaN(current)) current = min;
                            current += delta;
                            if (current < min) current = min; if (current > max) current = max;
                            numberInput.value = String(current);
                            rangeInput.value = String(current);
                            updateProgress(current);
                        }
                        numberInput.addEventListener('keydown', e => {
                            if (e.key === 'ArrowUp') { e.preventDefault(); stepValue(1); }
                            else if (e.key === 'ArrowDown') { e.preventDefault(); stepValue(-1); }
                        });
                        rangeInput.addEventListener('keydown', e => {
                            if (e.key === 'ArrowUp') { e.preventDefault(); stepValue(1); }
                            else if (e.key === 'ArrowDown') { e.preventDefault(); stepValue(-1); }
                        });
                        toggleBtn.addEventListener('click', () => {
                                const hidden = commentBox.classList.contains('hidden');
                                commentBox.classList.toggle('hidden');
                                toggleBtn.innerHTML = hidden
                                    ? '<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18 12H6" /></svg> Remove Comment'
                                    : '<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg> Add Comment';
                                if (!hidden) commentBox.value = '';
                                if (!hidden) commentBox.blur(); else commentBox.focus();
                                persist();
                        });

                        commentBox.addEventListener('input', persist);
                        updateProgress(numberInput.value || null);
                        updateValidity();
                });

        // Append footer (after fields) & initialize counters
        if (aggregateFooter.parentElement !== container.parentElement) {
            // place after container
            container.parentElement.appendChild(aggregateFooter);
        }
        aggregateFooter.querySelector('[data-total-count]').textContent = String(fieldsMeta.length);
        updateAggregate();

        hideSkeletons();

        // Inject reset button if not exists
        if (!aggregateFooter.querySelector('[data-reset-grading]')) {
            const controls = document.createElement('div');
            controls.className = 'flex flex-wrap items-center gap-2 pt-3 border-t border-[color:var(--border)]/50 mt-2';
            controls.innerHTML = `
               <button type="button" data-reset-grading class="px-3 py-1.5 text-xs font-medium rounded-md bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/50 border border-red-200 dark:border-red-800 focus:outline-none focus:ring-2 focus:ring-red-400/60">Reset All Scores</button>
               <span class="text-[10px] text-gray-500 dark:text-gray-400">(Clears scores, comments & draft)</span>
            `;
            aggregateFooter.appendChild(controls);
            controls.querySelector('[data-reset-grading]').addEventListener('click', () => {
                // Clear inputs & comments
                fieldsMeta.forEach(m => {
                    const numEl = container.querySelector(m.numberSelector);
                    const rangeEl = container.querySelector(`#${m.id}_range`);
                    const commentEl = container.querySelector(`textarea[name='comment_${m.id.replace('grading_','')}']`);
                    const toggleBtn = commentEl ? commentEl.parentElement.querySelector('[data-toggle-comment]') : null;
                    if (numEl) numEl.value = '';
                    if (rangeEl) rangeEl.value = String(m.min);
                    if (commentEl) {
                        commentEl.value = '';
                        if (!commentEl.classList.contains('hidden')) {
                            commentEl.classList.add('hidden');
                            if (toggleBtn) toggleBtn.innerHTML = '<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" /></svg> Add Comment';
                        }
                    }
                    const fieldValidityBadge = container.querySelector(`#${m.id}_number`)?.closest('.mb-4')?.querySelector('[data-validity-badge]');
                    if (fieldValidityBadge) fieldValidityBadge.innerHTML='';
                    const progressEl = container.querySelector(`#${m.id}_number`)?.closest('.flex.flex-col')?.querySelector('[data-progress]');
                    if (progressEl) progressEl.style.width='0%';
                });
                // Ensure all remaining badges cleared (fallback)
                container.querySelectorAll('[data-validity-badge]').forEach(b => b.innerHTML='');
                if (gradingStateKey) localStorage.removeItem(gradingStateKey);
                updateAggregate();
                persist(); // will write empty snapshot
                toast('Draft cleared','info');
            });
        }

        function updateAggregate() {
            const scores = fieldsMeta.map(m => {
                const el = container.querySelector(m.numberSelector);
                const val = Number(el?.value);
                return isNaN(val) ? null : val;
            }).filter(v => v != null);
            const filled = scores.length;
            const total = scores.reduce((a,b)=>a+b,0);
            const avg = filled ? (total / filled) : 0;
            aggregateFooter.querySelector('[data-filled-count]').textContent = String(filled);
            aggregateFooter.querySelector('[data-total-score]').textContent = filled ? total.toFixed(2).replace(/\.00$/,'') : '-';
            aggregateFooter.querySelector('[data-average-score]').textContent = filled ? avg.toFixed(2) : '-';
            const pct = fieldsMeta.length ? (filled / fieldsMeta.length) * 100 : 0;
            aggregateFooter.querySelector('[data-filled-bar]').style.width = pct + '%';
            const live = aggregateFooter.querySelector('#gradingAggregateLive');
            if (live) {
                live.textContent = filled ? `Filled ${filled} of ${fieldsMeta.length}. Total ${total.toFixed(2)}. Average ${avg.toFixed(2)}.` : 'No scores yet.';
            }

            // Side panel metrics (if present due to revamped UI)
            const sideTotal = document.querySelector('[data-score-total]');
            const sideAvg = document.querySelector('[data-score-average]');
            const sideAvgBig = document.querySelector('[data-score-avg]');
            const sideFilled = document.querySelector('[data-score-filled]');
            const sideProgress = document.querySelector('[data-score-progress]');
            const ring = document.querySelector('[data-score-ring]');
            if (sideTotal) sideTotal.textContent = filled ? total.toFixed(2).replace(/\.0$/,'') : '-';
            if (sideAvg) sideAvg.textContent = filled ? avg.toFixed(2) : '-';
            if (sideAvgBig) sideAvgBig.textContent = filled ? avg.toFixed(1) : '-';
            if (sideFilled) sideFilled.textContent = `${filled}/${fieldsMeta.length}`;
            if (sideProgress) sideProgress.style.width = pct + '%';
            if (ring) {
                const circumference = 2 * Math.PI * 54; // r=54
                const ratio = fieldsMeta.length ? (avg - Math.min(...scores, 0)) / (Math.max(...scores, 1) - Math.min(...scores, 0) || 1) : 0;
                // fallback: simple proportion of average vs max possible score
                const maxPossibleAvg = fieldsMeta.length ? Math.max(...fieldsMeta.map(m=>m.max)) : 1;
                const normalized = filled ? Math.min(Math.max(avg / maxPossibleAvg, 0), 1) : 0;
                ring.style.strokeDashoffset = String(circumference - (circumference * normalized));
            }
        }

        function persist() {
            if (!gradingStateKey) return;
            const snapshot = {};
            fieldsMeta.forEach(m => {
                const scoreEl = container.querySelector(m.numberSelector);
                const commentEl = container.querySelector(`textarea[name='comment_${m.id.replace('grading_','')}']`);
                const val = scoreEl?.value;
                const comment = commentEl?.classList.contains('hidden') ? '' : (commentEl?.value || '');
                if (val || comment) {
                    snapshot[m.id] = { score: val === '' ? null : Number(val), comment };
                }
            });
            try { localStorage.setItem(gradingStateKey, JSON.stringify(snapshot)); } catch (_) {}
        }


        function hideSkeletons(){
            sQ('gradingSkeleton').classList.add('hidden');
        }

        // Clear persistence when modal closed & submitted (handled elsewhere on success)
    }

    // Function to submit grading and accept the abstract
    async function submitGrading() {
        const form = sQ('gradingForm');
        
        // Validate form inputs
        const gradingInputs = form.querySelectorAll('input[name^="grading_"]');
        let isValid = true;
        
        gradingInputs.forEach(input => {
            const value = parseInt(input.value);
            const min = parseInt(input.min);
            const max = parseInt(input.max);
            
            if (isNaN(value) || value < min || value > max) {
                input.classList.add('border-red-500');
                isValid = false;
            } else {
                input.classList.remove('border-red-500');
            }
        });
        
        if (!isValid) {
            toast('Please ensure all scores are within the valid range', 'error');
            return;
        }
        
        try {
            // Prepare grading data
            const gradingData = [];
            gradingInputs.forEach(input => {
                const gradingTypeId = input.name.replace('grading_', '');
                const score = parseInt(input.value);
                const commentInput = form.querySelector(`textarea[name="comment_${gradingTypeId}"]`);
                const comments = commentInput ? commentInput.value : '';
                
                if (!isNaN(score)) {
                    gradingData.push({
                        grading_type_id: gradingTypeId,
                        score: score,
                        comments: comments,
                        abstract_id: selAbstract.id,
                        review_phase: selAbstract.review_phase  // Include the current review phase
                    });
                }
            });
            
            // Submit each grading individually
            for (const grade of gradingData) {
                await fetchJSON(`${BASE}/gradings`, {
                    method: 'POST',
                    headers: { ...headers(), 'Content-Type': 'application/json' },
                    body: JSON.stringify(grade)
                });
            }
            
            // After grading is submitted, accept the abstract
            await acceptAbstract(selAbstract.id);
            
            // Close the modal
            // Clear persisted draft for this abstract (scores committed)
            try { localStorage.removeItem(`grading_state_${selAbstract.id}`); } catch(_){}
            closeGradingModal();
            sQ('overallComments').value = '';  // Clear overall comments
            
            toast('Abstract graded and accepted successfully!', 'success');
        } catch (e) {
            console.error('Error submitting grading:', e);
            toast('Failed to submit grading: ' + (e.message || 'Unknown error'), 'error');
        }
    }

    // Function to cancel grading
    function cancelGrading() {
        closeGradingModal();
        sQ('overallComments').value = '';  // Clear overall comments
    }

    async function acceptAbstract(abstractId) {
        log(`Accepting abstract with ID: ${abstractId}`, 'info');
        try {
            const r = await fetch(`${BASE}/abstracts/${abstractId}/accept`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' }
            });
            if (!r.ok) {
                const errorText = await r.text();
                logError(`Failed to accept abstract ${abstractId}: ${r.status}`, new Error(errorText || r.status));
                throw new Error(errorText || r.status);
            }
            log(`Abstract ${abstractId} accepted successfully`, 'info');
            toast('Abstract accepted successfully!', 'success');
            await searchAbstracts();
            if (selAbstract && selAbstract.id === abstractId) {
                selAbstract = null;
                updatePanel();
                highlightSelection();
            }
            updateVerifyActionBtns('ACCEPTED');
        } catch (e) {
            logError(`Failed to accept abstract ${abstractId}:`, e);
            toast('Failed to accept abstract: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function rejectAbstract(abstractId) {
        log(`Prompting for rejection of abstract with ID: ${abstractId}`, 'info');
        if (!confirm('Are you sure you want to reject this abstract?')) return;
        
        try {
            const r = await fetch(`${BASE}/abstracts/${abstractId}/reject`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' }
            });
            if (!r.ok) {
                const errorText = await r.text();
                logError(`Failed to reject abstract ${abstractId}: ${r.status}`, new Error(errorText || r.status));
                throw new Error(errorText || r.status);
            }
            log(`Abstract ${abstractId} rejected successfully`, 'info');
            toast('Abstract rejected successfully!', 'success');
            await searchAbstracts();
            if (selAbstract && selAbstract.id === abstractId) {
                selAbstract = null;
                updatePanel();
                highlightSelection();
            }
            updateVerifyActionBtns('REJECTED');
        } catch (e) {
            logError(`Failed to reject abstract ${abstractId}:`, e);
            toast('Failed to reject abstract: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    function updateAbstractMeta(data) {
        state.abstracts.pages = data.pages || 1;
        const info = sQ('abstractPageInfo');
        if (info) info.textContent = `Page ${data.page || 1} / ${data.pages || 1}`;
        const stats = sQ('abstractStats');
        if (stats) {
            const filterLabel = state.abstracts.filter === '' ? 'All' : state.abstracts.filter.charAt(0).toUpperCase() + state.abstracts.filter.slice(1);
            stats.textContent = `${data.total || 0} total • Filter: ${filterLabel}`;
        }
    }

    function changeAbstractPage(delta) {
        state.abstracts.page = Math.min(Math.max(1, state.abstracts.page + delta), state.abstracts.pages);
        searchAbstracts();
    }

    function toast(msg, type = 'info') {
        // Create a toast notification
        const toastContainer = document.getElementById('toast-container') || createToastContainer();
        
        const toastEl = document.createElement('div');
        toastEl.className = `mb-2 p-3 rounded-lg text-white font-medium text-sm flex items-center gap-2 transform transition-all duration-300 ${type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : type === 'warn' ? 'bg-yellow-500' : 'bg-blue-500'}`;
        
        const icon = document.createElement('span');
        icon.innerHTML = type === 'success' ? 
            '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>' :
            type === 'error' ? 
            '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>' :
            '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>';
        
        toastEl.appendChild(icon);
        toastEl.appendChild(document.createTextNode(msg));
        
        toastContainer.appendChild(toastEl);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toastEl.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => {
                if (toastEl.parentNode) toastEl.parentNode.removeChild(toastEl);
            }, 300);
        }, 3000);
    }
    
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-4 right-4 z-50 w-80';
        document.body.appendChild(container);
        return container;
    }
    
    function escapeHtml(s) {
        return String(s).replaceAll('&', '&').replaceAll('<', '<').replaceAll('>', '>').replaceAll('"', '"').replaceAll("'", '&#039;');
    }

    function init() {
        log('Initializing abstract verification page...', 'info');
        updateStatsBar();
        sQ('abstractSearchBtn')?.addEventListener('click', () => { 
            log('Search button clicked', 'info');
            state.abstracts.page = 1; 
            searchAbstracts(); 
        });
        sQ('abstractSearch')?.addEventListener('keypress', (e) => { 
            if (e.key === 'Enter') { 
                log('Enter key pressed in search', 'info');
                state.abstracts.page = 1; 
                searchAbstracts(); 
            } 
        });
        sQ('abstractPrev')?.addEventListener('click', () => {
            log('Previous page button clicked', 'info');
            changeAbstractPage(-1);
        });
        sQ('abstractNext')?.addEventListener('click', () => {
            log('Next page button clicked', 'info');
            changeAbstractPage(1);
        });
        sQ('acceptBtn')?.addEventListener('click', () => {
            log('Accept button clicked', 'info');
            openGradingModal();
        });  // Changed to open grading modal
        sQ('rejectBtn')?.addEventListener('click', () => {
            if (selAbstract) {
                log(`Reject button clicked for abstract ID: ${selAbstract.id}`, 'info');
                rejectAbstract(selAbstract.id);
            } else {
                toast('Please select an abstract first', 'warn');
            }
        });

        // Grading modal events
        sQ('closeGradingModal')?.addEventListener('click', () => {
            log('Grading modal close button clicked', 'info');
            cancelGrading();
        });
        sQ('cancelGrading')?.addEventListener('click', () => {
            log('Cancel grading button clicked', 'info');
            cancelGrading();
        });
        sQ('submitGrading')?.addEventListener('click', () => {
            log('Submit grading button clicked', 'info');
            submitGrading();
        });

        const master = sQ('abstractMasterChk');
        master?.addEventListener('change', e => { 
            log(`Master checkbox changed, checked: ${e.target.checked}`, 'info');
            e.target.checked ? selectAllPage() : clearAllPage(); 
        });
        sQ('invertSelection')?.addEventListener('click', () => {
            log('Invert selection button clicked', 'info');
            invertSelection();
        });
        sQ('abstractSelectAll')?.addEventListener('click', () => {
            log('Select all button clicked', 'info');
            selectAllPage();
        });
        sQ('abstractClearSel')?.addEventListener('click', () => {
            log('Clear selection button clicked', 'info');
            clearAllPage();
        });
        sQ('bulkAcceptBtn')?.addEventListener('click', async () => {
            if (bulk.abstractIds.size === 0) {
                toast('Select abstracts to accept', 'warn');
                return;
            }
            
            if (!confirm(`Are you sure you want to accept ${bulk.abstractIds.size} abstract(s)?`)) return;
            
            log(`Bulk accepting ${bulk.abstractIds.size} abstracts`, 'info');
            
            // Show loading state
            const bulkStatus = sQ('bulkStatus');
            const originalText = bulkStatus.textContent;
            bulkStatus.textContent = 'Processing...';
            
            try {
                // Get only pending abstracts
                const ids = Array.from(bulk.abstractIds);
                let pendingIds = [];
                
                for (const id of ids) {
                    try {
                        const data = await fetchJSON(`/api/v1/research/abstracts/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        logError(`Failed to fetch abstract ${id}:`, e);
                    }
                }
                
                if (pendingIds.length === 0) {
                    toast('No selected abstracts are pending', 'warn');
                    return;
                }
                
                if (pendingIds.length < ids.length) {
                    const skipped = ids.length - pendingIds.length;
                    toast(`${skipped} abstract(s) are not pending and will be skipped.`, 'warn');
                }
                
                // Process pending abstracts
                let successCount = 0;
                for (const id of pendingIds) {
                    try {
                        const body = { status: 'ACCEPTED' };
                        const r = await fetch(`${BASE}/abstracts/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.abstractIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        logError(`Failed to accept abstract ${id}:`, e);
                    }
                }
                
                updateBulkStatus();
                syncMasterChk();
                
                if (successCount > 0) {
                    toast(`Successfully accepted ${successCount} abstract(s)`, 'success');
                    log(`Successfully bulk accepted ${successCount} abstracts`, 'info');
                    await searchAbstracts(); // Refresh the list
                } else {
                    toast('Failed to accept any abstracts', 'error');
                }
            } catch (e) {
                logError('Error processing bulk accept:', e);
                toast('Error processing bulk accept: ' + (e.message || 'Unknown error'), 'error');
            } finally {
                bulkStatus.textContent = originalText;
            }
        });
        
        sQ('bulkRejectBtn')?.addEventListener('click', async () => {
            if (bulk.abstractIds.size === 0) {
                toast('Select abstracts to reject', 'warn');
                return;
            }
            
            if (!confirm(`Are you sure you want to reject ${bulk.abstractIds.size} abstract(s)?`)) return;
            
            log(`Bulk rejecting ${bulk.abstractIds.size} abstracts`, 'info');
            
            // Show loading state
            const bulkStatus = sQ('bulkStatus');
            const originalText = bulkStatus.textContent;
            bulkStatus.textContent = 'Processing...';
            
            try {
                // Get only pending abstracts
                const ids = Array.from(bulk.abstractIds);
                let pendingIds = [];
                
                for (const id of ids) {
                    try {
                        const data = await fetchJSON(`/api/v1/research/abstracts/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        logError(`Failed to fetch abstract ${id}:`, e);
                    }
                }
                
                if (pendingIds.length === 0) {
                    toast('No selected abstracts are pending', 'warn');
                    return;
                }
                
                if (pendingIds.length < ids.length) {
                    const skipped = ids.length - pendingIds.length;
                    toast(`${skipped} abstract(s) are not pending and will be skipped.`, 'warn');
                }
                
                // Process pending abstracts
                let successCount = 0;
                for (const id of pendingIds) {
                    try {
                        const body = { status: 'REJECTED' };
                        const r = await fetch(`${BASE}/abstracts/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.abstractIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        logError(`Failed to reject abstract ${id}:`, e);
                    }
                }
                
                updateBulkStatus();
                syncMasterChk();
                
                if (successCount > 0) {
                    toast(`Successfully rejected ${successCount} abstract(s)`, 'success');
                    log(`Successfully bulk rejected ${successCount} abstracts`, 'info');
                    await searchAbstracts(); // Refresh the list
                } else {
                    toast('Failed to reject any abstracts', 'error');
                }
            } catch (e) {
                logError('Error processing bulk reject:', e);
                toast('Error processing bulk reject: ' + (e.message || 'Unknown error'), 'error');
            } finally {
                bulkStatus.textContent = originalText;
            }
        });
        
        wireSortGroups();
        wireSegmentedControls();
        log('Starting initial search for abstracts...', 'info');
        searchAbstracts();
    }
    
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

    // ==== EXTRA INITIALIZERS (CSP-safe) ====
    function initSidePanelCollapse(){
        const sidePanel = document.querySelector('#gradingModal [data-side-panel]');
        if(!sidePanel) return;
        const threshold = 640;
        function adjust(){
            if(window.innerHeight < threshold) sidePanel.classList.add('collapsed');
            else sidePanel.classList.remove('collapsed');
        }
        window.addEventListener('resize', adjust);
        adjust();
    }

    function initCriteriaFilter(){
        const input = document.getElementById('criteriaFilter');
        if(!input) return;
        function apply(){
            const q = input.value.trim().toLowerCase();
            const cards = document.querySelectorAll('#gradingFieldsContainer [data-criteria-card]');
            let shown = 0;
            cards.forEach(card => {
                const label = card.getAttribute('data-label') || card.querySelector('[data-criteria-label]')?.textContent || '';
                if(!q || label.toLowerCase().includes(q)){
                    card.classList.remove('hidden');
                    shown++;
                } else {
                    card.classList.add('hidden');
                }
            });
            const cont = document.getElementById('gradingFieldsContainer');
            if(cont) cont.dataset.visibleCount = String(shown);
        }
        input.addEventListener('input', apply);
        document.addEventListener('gradingCriteriaPopulated', apply);
    }

    if(document.readyState === 'loading'){
        document.addEventListener('DOMContentLoaded', () => { initSidePanelCollapse(); initCriteriaFilter(); });
    } else {
        initSidePanelCollapse();
        initCriteriaFilter();
    }
})();