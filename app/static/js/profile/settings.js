// Settings page logic extracted for CSP compliance
(function () {
  const BASE = '';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => r.querySelectorAll(s);
  const getToken = () => localStorage.getItem("token") || "";
  const withAuth = (opts = {}) => ({
    ...opts,
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...(opts.headers || {}),
      ...(getToken() ? { Authorization: "Bearer " + getToken() } : {}),
    },
  });

  async function logout() {
    const token = getToken();
    try {
      await fetch(BASE + "/api/v1/auth/logout", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    } catch {}
    try {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
    } catch {}
    try {
      window.location.assign(BASE + "/login");
    } catch {
      window.location.href = BASE + "/login";
    }
  }

  // Tab Navigation
  function initTabNavigation() {
    const tabButtons = $$('.tab-button');
    const tabContents = $$('.tab-content');

    function switchTab(targetTab) {
      // Update button states
      tabButtons.forEach(btn => {
        const isActive = btn.dataset.tab === targetTab;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive);
      });

      // Update content visibility
      tabContents.forEach(content => {
        const isActive = content.id === `${targetTab}-tab`;
        content.classList.toggle('active', isActive);
      });

      // Store active tab
      try {
        localStorage.setItem('settings.activeTab', targetTab);
      } catch {}
    }

    // Add click handlers
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        switchTab(btn.dataset.tab);
      });
    });

    // Restore last active tab
    try {
      const lastTab = localStorage.getItem('settings.activeTab');
      if (lastTab && $(`[data-tab="${lastTab}"]`)) {
        switchTab(lastTab);
      }
    } catch {}
  }

  // Form handling
  function initFormHandling() {
    const forms = $$('form');
    
    forms.forEach(form => {
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Handle checkboxes (they don't appear in FormData if unchecked)
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
          data[checkbox.name] = checkbox.checked;
        });

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
        
        try {
          // Simulate API call for now
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          // Show success message
          showNotification('Settings saved successfully!', 'success');
          
          // Save to localStorage for persistence
          const currentSettings = getStoredSettings();
          const updatedSettings = { ...currentSettings, ...data };
          saveSettingsToStorage(updatedSettings);
          
        } catch (error) {
          showNotification('Error saving settings. Please try again.', 'error');
        } finally {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalText;
        }
      });
    });
  }

  function getStoredSettings() {
    try {
      return JSON.parse(localStorage.getItem('user.settings') || '{}');
    } catch {
      return {};
    }
  }

  function saveSettingsToStorage(settings) {
    try {
      localStorage.setItem('user.settings', JSON.stringify(settings));
    } catch {}
  }

  function loadStoredSettings() {
    const settings = getStoredSettings();
    
    // Apply stored values to form fields
    Object.entries(settings).forEach(([key, value]) => {
      const field = $(`[name="${key}"]`);
      if (field) {
        if (field.type === 'checkbox') {
          field.checked = !!value;
        } else {
          field.value = value;
        }
      }
    });

    // Apply theme if stored
    if (settings.theme) {
      applyTheme(settings.theme);
    }
  }

  function applyTheme(theme) {
    const html = document.documentElement;
    const body = document.body;
    
    if (theme === 'dark') {
      html.classList.add('dark');
      body.classList.add('dark');
    } else if (theme === 'light') {
      html.classList.remove('dark');
      body.classList.remove('dark');
    } else if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      html.classList.toggle('dark', prefersDark);
      body.classList.toggle('dark', prefersDark);
    }
  }

  function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-triangle' : 'fa-info-circle'} mr-2"></i>
        ${message}
      </div>
    `;
    
    // Add styles if not already present
    if (!$('#notification-styles')) {
      const styles = document.createElement('style');
      styles.id = 'notification-styles';
      styles.textContent = `
        .notification {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 1000;
          padding: 1rem 1.5rem;
          border-radius: 0.5rem;
          color: white;
          font-weight: 500;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
          transform: translateX(100%);
          transition: transform 0.3s ease;
        }
        .notification-success { background: #16a34a; }
        .notification-error { background: #dc2626; }
        .notification-info { background: #2563eb; }
        .notification.show { transform: translateX(0); }
        .notification-content { display: flex; align-items: center; }
      `;
      document.head.appendChild(styles);
    }
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Hide and remove notification
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  // Initialize change password functionality
  function initPasswordChange() {
    const changePasswordBtn = $('#change-password-btn');
    if (changePasswordBtn) {
      changePasswordBtn.addEventListener('click', () => {
        // In a real app, this would open a modal or navigate to change password page
        showNotification('Change password functionality would be implemented here', 'info');
      });
    }
  }

  // Theme change handler
  function initThemeHandling() {
    const themeSelect = $('#theme');
    if (themeSelect) {
      themeSelect.addEventListener('change', (e) => {
        applyTheme(e.target.value);
      });
    }
  }

  // Initialize everything when DOM is loaded
  document.addEventListener('DOMContentLoaded', () => {
    initTabNavigation();
    initFormHandling();
    initPasswordChange();
    initThemeHandling();
    loadStoredSettings();
  });

  const API = {
    get: BASE + "/api/v1/user/settings",
    save: BASE + "/api/v1/user/settings",
  };

  // Legacy settings handling - keeping for compatibility
  const saveMsg = $("#saveMsg");
  const btnSave = $("#btnSave");
  const btnReset = $("#btnReset");
  const logoutBtn = document.getElementById("logoutBtn");

  const themeBtns = document.querySelectorAll("[data-theme]");
  const setCompact = $("#setCompact");
  const setAutoplay = $("#setAutoplay");
  const setQuality = $("#setQuality");
  const setSpeed = $("#setSpeed");
  const setEmail = $("#setEmail");
  const setDigest = $("#setDigest");
  const setPrivate = $("#setPrivate");
  const setPersonalize = $("#setPersonalize");

  function localGet() {
    try {
      return JSON.parse(localStorage.getItem("user.settings") || "{}");
    } catch {
      return {};
    }
  }
  function localSet(v) {
    try {
      localStorage.setItem("user.settings", JSON.stringify(v));
    } catch {}
  }

  let state = {
    theme: "system",
    compact: false,
    autoplay: false,
    quality: "auto",
    speed: "1.0",
    email_updates: false,
    weekly_digest: false,
    private_profile: false,
    personalize: true,
  };

  // ----- THEME HANDLING -----
  const THEME_KEY = "ui.theme"; // used by layout.js
  const prefersDark = () => window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  function applyEffectiveTheme(effective) {
    const html = document.documentElement;
    const body = document.body;
    const isDark = effective === "dark";
    html.classList.toggle("dark", isDark);
    body.classList.toggle("dark", isDark);
    html.setAttribute("data-theme", isDark ? "dark" : "light");
    body.setAttribute("data-theme", isDark ? "dark" : "light");
  }
  function setThemeChoice(choice) {
    // choice: 'light' | 'dark' | 'system'
    if (choice === "system") {
      try { localStorage.removeItem(THEME_KEY); } catch {}
      applyEffectiveTheme(prefersDark() ? "dark" : "light");
    } else {
      try { localStorage.setItem(THEME_KEY, choice); } catch {}
      applyEffectiveTheme(choice);
    }
    // reflect button state
    if (themeBtns.length > 0) {
      themeBtns.forEach((b) => b.setAttribute("aria-pressed", String(b.getAttribute("data-theme") === choice)));
    }
  }
  function applyToUI(s) {
    setThemeChoice(s.theme || "system");
    if (setCompact) setCompact.checked = !!s.compact;
    if (setAutoplay) setAutoplay.checked = !!s.autoplay;
    if (setQuality) setQuality.value = s.quality || "auto";
    if (setSpeed) setSpeed.value = String(s.speed || "1.0");
    if (setEmail) setEmail.checked = !!s.email_updates;
    if (setDigest) setDigest.checked = !!s.weekly_digest;
    if (setPrivate) setPrivate.checked = !!s.private_profile;
    if (setPersonalize) setPersonalize.checked = !!s.personalize;
  }

  function readFromUI() {
    const activeTheme = [...themeBtns].find((b) => b.getAttribute("aria-pressed") === "true");
    return {
      theme: activeTheme ? activeTheme.getAttribute("data-theme") : "system",
      compact: setCompact ? !!setCompact.checked : false,
      autoplay: setAutoplay ? !!setAutoplay.checked : false,
      quality: setQuality ? setQuality.value || "auto" : "auto",
      speed: setSpeed ? setSpeed.value || "1.0" : "1.0",
      email_updates: setEmail ? !!setEmail.checked : false,
      weekly_digest: setDigest ? !!setDigest.checked : false,
      private_profile: setPrivate ? !!setPrivate.checked : false,
      personalize: setPersonalize ? !!setPersonalize.checked : true,
    };
  }

  async function load() {
    if (saveMsg) saveMsg.textContent = "Loading your settings…";
    try {
      const res = await fetch(API.get, withAuth({ method: "GET" }));
      if (res.status === 401) return (location.href = BASE + "/login");
      if (!res.ok) throw new Error("http " + res.status);
      const s = await res.json();
      state = { ...state, ...s };
      applyToUI(state);
      localSet(state);
      if (saveMsg) saveMsg.textContent = "Loaded ✓";
    } catch (e) {
      state = { ...state, ...localGet() };
      applyToUI(state);
      if (saveMsg) saveMsg.textContent = "Offline mode: using saved device preferences.";
      console.warn(e);
    }
  }

  async function save() {
    const payload = readFromUI();
    if (saveMsg) saveMsg.textContent = "Saving…";
    if (btnSave) btnSave.disabled = true;
    try {
      const res = await fetch(API.save, withAuth({ method: "PUT", body: JSON.stringify(payload) }));
      if (res.status === 401) return (location.href = BASE + "/login");
      if (!res.ok) throw new Error("http " + res.status);
      state = payload;
      localSet(state);
      applyToUI(state);
      if (saveMsg) saveMsg.textContent = "Settings saved ✓";
    } catch (e) {
      state = payload;
      localSet(state);
      applyToUI(state);
      if (saveMsg) saveMsg.textContent = "Saved locally (network error).";
      console.error(e);
    } finally {
      if (btnSave) btnSave.disabled = false;
    }
  }

  function reset() {
    state = {
      theme: "system",
      compact: false,
      autoplay: false,
      quality: "auto",
      speed: "1.0",
      email_updates: false,
      weekly_digest: false,
      private_profile: false,
      personalize: true,
    };
    applyToUI(state);
    if (saveMsg) saveMsg.textContent = "Defaults restored. Click Save to keep.";
  }

  if (themeBtns.length > 0) {
    themeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const choice = btn.getAttribute("data-theme") || "system";
        setThemeChoice(choice);
      });
    });
  }
  
  if (btnSave) btnSave.addEventListener("click", save);
  if (btnReset) btnReset.addEventListener("click", reset);
  if (logoutBtn) logoutBtn.addEventListener("click", (e) => { e.preventDefault(); logout(); });

  // Initialize legacy settings if the new structure isn't found
  if (!$('.settings-container')) {
    load();
  }
})();
