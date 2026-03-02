/* ═══════════════════════════════════════════════════════════════════
   Crop Intelligence Platform — Core Application
   SPA Router + API Client + Shared Utilities
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = "/api/v1";

/* ── API Client ─────────────────────────────────────────────────── */
const api = {
  async post(endpoint, body = {}) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async get(endpoint) {
    const res = await fetch(endpoint);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  soil:       (body) => api.post("/soil/analyze", body),
  weather:    (body) => api.post("/weather/analyze", body),
  crop:       (body) => api.post("/crop/analyze", body),
  fertilizer: (body) => api.post("/fertilizer/recommend", body),
  disease:    (body) => api.post("/disease/assess", body),
  market:     (body) => api.post("/market/analyze", body),
  advisory:   (body) => api.post("/advisory/full", body),
  health:     ()     => api.get("/health"),
};

/* ── Helpers ────────────────────────────────────────────────────── */
function $(sel, ctx = document) { return ctx.querySelector(sel); }
function $$(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

function html(strings, ...vals) {
  return strings.reduce((out, s, i) => out + s + (vals[i] ?? ""), "");
}

function fmt(val, decimals = 1) {
  if (val == null) return "N/A";
  return typeof val === "number" ? val.toFixed(decimals) : String(val);
}

function fmtPct(val) {
  if (val == null) return "N/A";
  return (val * 100).toFixed(1) + "%";
}

function fmtUSD(val) {
  if (val == null) return "N/A";
  return "$" + Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function classify(val, thresholds = [33, 66]) {
  if (val == null) return "gray";
  if (val < thresholds[0]) return "red";
  if (val < thresholds[1]) return "amber";
  return "green";
}

function riskClass(score) {
  if (score == null) return "risk-low";
  if (score >= 70) return "risk-high";
  if (score >= 40) return "risk-medium";
  return "risk-low";
}

function scoreColor(score) {
  if (score == null) return "var(--ci-gray-400)";
  if (score >= 70) return "var(--ci-green-500)";
  if (score >= 40) return "var(--ci-amber-500)";
  return "var(--ci-red-500)";
}

function renderScoreRing(score, size = 56) {
  const r = 22;
  const c = Math.PI * 2 * r;
  const pct = Math.min(100, Math.max(0, score ?? 0));
  const offset = c * (1 - pct / 100);
  const color = scoreColor(score);
  return `
    <div class="score-ring" style="width:${size}px;height:${size}px">
      <svg viewBox="0 0 56 56">
        <circle class="ring-bg" cx="28" cy="28" r="${r}"/>
        <circle class="ring-fill" cx="28" cy="28" r="${r}"
                stroke="${color}"
                stroke-dasharray="${c}"
                stroke-dashoffset="${offset}"/>
      </svg>
      <span class="ring-value" style="color:${color}">${fmt(score, 0)}</span>
    </div>`;
}

function renderRiskBar(score, label) {
  const cls = riskClass(score);
  return `
    <div class="mb-8">
      <div class="flex justify-between items-center mb-4" style="margin-bottom:4px">
        <span class="text-sm">${label}</span>
        <span class="text-sm text-bold">${fmt(score, 0)}/100</span>
      </div>
      <div class="risk-bar ${cls}">
        <div class="risk-bar-fill" style="width:${Math.min(100, score ?? 0)}%"></div>
      </div>
    </div>`;
}

function renderKV(label, value, sub = "") {
  return `
    <div class="kv-item">
      <div class="kv-label">${label}</div>
      <div class="kv-value">${value}</div>
      ${sub ? `<div class="kv-sub">${sub}</div>` : ""}
    </div>`;
}

function renderBadge(text, color = "gray") {
  return `<span class="badge badge-${color}">${text}</span>`;
}

function renderRecs(recs = []) {
  if (!recs.length) return '<p class="text-sm text-muted">No recommendations.</p>';
  return `<ul class="rec-list">${recs.map((r) => `<li>${r}</li>`).join("")}</ul>`;
}

function showLoading(container) {
  container.innerHTML = `
    <div style="padding:40px;text-align:center">
      <div class="spinner" style="width:32px;height:32px;border:3px solid var(--ci-gray-200);border-top-color:var(--ci-green-600);border-radius:50%;margin:0 auto 16px;animation:spin 0.7s linear infinite"></div>
      <p class="text-sm text-muted">Analyzing data from external sources...</p>
    </div>`;
}

function showError(container, msg) {
  container.innerHTML = `
    <div class="alert alert-error">
      <span>&#9888;</span>
      <div>
        <strong>Analysis Failed</strong><br>
        <span class="text-sm">${msg}</span>
      </div>
    </div>`;
}

/* ── SPA Router ─────────────────────────────────────────────────── */
const routes = {};

function registerPage(path, { title, render }) {
  routes[path] = { title, render };
}

function navigate(path) {
  history.pushState(null, "", `#${path}`);
  renderRoute(path);
}

function renderRoute(path) {
  const route = routes[path];
  if (!route) return navigate("dashboard");

  /* Update sidebar active state */
  $$(".sidebar-link").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === path);
  });

  /* Update breadcrumb */
  const bc = $("#topbar-breadcrumb");
  if (bc) {
    bc.innerHTML = `
      <span>Platform</span>
      <span>/</span>
      <span class="crumb-active">${route.title}</span>`;
  }

  /* Render page */
  const container = $("#page-container");
  if (container) route.render(container);
}

window.addEventListener("hashchange", () => {
  const path = location.hash.slice(1) || "dashboard";
  renderRoute(path);
});

/* ── Boot ───────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  /* Bind sidebar navigation */
  $$(".sidebar-link").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(el.dataset.route);
    });
  });

  /* Initial route */
  const initialPath = location.hash.slice(1) || "dashboard";
  navigate(initialPath);

  /* Health check ping */
  api.health().then((d) => {
    const dot = $(".status-dot");
    if (dot) dot.style.background = "var(--ci-green-500)";
  }).catch(() => {
    const dot = $(".status-dot");
    if (dot) dot.style.background = "var(--ci-red-500)";
  });
});
