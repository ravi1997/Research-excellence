/* ==========================================================================
   Research Excellence Portal - Homepage logic
   Works with templates/index.html as provided.
   ========================================================================== */

(() => {
    // ------------------ DOM refs ------------------
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

    const BASE = '/video';

    // ------------------ Init ------------------
    function init() {
        // Initialize any interactive  on the homepage
        console.log("Research Excellence Portal initialized");

        // Add any specific initialization logic here
        setupFeatureCards();
        setupAnnouncements();

        fetchAbstractStatus();
        fetchAwardStatus();
        fetchBestPaperStatus();

        checkUserRoles(); // Check user roles to show/hide buttons
        setTimeout(() => {
            // Any delayed initialization if needed


            const abstract_pendingElement = $('#abstract-pending');
            const abstract_underReviewElement = $('#abstract-under-review');
            const abstract_acceptedElement = $('#abstract-accepted');
            const abstract_rejectedElement = $('#abstract-rejected');

            const award_pendingElement = $('#award-pending');
            const award_underReviewElement = $('#award-under-review');
            const award_acceptedElement = $('#award-accepted');
            const award_rejectedElement = $('#award-rejected');

            const bestPaper_pendingElement = $('#best-paper-pending');
            const bestPaper_underReviewElement = $('#best-paper-under-review');
            const bestPaper_acceptedElement = $('#best-paper-accepted');
            const bestPaper_rejectedElement = $('#best-paper-rejected');

            const pendingElement = $('#pending');
            const underReviewElement = $('#under-review');
            const acceptedElement = $('#accepted');
            const rejectedElement = $('#rejected');

            pendingElement.textContent =
                (parseInt(abstract_pendingElement.textContent, 10) || 0) +
                (parseInt(award_pendingElement.textContent, 10) || 0) +
                (parseInt(bestPaper_pendingElement.textContent, 10) || 0);

            underReviewElement.textContent =
                (parseInt(abstract_underReviewElement.textContent, 10) || 0) +
                (parseInt(award_underReviewElement.textContent, 10) || 0) +
                (parseInt(bestPaper_underReviewElement.textContent, 10) || 0);

            acceptedElement.textContent =
                (parseInt(abstract_acceptedElement.textContent, 10) || 0) +
                (parseInt(award_acceptedElement.textContent, 10) || 0) +
                (parseInt(bestPaper_acceptedElement.textContent, 10) || 0);

            rejectedElement.textContent =
                (parseInt(abstract_rejectedElement.textContent, 10) || 0) +
                (parseInt(award_rejectedElement.textContent, 10) || 0) +
                (parseInt(bestPaper_rejectedElement.textContent, 10) || 0);
        }, 150);
    }

    // ------------------ Feature Cards ------------------
    function setupFeatureCards() {
        // Add any interactivity to feature cards if needed
        const featureCards = $$('.feature-card');
        featureCards.forEach(card => {
            // Could add hover effects or other interactions
            card.addEventListener('mouseenter', () => {
                card.classList.add('hover-effect');
            });

            card.addEventListener('mouseleave', () => {
                card.classList.remove('hover-effect');
            });
        });
    }

    // ------------------ Announcements ------------------
    function setupAnnouncements() {
        // Add any interactivity to announcements if needed
        const announcements = $$('.research-item');
        announcements.forEach(item => {
            // Could add expand/collapse functionality or other interactions
        });
    }

    // ------------------ Abstract Status ------------------
    async function fetchAbstractStatus() {
        try {
            const response = await fetch('/video/api/v1/research/abstracts/status', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include' // Include cookies/session data
            });

            if (response.ok) {
                const data = await response.json();
                updateAbstractStatus(data);
            } else {
                console.error('Failed to fetch abstract status:', response.status);
            }
        } catch (error) {
            console.error('Error fetching abstract status:', error);
        }
    }

    function updateAbstractStatus(data) {
        // Update the abstract status elements
        const pendingElement = $('#abstract-pending');
        const underReviewElement = $('#abstract-under-review');
        const acceptedElement = $('#abstract-accepted');
        const rejectedElement = $('#abstract-rejected');

        if (pendingElement) pendingElement.textContent = data.pending || 0;
        if (underReviewElement) underReviewElement.textContent = data.under_review || 0;
        if (acceptedElement) acceptedElement.textContent = data.accepted || 0;
        if (rejectedElement) rejectedElement.textContent = data.rejected || 0;
    }
    // ------------------ Award Status ------------------
    async function fetchAwardStatus() {
        try {
            const response = await fetch('/video/api/v1/research/awards/status', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include' // Include cookies/session data
            });

            if (response.ok) {
                const data = await response.json();
                updateAwardStatus(data);
            } else {
                console.error('Failed to fetch award status:', response.status);
            }
        } catch (error) {
            console.error('Error fetching award status:', error);
        }
    }
    function updateAwardStatus(data) {
        // Update the award status elements
        const pendingElement = $('#award-pending');
        const underReviewElement = $('#award-under-review');
        const acceptedElement = $('#award-accepted');
        const rejectedElement = $('#award-rejected');

        if (pendingElement) pendingElement.textContent = data.pending || 0;
        if (underReviewElement) underReviewElement.textContent = data.under_review || 0;
        if (acceptedElement) acceptedElement.textContent = data.accepted || 0;
        if (rejectedElement) rejectedElement.textContent = data.rejected || 0;
    }


    // ------------------ Best Paper Status ------------------
    async function fetchBestPaperStatus() {
        try {
            const response = await fetch('/video/api/v1/research/best-papers/status', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include' // Include cookies/session data
            });

            if (response.ok) {
                const data = await response.json();
                updateBestPaperStatus(data);
            } else {
                console.error('Failed to fetch best paper status:', response.status);
            }
        } catch (error) {
            console.error('Error fetching best paper status:', error);
        }
    }
    function updateBestPaperStatus(data) {
        // Update the best paper status elements
        const pendingElement = $('#best-paper-pending');
        const underReviewElement = $('#best-paper-under-review');
        const acceptedElement = $('#best-paper-accepted');
        const rejectedElement = $('#best-paper-rejected');

        if (pendingElement) pendingElement.textContent = data.pending || 0;
        if (underReviewElement) underReviewElement.textContent = data.under_review || 0;
        if (acceptedElement) acceptedElement.textContent = data.accepted || 0;
        if (rejectedElement) rejectedElement.textContent = data.rejected || 0;
    }



    async function handleAuthFailure(resp, retryFn) {
        if (!resp || !(resp.status === 401 || resp.status === 403)) return;
        const status = resp.status;
        const path = window.location.pathname;

        if (status === 401) {
            window.location.replace(`/video/login`);
        }

        // Special case: forced password change (403 with error=password_change_required)
        if (status === 403) {
            try {
                const ct = resp.headers.get('content-type') || '';
                if (ct.includes('application/json')) {
                    const clone = resp.clone();
                    const data = await clone.json().catch(() => null);
                    if (data && data.error === 'password_change_required') {
                        if (!path.startsWith(BASE + '/change-password')) {
                            showToast('Password update required. Redirecting…', 'info', 3000);
                            setTimeout(() => { try { window.location.replace('/change-password'); } catch { window.location.href = '/change-password'; } }, 500);
                        }
                        return; // Do not treat as auth expiry
                    }
                }
            } catch { /* ignore parse errors */ }
        }

        if (path.startsWith(BASE + '/login')) return; // already on login
        // Attempt refresh once per navigation
        if (!sessionStorage.getItem('__refresh_attempted')) {
            sessionStorage.setItem('__refresh_attempted', '1');
            const ok = await tryRefreshToken();
            if (ok && typeof retryFn === 'function') {
                try { await retryFn(); return; } catch {/* swallow and fallback */ }
            }
        }
        if (sessionStorage.getItem('__auth_redirect_lock') === '1') return;
        sessionStorage.setItem('__auth_redirect_lock', '1');
        showToast('Session expired. Redirecting to login…', 'warn', 3500);
        clearAuthStorage();
        const ret = encodeURIComponent(path + window.location.search);
        setTimeout(() => { try { window.location.replace(`/video/login?next=${ret}`); } catch { window.location.href = `/video/login?next=${ret}`; } }, 1200);
    }

    function clearAuthStorage() {
        try {
            localStorage.removeItem("token");
            localStorage.removeItem("user");
            localStorage.removeItem("refresh_token");
        } catch { /* ignore */ }
    }
    // ------------------ Role-Based Visibility ------------------
    async function checkUserRoles() {
        try {
            // Fetch user info to determine roles
            const response = await fetch('/video/api/v1/auth/me', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });

            if (response.ok) {
                const userData = await response.json();
                const userRoles = userData.logged_in_as?.roles || [];

                // Show/hide buttons based on roles
                const applyButton = $('#abstract-apply');
                const verifyButton = $('#abstract-verify');

                const applyAwardButton = $('#award-apply');
                const verifyAwardButton = $('#award-verify');

                const applyBestPaperButton = $('#paper-apply');
                const verifyBestPaperButton = $('#paper-verify');


                // Normal users can apply
                if (applyButton) {
                    if (userRoles.includes('Role.USER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        applyButton.classList.remove('hidden');
                    } else {
                        applyButton.classList.add('hidden');
                    }
                }

                // Only verifiers, admins, and superadmins can verify
                if (verifyButton) {
                    if (userRoles.includes('Role.VERIFIER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        verifyButton.classList.remove('hidden');
                    } else {
                        verifyButton.classList.add('hidden');
                    }
                }

                // Awards
                if (applyAwardButton) {
                    if (userRoles.includes('Role.USER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        applyAwardButton.classList.remove('hidden');
                    } else {
                        applyAwardButton.classList.add('hidden');
                    }
                }

                if (verifyAwardButton) {
                    if (userRoles.includes('Role.VERIFIER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        verifyAwardButton.classList.remove('hidden');
                    } else {
                        verifyAwardButton.classList.add('hidden');
                    }
                }

                // Best Papers
                if (applyBestPaperButton) {
                    if (userRoles.includes('Role.USER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        applyBestPaperButton.classList.remove('hidden');
                    } else {
                        applyBestPaperButton.classList.add('hidden');
                    }
                }

                if (verifyBestPaperButton) {
                    if (userRoles.includes('Role.VERIFIER') || userRoles.includes('Role.ADMIN') || userRoles.includes('Role.SUPERADMIN')) {
                        verifyBestPaperButton.classList.remove('hidden');
                    } else {
                        verifyBestPaperButton.classList.add('hidden');
                    }
                }

            }
            else if (response.status === 401 || response.status === 403) {
                // console.error('Failed to fetch user info:', response.status);
                handleAuthFailure(response);
            }
        } catch (error) {
            console.error('Error checking user roles:', error);
            // Hide both buttons by default if we can't determine roles
            const applyButton = $('#abstract-apply');
            const verifyButton = $('#abstract-verify');
            if (applyButton) applyButton.style.display = 'none';
            if (verifyButton) verifyButton.style.display = 'none';
        }
    }

    // ------------------ Utility Functions ------------------
    function showToast(message, type = 'info') {
        // Simple toast notification system
        const toastHost = $('#toastHost') || document.body;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toastHost.appendChild(toast);

        // Remove toast after delay
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // ------------------ Expose API ------------------
    // Expose minimal API for template buttons to call
    window.researchPortal = Object.assign(window.researchPortal || {}, {
        showToast
    });

    // ------------------ Start ------------------
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();