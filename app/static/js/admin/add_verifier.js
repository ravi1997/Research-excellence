(() => {
    const BASE = '';
    const token = () => localStorage.getItem('token') || '';
    const headers = () => ({ 'Accept': 'application/json', 'Authorization': `Bearer ${token()}` });
    const sQ = id => document.getElementById(id);
    const abstractList = sQ('abstractList');
    const verifierList = sQ('verifierList');
    let selAbstract = null; let selVerifier = null;
    const bulk = { abstractIds: new Set() };

    const state = {
        abstracts: { page: 1, pages: 1, pageSize: 20, filter: '', q: '', sort: 'id', dir: 'desc' },
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

    function activateSeg(group, btn) {
        group.querySelectorAll('.seg').forEach(b => b.classList.remove('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]'));
        btn.classList.add('active', 'bg-[color:var(--brand-600)]', 'text-white', 'dark:bg-[color:var(--brand-500)]');
    }

    function wireSegmentedControls() {
        const aLinkGroup = sQ('abstractLinkedGroup');
        aLinkGroup?.addEventListener('click', e => {
            const btn = e.target.closest('.seg'); if (!btn) return;
            activateSeg(aLinkGroup, btn);
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

    // Attach sorting behavior to abstract & verifier sort button groups
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
            empty.textContent = type === 'abstract' ? 'No abstracts found' : 'No verifiers found';
            el.appendChild(empty);
            return;
        }

        const fragment = document.createDocumentFragment();

        items.forEach(it => {
            const li = document.createElement('li');
            const selected = bulk.abstractIds?.has?.(it.id) && type === 'abstract';

            // Layout fixes: items start, gap, allow text to wrap, badge stays visible
            li.className =
                'group py-3 px-3 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 ' +
                'cursor-pointer flex items-start justify-between gap-3 transition-colors rounded-lg ' +
                (selected ? 'bg-[color:var(--brand-100)] dark:bg-[color:var(--brand-900)]' : '');
            li.dataset.id = it.id;

            if (type === 'abstract') {
                const left = document.createElement('div');
                left.className = 'flex items-start gap-3 min-w-0 grow';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'bulkChk accent-[color:var(--brand-600)] rounded h-4 w-4 mt-1 shrink-0';
                checkbox.dataset.id = it.id;
                checkbox.checked = selected;

                const textCol = document.createElement('div');
                textCol.className = 'min-w-0';

                const titleSpan = document.createElement('div');
                // Multi-line title: allow wrapping; avoid truncation; break long words
                titleSpan.className = 'font-medium whitespace-normal break-words';
                titleSpan.textContent = it.title || 'Untitled Abstract';
                titleSpan.title = it.title || 'Untitled Abstract'; // tooltip for very long titles

                const meta = document.createElement('div');
                meta.className = 'muted text-xs mt-1 space-x-2';
                const cat = document.createElement('span');
                cat.textContent = it.category?.name || 'No Category';
                const dot = document.createElement('span');
                dot.textContent = '•';
                const submittedBy = document.createElement('span');
                submittedBy.textContent = `Submitted by: ${it.submitted_by?.username || it.created_by?.username || 'Unknown'}`;
                const dot2 = document.createElement('span');
                dot2.textContent = '•';
                const abstractNum = document.createElement('span');
                abstractNum.textContent = `Abstract #${it.abstract_number || 'N/A'}`;

                meta.appendChild(cat);
                meta.appendChild(dot);
                meta.appendChild(submittedBy);
                meta.appendChild(dot2);
                meta.appendChild(abstractNum);

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
                    selAbstract = it;
                    updatePanel();
                    highlightSelection();
                });

                // Checkbox behavior
                checkbox.addEventListener('change', (e) => {
                    const id = e.target.dataset.id;
                    if (e.target.checked) bulk.abstractIds.add(id); else bulk.abstractIds.delete(id);
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
                if (it.abstracts_count && it.abstracts_count > 0) {
                    badge.className += ' bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
                    badge.textContent = `${it.abstracts_count} abstract${it.abstracts_count > 1 ? 's' : ''}`;
                } else {
                    badge.className += ' bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
                    badge.textContent = 'no abstracts';
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
        if (type === 'abstract') {
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

    function renderSelectedAbstract(a) {
        const $ = (id) => document.getElementById(id);

        // Title
        $('selAbstractTitle').textContent = a?.title || 'Untitled Abstract';

        // Meta badges (number, category, status, phase, created)
        const num = a?.abstract_number ? `#${a.abstract_number}` : 'No Number';
        const cat = a?.category?.name || 'No Category';
        const status = (a?.status || '').toString().replace(/^Status\./, '') || 'UNKNOWN';
        const phase = (a?.review_phase ?? '—');

        $('selAbstractMeta').innerHTML = [
            badge(num, 'bg-white/60 dark:bg-white/5'),
            badge(cat, 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'),
            badge(status, status === 'PENDING'
                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200'
                : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'),
            badge(`Phase ${phase}`, 'bg-white/60 dark:bg-white/5'),
            badge(`Submitted ${formatDateISO(a?.submitted_on)}`, 'bg-white/60 dark:bg-white/5')
        ].join(' ');

        // Submitted By
        const sb = a?.submitted_by || a?.created_by || {};
        const sbLines = [
            `<div><span class="font-medium">${sb.username || 'Unknown'}</span></div>`,
            `<div class="muted break-all">${sb.email || 'No email'}</div>`,
            `<div class="muted break-all">${sb.mobile || 'No mobile'}</div>`
        ].join('');
        $('selSubmittedBy').innerHTML = sbLines;

        // Authors
        const authors = Array.isArray(a?.authors) ? a.authors : [];
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
        <div class="font-medium break-words">${au.name || 'Unnamed'}</div>
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
        $('selAbstractDetails').textContent = a?.content || '—';

        // PDF link
        const pdfHref = '/api/v1/research/abstracts/' + (a?.id || '') + '/pdf';
        const pdfEl = $('selPdfLink');
        pdfEl.href = pdfHref || '#';
        pdfEl.textContent = pdfHref && pdfHref !== '#' ? pdfHref : 'Not uploaded';

        // Verifiers section
        const vWrap = document.getElementById('selAbstractVerifiers');
        const vList = document.getElementById('abstractVerifiersList');
        vList.innerHTML = '';
        const verifiers = Array.isArray(a?.verifiers) ? a.verifiers : [];
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
        <div class="font-medium break-words">${v.username || '—'}</div>
        <div class="text-[12px] muted break-all">${v.email || 'No email'}${v.mobile ? ' • ' + v.mobile : ''}</div>
      `;
                li.appendChild(left);
                frag.appendChild(li);
            });
            vList.appendChild(frag);
        }
    }

    function updatePanel() {
        const panel = sQ('assignPanel');
        const aSpan = sQ('selAbstract') || sQ('selAbstractTitle');   // legacy or new title
        const aDetails = sQ('selAbstractDetails');
        const vSpan = sQ('selVerifier');
        const vStatus = sQ('selVerifierStatus');

        // ----- ABSTRACT SIDE -----
        if (selAbstract) {
            // Use the rich renderer if present (from the upgraded UI)
            if (typeof renderSelectedAbstract === 'function') {
                renderSelectedAbstract(selAbstract);
            }
            // Keep legacy fields in sync (safe no-ops if missing)
            if (aSpan) aSpan.textContent = selAbstract.title || 'Untitled Abstract';
            if (aDetails) aDetails.textContent = selAbstract.content
                ? selAbstract.content
                : 'No content available';

            // Load verifiers list for this abstract
            loadAbstractVerifiers(selAbstract.id);
        } else {
            // Reset abstract UI (both new and legacy)
            if (aSpan) aSpan.textContent = 'No abstract selected';
            if (aDetails) aDetails.textContent = 'Select an abstract to view details';

            const sb = document.getElementById('selSubmittedBy');
            if (sb) sb.innerHTML = '';

            const authors = document.getElementById('selAuthorsList');
            if (authors) authors.innerHTML = '';

            const meta = document.getElementById('selAbstractMeta');
            if (meta) meta.innerHTML = '';

            const pdf = document.getElementById('selPdfLink');
            if (pdf) { pdf.href = '#'; pdf.textContent = 'Not uploaded'; }

            const vWrap = document.getElementById('selAbstractVerifiers');
            const vList = document.getElementById('abstractVerifiersList');
            if (vList) vList.innerHTML = '';
            if (vWrap) vWrap.classList.add('hidden');

            hideAbstractVerifiers();
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
            loadVerifierAbstracts(selVerifier.id);
        } else {
            if (vSpan) vSpan.textContent = 'No verifier selected';
            if (vStatus) vStatus.textContent = 'Select a verifier to assign';
            hideVerifierAbstracts();
        }

        // Show panel if either side has a selection
        panel.hidden = !(selAbstract || selVerifier);
    }

    
    function hideAbstractVerifiers() {
        const box = sQ('selAbstractVerifiers');
        if (box) { box.classList.add('hidden'); }
    }
    
    function hideVerifierAbstracts() {
        const box = sQ('selVerifierAbstracts');
        if (box) { box.classList.add('hidden'); }
    }

    async function loadAbstractVerifiers(abstractId) {
        try {
            const data = await fetchJSON(`${BASE}/api/v1/research/abstracts/${abstractId}/verifiers`);
            const box = sQ('selAbstractVerifiers');
            if (!box) return;
            const list = sQ('abstractVerifiersList');
            
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
                li.textContent = 'No verifiers assigned to this abstract';
                list.appendChild(li);
                box.classList.remove('hidden');
            }
            
            // Wire inline unassign buttons
            list.querySelectorAll('.unassignVerifier').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const verifierId = btn.dataset.id;
                    try {
                        const r = await fetch(`${BASE}/api/v1/research/abstracts/${abstractId}/verifiers/${verifierId}`, { 
                            method: 'DELETE', 
                            headers: headers() 
                        });
                        if (!r.ok) throw new Error(await r.text() || r.status);
                        toast('Verifier unassigned successfully', 'success');
                        await searchAbstracts();
                        await loadAbstractVerifiers(abstractId); // refresh list
                        highlightSelection();
                    } catch (err) {
                        toast('Failed to unassign verifier: ' + (err.message || 'Unknown error'), 'error');
                    }
                });
            });
        } catch (e) {
            toast('Failed to load abstract verifiers: ' + (e.message || 'Unknown error'), 'error');
            hideAbstractVerifiers();
        }
    }
    
    async function loadVerifierAbstracts(verifierId) {
        try {
            const data = await fetchJSON(`${BASE}/api/v1/research/verifiers/${verifierId}/abstracts`);
            const box = sQ('selVerifierAbstracts');
            if (!box) return;
            const list = sQ('verifierAbstractsList');
            
            // Clear the list efficiently
            while (list.firstChild) {
                list.removeChild(list.firstChild);
            }
            
            const abstracts = Array.isArray(data) ? data : (data.abstracts || []);
            if (abstracts.length > 0) {
                const fragment = document.createDocumentFragment();
                abstracts.forEach(a => {
                    const li = document.createElement('li');
                    li.className = 'px-3 py-2 flex items-center justify-between gap-2 hover:bg-[color:var(--brand-50)] dark:hover:bg-[color:var(--brand-900)]/40 rounded';
                    
                    const titleSpan = document.createElement('span');
                    titleSpan.className = 'truncate font-medium';
                    titleSpan.textContent = a.title || 'Untitled Abstract';
                    
                    const btn = document.createElement('button');
                    btn.className = 'unassignAbstract btn btn-ghost px-2 py-1 text-[10px] flex items-center gap-1';
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
                li.textContent = 'No abstracts assigned to this verifier';
                list.appendChild(li);
            }
            
            sQ('verifierAbstractCount').textContent = abstracts.length;
            box.classList.remove('hidden');
            
            // Wire inline unassign buttons
            list.querySelectorAll('.unassignAbstract').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const abstractId = btn.dataset.id;
                    try {
                        const r = await fetch(`${BASE}/api/v1/research/abstracts/${abstractId}/verifiers/${verifierId}`, { 
                            method: 'DELETE', 
                            headers: headers() 
                        });
                        if (!r.ok) throw new Error(await r.text() || r.status);
                        toast('Abstract unassigned successfully', 'success');
                        await searchAbstracts();
                        await loadVerifierAbstracts(verifierId); // refresh list
                        highlightSelection();
                    } catch (err) {
                        toast('Failed to unassign abstract: ' + (err.message || 'Unknown error'), 'error');
                    }
                });
            });
        } catch (e) {
            toast('Failed to load verifier abstracts: ' + (e.message || 'Unknown error'), 'error');
            hideVerifierAbstracts();
        }
    }
    
    async function searchAbstracts() {
        state.abstracts.q = (sQ('abstractSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.abstracts;
        const url = `${BASE}/api/v1/research/abstracts?q=${encodeURIComponent(q)}&verifiers=${filter}&page=${page}&page_size=${pageSize}&sort=${sort}&dir=${dir}`;
        try {
            const data = await fetchJSON(url);
            renderList(abstractList, data.items || data || [], 'abstract');
            updateAbstractMeta(data);
        } catch (e) {
            console.error(e);
            toast('Failed to load abstracts: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function searchVerifiers() {
        state.verifiers.q = (sQ('verifierSearch').value || '').trim();
        const { q, filter, page, pageSize, sort, dir } = state.verifiers;
        const url = `${BASE}/api/v1/user/users/verifiers?q=${encodeURIComponent(q)}&has_abstracts=${filter}&page=${page}&page_size=${pageSize}&sort_by=${sort}&sort_dir=${dir}`;
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
        if (!(selAbstract && selVerifier)) {
            toast('Please select both an abstract and a verifier', 'warn');
            return;
        }
        try {
            const r = await fetch(`${BASE}/api/v1/research/abstracts/${selAbstract.id}/verifiers/${selVerifier.id}`, {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' }
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Verifier assigned successfully', 'success');
            await searchAbstracts();
            await searchVerifiers();
            highlightSelection();
            updatePanel();
        } catch (e) {
            toast('Failed to assign verifier: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function unassign() {
        if (!(selAbstract && selVerifier)) {
            toast('Please select both an abstract and a verifier', 'warn');
            return;
        }
        try {
            const r = await fetch(`${BASE}/api/v1/research/abstracts/${selAbstract.id}/verifiers/${selVerifier.id}`, {
                method: 'DELETE',
                headers: headers()
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            toast('Verifier unassigned successfully', 'success');
            await searchAbstracts();
            await searchVerifiers();
            highlightSelection();
            updatePanel();
        } catch (e) {
            toast('Failed to unassign verifier: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function bulkAssign() {
        if (!bulk.abstractIds.size || !selVerifier) {
            toast('Select abstracts and a verifier first', 'warn');
            return;
        }
        
        // Show confirmation dialog for bulk operations
        if (!confirm(`Are you sure you want to assign ${bulk.abstractIds.size} abstract(s) to ${selVerifier.username}?`)) {
            return;
        }
        
        try {
            const body = {
                abstract_ids: Array.from(bulk.abstractIds),
                user_ids: [selVerifier.id]
            };
            const r = await fetch(BASE + '/api/v1/research/abstracts/bulk-assign-verifiers', {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            const result = await r.json();
            toast(`Bulk assigned: ${result.assignments_created} assignments created`, 'success');
            await searchAbstracts();
            await searchVerifiers();
            highlightSelection();
            // Clear bulk selection after successful assignment
            bulk.abstractIds.clear();
            syncMasterChk();
            updateBulkStatus();
        } catch (e) {
            toast('Bulk assign failed: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    async function bulkUnassign() {
        if (!bulk.abstractIds.size || !selVerifier) {
            toast('Select abstracts and a verifier first', 'warn');
            return;
        }
        
        // Show confirmation dialog for bulk operations
        if (!confirm(`Are you sure you want to unassign ${bulk.abstractIds.size} abstract(s) from ${selVerifier.username}?`)) {
            return;
        }
        
        try {
            const body = {
                abstract_ids: Array.from(bulk.abstractIds),
                user_ids: [selVerifier.id]
            };
            const r = await fetch(BASE + '/api/v1/research/abstracts/bulk-unassign-verifiers', {
                method: 'POST',
                headers: { ...headers(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!r.ok) throw new Error(await r.text() || r.status);
            const result = await r.json();
            toast(`Bulk unassigned: ${result.assignments_deleted} assignments deleted`, 'success');
            await searchAbstracts();
            await searchVerifiers();
            highlightSelection();
            // Clear bulk selection after successful unassignment
            bulk.abstractIds.clear();
            syncMasterChk();
            updateBulkStatus();
        } catch (e) {
            toast('Bulk unassign failed: ' + (e.message || 'Unknown error'), 'error');
        }
    }
    
    function clearSel() {
        selAbstract = null;
        selVerifier = null;
        updatePanel();
        highlightSelection();
        // Clear bulk selection when clearing selections
        bulk.abstractIds.clear();
        syncMasterChk();
        updateBulkStatus();
    }

    function updateAbstractMeta(data) {
        state.abstracts.pages = data.pages || 1;
        const info = sQ('abstractPageInfo');
        if (info) info.textContent = `Page ${data.page || 1} of ${data.pages || 1}`;
        const stats = sQ('abstractStats');
        if (stats) {
            const filterLabel = state.abstracts.filter === '' ? 'All' : (state.abstracts.filter === 'yes' ? 'With Verifiers' : 'Without Verifiers');
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

    function changeAbstractPage(delta) {
        state.abstracts.page = Math.min(Math.max(1, state.abstracts.page + delta), state.abstracts.pages);
        searchAbstracts();
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
    
    const debouncedSearchAbstracts = debounce(() => {
        state.abstracts.page = 1;
        searchAbstracts();
    }, 300);
    
    const debouncedSearchVerifiers = debounce(() => {
        state.verifiers.page = 1;
        searchVerifiers();
    }, 300);

    function init() {
        // Search buttons
        sQ('abstractSearchBtn')?.addEventListener('click', () => { 
            state.abstracts.page = 1; 
            searchAbstracts(); 
        });
        sQ('verifierSearchBtn')?.addEventListener('click', () => { 
            state.verifiers.page = 1; 
            searchVerifiers(); 
        });
        
        // Pagination buttons
        sQ('abstractPrev')?.addEventListener('click', () => changeAbstractPage(-1));
        sQ('abstractNext')?.addEventListener('click', () => changeAbstractPage(1));
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
        const master = sQ('abstractMasterChk');
        master?.addEventListener('change', e => { e.target.checked ? selectAllPage() : clearAllPage(); });
        sQ('invertSelection')?.addEventListener('click', invertSelection);
        sQ('abstractSelectAll')?.addEventListener('click', selectAllPage);
        sQ('abstractClearSel')?.addEventListener('click', clearAllPage);
        
        // Enter key support for search
        sQ('abstractSearch')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                state.abstracts.page = 1;
                searchAbstracts();
            }
        });
        sQ('verifierSearch')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                state.verifiers.page = 1;
                searchVerifiers();
            }
        });
        
        // Real-time search with debounce
        sQ('abstractSearch')?.addEventListener('input', debouncedSearchAbstracts);
        sQ('verifierSearch')?.addEventListener('input', debouncedSearchVerifiers);
        
        // Initialize UI
        wireSortGroups();
        wireSegmentedControls();
        searchAbstracts();
        searchVerifiers();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();