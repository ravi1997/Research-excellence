(() => {
    const BASE = '/video';
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
            const resp = await fetch('/video/api/v1/research/abstracts/status', {
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

    // Hide Accept/Reject buttons if status is not PENDING
    function updateVerifyActionBtns(status) {
        var btns = sQ('verifyActionBtns');
        if (!btns) return;
        if ((status || '').toUpperCase() === 'STATUS.PENDING') btns.classList.remove('hidden');
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
        const bar = document.getElementById('globalLoading');
        bar && bar.classList.remove('hidden');
        try {
            const r = await fetch(url, { headers: headers(), ...opts });
            if (!r.ok) throw new Error(await r.text() || r.status);
            return r.json();
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
                            </div>
                        </div>
                        <div class="flex items-center gap-2 p-3 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                            <div class="p-2 rounded-md bg-blue-100 dark:bg-blue-900/30">
                                <svg class="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24"
                                    stroke="currentColor" aria-hidden="true">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </div>
                            <div>
                                <div class="text-xs muted">Submitted By</div>
                                <div id="summaryAuthor" class="font-medium">${escapeHtml(it.created_by?.username || 'Unknown User')}</div>
                            </div>
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
            case 'rejected': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100';
            case 'under_review': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100';
            default: return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100';
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
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Abstract Content</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Main body of the abstract</p>
                        </div>
                    </div>
                    
                    <div class="ml-2">
                        <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg border border-gray-200 dark:border-gray-600">
                            <p class="whitespace-pre-wrap text-gray-800 dark:text-gray-200">${escapeHtml(selAbstract.content || '')}</p>
                        </div>
                    </div>
                </div>
                
                <!-- Authors Section -->
                <div class="p-5">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Authors</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">List of contributing authors</p>
                        </div>
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
                    </div>
                    <div class="ml-2">
                        ${selAbstract.pdf_path ? `
                            <div id="pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800" style="max-height: 500px; overflow-y: auto;">
                                <div class="p-4 text-center">
                                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span class="text-blue-600 dark:text-blue-400">Loading PDF...</span>
                                    </div>
                                </div>
                                <!-- Canvases for PDF pages will be rendered here -->
                            </div>
                        ` : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No PDF uploaded for this abstract.</p>`}
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
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/video/static/js/pdf.worker.min.js';
        fetch(`/video/api/v1/research/abstracts/${abstractId}/pdf`, {
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
                    if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to load PDF: ' + (error.message || 'Unknown error') + '</p>';
                });
            })
            .catch(() => {
                const container = document.getElementById('pdf-preview-container');
                if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">Unable to fetch PDF file.</p>';
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
        const url = `${BASE}/api/v1/research/abstracts?q=${encodeURIComponent(q)}&status=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}&verifier=true`;
        try {
            const data = await fetchJSON(url);
            renderList(abstractList, data.items || data || [], 'abstract');
            updateAbstractMeta(data);
        } catch (e) {
            console.error(e);
            toast('Failed to search abstracts: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function acceptAbstract(abstractId) {
        if (!confirm('Are you sure you want to accept this abstract?')) return;
        
        try {
            const body = {
                status: 'ACCEPTED',
            };
            const r = await fetch(`${BASE}/api/v1/research/abstracts/${abstractId}`, {
                method: 'PUT',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Abstract accepted successfully!', 'success');
            await searchAbstracts();
            if (selAbstract && selAbstract.id === abstractId) {
                selAbstract = null;
                updatePanel();
                highlightSelection();
            }
            updateVerifyActionBtns('ACCEPTED');
        } catch (e) {
            toast('Failed to accept abstract: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function rejectAbstract(abstractId) {
        if (!confirm('Are you sure you want to reject this abstract?')) return;
        
        try {
            const body = {
                status: 'REJECTED'
            };
            const r = await fetch(`${BASE}/api/v1/research/abstracts/${abstractId}`, {
                method: 'PUT',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Abstract rejected successfully!', 'success');
            await searchAbstracts();
            if (selAbstract && selAbstract.id === abstractId) {
                selAbstract = null;
                updatePanel();
                highlightSelection();
            }
            updateVerifyActionBtns('REJECTED');
        } catch (e) {
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
        toastEl.className = `mb-2 p-3 rounded-lg text-white font-medium text-sm flex items-center gap-2 transform transition-all duration-300 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            type === 'warn' ? 'bg-yellow-500' : 
            'bg-blue-500'
        }`;
        
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
        return String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
    }

    function init() {
        updateStatsBar();
        sQ('abstractSearchBtn')?.addEventListener('click', () => { state.abstracts.page = 1; searchAbstracts(); });
        sQ('abstractSearch')?.addEventListener('keypress', (e) => { if (e.key === 'Enter') { state.abstracts.page = 1; searchAbstracts(); } });
        sQ('abstractPrev')?.addEventListener('click', () => changeAbstractPage(-1));
        sQ('abstractNext')?.addEventListener('click', () => changeAbstractPage(1));
        sQ('acceptBtn')?.addEventListener('click', () => {
            if (selAbstract) {
                acceptAbstract(selAbstract.id);
            } else {
                toast('Please select an abstract first', 'warn');
            }
        });
        sQ('rejectBtn')?.addEventListener('click', () => {
            if (selAbstract) {
                rejectAbstract(selAbstract.id);
            } else {
                toast('Please select an abstract first', 'warn');
            }
        });

        const master = sQ('abstractMasterChk');
        master?.addEventListener('change', e => { e.target.checked ? selectAllPage() : clearAllPage(); });
        sQ('invertSelection')?.addEventListener('click', invertSelection);
        sQ('abstractSelectAll')?.addEventListener('click', selectAllPage);
        sQ('abstractClearSel')?.addEventListener('click', clearAllPage);
        sQ('bulkAcceptBtn')?.addEventListener('click', async () => {
            if (bulk.abstractIds.size === 0) {
                toast('Select abstracts to accept', 'warn');
                return;
            }
            
            if (!confirm(`Are you sure you want to accept ${bulk.abstractIds.size} abstract(s)?`)) return;
            
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
                        const data = await fetchJSON(`/video/api/v1/research/abstracts/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        console.warn(`Failed to fetch abstract ${id}:`, e);
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
                        const r = await fetch(`${BASE}/api/v1/research/abstracts/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.abstractIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        console.error(`Failed to accept abstract ${id}:`, e);
                    }
                }
                
                updateBulkStatus();
                syncMasterChk();
                
                if (successCount > 0) {
                    toast(`Successfully accepted ${successCount} abstract(s)`, 'success');
                    await searchAbstracts(); // Refresh the list
                } else {
                    toast('Failed to accept any abstracts', 'error');
                }
            } catch (e) {
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
                        const data = await fetchJSON(`/video/api/v1/research/abstracts/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        console.warn(`Failed to fetch abstract ${id}:`, e);
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
                        const r = await fetch(`${BASE}/api/v1/research/abstracts/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.abstractIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        console.error(`Failed to reject abstract ${id}:`, e);
                    }
                }
                
                updateBulkStatus();
                syncMasterChk();
                
                if (successCount > 0) {
                    toast(`Successfully rejected ${successCount} abstract(s)`, 'success');
                    await searchAbstracts(); // Refresh the list
                } else {
                    toast('Failed to reject any abstracts', 'error');
                }
            } catch (e) {
                toast('Error processing bulk reject: ' + (e.message || 'Unknown error'), 'error');
            } finally {
                bulkStatus.textContent = originalText;
            }
        });
        
        wireSortGroups();
        wireSegmentedControls();
        searchAbstracts();
    }
    
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
