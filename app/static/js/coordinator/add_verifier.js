(() => {
    const BASE = '';
    const token = () => localStorage.getItem('token') || '';
    const headers = () => ({ 'Accept': 'application/json', 'Authorization': `Bearer ${token()}` });
    const fallbackIds = {
        bestpaperList: 'bestPaperList',
        bestpaperSearch: 'bestpaperSearch',
        bestpaperSearchBtn: 'bestpaperSearchBtn',
        bestpaperLinkedGroup: 'bestpaperLinkedGroup',
        bestpaperSortGroup: 'bestpaperSortGroup',
        bestpaperPageSizeGroup: 'bestpaperPageSizeGroup',
        bestpaperStats: 'bestpaperStats',
        bestpaperPageInfo: 'bestpaperPageInfo',
        bestpaperPrev: 'bestpaperPrev',
        bestpaperNext: 'bestpaperNext',
        bestpaperMasterChk: 'bestpaperMasterChk',
        bestpaperSelectAll: 'bestpaperSelectAll',
        bestpaperClearSel: 'bestpaperClearSel',
        selBestPaperTitle: 'selBestPaperTitle',
        selBestPaperMeta: 'selBestPaperMeta',
        selAuthorsList: 'selAuthorsList',
        selBestPaperDetails: 'selBestPaperDetails',
        selBestPaperVerifiers: 'selBestPaperVerifiers',
        bestpaperVerifiersList: 'bestPaperVerifiersList',
        rejectBestPaperBtn: 'rejectBestPaperBtn',
        selBestPaper: 'selBestPaperTitle',
        selBestPaperDetails: 'selBestPaperDetails',
        selBestPaperVerifiersList: 'bestPaperVerifiersList'
    };
    const sQ = id => document.getElementById(id) || (fallbackIds[id] ? document.getElementById(fallbackIds[id]) : null);
    const bestpaperList = sQ('bestpaperList') || sQ('bestPaperList');
    const verifierList = sQ('verifierList');
    let selBestPaper = null; let selVerifier = null;
    const bulk = { bestpaperIds: new Set() };

    const state = {
        bestpapers: { page: 1, pages: 1, pageSize: 20, filter: '', q: '', sort: 'id', dir: 'desc' },
        verifiers: { page: 1, pages: 1, pageSize: 20, filter: '', q: '', sort: 'created_at', dir: 'desc' }
    };

    // Cache for DOM elements to avoid repeated queries
    const domCache = new Map();

    function getCachedElement(id) {
        if (!domCache.has(id)) {
            domCache.set(id, document.getElementById(id));
        }
        return domCache.get(id);
    }

    function normalizeStatus(statusVal) {
        const raw = statusVal?.value || statusVal?.name || statusVal || '';
        const cleaned = raw.toString().replace(/^Status\.?/i, '').toLowerCase();
        const label = cleaned
            ? cleaned.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
            : 'Unknown';
        return { raw, value: cleaned, label };
    }

    function normalizeBestPaper(raw = {}) {
        const statusInfo = normalizeStatus(raw.status);
        const category = raw.category || raw.paper_category || raw.paperCategory;
        const categoryId = raw.category_id || raw.paper_category_id || raw.paperCategoryId;
        const author = raw.author || (Array.isArray(raw.authors) ? raw.authors[0] : undefined);

        return {
            ...raw,
            bestpaper_number: raw.bestpaper_number ?? raw.bestpaperNumber ?? raw.bestpapernumber ?? raw.bestpaper_number ?? raw.bestpaperNumber ?? raw.bestpapernumber,
            category,
            category_id: categoryId,
            paper_category: raw.paper_category || raw.category || category,
            paper_category_id: raw.paper_category_id || raw.category_id || categoryId,
            submitted_on: raw.submitted_on || raw.created_at || raw.created_on,
            updated_on: raw.updated_on || raw.updated_at || raw.modified_on,
            submitted_by: raw.submitted_by || raw.created_by || raw.user,
            updated_by: raw.updated_by || raw.modified_by,
            author,
            authors: Array.isArray(raw.authors) ? raw.authors : (author ? [author] : []),
            complete_pdf_path: raw.complete_pdf_path || raw.full_paper_path,
            covering_letter_pdf_path: raw.covering_letter_pdf_path || raw.forwarding_letter_path,
            work_of_aiims: raw.work_of_aiims ?? raw.is_aiims_work,
            review_phase: raw.review_phase ?? raw.phase ?? 1,
            status_key: statusInfo.value,
            status_label: statusInfo.label,
        };
    }

    const normalizeBestPaperArray = (items) => (items || []).map(normalizeBestPaper);

    function statusBadgeTone(statusKey) {
        switch (statusKey) {
            case 'pending':
                return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200';
            case 'under_review':
                return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200';
            case 'rejected':
                return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
            case 'accepted':
                return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200';
            default:
                return 'bg-white/60 dark:bg-white/5';
        }
    }

    function activateSeg(group, btn) {
        group.querySelectorAll('.seg').forEach(b => b.classList.remove('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]'));
        btn.classList.add('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
    }

    function wireSegmentedControls() {
        const aLinkGroup = sQ('bestpaperLinkedGroup');
        aLinkGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aLinkGroup, btn);
            state.bestpapers.filter = btn.dataset.val || '';
            state.bestpapers.page = 1; searchBestPapers();
        });

        const aPageGroup = sQ('bestpaperPageSizeGroup');
        aPageGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aPageGroup, btn);
            state.bestpapers.pageSize = +btn.dataset.size;
            state.bestpapers.page = 1; searchBestPapers();
        });

        const vLinkGroup = sQ('verifierLinkedGroup');
        vLinkGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(vLinkGroup, btn);
            state.verifiers.filter = btn.dataset.val || '';
            state.verifiers.page = 1; searchVerifiers();
        });

        const vPageGroup = sQ('verifierPageSizeGroup');
        vPageGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(vPageGroup, btn);
            state.verifiers.pageSize = +btn.dataset.size;
            state.verifiers.page = 1; searchVerifiers();
        });
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

    // Attach sorting behavior to bestpaper & verifier sort button groups
    function wireSortGroups() {
        const aGroup = sQ('bestpaperSortGroup');
        if (aGroup) {
            applySortStyles(aGroup, state.bestpapers.sort, state.bestpapers.dir);
            aGroup.addEventListener('click', e => {
                const btn = e.target.closest('.sort-btn');
                if (!btn) return;
                const key = btn.dataset.key;
                if (state.bestpapers.sort === key) {
                    state.bestpapers.dir = state.bestpapers.dir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.bestpapers.sort = key;
                    state.bestpapers.dir = 'asc';
                }
                applySortStyles(aGroup, state.bestpapers.sort, state.bestpapers.dir);
                searchBestPapers();
            });
        }
        const vGroup = sQ('verifierSortGroup');
        if (vGroup) {
            applySortStyles(vGroup, state.verifiers.sort, state.verifiers.dir);
            vGroup.addEventListener('click', e => {
                const btn = e.target.closest('.sort-btn');
                if (!btn) return;
                const key = btn.dataset.key;
                if (state.verifiers.sort === key) {
                    state.verifiers.dir = state.verifiers.dir === 'asc' ? 'desc' : 'asc';
                } else {
                    state.verifiers.sort = key;
                    state.verifiers.dir = 'asc';
                }
                applySortStyles(vGroup, state.verifiers.sort, state.verifiers.dir);
                searchVerifiers();
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
    
    // Optimized renderList using DocumentFragment for better performance
    function renderList(el, items, type) {
        // Clear the list efficiently
        while (el.firstChild) el.removeChild(el.firstChild);

        if (!items.length) {
            const empty = document.createElement('li');
            empty.className = 'py-8 text-center text-xs uppercase tracking-wide text-[color:var(--muted)]';
            empty.textContent = type === 'bestpaper' ? 'No best papers found' : 'No verifiers found';
            el.appendChild(empty);
            return;
        }

        const fragment = document.createDocumentFragment();

        items.forEach(rawItem => {
            const it = type === 'bestpaper' ? normalizeBestPaper(rawItem) : rawItem;
            const li = document.createElement('li');
            const selected = bulk.bestpaperIds?.has?.(it.id) && type === 'bestpaper';

            // Layout fixes: items start, gap, allow text to wrap, badge stays visible
            li.className =
                'group py-3 px-3 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 ' +
                'cursor-pointer flex items-start justify-between gap-3 transition-colors rounded-lg ' +
                (selected ? 'bg-[color:var(--brand-100)] dark:bg-[color:var(--brand-900)]' : '');
            li.dataset.id = it.id;

            if (type === 'bestpaper') {
                const left = document.createElement('div');
                left.className = 'flex items-start gap-3 min-w-0 grow';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'bulkChk accent-[color:var(--brand-600)] rounded h-4 w-4 mt-1 shrink-0';
                checkbox.dataset.id = it.id;
                checkbox.checked = selected;
                const bestpaperLabel = `Select best paper ${it.title || `#${it.bestpaper_number || it.id}`}`;
                checkbox.setAttribute('aria-label', bestpaperLabel);
                checkbox.setAttribute('title', bestpaperLabel);

                const textCol = document.createElement('div');
                textCol.className = 'min-w-0';

                const titleSpan = document.createElement('div');
                // Multi-line title: allow wrapping; avoid truncation; break long words
                titleSpan.className = 'font-medium whitespace-normal break-words';
                titleSpan.textContent = it.title || 'Untitled Best Paper';
                titleSpan.title = it.title || 'Untitled Best Paper'; // tooltip for very long titles

                const meta = document.createElement('div');
                meta.className = 'muted text-xs mt-1 space-x-2';
                const cat = document.createElement('span');
                cat.textContent = it.category?.name || it.paper_category?.name || 'No Category';
                const dot = document.createElement('span');
                dot.textContent = '•';
                const submittedBy = document.createElement('span');
                submittedBy.textContent = `Submitted by: ${it.submitted_by?.username || it.created_by?.username || it.author?.name || 'Unknown'}`;
                const dot2 = document.createElement('span');
                dot2.textContent = '•';
                const bestpaperNum = document.createElement('span');
                bestpaperNum.textContent = `Best Paper #${it.bestpaper_number || 'N/A'}`;

                meta.appendChild(cat);
                meta.appendChild(dot);
                meta.appendChild(submittedBy);
                meta.appendChild(dot2);
                meta.appendChild(bestpaperNum);

                textCol.appendChild(titleSpan);
                textCol.appendChild(meta);

                left.appendChild(checkbox);
                left.appendChild(textCol);

                const badge = document.createElement('span');
                badge.className = 'text-[10px] uppercase tracking-wide px-2 py-1 rounded-full shrink-0 self-center';
                if (it.verifiers_count && it.verifiers_count > 0) {
                    badge.className += ' bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300';
                    badge.textContent = `${it.verifiers_count} verifier${it.verifiers_count > 1 ? 's' : ''}`;
                } else {
                    badge.className += ' bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
                    badge.textContent = 'no verifiers';
                }

                li.appendChild(left);
                li.appendChild(badge);

                // List item click (ignore checkbox)
                li.addEventListener('click', (e) => {
                    if (e.target.classList.contains('bulkChk')) return;
                    selBestPaper = it;
                    updatePanel();
                    highlightSelection();
                });

                // Checkbox behavior
                checkbox.addEventListener('change', (e) => {
                    const id = e.target.dataset.id;
                    if (e.target.checked) bulk.bestpaperIds.add(id); else bulk.bestpaperIds.delete(id);
                    syncMasterChk();
                    updateBulkStatus();
                });

            } else {
                // -------- Verifier list item (layout fixed to prevent cropping) --------
                const left = document.createElement('div');
                left.className = 'flex items-start gap-3 min-w-0 grow';

                const radio = document.createElement('input');
                radio.type = 'radio';
                radio.name = 'verifierSelect';
                radio.className = 'verifierPick accent-[color:var(--brand-600)] h-4 w-4 mt-1 shrink-0';
                radio.dataset.id = it.id;
                radio.checked = !!(selVerifier && selVerifier.id === it.id);
                const verifierLabel = `Select verifier ${it.username || it.email || it.id}`;
                radio.setAttribute('aria-label', verifierLabel);
                radio.setAttribute('title', verifierLabel);

                const textCol = document.createElement('div');
                textCol.className = 'flex flex-col min-w-0';

                const usernameSpan = document.createElement('div');
                // Don’t crop: allow wrapping; break long names
                usernameSpan.className = 'text-sm font-medium whitespace-normal break-words';
                usernameSpan.textContent = it.username || '';

                const emailSpan = document.createElement('div');
                // Emails can be long → break-all
                emailSpan.className = 'muted text-xs mt-1 break-all';
                emailSpan.textContent = it.email || 'No email';

                // --- New: mobile number line ---
                const mobileSpan = document.createElement('div');
                mobileSpan.className = 'muted text-xs mt-1 break-all';
                mobileSpan.textContent = it.mobile ? `📱 ${it.mobile}` : '📱 Not available';

                textCol.appendChild(usernameSpan);
                textCol.appendChild(emailSpan);
                textCol.appendChild(mobileSpan);

                left.appendChild(radio);
                left.appendChild(textCol);

                const badge = document.createElement('span');
                badge.className = 'text-[10px] uppercase tracking-wide px-2 py-1 rounded-full shrink-0 self-center';
                if (it.bestpapers_count && it.bestpapers_count > 0) {
                    badge.className += ' bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
                    badge.textContent = `${it.bestpapers_count} bestpaper${it.bestpapers_count > 1 ? 's' : ''}`;
                } else {
                    badge.className += ' bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
                    badge.textContent = 'no bestpapers';
                }

                li.appendChild(left);
                li.appendChild(badge);


                // List item click (ignore radio)
                li.addEventListener('click', (e) => {
                    if (e.target.classList.contains('verifierPick')) return;
                    selVerifier = it;
                    updatePanel();
                    highlightSelection();
                    syncVerifierRadios();
                });

                // Radio change
                radio.addEventListener('change', () => {
                    selVerifier = it;
                    updatePanel();
                    highlightSelection();
                    syncVerifierRadios();
                });
            }

            fragment.appendChild(li);
        });

        el.appendChild(fragment);

        // Sync controls after rendering
        if (type === 'bestpaper') {
            syncMasterChk();
        } else {
            syncVerifierRadios();
        }
    }

    
    function syncVerifierRadios() {
        const radios = verifierList.querySelectorAll('.verifierPick');
        radios.forEach(r => { r.checked = selVerifier && selVerifier.id === r.dataset.id; });
    }
    
    function syncMasterChk() {
        const master = sQ('bestpaperMasterChk');
        if (!master) return;
        const boxes = bestpaperList.querySelectorAll('.bulkChk');
        const total = boxes.length;
        const checked = Array.from(boxes).filter(b => b.checked).length;
        master.indeterminate = checked > 0 && checked < total;
        master.checked = total > 0 && checked === total;
    }
    
    function selectAllPage() {
        bestpaperList.querySelectorAll('.bulkChk').forEach(chk => { chk.checked = true; bulk.bestpaperIds.add(chk.dataset.id); });
        syncMasterChk(); updateBulkStatus();
    }
    
    function clearAllPage() {
        bestpaperList.querySelectorAll('.bulkChk').forEach(chk => { chk.checked = false; bulk.bestpaperIds.delete(chk.dataset.id); });
        syncMasterChk(); updateBulkStatus();
    }
    
    function invertSelection() {
        bestpaperList.querySelectorAll('.bulkChk').forEach(chk => {
            const id = chk.dataset.id;
            if (chk.checked) { chk.checked = false; bulk.bestpaperIds.delete(id); }
            else { chk.checked = true; bulk.bestpaperIds.add(id); }
        });
        syncMasterChk(); updateBulkStatus();
    }
    
    function updateBulkStatus() {
        const el = sQ('bulkStatus');
        if (el) el.textContent = bulk.bestpaperIds.size ? `${bulk.bestpaperIds.size} selected` : '';
    }
    
    function highlightSelection() {
        // Clear previous highlight
        Array.from(bestpaperList.children).forEach(li => li.classList.remove('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]'));
        if (selBestPaper) {
            const el = bestpaperList.querySelector(`[data-id='${selBestPaper.id}']`);
            if (el) el.classList.add('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]');
        }
        Array.from(verifierList.children).forEach(li => li.classList.remove('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]'));
        if (selVerifier) {
            const el = verifierList.querySelector(`[data-id='${selVerifier.id}']`);
            if (el) el.classList.add('ring', 'ring-[color:var(--brand-600)]', 'selected-row', 'bg-[color:var(--brand-200)]', 'dark:bg-[color:var(--brand-800)]');
        }
    }
    function formatDateISO(s) {
        if (!s) return '—';
        try {
            const d = new Date(s);
            // DD Mon YYYY, HH:MM
            return d.toLocaleString(undefined, {
                day: '2-digit', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            });
        } catch { return s; }
    }

    function badge(text, extra = '') {
        const base = 'px-2 py-1 rounded-full text-[10px] uppercase tracking-wide border border-[color:var(--border)]/70';
        return `<span class="${base} ${extra}">${text}</span>`;
    }

    function renderSelectedBestPaper(a) {
        const $ = (id) => sQ(id);
        const bestpaper = normalizeBestPaper(a || {});
        const statusInfo = normalizeStatus(bestpaper.status_key || bestpaper.status);

        // Title
        $('selBestPaperTitle').textContent = bestpaper?.title || 'Untitled Best Paper';

        // Meta badges (number, category, status, phase, created)
        const num = bestpaper?.bestpaper_number ? `#${bestpaper.bestpaper_number}` : (bestpaper?.bestpaper_number ? `#${bestpaper.bestpaper_number}` : 'No Number');
        const cat = bestpaper?.category?.name || bestpaper?.paper_category?.name || 'No Category';
        const statusKey = statusInfo.value;
        const status = (statusInfo.label || 'Unknown').toUpperCase();
        const phase = (bestpaper?.review_phase ?? '—');

        $('selBestPaperMeta').innerHTML = [
            badge(num, 'bg-white/60 dark:bg-white/5'),
            badge(cat, 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'),
            badge(status, statusBadgeTone(statusKey)),
            badge(`Phase ${phase}`, 'bg-white/60 dark:bg-white/5'),
            badge(`Submitted ${formatDateISO(bestpaper?.submitted_on)}`, 'bg-white/60 dark:bg-white/5')
        ].join(' ');

        // Submitted By
        const sb = bestpaper?.submitted_by || bestpaper?.created_by || bestpaper?.author || {};
        const sbLines = [
            `<div><span class="font-medium">${sb.username || sb.name || 'Unknown'}</span></div>`,
            `<div class="muted break-all">${sb.email || 'No email'}</div>`,
            `<div class="muted break-all">${sb.mobile || 'No mobile'}</div>`
        ].join('');
        const sbEl = $('selSubmittedBy');
        if (sbEl) {
            sbEl.setAttribute('data-loaded', 'true');
            sbEl.innerHTML = sbLines;
        }

        // Authors
        const authors = Array.isArray(bestpaper?.authors) ? bestpaper.authors : [];
        const $authors = $('selAuthorsList');
        $authors.innerHTML = '';
        if (!authors.length) {
            $authors.innerHTML = `<li class="muted">No authors</li>`;
        } else {
            const frag = document.createDocumentFragment();
            authors.forEach((au) => {
                const li = document.createElement('li');
                li.className = 'flex items-start justify-between gap-3';
                const left = document.createElement('div');
                left.className = 'min-w-0';
                left.innerHTML = `
        <div class="font-medium wrap-break-word">${au.name || 'Unnamed'}</div>
        <div class="text-[12px] muted break-all">${au.email || 'No email'}${au.affiliation ? ' • ' + au.affiliation : ''}</div>
      `;
                const right = document.createElement('div');
                right.className = 'shrink-0 flex items-center gap-1';
                if (au.is_presenter) right.insertAdjacentHTML('beforeend', badge('Presenter', 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200'));
                if (au.is_corresponding) right.insertAdjacentHTML('beforeend', badge('Corresponding', 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'));
                li.appendChild(left);
                li.appendChild(right);
                frag.appendChild(li);
            });
            $authors.appendChild(frag);
        }

        // Content preview (full scrollable, no clamp)
        const detailText = bestpaper?.content || bestpaper?.description || (bestpaper?.complete_pdf_path || bestpaper?.full_paper_path ? 'Full paper uploaded (no inline description available)' : '—');
        $('selBestPaperDetails').textContent = detailText;

        // PDF link
        const pdfHref = '/api/v1/research/best-papers/' + (bestpaper?.id || '') + '/pdf';
        const pdfEl = $('selPdfLink');
        pdfEl.href = pdfHref || '#';
        pdfEl.textContent = pdfHref && pdfHref !== '#' ? pdfHref : 'Not uploaded';

        // Verifiers section
        const vWrap = sQ('selBestPaperVerifiers');
        const vList = sQ('bestPaperVerifiersList');
        vList.innerHTML = '';
        const verifiers = Array.isArray(bestpaper?.verifiers) ? bestpaper.verifiers : [];
        vWrap.classList.remove('hidden');
        if (!verifiers.length) {
            vList.innerHTML = `<li class="muted">No verifiers assigned</li>`;
        } else {
            const frag = document.createDocumentFragment();
            verifiers.forEach(v => {
                const li = document.createElement('li');
                li.className = 'flex items-start justify-between gap-3';
                const left = document.createElement('div');
                left.className = 'min-w-0';
                left.innerHTML = `
        <div class="font-medium wrap-break-word">${v.username || '—'}</div>
        <div class="text-[12px] muted break-all">${v.email || 'No email'}${v.mobile ? ' • ' + v.mobile : ''}</div>
      `;
                li.appendChild(left);
                frag.appendChild(li);
            });
            vList.appendChild(frag);
        }
        const rejectBtn = $('rejectBestPaperBtn');
        if ((verifiers.length === 0) && (statusKey === 'pending'))
            rejectBtn.classList.remove('hidden');
        else
            rejectBtn.classList.add('hidden');
        rejectBtn.onclick = () => {
            if (confirm('Are you sure you want to reject this best paper?')) {
                // Call the API to reject the bestpaper
                rejectBestPaper(bestpaper);
            }
        };
    }

    function rejectBestPaper(bestpaper) {
        // Call the API to reject the bestpaper
        fetch(`/api/v1/research/best-papers/${bestpaper?.id}/reject`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': "Bearer " + token()
            },
            body: JSON.stringify({ reason: 'Inappropriate content' })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('Best paper rejected:', data);
            // Update the UI accordingly
            init();
            selBestPaper = null;
            updatePanel();
        })
        .catch(error => {
            console.error('Error rejecting bestpaper:', error);
        });
    }

    function updatePanel() {
        const panel = sQ('assignPanel');
        const aSpan = sQ('selBestPaperTitle');   // title
        const aDetails = sQ('selBestPaperDetails');
        const vSpan = sQ('selVerifier');
        const vStatus = sQ('selVerifierStatus');

        // ----- ABSTRACT SIDE -----
        if (selBestPaper) {
            const normalizedBestPaper = normalizeBestPaper(selBestPaper);
            // Use the rich renderer if present (from the upgraded UI)
            if (typeof renderSelectedBestPaper === 'function') {
                renderSelectedBestPaper(normalizedBestPaper);
            }
            // Keep legacy fields in sync (safe no-ops if missing)
            if (aSpan) aSpan.textContent = normalizedBestPaper.title || 'Untitled Best Paper';
            if (aDetails) {
                const detailText = normalizedBestPaper.content || normalizedBestPaper.description || (normalizedBestPaper.complete_pdf_path || normalizedBestPaper.full_paper_path ? 'Full paper uploaded (no inline description available)' : 'No content available');
                aDetails.textContent = detailText;
            }

            // Load verifiers list for this best paper
            loadBestPaperVerifiers(normalizedBestPaper.id);
        } else {
            // Reset bestpaper UI (both new and legacy)
            if (aSpan) aSpan.textContent = 'No best paper selected';
            if (aDetails) aDetails.textContent = 'Select a best paper to view details';

            const sb = document.getElementById('selSubmittedBy');
            if (sb) sb.innerHTML = '';

            const authors = document.getElementById('selAuthorsList');
            if (authors) authors.innerHTML = '';

            const meta = document.getElementById('selBestPaperMeta');
            if (meta) meta.innerHTML = '';

            const pdf = document.getElementById('selPdfLink');
            if (pdf) { pdf.href = '#'; pdf.textContent = 'Not uploaded'; }

            const vWrap = document.getElementById('selBestPaperVerifiers');
            const vList = document.getElementById('bestPaperVerifiersList');
            if (vList) vList.innerHTML = '';
            if (vWrap) vWrap.classList.add('hidden');

            hideBestPaperVerifiers();
        }

        // ----- VERIFIER SIDE -----
        if (selVerifier) {
            if (vSpan) vSpan.textContent = selVerifier.username || 'Unknown Verifier';
            if (vStatus) {
                const bits = [];
                bits.push(selVerifier.email || 'No email provided');
                if (selVerifier.mobile) bits.push(selVerifier.mobile);
                vStatus.textContent = bits.join(' • ');
            }
            loadVerifierBestPapers(selVerifier.id);
        } else {
            if (vSpan) vSpan.textContent = 'No verifier selected';
            if (vStatus) vStatus.textContent = 'Select a verifier to assign';
            hideVerifierBestPapers();
        }

        // Show panel if either side has a selection
        panel.hidden = !(selBestPaper || selVerifier);
    }

    
    function hideBestPaperVerifiers() {
        const box = sQ('selBestPaperVerifiers');
        if (box) { box.classList.add('hidden'); }
    }
    
    function hideVerifierBestPapers() {
        const box = sQ('selVerifierBestPapers');
        if (box) { box.classList.add('hidden'); }
    }

    async function loadBestPaperVerifiers(bestpaperId) {
        try {
            const data = await fetchJSON(`${BASE}/api/v1/research/best-papers/${bestpaperId}/verifiers`);
            const box = sQ('selBestPaperVerifiers');
            if (!box) return;
            const list = sQ('bestPaperVerifiersList');
            
            // Clear the list efficiently
            while (list.firstChild) {
                list.removeChild(list.firstChild);
            }
            
            if (data && data.length > 0) {
                const fragment = document.createDocumentFragment();
                data.forEach(v => {
                    const li = document.createElement('li');
                    li.className = 'px-3 py-2 flex items-center justify-between gap-2 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 rounded';
                    
                    const nameSpan = document.createElement('span');
                    nameSpan.className = 'truncate font-medium';
                    nameSpan.textContent = v.username || v.email || 'Unknown Verifier';
                    
                    const btn = document.createElement('button');
                    btn.className = 'unassignVerifier btn btn-ghost px-2 py-1 text-[10px] flex items-center gap-1';
                    btn.dataset.id = v.id;
                    
                    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    svg.className = 'w-3 h-3';
                    svg.setAttribute('fill', 'none');
                    svg.setAttribute('viewBox', '0 0 24 24');
                    svg.setAttribute('stroke', 'currentColor');
                    
                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    path.setAttribute('stroke-linecap', 'round');
                    path.setAttribute('stroke-linejoin', 'round');
                    path.setAttribute('stroke-width', '2');
                    path.setAttribute('d', 'M6 18L18 6M6 6l12 12');
                    svg.appendChild(path);
                    
                    btn.appendChild(svg);
                    btn.appendChild(document.createTextNode('Unassign'));
                    
                    li.appendChild(nameSpan);
                    li.appendChild(btn);
                    fragment.appendChild(li);
                });
                list.appendChild(fragment);
                box.classList.remove('hidden');
            } else {
                const li = document.createElement('li');
                li.className = 'px-3 py-2 text-muted text-sm';
                li.textContent = 'No verifiers assigned to this best paper';
                list.appendChild(li);
                box.classList.remove('hidden');
            }
            
            // Wire inline unassign buttons
            list.querySelectorAll('.unassignVerifier').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const verifierId = btn.dataset.id;
                    try {
                        const r = await fetch(`${BASE}/api/v1/research/best-papers/${bestpaperId}/verifiers/${verifierId}`, { 
                            method: 'DELETE', 
                            headers: headers() 
                        });
                        if (!r.ok) throw new Error(await r.text() || r.status);
                        toast('Verifier unassigned successfully', 'success');
                        await searchBestPapers();
                        await loadBestPaperVerifiers(bestpaperId); // refresh list
                        highlightSelection();
                    } catch (err) {
                        toast('Failed to unassign verifier: ' + (err.message || 'Unknown error'), 'error');
                    }
                });
            });
        } catch (e) {
            toast('Failed to load best paper verifiers: ' + (e.message || 'Unknown error'), 'error');
            hideBestPaperVerifiers();
        }
    }
    
    async function loadVerifierBestPapers(verifierId) {
        try {
            const data = await fetchJSON(`${BASE}/api/v1/research/verifiers/${verifierId}/best-papers`);
            const box = sQ('selVerifierBestPapers');
            if (!box) return;
            const list = sQ('verifierBestPapersList');
            
            // Clear the list efficiently
            while (list.firstChild) {
                list.removeChild(list.firstChild);
            }
            
            const bestpapers = normalizeBestPaperArray(Array.isArray(data) ? data : (data.bestpapers || data.best_papers || []));
            if (bestpapers.length > 0) {
                const fragment = document.createDocumentFragment();
                bestpapers.forEach(a => {
                    const li = document.createElement('li');
                    li.className = 'px-3 py-2 flex items-center justify-between gap-2 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 rounded';
                    
                    const titleSpan = document.createElement('span');
                    titleSpan.className = 'truncate font-medium';
                    titleSpan.textContent = a.title || 'Untitled Best Paper';
                    
                    const btn = document.createElement('button');
                    btn.className = 'unassignBestPaper btn btn-ghost px-2 py-1 text-[10px] flex items-center gap-1';
                    btn.dataset.id = a.id;
                    
                    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    svg.className = 'w-3 h-3';
                    svg.setAttribute('fill', 'none');
                    svg.setAttribute('viewBox', '0 0 24 24');
                    svg.setAttribute('stroke', 'currentColor');
                    
                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    path.setAttribute('stroke-linecap', 'round');
                    path.setAttribute('stroke-linejoin', 'round');
                    path.setAttribute('stroke-width', '2');
                    path.setAttribute('d', 'M6 18L18 6M6 6l12 12');
                    svg.appendChild(path);
                    
                    btn.appendChild(svg);
                    btn.appendChild(document.createTextNode('Unassign'));
                    
                    li.appendChild(titleSpan);
                    li.appendChild(btn);
                    fragment.appendChild(li);
                });
                list.appendChild(fragment);
            } else {
                const li = document.createElement('li');
                li.className = 'px-3 py-2 text-muted text-sm';
                li.textContent = 'No best papers assigned to this verifier';
                list.appendChild(li);
            }
            
            const countEl = sQ('verifierBestPaperCount') || sQ('verifierBestPaperCount');
            if (countEl) countEl.textContent = bestpapers.length;
            box.classList.remove('hidden');
            
            // Wire inline unassign buttons
            list.querySelectorAll('.unassignBestPaper').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const bestpaperId = btn.dataset.id;
                    try {
                        const r = await fetch(`${BASE}/api/v1/research/best-papers/${bestpaperId}/verifiers/${verifierId}`, { 
                            method: 'DELETE', 
                            headers: headers() 
                        });
                        if (!r.ok) throw new Error(await r.text() || r.status);
                        toast('Best paper unassigned successfully', 'success');
                        await searchBestPapers();
                        await loadVerifierBestPapers(verifierId); // refresh list
                        highlightSelection();
                    } catch (err) {
                        toast('Failed to unassign best paper: ' + (err.message || 'Unknown error'), 'error');
                    }
                });
            });
        } catch (e) {
            toast('Failed to load verifier best papers: ' + (e.message || 'Unknown error'), 'error');
            hideVerifierBestPapers();
        }
    }
    
    async function searchBestPapers() {
        state.bestpapers.q = (sQ('bestpaperSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.bestpapers;
        const url = `${BASE}/api/v1/research/best-papers?q=${encodeURIComponent(q)}&verifiers=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}`;
        try {
            const data = await fetchJSON(url);
            const normalizedItems = normalizeBestPaperArray(Array.isArray(data) ? data : (data.items || []));
            renderList(bestpaperList, normalizedItems, 'bestpaper');
            updateBestPaperMeta(data);
        } catch (e) {
            console.error(e);
            toast('Failed to load best papers: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function searchVerifiers() {
        state.verifiers.q = (sQ('verifierSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.verifiers;
        const url = `${BASE}/api/v1/user/users/verifiers?q=${encodeURIComponent(q)}&has_bestpapers=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}`;
        try {
            const data = await fetchJSON(url);
            renderList(verifierList, data.items || data || [], 'verifier');
            updateVerifierMeta(data);
        } catch (e) {
            console.error(e);
            toast('Failed to load verifiers: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function assign() {
        if (!(selBestPaper && selVerifier)) {
            toast('Please select both a best paper and a verifier', 'warn');
            return;
        }
        try {
            const r = await fetch(`${BASE}/api/v1/research/best-papers/${selBestPaper.id}/verifiers/${selVerifier.id}`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' }
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Verifier assigned successfully', 'success');
            await searchBestPapers();
            await searchVerifiers();
            highlightSelection();
            updatePanel();
        } catch (e) {
            toast('Failed to assign verifier: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function unassign() {
        if (!(selBestPaper && selVerifier)) {
            toast('Please select both a best paper and a verifier', 'warn');
            return;
        }
        try {
            const r = await fetch(`${BASE}/api/v1/research/best-papers/${selBestPaper.id}/verifiers/${selVerifier.id}`, {
                method: 'DELETE',
                headers: headers()
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Verifier unassigned successfully', 'success');
            await searchBestPapers();
            await searchVerifiers();
            highlightSelection();
            updatePanel();
        } catch (e) {
            toast('Failed to unassign verifier: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function bulkAssign() {
        if (!bulk.bestpaperIds.size || !selVerifier) {
            toast('Select best papers and a verifier first', 'warn');
            return;
        }
        
        // Show confirmation dialog for bulk operations
        if (!confirm(`Are you sure you want to assign ${bulk.bestpaperIds.size} best paper(s) to ${selVerifier.username}?`)) {
            return;
        }
        
        try {
            const body = {
                best_paper_ids: Array.from(bulk.bestpaperIds),
                user_ids: [selVerifier.id]
            };
            const r = await fetch(BASE + '/api/v1/research/best-papers/bulk-assign-verifiers', {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            const result = await r.json();
            toast(`Bulk assigned: ${result.assignments_created} assignments created`, 'success');
            await searchBestPapers();
            await searchVerifiers();
            highlightSelection();
            // Clear bulk selection after successful assignment
            bulk.bestpaperIds.clear();
            syncMasterChk();
            updateBulkStatus();
        } catch (e) {
            toast('Bulk assign failed: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function bulkUnassign() {
        if (!bulk.bestpaperIds.size || !selVerifier) {
            toast('Select best papers and a verifier first', 'warn');
            return;
        }
        
        // Show confirmation dialog for bulk operations
        if (!confirm(`Are you sure you want to unassign ${bulk.bestpaperIds.size} best paper(s) from ${selVerifier.username}?`)) {
            return;
        }
        
        try {
            const body = {
                best_paper_ids: Array.from(bulk.bestpaperIds),
                user_ids: [selVerifier.id]
            };
            const r = await fetch(BASE + '/api/v1/research/best-papers/bulk-unassign-verifiers', {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            const result = await r.json();
            toast(`Bulk unassigned: ${result.assignments_deleted} assignments deleted`, 'success');
            await searchBestPapers();
            await searchVerifiers();
            highlightSelection();
            // Clear bulk selection after successful unassignment
            bulk.bestpaperIds.clear();
            syncMasterChk();
            updateBulkStatus();
        } catch (e) {
            toast('Bulk unassign failed: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    function clearSel() {
        selBestPaper = null;
        selVerifier = null;
        updatePanel();
        highlightSelection();
        // Clear bulk selection when clearing selections
        bulk.bestpaperIds.clear();
        syncMasterChk();
        updateBulkStatus();
    }

    function updateBestPaperMeta(data) {
        state.bestpapers.pages = data.pages || 1;
        const info = sQ('bestpaperPageInfo');
        if (info) info.textContent = `Page ${data.page || 1} of ${data.pages || 1}`;
        const stats = sQ('bestpaperStats');
        if (stats) {
            const filterLabel = state.bestpapers.filter === '' ? 'All' : (state.bestpapers.filter === 'yes' ? 'With Verifiers' : 'Without Verifiers');
            stats.textContent = `${data.total || 0} total • Filter: ${filterLabel}`;
        }
    }
    
    function updateVerifierMeta(data) {
        state.verifiers.pages = data.pages || 1;
        const info = sQ('verifierPageInfo');
        if (info) info.textContent = `Page ${data.page || 1} of ${data.pages || 1}`;
        const stats = sQ('verifierStats');
        if (stats) {
            const filterLabel = state.verifiers.filter === '' ? 'All' : (state.verifiers.filter === 'yes' ? 'Assigned' : 'Unassigned');
            stats.textContent = `${data.total || 0} total • Filter: ${filterLabel}`;
        }
    }

    function changeBestPaperPage(delta) {
        state.bestpapers.page = Math.min(Math.max(1, state.bestpapers.page + delta), state.bestpapers.pages);
        searchBestPapers();
    }
    
    function changeVerifierPage(delta) {
        state.verifiers.page = Math.min(Math.max(1, state.verifiers.page + delta), state.verifiers.pages);
        searchVerifiers();
    }

    function toast(msg, type = 'info') {
        if (window.showToast) window.showToast(msg, type, 4000);
        else console.log(`[${type.toUpperCase()}] ${msg}`);
    }
    
    function escapeHtml(s) {
        return String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
    }

    // Enhanced search with debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    const debouncedSearchBestPapers = debounce(() => {
        state.bestpapers.page = 1;
        searchBestPapers();
    }, 300);
    
    const debouncedSearchVerifiers = debounce(() => {
        state.verifiers.page = 1;
        searchVerifiers();
    }, 300);

    function init() {
        // Search buttons
        sQ('bestpaperSearchBtn')?.addEventListener('click', () => { 
            state.bestpapers.page = 1; 
            searchBestPapers(); 
        });
        sQ('verifierSearchBtn')?.addEventListener('click', () => { 
            state.verifiers.page = 1; 
            searchVerifiers(); 
        });
        
        // Pagination buttons
        sQ('bestpaperPrev')?.addEventListener('click', () => changeBestPaperPage(-1));
        sQ('bestpaperNext')?.addEventListener('click', () => changeBestPaperPage(1));
        sQ('verifierPrev')?.addEventListener('click', () => changeVerifierPage(-1));
        sQ('verifierNext')?.addEventListener('click', () => changeVerifierPage(1));
        
        // Bulk action buttons
        sQ('bulkAssignBtn')?.addEventListener('click', bulkAssign);
        sQ('bulkUnassignBtn')?.addEventListener('click', bulkUnassign);
        
        // Assignment buttons
        sQ('assignBtn')?.addEventListener('click', assign);
        sQ('unassignBtn')?.addEventListener('click', unassign);
        sQ('clearSel')?.addEventListener('click', clearSel);
        
        // Selection controls
        const master = sQ('bestpaperMasterChk');
        master?.addEventListener('change', e => { e.target.checked ? selectAllPage() : clearAllPage(); });
        sQ('invertSelection')?.addEventListener('click', invertSelection);
        sQ('bestpaperSelectAll')?.addEventListener('click', selectAllPage);
        sQ('bestpaperClearSel')?.addEventListener('click', clearAllPage);
        
        // Enter key support for search
        sQ('bestpaperSearch')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                state.bestpapers.page = 1;
                searchBestPapers();
            }
        });
        sQ('verifierSearch')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                state.verifiers.page = 1;
                searchVerifiers();
            }
        });
        
        // Real-time search with debounce
        sQ('bestpaperSearch')?.addEventListener('input', debouncedSearchBestPapers);
        sQ('verifierSearch')?.addEventListener('input', debouncedSearchVerifiers);
        
        // Initialize UI
        wireSortGroups();
        wireSegmentedControls();
        searchBestPapers();
        searchVerifiers();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
