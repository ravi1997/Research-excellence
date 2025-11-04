/* ==========================================================================
   Research Excellence Portal - Homepage logic
   Updated to align with platform-wide auth, routing, and accessibility
   patterns (2025).
   ========================================================================== */

(() => {
    "use strict";

    const API_BASE = (window.API_BASE || "/api/v1").replace(/\/$/, "");
    const STATUS_FIELDS = ["pending", "under_review", "accepted", "rejected"];

    const STATUS_CONFIG = {
        abstract: {
            endpoint: "/research/abstracts/status",
            fields: {
                pending: "#abstract-pending",
                under_review: "#abstract-under-review",
                accepted: "#abstract-accepted",
                rejected: "#abstract-rejected",
            },
        },
        award: {
            endpoint: "/research/awards/status",
            fields: {
                pending: "#award-pending",
                under_review: "#award-under-review",
                accepted: "#award-accepted",
                rejected: "#award-rejected",
            },
        },
        bestPaper: {
            endpoint: "/research/best-papers/status",
            fields: {
                pending: "#best-paper-pending",
                under_review: "#best-paper-under-review",
                accepted: "#best-paper-accepted",
                rejected: "#best-paper-rejected",
            },
        },
    };

    const OVERVIEW_FIELDS = {
        pending: "#pending",
        under_review: "#under-review",
        accepted: "#accepted",
        rejected: "#rejected",
    };

    const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
    const abortController = new AbortController();

    const statusState = new Map(
        Object.keys(STATUS_CONFIG).map((key) => [key, createEmptyTotals()])
    );

    const toast =
        window.SubmitList?.utils?.toast ||
        window.researchPortal?.showToast ||
        ((message, type = "info") => {
            (type === "error" ? console.error : console.warn)(`[Home] ${message}`);
        });

    function createEmptyTotals() {
        return { pending: 0, under_review: 0, accepted: 0, rejected: 0 };
    }

    function getToken() {
        const candidates = ["token", "access_token"];
        for (const key of candidates) {
            const value = localStorage.getItem(key);
            if (value && value.trim()) return value.trim();
        }
        return "";
    }

    function buildHeaders(initHeaders = {}, body) {
        const headers = new Headers(initHeaders);
        headers.set("Accept", "application/json");

        const token = getToken();
        if (token && !headers.has("Authorization")) {
            headers.set("Authorization", `Bearer ${token}`);
        }

        const isJsonBody = body && !(body instanceof FormData);
        if (isJsonBody && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }

        return headers;
    }

    async function request(path, { method = "GET", body, headers, signal } = {}) {
        const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
        const resolvedHeaders = buildHeaders(headers, body);
        const init = {
            method,
            headers: resolvedHeaders,
            signal,
        };

        if (body) {
            init.body = body instanceof FormData ? body : JSON.stringify(body);
        }

        let response;
        try {
            response = await fetch(url, init);
        } catch (error) {
            toast("Network error while contacting the service.", "error");
            throw error;
        }

        if (response.status === 204) {
            return {};
        }

        if (!response.ok) {
            const message = await extractErrorMessage(response);
            if (response.status >= 500) {
                toast("The service is temporarily unavailable. Please try again later.", "error");
            } else if (message) {
                toast(message, "warn");
            }
            throw new Error(message || `Request failed (${response.status})`);
        }

        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            return {};
        }
        return response.json();
    }

    async function extractErrorMessage(response) {
        try {
            const data = await response.clone().json();
            return data?.error || data?.message || "";
        } catch {
            return response.statusText || "";
        }
    }

    function safeCount(value) {
        const num = Number.parseInt(value, 10);
        return Number.isFinite(num) ? num : 0;
    }

    function normalizeStatusPayload(raw) {
        const source = raw || {};
        const normalised = createEmptyTotals();

        for (const key of STATUS_FIELDS) {
            if (key in source) {
                normalised[key] = safeCount(source[key]);
                continue;
            }

            const camelKey = key.replace(/_(\w)/g, (_, ch) => ch.toUpperCase());
            if (camelKey in source) {
                normalised[key] = safeCount(source[camelKey]);
                continue;
            }

            const upperKey = key.toUpperCase();
            if (upperKey in source) {
                normalised[key] = safeCount(source[upperKey]);
            }
        }

        return normalised;
    }

    function updateNodes(fieldMap, values) {
        Object.entries(fieldMap).forEach(([field, selector]) => {
            const element = document.querySelector(selector);
            if (!element) return;
            const value = values[field] ?? 0;
            element.textContent = numberFormatter.format(value);
        });
    }

    function updateOverview() {
        const totals = createEmptyTotals();
        statusState.forEach((values) => {
            STATUS_FIELDS.forEach((field) => {
                totals[field] += safeCount(values[field]);
            });
        });
        updateNodes(OVERVIEW_FIELDS, totals);
    }

    function applyStatus(key, payload) {
        const config = STATUS_CONFIG[key];
        if (!config) return;
        const normalised = normalizeStatusPayload(payload);
        statusState.set(key, normalised);
        updateNodes(config.fields, normalised);
        updateOverview();
    }

    async function refreshStatuses() {
        const tasks = Object.entries(STATUS_CONFIG).map(async ([key, config]) => {
            try {
                const data = await request(config.endpoint, { signal: abortController.signal });
                applyStatus(key, data);
            } catch (error) {
                if (error?.name === "AbortError") {
                    return;
                }
                console.warn(`[Home] Unable to load ${key} status`, error);
                applyStatus(key, {});
            }
        });

        await Promise.allSettled(tasks);
    }

    function init() {
        Object.keys(STATUS_CONFIG).forEach((key) => {
            const snapshot = statusState.get(key);
            applyStatus(key, snapshot);
        });
        refreshStatuses();
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                refreshStatuses();
            }
        });
    }

    window.addEventListener("beforeunload", () => abortController.abort());

    window.researchPortal = Object.assign({}, window.researchPortal, {
        showToast: toast,
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
