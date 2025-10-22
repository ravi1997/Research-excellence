// abstract_submit.js
(function() {
    function setupFlow() {
        // Step navigation
        const step1 = document.getElementById('step1');
        const step2 = document.getElementById('step2');
        const step3 = document.getElementById('step3');
        const step4 = document.getElementById('step4');
        const step5 = document.getElementById('step5');
        const next1 = document.querySelector('.next-step[data-step="1"]');
        const next2 = document.querySelector('.next-step[data-step="2"]');
        const next3 = document.querySelector('.next-step[data-step="3"]');
        const next4 = document.querySelector('.next-step[data-step="4"]');
        const next5 = document.querySelector('.next-step[data-step="5"]');
        const prev2 = document.querySelector('.prev-step[data-step="2"]');
        const prev3 = document.querySelector('.prev-step[data-step="3"]');
        const prev4 = document.querySelector('.prev-step[data-step="4"]');
        const prev5 = document.querySelector('.prev-step[data-step="5"]');

        const abstract_title = document.getElementById('title');
        const abstract_title_count = document.getElementById('title_count');

        if (abstract_title && abstract_title_count) {
            abstract_title.addEventListener('input', function() {
                const words = countWords(this.value);
                abstract_title_count.textContent = words;
            });
        }

        function show(el) { if (el) el.classList.remove('hidden'); }
        function hide(el) { if (el) el.classList.add('hidden'); }
        function mark(step) {
            const circles = document.querySelectorAll('#progress_bar .w-6.h-6');
            const labels = document.querySelectorAll('#progress_bar .sm\\:inline');
            circles.forEach((n, i) => {
                if (!n) return;
                const idx = i + 1;
                if (idx === step) {
                    n.classList.add('bg-[color:var(--brand-600)]', 'text-white');
                    n.classList.remove('bg-[color:var(--border)]', 'text-[color:var(--text-muted)]');
                    if (labels[i]) labels[i].classList.add('text-[color:var(--brand-600)]');
                } else {
                    n.classList.remove('bg-[color:var(--brand-600)]', 'text-white');
                    n.classList.add('bg-[color:var(--border)]', 'text-[color:var(--text-muted)]');
                    if (labels[i]) labels[i].classList.remove('text-[color:var(--brand-600)]');
                }
            });
        }
        mark(1);

        if (next1) next1.addEventListener('click', function() {
            const title = document.getElementById('title');
            const category = document.getElementById('category');
            if (!title || !title.value.trim()) {
                showToast('Please enter an abstract title.', 'error');
                title && title.focus();
                return;
            }

            if(title && countWords(title.value) > 50) {
                showToast('Abstract title must be at most 50 words.', 'error');
                title && title.focus();
                return;
            }


            if (!category || !category.value) {
                showToast('Please select a category.', 'error');
                category && category.focus();
                return;
            }
            hide(step1); show(step2); mark(2);
            // Ensure at least one author field exists
            const authorsContainer = document.getElementById('authors-container');
            if (authorsContainer && authorsContainer.children.length === 0) {
                addAuthorField();
            }
        });

        if (next2) next2.addEventListener('click', function() {
            // Validate authors: at least one with name, valid emails, exactly one presenter and one corresponding
            if (!validateAuthorsAndEmails()) return;
            hide(step2); show(step3); mark(3);
        });

        if (next3) next3.addEventListener('click', function() {
            const MAX_WORDS = 500;
            const wordTotal = getTotalWordsAcrossSections();
            if (wordTotal === 0) { showToast('Abstract content is required.', 'error'); return; }
            if (wordTotal > MAX_WORDS) { showToast(`Abstract content must be at most ${MAX_WORDS} words (total across sections).`, 'error'); return; }
            hide(step3); show(step4); mark(4);
        });

        if (next4) next4.addEventListener('click', function() {
            hide(step4); show(step5); mark(5);
            generatePreview();
        });

        if (next5) next5.addEventListener('click', function() {
            // Already on final step
        });

        if (prev2) prev2.addEventListener('click', function() { hide(step2); show(step1); mark(1); });
        if (prev3) prev3.addEventListener('click', function() { hide(step3); show(step2); mark(2); });
        if (prev4) prev4.addEventListener('click', function() { hide(step4); show(step3); mark(3); });
        if (prev5) prev5.addEventListener('click', function() { hide(step5); show(step4); mark(4); });

        // Handle PDF file selection
        const pdfInput = document.getElementById('abstract_pdf');
        if (pdfInput) {
            pdfInput.addEventListener('change', function() {
                const file = this.files && this.files[0];
                if (!file) { const p = document.getElementById('pdf-preview'); if (p) p.classList.add('hidden'); clearPdfError(); return; }
                if (!validatePdf(file, this)) { this.value = ''; return; }
                updatePdfPreview(file);
            });
        }

        // Handle PDF removal
        const removePdfBtn = document.getElementById('remove-pdf');
        if (removePdfBtn) {
            removePdfBtn.addEventListener('click', function() {
                const pdfInput = document.getElementById('abstract_pdf');
                const preview = document.getElementById('pdf-preview');
                if (pdfInput) pdfInput.value = '';
                if (preview) preview.classList.add('hidden');
            });
        }
    }

    function setupEvents() {
        // Fetch categories for dropdown
        fetchCategories();
        fetchLatestActiveCycle();

        // Add author button
        var addAuthorBtn = document.getElementById('add-author-btn');
        if (addAuthorBtn) addAuthorBtn.addEventListener('click', addAuthorField);

        // Form submission
        var abstractForm = document.getElementById('abstract-form');
        if (abstractForm) abstractForm.addEventListener('submit', submitAbstract);

        // Save draft button
        var saveDraftBtn = document.getElementById('save-draft-btn');
        if (saveDraftBtn) saveDraftBtn.addEventListener('click', saveDraft);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setupFlow();
            setupEvents();
            initEditor();
            initContentCounter();
            initPdfDropzoneAndValidation();
        });
    } else {
        setupFlow();
        setupEvents();
        initEditor();
        initContentCounter();
        initPdfDropzoneAndValidation();
    }
})();

// Base API URL - using the correct prefix for the research API
const BASE_API_URL = '/api/v1/research';

// Show a toast message
function showToast(message, type = 'info') {
    // In a real implementation, this would use the existing toast system
    // For now, we'll show an alert and also log to console
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Try to use the existing toast system if available
    if (typeof window.showToast === 'function' && window.showToast !== showToast) {
        window.showToast(message, type);
    } else {
        // Fallback to alert
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize live character counter and softly gate Next button
function initContentCounter() {
    const out = document.getElementById('content-char');
    const nextBtn = document.querySelector('.next-step[data-step="3"]');
    if (!out) return;
    const MAX_WORDS = 500;
    const update = () => {
        const words = getTotalWordsAcrossSections();
        out.textContent = words;
        const isEmpty = words === 0;
        const tooLong = words > MAX_WORDS;
        const ok = !isEmpty && !tooLong;
        out.classList.toggle('text-red-600', tooLong);
        out.classList.toggle('text-gray-500', ok || isEmpty);
        if (nextBtn) {
            if (!ok) {
                nextBtn.classList.add('opacity-60', 'pointer-events-none');
                nextBtn.setAttribute('aria-disabled', 'true');
                nextBtn.title = `Content must be 1–${MAX_WORDS} words (total across sections).`;
            } else {
                nextBtn.classList.remove('opacity-60', 'pointer-events-none');
                nextBtn.removeAttribute('aria-disabled');
                nextBtn.removeAttribute('title');
            }
        }
    };
    // Fallback: listen to all section textareas for input events
    SECTION_META.forEach(sec => {
        const el = document.getElementById(sec.id);
        if (el) el.addEventListener('input', update);
    });
    // Hook into editor updates if available
    setEditorChangeHandler(update);
    update();
}

// Count words in a string (Unicode-aware, splits on whitespace). Numbers and symbols count as words; empty tokens are ignored.
function countWords(text) {
    if (!text) return 0;
    const trimmed = String(text).trim();
    if (!trimmed) return 0;
    // Replace line breaks/tabs with spaces, collapse multiple spaces, then split.
    return trimmed
        .replace(/[\t\n\r]+/g, ' ')
        .split(/\s+/)
        .filter(Boolean)
        .length;
}

// CKEditor integration for five sections
const SECTION_META = [
    { id: 'content_introduction', label: 'Introduction:' },
    { id: 'content_aims', label: 'Aims & Objectives:' },
    { id: 'content_materials_methods', label: 'Materials and methods:' },
    { id: 'content_results', label: 'Results:' },
    { id: 'content_conclusion', label: 'Conclusion:' }
];

let CKEDITOR_INSTANCES = {};

function initEditor() {
    if (typeof window.ClassicEditor === 'undefined') return;
    SECTION_META.forEach(({ id }) => {
        const textarea = document.getElementById(id);
        if (!textarea) return;
        window.ClassicEditor
            .create(textarea, {
                toolbar: {
                    items: ['heading', '|', 'bold', 'italic', 'underline', 'bulletedList', 'numberedList', '|', 'undo', 'redo'],
                    shouldNotGroupWhenFull: true
                },
                placeholder: 'Write here…',
                removePlugins: [
                    'CKBox', 'CKFinder', 'EasyImage', 'RealTimeCollaborativeComments', 'RealTimeCollaborativeTrackChanges',
                    'RealTimeCollaborativeRevisionHistory', 'PresenceList', 'Comments', 'TrackChanges', 'TrackChangesData',
                    'RevisionHistory', 'Pagination', 'WProofreader', 'MathType', 'SlashCommand', 'Template', 'DocumentOutline',
                    'FormatPainter', 'TableOfContents', 'ExportPdf', 'ExportWord', 'ImportWord'
                ]
            })
            .then(editor => {
                CKEDITOR_INSTANCES[id] = editor;
                // Update counter on content change
                editor.model.document.on('change:data', () => {
                    const ev = new Event('input');
                    textarea.dispatchEvent(ev);
                });
            })
            .catch(err => {
                console.error('CKEditor init failed for', id, err);
            });
    });
}

function getEditorsPlainMap() {
    const out = {};
    SECTION_META.forEach(({ id }) => {
        try {
            const ed = CKEDITOR_INSTANCES[id];
            if (ed) {
                out[id] = stripHtmlToPlain(ed.getData());
            } else {
                const ta = document.getElementById(id);
                out[id] = (ta && ta.value) ? stripHtmlToPlain(ta.value) : '';
            }
        } catch (e) {
            out[id] = '';
        }
    });
    return out;
}

function getTotalWordsAcrossSections() {
    const map = getEditorsPlainMap();
    let total = 0;
    Object.values(map).forEach(text => { total += countWords(text || ''); });
    return total;
}

function setEditorChangeHandler(fn) {
    const attach = () => {
        let attached = false;
        SECTION_META.forEach(({ id }) => {
            const ed = CKEDITOR_INSTANCES[id];
            if (ed) {
                ed.model.document.on('change:data', fn);
                attached = true;
            }
        });
        return attached;
    };
    if (!attach()) {
        setTimeout(() => { attach(); }, 800);
    }
}

function stripHtmlToPlain(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html || '';
    return (tmp.textContent || tmp.innerText || '').replace(/\u00A0/g, ' ').trim();
}

// Drag & drop and validation for PDF upload
function initPdfDropzoneAndValidation() {
    const dz = document.getElementById('pdf-dropzone');
    const input = document.getElementById('abstract_pdf');
    if (!dz || !input) return;
    const enter = (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.add('ring-2', 'ring-blue-400'); };
    const leave = (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.remove('ring-2', 'ring-blue-400'); };
    const over = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; };
    const drop = (e) => {
        e.preventDefault(); e.stopPropagation(); dz.classList.remove('ring-2', 'ring-blue-400');
        const file = e.dataTransfer.files && e.dataTransfer.files[0];
        if (!file) return;
        if (!validatePdf(file, input)) return;
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event('change', { bubbles: true }));
    };
    dz.addEventListener('dragenter', enter);
    dz.addEventListener('dragleave', leave);
    dz.addEventListener('dragover', over);
    dz.addEventListener('drop', drop);
}

// Simple email regex for client-side validation
function isValidEmail(email) {
    if (!email) return true; // empty is allowed for optional
    // Lightweight RFC5322-ish regex sufficient for UI validation
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/i;
    return re.test(String(email).trim());
}

// Enforce author constraints and validate emails
function validateAuthorsAndEmails() {
    const authorFields = document.querySelectorAll('.author-field');
    if (authorFields.length === 0) {
        showToast('Please add at least one author.', 'error');
        return false;
    }

    let hasNamed = false;
    for (const field of authorFields) {
        const nameInput = field.querySelector('[id^="author-name-"]');
        const emailInput = field.querySelector('[id^="author-email-"]');
        const name = nameInput ? nameInput.value.trim() : '';
        const email = emailInput ? emailInput.value.trim() : '';
        if (name) hasNamed = true;
        if (email && !isValidEmail(email)) {
            showToast(`Invalid email: ${email}`, 'error');
            emailInput && emailInput.focus();
            return false;
        }
    }

    if (!hasNamed) {
        showToast('Please enter at least one author name.', 'error');
        return false;
    }
    const presenters = document.querySelectorAll('.author-field [id^="presenter-"]:checked').length;
    const correspondings = document.querySelectorAll('.author-field [id^="corresponding-"]:checked').length;
    if (presenters > 1) {
        showToast('Multiple presenters selected. Please select exactly one Presenter.', 'error');
        return false;
    }
    if (presenters < 1) {
        showToast('Please select a Presenter.', 'error');
        return false;
    }
    if (correspondings > 1) {
        showToast('Multiple corresponding authors selected. Please select exactly one Corresponding Author.', 'error');
        return false;
    }
    if (correspondings < 1) {
        showToast('Please select a Corresponding Author.', 'error');
        return false;
    }
    return true;
}

function validatePdf(file, inputEl) {
    const errEl = document.getElementById('pdf-error');
    const maxMB = Number(inputEl?.dataset?.maxSizeMb || 5);
    const isPdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name || '');
    const sizeOk = file.size <= maxMB * 1024 * 1024;
    let msg = '';
    if (!isPdf) msg = 'Only PDF files are allowed.';
    else if (!sizeOk) msg = `File is too large. Maximum size is ${maxMB} MB.`;
    if (msg) {
        if (errEl) { errEl.textContent = msg; errEl.classList.remove('sr-only'); }
        showToast(msg, 'error');
        hidePdfPreview();
        return false;
    }
    if (errEl) { errEl.textContent = ''; errEl.classList.add('sr-only'); }
    return true;
}

function clearPdfError() {
    const errEl = document.getElementById('pdf-error');
    if (errEl) { errEl.textContent = ''; errEl.classList.add('sr-only'); }
}

function updatePdfPreview(file) {
    const preview = document.getElementById('pdf-preview');
    const fileName = document.getElementById('pdf-file-name');
    const fileSize = document.getElementById('pdf-file-size');
    if (preview && fileName && fileSize) {
        fileName.textContent = file.name;
        fileSize.textContent = `Size: ${(file.size / 1024 / 1024).toFixed(2)} MB`;
        preview.classList.remove('hidden');
    }
}

function hidePdfPreview() {
    const preview = document.getElementById('pdf-preview');
    if (preview) preview.classList.add('hidden');
}

// Fetch categories from the API
async function fetchCategories() {
    const select = document.getElementById('category');
    if (!select) return;
    
    try {
        // Show loading state
        select.innerHTML = '<option value="">Loading categories...</option>';
        select.disabled = true;
        
        const response = await fetch(`${BASE_API_URL}/categories`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        const categories = Array.isArray(result) ? result : (result.categories || result.data || []);
        
        // Clear and populate options
        select.innerHTML = '<option value="">Select a category</option>';
        
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id || category.category_id;
            option.textContent = category.name || category.category_name || 'Unnamed Category';
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching categories:', error);
        showToast('Failed to load categories. Using default options.', 'error');
        // Fallback to mock data if API fails
        select.innerHTML = '<option value="">Select a category</option>';
        const categories = [
            { id: 1, name: 'Medical Research' },
            { id: 2, name: 'Clinical Research' },
            { id: 3, name: 'Public Health' },
            { id: 4, name: 'Biotechnology' }
        ];
        
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            select.appendChild(option);
        });
    } finally {
        if (select) select.disabled = false;
    }
}

// Fetch cycles from the API
// Fetch latest active cycle from the API and store its id
let latestCycleId = null;
let verifiers = []; // Store loaded verifiers

async function fetchLatestActiveCycle() {
    try {
        const response = await fetch(`${BASE_API_URL}/cycles`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const result = await response.json();
        const cycles = Array.isArray(result) ? result : (result.cycles || result.data || []);
        // Find latest active cycle (end_date in future, or latest end_date)
        const now = new Date();
        let activeCycles = cycles.filter(cycle => {
            if (!cycle.end_date) return false;
            const endDate = new Date(cycle.end_date);
            return endDate >= now;
        });
        let latestCycle = null;
        if (activeCycles.length > 0) {
            // Pick the one with the latest end_date
            latestCycle = activeCycles.reduce((a, b) => new Date(a.end_date) > new Date(b.end_date) ? a : b);
        } else if (cycles.length > 0) {
            // If no active, pick the latest overall
            latestCycle = cycles.reduce((a, b) => new Date(a.end_date) > new Date(b.end_date) ? a : b);
        }
        if (latestCycle) {
            latestCycleId = latestCycle.id;
        } else {
            // Fallback: use first cycle
            latestCycleId = cycles.length > 0 ? cycles[0].id : null;
        }
    } catch (error) {
        console.error('Error fetching cycles:', error);
        showToast('Failed to auto-select research cycle. Please contact admin.', 'error');
        latestCycleId = null;
    }
}

// Load verifiers for selection
async function loadVerifiers() {
    const verifierContainer = document.getElementById('verifiers-container');
    const verifierSelect = document.getElementById('verifier-select');
    
    if (!verifierContainer || !verifierSelect) return;
    
    try {
        // Show loading state
        verifierSelect.innerHTML = '<option value="">Loading verifiers...</option>';
        verifierSelect.disabled = true;
        
        const response = await fetch(`${BASE_API_URL}/verifiers`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        verifiers = Array.isArray(result) ? result : (result.verifiers || result.data || []);
        
        // Clear and populate options
        verifierSelect.innerHTML = '<option value="">Select a verifier (optional)</option>';
        
        verifiers.forEach(verifier => {
            const option = document.createElement('option');
            option.value = verifier.id;
            option.textContent = `${verifier.username || 'Unknown User'} (${verifier.email || 'No email'})`;
            verifierSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching verifiers:', error);
        showToast('Failed to load verifiers. You can still submit without selecting a verifier.', 'error');
        verifierSelect.innerHTML = '<option value="">Failed to load verifiers</option>';
    } finally {
        verifierSelect.disabled = false;
    }
}

function addAuthorField() {
    const container = document.getElementById('authors-container');
    if (!container) return;
    
    const authorCount = container.children.length;
    
    const authorDiv = document.createElement('div');
    authorDiv.className = 'author-field rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] p-4 mb-4';
    authorDiv.setAttribute('role', 'group');
    authorDiv.setAttribute('aria-labelledby', `author-heading-${authorCount}`);
    authorDiv.dataset.authorIndex = String(authorCount);
    authorDiv.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <h3 id="author-heading-${authorCount}" class="text-sm font-semibold">Author #${authorCount + 1}</h3>
            <button type="button" class="remove-author-btn btn btn-ghost" aria-label="Remove author #${authorCount + 1}" title="Remove this author">
                Remove
                <span class="sr-only">Remove author ${authorCount + 1}</span>
            </button>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div>
                <label for="author-name-${authorCount}" class="block text-sm font-medium mb-1">Name *</label>
                <input type="text" id="author-name-${authorCount}" name="author_name_${authorCount}" required class="form-input input w-full">
            </div>
            
            <div>
                <label for="author-email-${authorCount}" class="block text-sm font-medium mb-1">Email (optional)</label>
                <input type="email" id="author-email-${authorCount}" name="author_email_${authorCount}" class="form-input input w-full">
            </div>
        </div>
        
        <div class="mb-3">
            <label for="author-affiliation-${authorCount}" class="block text-sm font-medium mb-1">Affiliation (optional)</label>
            <input type="text" id="author-affiliation-${authorCount}" name="author_affiliation_${authorCount}" class="form-input input w-full">
        </div>
        
        <div class="mt-3 pt-3 border-t border-[color:var(--border)]">
            <div class="text-xs mb-2">Roles</div>
            <div class="flex flex-wrap gap-4">
                <label class="inline-flex items-center gap-2 text-sm" for="presenter-${authorCount}">
                    <input type="checkbox" id="presenter-${authorCount}" name="presenter_${authorCount}" class="h-4 w-4">
                    <span>Presenter</span>
                </label>
                <label class="inline-flex items-center gap-2 text-sm" for="corresponding-${authorCount}">
                    <input type="checkbox" id="corresponding-${authorCount}" name="corresponding_${authorCount}" class="h-4 w-4">
                    <span>Corresponding Author</span>
                </label>
            </div>
        </div>
    `;
    
    container.appendChild(authorDiv);
    
    // Add event listener to remove button
    const removeBtn = authorDiv.querySelector('.remove-author-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            container.removeChild(authorDiv);
            // Update author numbers
            updateAuthorNumbers();
            // After removal, ensure constraints still hold (optional guidance)
            // Do not block UI here; only show guidance if now zero or >1 of roles
            const authorFields = document.querySelectorAll('.author-field');
            let presenters = 0, correspondings = 0;
            authorFields.forEach(f => {
                const p = f.querySelector('[id^="presenter-"]');
                const c = f.querySelector('[id^="corresponding-"]');
                if (p && p.checked) presenters += 1;
                if (c && c.checked) correspondings += 1;
            });
            if (presenters !== 1 || correspondings !== 1) {
                showToast('Tip: ensure exactly one Presenter and one Corresponding Author.', 'info');
            }
        });
    }

    // Autofocus first input and bring block into view
    const firstInput = authorDiv.querySelector(`#author-name-${authorCount}`);
    if (firstInput) firstInput.focus();
    authorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Attach mutual exclusion for Presenter and Corresponding checkboxes across authors
    const presenterCb = authorDiv.querySelector(`#presenter-${authorCount}`);
    const correspondingCb = authorDiv.querySelector(`#corresponding-${authorCount}`);
    if (presenterCb) {
        presenterCb.addEventListener('change', () => {
            if (presenterCb.checked) {
                document.querySelectorAll('.author-field [id^="presenter-"]').forEach(cb => {
                    if (cb !== presenterCb) cb.checked = false;
                });
            }
        });
    }
    if (correspondingCb) {
        correspondingCb.addEventListener('change', () => {
            if (correspondingCb.checked) {
                document.querySelectorAll('.author-field [id^="corresponding-"]').forEach(cb => {
                    if (cb !== correspondingCb) cb.checked = false;
                });
            }
        });
    }
}

// Update author numbers after removal
function updateAuthorNumbers() {
    const container = document.getElementById('authors-container');
    if (!container) return;
    
    const authorFields = container.querySelectorAll('.author-field');
    authorFields.forEach((field, index) => {
        const heading = field.querySelector('h3');
        if (heading) {
            heading.textContent = `Author #${index + 1}`;
            heading.id = `author-heading-${index}`;
            field.setAttribute('aria-labelledby', `author-heading-${index}`);
        }
        const badge = field.querySelector('[data-role="author-badge"]');
        if (badge) {
            badge.textContent = String(index + 1);
        }
        const removeBtn = field.querySelector('.remove-author-btn');
        if (removeBtn) {
            removeBtn.setAttribute('aria-label', `Remove author #${index + 1}`);
            const sr = removeBtn.querySelector('.sr-only');
            if (sr) sr.textContent = `Remove author ${index + 1}`;
        }
    });
}

// Collect form data with validation
function collectFormData() {
    const form = document.getElementById('abstract-form');
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    
    // Basic fields (should already be validated in step navigation)
    data.title = formData.get('title') || '';
    data.category_id = formData.get('category_id') || '';
    
    // Auto-select latest cycle
    if (!latestCycleId) {
        throw new Error('No active research cycle found. Please contact admin.');
    }
    data.cycle_id = latestCycleId;
    
    // Combine all sections into a single plain-text field for server submission
    const sectionsPlain = getEditorsPlainMap();
    const joined = [
        `Introduction:\n${sectionsPlain.content_introduction || ''}`,
        `\n\nAims & Objectives:\n${sectionsPlain.content_aims || ''}`,
        `\n\nMaterials and methods:\n${sectionsPlain.content_materials_methods || ''}`,
        `\n\nResults:\n${sectionsPlain.content_results || ''}`,
        `\n\nConclusion:\n${sectionsPlain.content_conclusion || ''}`
    ].join('');
    data.content = joined.trim();
    
    
    // Authors (should already be validated in step navigation)
    data.authors = [];
    const authorContainers = document.querySelectorAll('.author-field');
    authorContainers.forEach((container) => {
        // Get inputs by their actual IDs instead of assuming index-based IDs
        const nameInput = container.querySelector('[id^="author-name-"]');
        const emailInput = container.querySelector('[id^="author-email-"]');
        const affiliationInput = container.querySelector('[id^="author-affiliation-"]');
        const presenterCheckbox = container.querySelector('[id^="presenter-"]');
        const correspondingCheckbox = container.querySelector('[id^="corresponding-"]');
        const name = nameInput ? nameInput.value.trim() : '';
        const email = emailInput ? emailInput.value.trim() : '';
        const affiliation = affiliationInput ? affiliationInput.value.trim() : '';
        const isPresenter = presenterCheckbox ? presenterCheckbox.checked : false;
        const isCorresponding = correspondingCheckbox ? correspondingCheckbox.checked : false;
        
        data.authors.push({
            name,
            email: email || null,
            affiliation: affiliation || null,
            is_presenter: isPresenter || false,
            is_corresponding: isCorresponding || false
        });
    });
    
    // Verifier selection (optional)
    const verifierSelect = document.getElementById('verifier-select');
    if (verifierSelect && verifierSelect.value) {
        data.verifier_id = verifierSelect.value;
    }
    

    data.consent = document.getElementById('consent-checkbox').checked || false;

    return data;
}

// Submit abstract to the API
async function submitAbstract(event) {
    event.preventDefault();
    
    // Get submit button and show loading state
    const submitBtn = document.querySelector('button[type="submit"]');
    // Validate authors and emails and roles before submitting (defense-in-depth)
    if (!validateAuthorsAndEmails()) {
        return;
    }
    
    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="flex items-center"><span class="animate-spin mr-2">●</span> Submitting...</span>';
        }
        
        // Collect and validate form data
        const jsonData = collectFormData();
        
        // Check if a PDF file is selected
        const pdfInput = document.getElementById('abstract_pdf');
        if (pdfInput && pdfInput.files[0]) {
            // Validate again on submit to guard against edge cases
            if (!validatePdf(pdfInput.files[0], pdfInput)) {
                throw new Error('Invalid PDF file. Please select a valid PDF under the size limit.');
            }
            // Use FormData for file upload
            const formData = new FormData();
            formData.append('data', JSON.stringify(jsonData));
            formData.append('abstract_pdf', pdfInput.files[0]);
            
            // Submit to API
            const response = await fetch(`${BASE_API_URL}/abstracts`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Failed to submit abstract: ${response.status} ${response.statusText}`;
                
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // If parsing fails, use the raw text if it's not empty
                    if (errorText.trim()) {
                        errorMessage = errorText;
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            showToast('Abstract submitted successfully!', 'success');
        } else {
            // No file selected, send as JSON
            const response = await fetch(`${BASE_API_URL}/abstracts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(jsonData)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Failed to submit abstract: ${response.status} ${response.statusText}`;
                
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // If parsing fails, use the raw text if it's not empty
                    if (errorText.trim()) {
                        errorMessage = errorText;
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            showToast('Abstract submitted successfully!', 'success');
        }
        
        // Redirect to research dashboard after a short delay
        setTimeout(() => {
            window.location.href = '/';
        }, 1500);
    } catch (error) {
        console.error('Error submitting abstract:', error);
        showToast(`Failed to submit abstract: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Submit Abstract';
        }
    }
}

// Save draft functionality
async function saveDraft() {
    // Get draft button and show loading state
    const draftBtn = document.getElementById('save-draft-btn');
    
    try {
        if (draftBtn) {
            draftBtn.disabled = true;
            draftBtn.innerHTML = '<span class="flex items-center"><span class="animate-spin mr-2">●</span> Saving...</span>';
        }
        
        // Collect and validate form data
        const jsonData = collectFormData();
        
        // Add draft status
        jsonData.status = 'draft';
        
        // Check if a PDF file is selected
        const pdfInput = document.getElementById('abstract_pdf');
        if (pdfInput && pdfInput.files[0]) {
            // Validate again on save draft
            if (!validatePdf(pdfInput.files[0], pdfInput)) {
                throw new Error('Invalid PDF file. Please select a valid PDF under the size limit.');
            }
            // Use FormData for file upload
            const formData = new FormData();
            formData.append('data', JSON.stringify(jsonData));
            formData.append('abstract_pdf', pdfInput.files[0]);
            
            // Save to API
            const response = await fetch(`${BASE_API_URL}/abstracts`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Failed to save draft: ${response.status} ${response.statusText}`;
                
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // If parsing fails, use the raw text if it's not empty
                    if (errorText.trim()) {
                        errorMessage = errorText;
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            showToast('Draft saved successfully!', 'success');
        } else {
            // No file selected, send as JSON
            const response = await fetch(`${BASE_API_URL}/abstracts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(jsonData)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                let errorMessage = `Failed to save draft: ${response.status} ${response.statusText}`;
                
                try {
                    const errorData = JSON.parse(errorText);
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (e) {
                    // If parsing fails, use the raw text if it's not empty
                    if (errorText.trim()) {
                        errorMessage = errorText;
                    }
                }
                
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            showToast('Draft saved successfully!', 'success');
        }
    } catch (error) {
        console.error('Error saving draft:', error);
        showToast(`Failed to save draft: ${error.message}`, 'error');
    } finally {
        if (draftBtn) {
            draftBtn.disabled = false;
            draftBtn.innerHTML = '<span class="flex items-center"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" /></svg> Save as Draft</span>';
        }
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    return text
        .toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Generate preview of all form data
function generatePreview() {
    const previewContent = document.getElementById('preview-content');
    if (!previewContent) return;
    
    // Collect all form data
    const formData = collectFormData();
    
    // Get category name
    let categoryName = 'Not selected';
    const categorySelect = document.getElementById('category');
    if (categorySelect && categorySelect.options[categorySelect.selectedIndex]) {
        categoryName = categorySelect.options[categorySelect.selectedIndex].text;
    }
    
    // Get PDF file info
    let pdfInfo = 'No file uploaded';
    let pdfPreview = '';
    const pdfInput = document.getElementById('abstract_pdf');
    if (pdfInput && pdfInput.files[0]) {
        const file = pdfInput.files[0];
        pdfInfo = `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        
        // Create a container for the PDF preview
        pdfPreview = `
            <div class="mt-2 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <div>
                            <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(file.name)}</p>
                            <p class="text-sm text-gray-500 dark:text-gray-300">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                    </div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                        Ready
                    </span>
                </div>
                <div id="pdf-preview-container" class="border border-gray-300 dark:border-gray-600 rounded mt-3 bg-white dark:bg-gray-800">
                    <canvas id="pdf-canvas" class="w-full"></canvas>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">PDF file will be submitted with your abstract</p>
            </div>
        `;
    }
    
    // Generate preview HTML with improved styling
    let previewHTML = `
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <!-- Abstract Details Section -->
            <div class="p-6">
                <div class="flex items-center mb-4">
                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Abstract Details</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Title and category information</p>
                    </div>
                </div>
                
                <div class="ml-2 space-y-3">
                    <div class="flex">
                        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 w-24">Title</dt>
                        <dd class="text-sm text-gray-900 dark:text-white">${escapeHtml(formData.title)}</dd>
                    </div>
                    <div class="flex">
                        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400 w-24">Category</dt>
                        <dd class="text-sm text-gray-900 dark:text-white">${escapeHtml(categoryName)}</dd>
                    </div>
                </div>
            </div>
            
            <!-- Authors Section -->
            <div class="p-6">
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
    
    formData.authors.forEach((author, index) => {
        const roles = [];
        if (author.is_presenter) roles.push('Presenter');
        if (author.is_corresponding) roles.push('Corresponding');
        
        previewHTML += `
            <div class="border-l-4 border-blue-400 dark:border-blue-600 pl-4 py-1">
                <div class="flex justify-between">
                    <p class="font-medium text-gray-900 dark:text-white">${escapeHtml(author.name)}</p>
                    ${roles.length > 0 ? `<div class="flex space-x-2">${roles.map(role => 
                        `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                            ${role}
                        </span>`).join('')}</div>` : ''}
                </div>
                ${author.email ? `<p class="text-sm text-gray-600 dark:text-gray-300 mt-1">${escapeHtml(author.email)}</p>` : ''}
                ${author.affiliation ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${escapeHtml(author.affiliation)}</p>` : ''}
            </div>
        `;
    });
    
    previewHTML += `
                </div>
            </div>
            
            <!-- Abstract Content Section -->
            <div class="p-6">
                <div class="flex items-center mb-4">
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
                        ${renderSectionsPreviewHtml()}
                    </div>
                </div>
            </div>
            
            <!-- PDF File Section -->
            <div class="p-6">
                <div class="flex items-center mb-4">
                    <div class="flex-shrink-0 h-10 w-10 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <div class="ml-4">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">PDF Attachment</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Uploaded document</p>
                    </div>
                </div>
                
                <div class="ml-2">
                    ${pdfPreview || `<p class="text-gray-500 dark:text-gray-400 italic">No PDF file uploaded</p>`}
                </div>
            </div>
        </div>
    `;
    
    previewContent.innerHTML = previewHTML;
    
    // Render PDF preview if a file is selected
    if (pdfInput && pdfInput.files[0]) {
        renderPdfPreview(pdfInput.files[0]);
    }
}

// Render sanitized HTML from CKEditor for preview while maintaining safe output
function renderEditorPreviewHtml() {
    const editorHtml = (typeof CKEDITOR_INSTANCE !== 'undefined' && CKEDITOR_INSTANCE) ? CKEDITOR_INSTANCE.getData() : null;
    if (editorHtml && typeof DOMPurify !== 'undefined') {
        // Allow a safe subset of tags that CKEditor produces for headings and paragraphs
        const clean = DOMPurify.sanitize(editorHtml, {
            ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h2', 'h3', 'h4', 'blockquote'],
            ALLOWED_ATTR: []
        });
        return `<div class="prose prose-sm dark:prose-invert max-w-none">${clean}</div>`;
    }
    // Fallback: show plain text safely
    const formData = collectFormData();
    return `<p class="whitespace-pre-wrap break-words text-gray-800 dark:text-gray-200">${escapeHtml(formData.content || '')}</p>`;
}

// Render five-section preview; prefer rich HTML from CKEditor instances, sanitize with DOMPurify
function renderSectionsPreviewHtml() {
    const sections = SECTION_META.map(({ id, label }) => {
        let html = '';
        const ed = CKEDITOR_INSTANCES[id];
        if (ed) {
            html = ed.getData();
        } else {
            const ta = document.getElementById(id);
            html = ta ? escapeHtml(ta.value || '') : '';
            // If no editor, treat textarea as plain text
            html = `<p>${html.replace(/\n/g, '<br>')}</p>`;
        }
        // Sanitize user-provided HTML only
        let clean = html;
        if (typeof DOMPurify !== 'undefined') {
            clean = DOMPurify.sanitize(html, {
                ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote'],
                ALLOWED_ATTR: []
            });
        }
        const isEmpty = !stripHtmlToPlain(clean);
        if (isEmpty) return '';
        return `
            <section class="mb-3">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-1">${escapeHtml(label)}</h3>
                <div class="prose prose-sm dark:prose-invert max-w-none">${clean}</div>
            </section>
        `;
    }).filter(Boolean);
    if (sections.length === 0) {
        return `<p class="italic text-gray-500 dark:text-gray-400">No content provided.</p>`;
    }
    return sections.join('\n');
}

// Render PDF preview using local PDF.js
function renderPdfPreview(file) {
    // Check if PDF.js is loaded
    if (typeof pdfjsLib === 'undefined') {
        console.error('PDF.js library not loaded');
        showPdfPreviewError('PDF.js library not available');
        return;
    }

    // Set the worker URL for PDF.js to use the local worker
    pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.worker.min.js';

    const fileReader = new FileReader();

    fileReader.onload = function() {
        const typedarray = new Uint8Array(this.result);

        // Configure PDF loading with password handling
        const loadingTask = pdfjsLib.getDocument({
            data: typedarray,
            password: "" // Try with empty password first
        });

        loadingTask.promise.then(function(pdf) {
            // Successfully loaded PDF, now render the first page
            renderPdfPage(pdf, file);
        }).catch(function(error) {
            console.error('Error loading PDF document:', error);
            // Handle specific error types
            if (error.name === 'PasswordException') {
                // For password-protected PDFs, we can't show a preview
                showPdfPreviewError('Password-protected PDFs cannot be previewed for security reasons. Your file will still be submitted correctly.');
            } else if (error.name === 'InvalidPDFException') {
                showPdfPreviewError('Invalid PDF file or corrupted document');
            } else if (error.name === 'MissingPDFException') {
                showPdfPreviewError('PDF file not found');
            } else {
                showPdfPreviewError('Unable to load PDF document: ' + (error.message || 'Unknown error'));
            }
        });
    };

    fileReader.onerror = function() {
        console.error('Error reading file');
        showPdfPreviewError('Error reading PDF file');
    };

    fileReader.readAsArrayBuffer(file);
}

// Render a specific page of a PDF document
function renderPdfPage(pdf, file) {
    // Fetch the first page
    pdf.getPage(1).then(function(page) {
        const scale = 1.5;
        const viewport = page.getViewport({ scale: scale });

        // Prepare canvas using PDF page dimensions
        const canvas = document.getElementById('pdf-canvas');
        const container = document.getElementById('pdf-preview-container');
        if (!canvas || !container) {
            showPdfPreviewError('PDF preview container not found');
            return;
        }

        // Show loading state
        container.innerHTML = `
            <div class="flex items-center justify-center p-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span class="ml-3 text-gray-600 dark:text-gray-300">Loading PDF preview...</span>
            </div>
        `;

        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        // Render PDF page into canvas context
        const renderContext = {
            canvasContext: context,
            viewport: viewport
        };
        page.render(renderContext).promise.then(function() {
            // Success - show the canvas
            container.innerHTML = '';
            container.appendChild(canvas);

            // Add file info below the preview
            const fileInfo = document.createElement('div');
            fileInfo.className = 'mt-3 text-center';
            fileInfo.innerHTML = `
                <p class="text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(file.name)}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                <div class="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    PDF Preview Loaded
                </div>
            `;
            container.appendChild(fileInfo);
        }).catch(function(renderError) {
            console.error('Error rendering PDF:', renderError);
            showPdfPreviewError('Error rendering PDF preview');
        });
    }).catch(function(pageError) {
        console.error('Error loading PDF page:', pageError);
        showPdfPreviewError('Error loading PDF page');
    });
}

// Show PDF preview error message
function showPdfPreviewError(message) {
    const container = document.getElementById('pdf-preview-container');
    if (container) {
        container.innerHTML = `
            <div class="p-6 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 dark:bg-red-900">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <div class="mt-3">
                    <p class="text-lg font-medium text-gray-900 dark:text-white">PDF Preview Unavailable</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">${escapeHtml(message)}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                        Don't worry - your file will still be submitted with your abstract
                    </p>
                </div>
                <div class="mt-4">
                    <div class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        ${escapeHtml(document.getElementById('abstract_pdf').files[0]?.name || 'PDF Document')}
                    </div>
                </div>
            </div>
        `;
    }
}