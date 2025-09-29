(() => {
    const BASE = '/video/api/v1/research';  // Fixed path
    const token = () => localStorage.getItem('token') || '';
    const headers = () => ({ 'Accept': 'application/json', 'Authorization': `Bearer ${token()}` });
    const sQ = id => document.getElementById(id);
    const paperList = sQ('paperList');
    let selPaper = null;
    const bulk = { paperIds: new Set() };

    const state = {
        papers: { page: 1, pages: 1, pageSize: 20, filter: '', q: '', sort: 'id', dir: 'desc' }
    };

    function activateSeg(group, btn) {
        group.querySelectorAll('.seg').forEach(b => b.classList.remove('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]'));
        btn.classList.add('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
    }

    function wireSegmentedControls() {
        const aStatusGroup = sQ('paperStatusGroup');
        aStatusGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aStatusGroup, btn);
            state.papers.filter = btn.dataset.val || '';
            state.papers.page = 1; searchPapers();
        });

        const aPageGroup = sQ('paperPageSizeGroup');
        aPageGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aPageGroup, btn);
            state.papers.pageSize = +btn.dataset.size;
            state.papers.page = 1; searchPapers();
        });
    }
    
    async function updateStatsBar() {
        try {
            const resp = await fetch(`${BASE}/best-papers/status`, {
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

    // Attach sorting behavior to best paper sort button group
    function wireSortGroups() {
        const aGroup = sQ('paperSortGroup');
        if (aGroup) {
            applySortStyles(aGroup, state.papers.sort, state.papers.dir);
            aGroup.addEventListener('click', e => {
                const btn = e.target.closest('.sort-btn');
                if (!btn) return;
                const key = btn.dataset.key;
                if (state.papers.sort === key) {
                    state.papers.dir = state.papers.dir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.papers.sort = key;
                    state.papers.dir = 'asc';
                }
                applySortStyles(aGroup, state.papers.sort, state.papers.dir);
                searchPapers();
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
            empty.textContent = type === 'best paper' ? 'No papers found' : 'No items found';
            el.appendChild(empty);
            return;
        }
        items.forEach(it => {
            const li = document.createElement('li');
            const selected = bulk.paperIds.has(it.id) && type === 'best paper';
            li.className = 'group py-3 px-3 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 cursor-pointer flex justify-between items-center transition-colors rounded-lg ' + (selected ? 'bg-[color:var(--brand-100)] dark:bg-[color:var(--brand-900)]' : '');
            li.dataset.id = it.id;
            if (type === 'best paper') {
                li.innerHTML = `
                    <span class="flex items-center gap-3 w-full">
                        <div class="flex-1 min-w-0">
                            <div class="font-medium text-gray-900 dark:text-white truncate">${escapeHtml(it.title || 'Untitled Best Paper')}</div>
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
                    selPaper = it; 
                    updatePanel(); 
                    highlightSelection(); 
                });
            }
            el.appendChild(li);
        });
        if (type === 'best paper') {
            el.querySelectorAll('.bulkChk').forEach(chk => {
                chk.addEventListener('change', e => {
                    const id = e.target.getAttribute('data-id');
                    if (e.target.checked) bulk.paperIds.add(id); else bulk.paperIds.delete(id);
                    
                   
                });
            });
            
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
    
    
    function highlightSelection() {
        // Clear previous highlight
        Array.from(paperList.children).forEach(li => li.classList.remove('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]'));
        if (selPaper) {
            const el = paperList.querySelector(`[data-id='${selPaper.id}']`);
            if (el) el.classList.add('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]');
        }
    }
    
    function updatePanel() {
        const noPaperSelected = sQ('noPaperSelected');
        const paperContent = sQ('paperContent');
        if (selPaper) {
            noPaperSelected.classList.add('hidden');
            paperContent.classList.remove('hidden');
            
            // Generate preview content
            generatePreview();
        } else {
            noPaperSelected.classList.remove('hidden');
            paperContent.classList.add('hidden');
        }
    }
    
    // Generate preview of best paper details
    function generatePreview() {
        const previewContent = sQ('preview-content');
        if (!previewContent || !selPaper) return;
        
        // Get category name
        const categoryName = selPaper.category?.name || 'No Category';

        // Update summary card info
        sQ('summaryTitle') && (sQ('summaryTitle').textContent = selPaper.title || 'Untitled Best Paper');
        
        sQ('summaryCategory') && (sQ('summaryCategory').textContent = categoryName);
        sQ('summaryPaperNumber') && (sQ('summaryPaperNumber').textContent = selPaper.paper_number || 'Unknown ID');
        
        sQ('summaryStatus') && (sQ('summaryStatus').textContent = selPaper.status || 'PENDING');
        sQ('summaryStatus') && (sQ('summaryStatus').className = 'badge ' + getStatusClass(selPaper.status));
        sQ('summaryAuthor') && (sQ('summaryAuthor').textContent = selPaper.created_by?.username || 'Unknown User');
        sQ('summaryDate') && (sQ('summaryDate').textContent = formatDate(selPaper.created_at));

        // Generate preview HTML with improved styling
        let previewHTML = `
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
               
                <!-- Best Paper Content Section -->
                <div class="p-5">
                    <div class="hidden flex items-center mb-4">
                        <div class="flex-shrink-0 h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </div>
                        <div class="ml-4">
                            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Best Paper Content</h3>
                            <p class="text-sm text-gray-500 dark:text-gray-400">Main body of the best paper</p>
                        </div>
                    </div>
                    
                    <div class="ml-2">
                        <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg border border-gray-200 dark:border-gray-600">
                            <p class="whitespace-pre-wrap text-gray-800 dark:text-gray-200">${escapeHtml(selPaper.content || '')}</p>
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
        
        if (selPaper.authors && selPaper.authors.length > 0) {
            selPaper.authors.forEach((author) => {
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
                            <p class="text-sm text-gray-500 dark:text-gray-400">Uploaded best paper PDF</p>
                        </div>
                    </div>
                    <div class="ml-2">
                        ${selPaper.pdf_path ? `
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
                        ` : `<p class="text-gray-500 dark:text-gray-400 italic p-4 text-center">No PDF uploaded for this best paper.</p>`}
                    </div>
                </div>
            </div>
        `;
        previewContent.innerHTML = previewHTML;
        // After rendering, if PDF exists, render preview using PDF.js
        if (selPaper.pdf_path) {
            renderVerifierPdfPreview(selPaper.id);
        }
    }
    
    // Render PDF preview for verifier using PDF.js
    function renderVerifierPdfPreview(paperId) {
        if (typeof pdfjsLib === 'undefined') {
            const container = document.getElementById('pdf-preview-container');
            if (container) container.innerHTML = '<p class="text-red-600 dark:text-red-400 text-center p-4">PDF.js library not available. Cannot preview PDF.</p>';
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/video/static/js/pdf.worker.min.js';
        fetch(`${BASE}/best-papers/${paperId}/pdf`, {
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

    async function searchPapers() {
        state.papers.q = (sQ('paperSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.papers;
        const url = `${BASE}/best-papers?q=${encodeURIComponent(q)}&status=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}`;
        try {
            const data = await fetchJSON(url);
            renderList(paperList, data.items || data || [], 'best paper');
            updatePaperMeta(data);
        } catch (e) {
            console.error(e);
            toast('Failed to search papers: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    

    
    function updatePaperMeta(data) {
        state.papers.pages = data.pages || 1;
        const info = sQ('paperPageInfo');
        if (info) info.textContent = `Page ${data.page || 1} / ${data.pages || 1}`;
        const stats = sQ('paperStats');
        if (stats) {
            const filterLabel = state.papers.filter === '' ? 'All' : state.papers.filter.charAt(0).toUpperCase() + state.papers.filter.slice(1);
            stats.textContent = `${data.total || 0} total • Filter: ${filterLabel}`;
        }
    }

    function changePaperPage(delta) {
        state.papers.page = Math.min(Math.max(1, state.papers.page + delta), state.papers.pages);
        searchPapers();
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
        return String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
    }

    function init() {
        updateStatsBar();
        sQ('paperSearchBtn')?.addEventListener('click', () => { state.papers.page = 1; searchPapers(); });
        sQ('paperSearch')?.addEventListener('keypress', (e) => { if (e.key === 'Enter') { state.papers.page = 1; searchPapers(); } });
        sQ('paperPrev')?.addEventListener('click', () => changePaperPage(-1));
        sQ('paperNext')?.addEventListener('click', () => changePaperPage(1));
        

        const master = sQ('paperMasterChk');
        master?.addEventListener('change', e => { e.target.checked ? selectAllPage() : clearAllPage(); });
        sQ('invertSelection')?.addEventListener('click', invertSelection);
        sQ('paperSelectAll')?.addEventListener('click', selectAllPage);
        sQ('paperClearSel')?.addEventListener('click', clearAllPage);
        sQ('bulkAcceptBtn')?.addEventListener('click', async () => {
            if (bulk.paperIds.size === 0) {
                toast('Select papers to accept', 'warn');
                return;
            }
            
            if (!confirm(`Are you sure you want to accept ${bulk.paperIds.size} best paper(s)?`)) return;
            
            // Show loading state
            const bulkStatus = sQ('bulkStatus');
            const originalText = bulkStatus.textContent;
            bulkStatus.textContent = 'Processing...';
            
            try {
                // Get only pending papers
                const ids = Array.from(bulk.paperIds);
                let pendingIds = [];
                
                for (const id of ids) {
                    try {
                        const data = await fetchJSON(`${BASE}/best-papers/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        console.warn(`Failed to fetch best paper ${id}:`, e);
                    }
                }
                
                if (pendingIds.length === 0) {
                    toast('No selected papers are pending', 'warn');
                    return;
                }
                
                if (pendingIds.length < ids.length) {
                    const skipped = ids.length - pendingIds.length;
                    toast(`${skipped} best paper(s) are not pending and will be skipped.`, 'warn');
                }
                
                // Process pending papers
                let successCount = 0;
                for (const id of pendingIds) {
                    try {
                        const body = { status: 'ACCEPTED' };
                        const r = await fetch(`${BASE}/best-papers/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.paperIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        console.error(`Failed to accept best paper ${id}:`, e);
                    }
                }
                
               
                
                
                if (successCount > 0) {
                    toast(`Successfully accepted ${successCount} best paper(s)`, 'success');
                    await searchPapers(); // Refresh the list
                } else {
                    toast('Failed to accept any papers', 'error');
                }
            } catch (e) {
                toast('Error processing bulk accept: ' + (e.message || 'Unknown error'), 'error');
            } finally {
                bulkStatus.textContent = originalText;
            }
        });
        
        sQ('bulkRejectBtn')?.addEventListener('click', async () => {
            if (bulk.paperIds.size === 0) {
                toast('Select papers to reject', 'warn');
                return;
            }
            
            if (!confirm(`Are you sure you want to reject ${bulk.paperIds.size} best paper(s)?`)) return;
            
            // Show loading state
            const bulkStatus = sQ('bulkStatus');
            const originalText = bulkStatus.textContent;
            bulkStatus.textContent = 'Processing...';
            
            try {
                // Get only pending papers
                const ids = Array.from(bulk.paperIds);
                let pendingIds = [];
                
                for (const id of ids) {
                    try {
                        const data = await fetchJSON(`${BASE}/best-papers/${id}`);
                        if ((data.status || '').toUpperCase() === 'PENDING') {
                            pendingIds.push(id);
                        }
                    } catch (e) {
                        // skip if error
                        console.warn(`Failed to fetch best paper ${id}:`, e);
                    }
                }
                
                if (pendingIds.length === 0) {
                    toast('No selected papers are pending', 'warn');
                    return;
                }
                
                if (pendingIds.length < ids.length) {
                    const skipped = ids.length - pendingIds.length;
                    toast(`${skipped} best paper(s) are not pending and will be skipped.`, 'warn');
                }
                
                // Process pending papers
                let successCount = 0;
                for (const id of pendingIds) {
                    try {
                        const body = { status: 'REJECTED' };
                        const r = await fetch(`${BASE}/best-papers/${id}`, {
                            method: 'PUT',
                            headers: { ...headers(), 'Content-Type': 'application/json' },
                            body: JSON.stringify(body)
                        });
                        if (r.ok) {
                            successCount++;
                            bulk.paperIds.delete(id); // Remove from selection
                        }
                    } catch (e) {
                        console.error(`Failed to reject best paper ${id}:`, e);
                    }
                }
                
               
                
                
                if (successCount > 0) {
                    toast(`Successfully rejected ${successCount} best paper(s)`, 'success');
                    await searchPapers(); // Refresh the list
                } else {
                    toast('Failed to reject any papers', 'error');
                }
            } catch (e) {
                toast('Error processing bulk reject: ' + (e.message || 'Unknown error'), 'error');
            } finally {
                bulkStatus.textContent = originalText;
            }
        });
        
        wireSortGroups();
        wireSegmentedControls();
        searchPapers();
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
        document.addEventListener('DOMContentLoaded', () => {initCriteriaFilter(); });
    } else {
        initCriteriaFilter();
    }
})();