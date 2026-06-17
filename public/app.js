const STATUSES = ["Concept Stage", "Scripting", "In Production", "In Review", "Ready", "Completed", "Published", "On Hold"];
const ACTIVE_STATUSES = ["Scripting", "In Production", "In Review", "Ready"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];
const STATUS_COLORS = {
  "Concept Stage": "#98a2b3",
  "Scripting": "#8b5cf6",
  "In Production": "#2563eb",
  "In Review": "#d98a08",
  "Ready": "#0f9f9a",
  "Completed": "#0e7490",
  "Published": "#12a36d",
  "On Hold": "#d04444",
};
const QUICK_FILTERS = [
  ["needs-owner", "Needs primary"],
  ["needs-secondary", "Needs secondary"],
  ["needs-deadline", "Needs expected date"],
  ["needs-admin", "Needs admin"],
  ["in-review", "In review"],
  ["ready-to-publish", "Ready to publish"],
  ["active", "Active pipeline"],
  ["completed", "Completed"],
  ["published", "Published"],
];

const state = {
  view: localStorage.getItem("taskmaster_view") || "dashboard",
  role: "viewer",
  currentUser: null,
  login: { username: "", password: "" },
  password: { currentPassword: "", newPassword: "", confirmPassword: "" },
  tasks: [],
  analytics: null,
  command: null,
  options: {},
  users: [],
  myWork: { tasks: [], counts: {} },
  planning: { calendar: [], missingDates: [], timeline: [] },
  notifications: [],
  digest: { summary: {} },
  accessMatrix: [],
  auditEvents: [],
  deployment: null,
  collaboration: {},
  forms: { comment: "", assetType: "Final Video", assetLabel: "", assetUrl: "", reviewNote: "" },
  newUser: { username: "", displayName: "", role: "editor", email: "", phone: "", team: "", agencyName: "", isAgencyUser: false, accessType: "bucket", accessValue: "" },
  loading: true,
  error: "",
  toast: "",
  selectedTaskId: "",
  selectedIds: new Set(),
  bulk: { bucketAdmin: "", primaryOwner: "", secondaryOwner: "", deadline: "", agency: "", status: "", priority: "" },
  fix: { primaryOwner: "", secondaryOwner: "", deadline: "", bucketAdmin: "" },
  triageOffset: 0,
  mobileFiltersOpen: false,
  filters: {
    q: "",
    brand: "",
    bucket: "",
    zone: "",
    agency: "",
    owner: "",
    bucketAdmin: "",
    primaryOwner: "",
    secondaryOwner: "",
    reviewer: "",
    status: "",
    overdue: "",
    quickFilter: "",
    deadlineFrom: "",
    deadlineTo: "",
  },
  activityTask: "",
  activity: [],
};

const app = document.getElementById("app");

function icon(name) {
  const paths = {
    search: '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path>',
    plus: '<path d="M12 5v14M5 12h14"></path>',
    dashboard: '<path d="M4 13h6V4H4v9Zm10 7h6V4h-6v16ZM4 20h6v-4H4v4Z"></path>',
    board: '<path d="M4 5h5v14H4V5Zm7 0h5v9h-5V5Zm7 0h2v14h-2V5Z"></path>',
    table: '<path d="M4 5h16v14H4V5Zm0 5h16M9 5v14"></path>',
    report: '<path d="M5 20V4h14v16H5Zm4-4h6M9 12h6M9 8h3"></path>',
    copy: '<path d="M8 8h11v11H8V8Zm-3 8V5h11"></path>',
    trash: '<path d="M5 7h14M9 7V5h6v2m-8 0 1 13h8l1-13"></path>',
    reset: '<path d="M4 7v5h5M20 17a8 8 0 0 1-14.4-4.8M4 12a8 8 0 0 1 14.4-4.8"></path>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7M3 5v6h6M12 7v5l3 2"></path>',
    command: '<path d="M4 6h16M4 12h10M4 18h7"></path><path d="m17 14 3 3-3 3"></path>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h7M15 18h5"></path><path d="M14 4v4M8 10v4M13 16v4"></path>',
    close: '<path d="M18 6 6 18M6 6l12 12"></path>',
  };
  return `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || ""}</svg>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function params() {
  const p = new URLSearchParams();
  Object.entries(state.filters).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  return p.toString();
}

async function api(path, options = {}) {
  const headers = options.body instanceof FormData ? { ...(options.headers || {}) } : {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const res = await fetch(path, { ...options, headers });
  const type = res.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await res.json() : await res.text();
  if (res.status === 401) {
    state.currentUser = null;
    state.role = "viewer";
  }
  if (!res.ok) throw new Error(data.error || data || "Request failed");
  return data;
}

async function loadMe() {
  const res = await api("/api/me");
  state.currentUser = res.user || null;
  state.role = state.currentUser?.role || "viewer";
  return state.currentUser;
}

async function boot() {
  state.loading = true;
  render();
  try {
    const user = await loadMe();
    if (user) {
      await loadAll();
    } else {
      state.loading = false;
      render();
    }
  } catch (err) {
    state.loading = false;
    render();
  }
}

async function loadAll() {
  if (!state.currentUser) {
    state.loading = false;
    render();
    return;
  }
  state.loading = true;
  state.error = "";
  render();
  try {
    const q = params();
    const bootstrapParams = new URLSearchParams(q);
    bootstrapParams.set("view", state.view);
    const { tasks, analytics, command, options, notifications, digest, myWork, planning, users, accessMatrix, deployment, audit } = await api(`/api/bootstrap?${bootstrapParams.toString()}`);
    state.tasks = tasks.tasks;
    state.analytics = analytics;
    state.command = command;
    state.options = options;
    state.notifications = notifications.notifications || [];
    state.digest = digest || { summary: {} };
    state.myWork = myWork;
    state.planning = planning;
    state.users = users.users || options.users || [];
    state.accessMatrix = accessMatrix.matrix || [];
    state.deployment = deployment;
    state.auditEvents = audit.events || [];
    state.selectedIds = new Set([...state.selectedIds].filter((id) => state.tasks.some((t) => t.id === id)));
  } catch (err) {
    state.error = err.message;
  } finally {
    state.loading = false;
    render();
  }
}

function toast(message) {
  state.toast = message;
  render();
  setTimeout(() => {
    if (state.toast === message) {
      state.toast = "";
      render();
    }
  }, 2200);
}

function isViewer() { return state.role === "viewer"; }
function isAdmin() { return state.role === "super_admin"; }
function isSuperAdmin() { return state.role === "super_admin"; }
function isAgencyUser() { return state.role === "agency" || state.currentUser?.isAgencyUser; }
function taskById(id) { return state.tasks.find((t) => t.id === id); }
function selectedTask() { return taskById(state.selectedTaskId); }

function activeUsers() {
  return (state.options.users || state.users || []).filter((u) => u.isActive !== false);
}

function peopleOptions(current = "") {
  const opts = new Set(["", ...activeUsers().map((u) => u.displayName), current].filter((v) => v !== undefined));
  return [...opts].map((o) => `<option value="${escapeHtml(o)}" ${o === current ? "selected" : ""}>${o ? escapeHtml(o) : "Assign..."}</option>`).join("");
}

function agencyOptions(current = "") {
  const opts = new Set(["", ...(state.options.agency || []), current].filter((v) => v !== undefined));
  return [...opts].map((o) => `<option value="${escapeHtml(o)}" ${o === current ? "selected" : ""}>${o ? escapeHtml(o) : "Select agency..."}</option>`).join("");
}

function setView(view) {
  state.view = view;
  localStorage.setItem("taskmaster_view", view);
  render();
}

function setRole(role) {
  state.role = role;
  loadAll();
}

function applyQuickFilter(quickFilter, view = "table") {
  state.filters.quickFilter = quickFilter;
  state.view = view;
  localStorage.setItem("taskmaster_view", view);
  loadAll();
}

function clearFilters() {
  Object.keys(state.filters).forEach((k) => (state.filters[k] = ""));
  state.selectedIds.clear();
  loadAll();
}

function queryWithQuickFilter(quickFilter) {
  const p = new URLSearchParams();
  Object.entries(state.filters).forEach(([k, v]) => {
    if (v && k !== "quickFilter") p.set(k, v);
  });
  p.set("quickFilter", quickFilter);
  return p.toString();
}

function riskLabel(task) {
  const r = task.risk || {};
  if (r.overdue) return ["Overdue", "red"];
  if (r.readyToPublish) return ["Ready to publish", "green"];
  if (r.stuck) return [`Stuck ${r.stageAgeDays}d`, "red"];
  if (r.missingPrimary) return ["No primary", "red"];
  if (r.missingSecondary) return ["No secondary", "amber"];
  if (r.missingAdmin) return ["No admin", "red"];
  if (r.missingDeadline) return ["No expected date", "amber"];
  if (r.dueSoon) return ["Due soon", "amber"];
  return [`${r.stageAgeDays || 0}d in stage`, "gray"];
}

function statusPill(status) {
  return `<span class="status-pill" style="--pill:${STATUS_COLORS[status] || "#98a2b3"}"><i></i>${escapeHtml(status)}</span>`;
}

function priorityChip(priority) {
  const tone = priority === "Urgent" || priority === "High" ? "red" : priority === "Medium" ? "amber" : "gray";
  return `<span class="chip ${tone}">${escapeHtml(priority || "Medium")}</span>`;
}

function renderTopbar() {
  const nav = [
    ["dashboard", "Command", "dashboard"],
    ["mywork", "My Work", "command"],
    ["planning", "Planning", "report"],
    ["board", "Board", "board"],
    ["table", "Table", "table"],
    ["reports", "Reports", "report"],
  ];
  if (isAdmin()) nav.push(["admin", "Admin", "sliders"]);
  return `
    <header class="topbar">
      <div class="brand">
        <div class="mark"><img src="/astral-logo-cropped.jpg" alt="Astral" /></div>
        <div>
          <h1>Production Command Center</h1>
          <p>Owners, expected completion dates, bottlenecks, and publishing readiness in one operating view.</p>
        </div>
      </div>
      <nav class="nav" aria-label="Primary">
        ${nav.map(([id, label, ico]) => `<button class="${state.view === id ? "active" : ""}" data-view="${id}">${icon(ico)}${label}</button>`).join("")}
      </nav>
      <div class="top-actions">
        ${isSuperAdmin() ? '<span class="viewer-lock super">Super Admin</span>' : ""}
        <div class="user-chip">
          <strong>${escapeHtml(state.currentUser?.displayName || "User")}</strong>
          <span>${escapeHtml((state.currentUser?.role || "").replace("_", " "))}</span>
        </div>
        <button class="btn ghost" data-logout>Logout</button>
      </div>
    </header>
  `;
}

function renderLogin() {
  return `<main class="login-shell">
    <section class="login-card">
      <div class="login-brand">
        <img src="/astral-logo-cropped.jpg" alt="Astral" />
        <span>Taskmaster</span>
      </div>
      <h1>Production Command Center</h1>
      <div class="login-context">Secure access for Astral production teams</div>
      <form class="login-form" data-login-form>
        <label>User ID<input name="username" autocomplete="username" value="${escapeHtml(state.login.username)}" placeholder="Enter your user ID" /></label>
        <label>Password<input name="password" type="password" autocomplete="current-password" value="${escapeHtml(state.login.password)}" placeholder="Enter your password" /></label>
        <button class="btn" type="submit">Sign in</button>
      </form>
      <div class="login-support">Need access or a password reset? Contact your Taskmaster admin.</div>
      ${state.error ? `<div class="error compact">${escapeHtml(state.error)}</div>` : ""}
    </section>
  </main>`;
}

function renderPasswordNotice() {
  if (!state.currentUser?.mustChangePassword) return "";
  return `<section class="password-notice">
    <div>
      <strong>Change your temporary password</strong>
      <span>Your account is active. Set a private password so this login is ready for team use.</span>
    </div>
    <form class="password-form" data-password-form>
      <input name="currentPassword" type="password" autocomplete="current-password" placeholder="Current password" value="${escapeHtml(state.password.currentPassword)}" />
      <input name="newPassword" type="password" autocomplete="new-password" placeholder="New password" value="${escapeHtml(state.password.newPassword)}" />
      <input name="confirmPassword" type="password" autocomplete="new-password" placeholder="Confirm" value="${escapeHtml(state.password.confirmPassword)}" />
      <button class="btn" type="submit">Update password</button>
    </form>
  </section>`;
}

function filterControl(label, key, options, className = "") {
  return `
    <label class="control ${className}">
      <select data-filter="${key}">
        <option value="">${label}: All</option>
        ${(options || []).map((o) => `<option value="${escapeHtml(o)}" ${state.filters[key] === o ? "selected" : ""}>${escapeHtml(o)}</option>`).join("")}
      </select>
    </label>
  `;
}

function renderQuickFilters() {
  return `<div class="quickbar">
    ${QUICK_FILTERS.map(([id, label]) => `<button class="${state.filters.quickFilter === id ? "on" : ""}" data-quick="${id}">${label}</button>`).join("")}
  </div>`;
}

function renderFilters() {
  const options = state.options || {};
  return `
    <button class="mobile-filter-toggle" data-toggle-filters>
      ${icon("sliders")} ${state.mobileFiltersOpen ? "Hide filters" : "More filters"}
    </button>
    <section class="filterbar premium ${state.mobileFiltersOpen ? "show-advanced" : ""}">
      <label class="search filter-search">${icon("search")}<input data-filter="q" value="${escapeHtml(state.filters.q)}" placeholder="Search videos, owners, zones, agencies..." /></label>
      ${filterControl("Brand", "brand", options.brand, "filter-cell core-filter")}
      ${filterControl("Bucket", "bucket", options.bucket, "filter-cell core-filter")}
      ${filterControl("Agency", "agency", options.agency, "filter-cell core-filter")}
      ${filterControl("Zone", "zone", options.zone, "filter-cell advanced-filter")}
      ${filterControl("Admin", "bucketAdmin", options.bucketAdmin, "filter-cell advanced-filter")}
      ${filterControl("Primary", "primaryOwner", options.primaryOwner, "filter-cell advanced-filter")}
      ${filterControl("Secondary", "secondaryOwner", options.secondaryOwner, "filter-cell wide-filter advanced-filter")}
      ${filterControl("Status", "status", STATUSES, "filter-cell advanced-filter")}
      <label class="control filter-cell advanced-filter">
        <select data-filter="overdue">
          <option value="">Expected date: All</option>
          <option value="overdue" ${state.filters.overdue === "overdue" ? "selected" : ""}>Overdue only</option>
          <option value="no-deadline" ${state.filters.overdue === "no-deadline" ? "selected" : ""}>No expected date</option>
        </select>
      </label>
      <div class="date-pair">
        <label class="control"><input type="date" data-filter="deadlineFrom" value="${escapeHtml(state.filters.deadlineFrom)}" /></label>
        <label class="control"><input type="date" data-filter="deadlineTo" value="${escapeHtml(state.filters.deadlineTo)}" /></label>
      </div>
      <div class="filter-actions">
        <button class="btn ghost" data-clear>Clear</button>
        <button class="btn" data-new ${isViewer() ? "disabled" : ""}>${icon("plus")} New</button>
      </div>
    </section>
    ${state.view === "dashboard" ? "" : renderQuickFilters()}
    <div class="statusline">
      <span>Showing <strong>${state.tasks.length}</strong> tasks ${state.filters.quickFilter ? `in <strong>${escapeHtml(labelForQuick(state.filters.quickFilter))}</strong>` : ""}</span>
    </div>
  `;
}

function labelForQuick(id) {
  return (QUICK_FILTERS.find((q) => q[0] === id) || ["", id])[1];
}

function pct(part, total) {
  return total ? Math.round((Number(part || 0) / Number(total || 1)) * 100) : 0;
}

function healthMetrics() {
  const c = state.command?.cards || {};
  const total = Math.max(1, Number(c.needsAttention || state.tasks.length || 0));
  const primary = Math.max(0, 100 - pct(c.missingPrimary, total));
  const secondary = Math.max(0, 100 - pct(c.missingSecondary, total));
  const deadline = Math.max(0, 100 - pct(c.missingDeadline, total));
  const admin = Math.max(0, 100 - pct(c.missingAdmin, total));
  const reviewLoad = Math.max(0, 100 - pct(c.stuckReview, total));
  const score = Math.round((primary * 0.3) + (secondary * 0.18) + (deadline * 0.27) + (admin * 0.15) + (reviewLoad * 0.1));
  return { score, primary, secondary, deadline, admin, reviewLoad };
}

function totalForHealth() {
  const c = state.command?.cards || {};
  return Math.max(1, Number(c.needsAttention || state.tasks.length || 0));
}

function completedCount(missing) {
  return Math.max(0, totalForHealth() - Number(missing || 0));
}

function healthTone(score) {
  if (score >= 80) return "green";
  if (score >= 55) return "amber";
  return "red";
}

function isColdStart() {
  const c = state.command?.cards || {};
  const total = Math.max(1, Number(c.needsAttention || state.tasks.length || 0));
  return pct(c.missingPrimary, total) >= 70 || pct(c.missingDeadline, total) >= 70;
}

function semanticTone(key, value) {
  if (Number(value || 0) === 0) return "green";
  if (key === "readyToPublish") return "green";
  if (key === "missingPrimary" || key === "needsAttention") return "red";
  if (key === "missingAdmin") return Number(value || 0) ? "red" : "green";
  return "amber";
}

function commandCard(key, label, value, tone, quickFilter) {
  const resolvedTone = tone || semanticTone(key, value);
  return `<button class="command-card ${resolvedTone}" data-quick="${quickFilter || ""}">
    <span>${label}</span>
    <strong>${value || 0}</strong>
    <small>${quickFilter ? "Open list" : "Live"}</small>
  </button>`;
}

function renderDashboard() {
  const c = state.command?.cards || {};
  const h = healthMetrics();
  if (isColdStart()) return renderColdStartDashboard(c, h);
  return `
    <section class="command-hero">
      <div>
        <h2>Today’s Command Center</h2>
        <p>${c.needsAttention || 0} items need attention. The fastest productivity lift is to complete accountability first: primary owner, secondary owner, bucket admin, then expected completion date.</p>
      </div>
      <button class="btn" data-quick="needs-owner">${icon("command")} Triage now</button>
    </section>
    <section class="command-top">
      ${productionHealth(h)}
      ${priorityQueue()}
      ${guidedFixPanel()}
    </section>
    ${commandCockpit()}
  `;
}

function renderColdStartDashboard(c, h) {
  const total = totalForHealth();
  const deadlineDominant = pct(c.missingDeadline, total) >= 70 && pct(c.missingPrimary, total) < 30;
  const heroTitle = deadlineDominant ? "Set expected dates to unlock forecasting" : "Assign owners to unlock this dashboard";
  const heroBody = deadlineDominant
    ? `${c.missingDeadline || 0} of ${total} tasks have no expected completion date. Ownership is mostly ready, so the next cleanup pass is completion-date planning.`
    : `${c.missingPrimary || 0} of ${total} tasks have no primary owner, and ${c.missingDeadline || 0} have no expected completion date. Triage these rows here first; the dashboard becomes an operating view once hygiene improves.`;
  const heroQuick = deadlineDominant ? "needs-deadline" : "needs-owner";
  const heroCta = deadlineDominant ? `Set expected dates for ${c.missingDeadline || 0} items` : `Triage all ${c.missingPrimary || 0} items`;
  const importLabel = deadlineDominant ? "Import expected dates from CSV" : "Import owners from CSV";
  return `
    <section class="setup-hero">
      <div class="setup-top">
        <div class="setup-main">
          <span class="setup-eyebrow">Setup needed · ${100 - h.score}% of operating hygiene incomplete</span>
          <h2>${heroTitle}</h2>
          <p>${heroBody}</p>
          <div class="setup-actions">
            <button class="btn" data-quick="${heroQuick}">${icon("command")} ${heroCta}</button>
            <button class="btn ghost" data-view="reports">${importLabel}</button>
          </div>
        </div>
        <div class="hygiene-panel">
          ${hygieneRow("Primary owners", completedCount(c.missingPrimary), totalForHealth(), h.primary, h.primary >= 70 ? "green" : "red")}
          ${hygieneRow("Secondary owners", completedCount(c.missingSecondary), totalForHealth(), h.secondary, h.secondary >= 70 ? "green" : "red")}
          ${hygieneRow("Expected dates", completedCount(c.missingDeadline), totalForHealth(), h.deadline, h.deadline >= 70 ? "green" : "amber")}
          ${hygieneRow("Bucket admins", completedCount(c.missingAdmin), totalForHealth(), h.admin, h.admin === 100 ? "green" : "red")}
        </div>
      </div>
      ${triageTable()}
    </section>
    ${commandCockpit()}
  `;
}

function hygieneRow(label, completed, total, percentValue, tone) {
  return `<div class="hygiene-row">
    <span class="hygiene-label">${label}</span>
    <div class="hygiene-track"><div class="hygiene-fill ${tone}" style="width:${Math.max(0, Math.min(100, percentValue))}%"></div></div>
    <span class="hygiene-num ${tone}">${completed} / ${total}</span>
  </div>`;
}

function statusCount(status) {
  return state.tasks.filter((t) => t.status === status).length;
}

function kpiCard(label, value, subtitle, tone, quickFilter) {
  return `<button class="kpi-card ${tone}" data-quick="${quickFilter}">
    <span>${label}</span>
    <strong>${value || 0}</strong>
    <small>${subtitle}</small>
  </button>`;
}

function commandCockpit() {
  return `<section class="cockpit-grid">
    <article class="panel cockpit-flow">
      <div class="panel-head">
        <div><h2>Production Flow</h2><small>Where work is planned, moving, waiting, and shipped</small></div>
        <button class="panel-action" data-quick="active">Open active</button>
      </div>
      ${productionFlowChart()}
    </article>
    <article class="panel cockpit-plan">
      <div class="panel-head">
        <div><h2>Planning Readiness</h2><small>Expected dates by bucket, so forecasting becomes real</small></div>
        <button class="panel-action" data-quick="needs-deadline">Set dates</button>
      </div>
      ${dateReadinessChart()}
    </article>
    <article class="panel cockpit-people">
      <div class="panel-head">
        <div><h2>People Load</h2><small>Primary owners and bucket-admin responsibility</small></div>
        <button class="panel-action" data-view="table">Open table</button>
      </div>
      ${peopleLoadCockpit()}
    </article>
    <article class="panel cockpit-actions">
      <div class="panel-head">
        <div><h2>Action Queue</h2><small>The next work that actually changes output</small></div>
        <button class="panel-action" data-quick="ready-to-publish">Publish queue</button>
      </div>
      ${priorityQueueList()}
    </article>
    <article class="panel cockpit-heatmap">
      <div class="panel-head"><div><h2>Deadline Heatmap</h2><small>Expected completions by week and bucket</small></div></div>
      ${deadlineHeatmap()}
    </article>
    <article class="panel cockpit-throughput">
      <div class="panel-head"><div><h2>Agency Throughput</h2><small>Active, stuck, completed, and published</small></div></div>
      ${agencyThroughputChart()}
    </article>
    <article class="panel cockpit-review">
      <div class="panel-head"><div><h2>Review Aging</h2><small>How long work has waited in review</small></div></div>
      ${reviewAgingChart()}
    </article>
    <article class="panel cockpit-trend">
      <div class="panel-head"><div><h2>Planned vs Completed</h2><small>Monthly execution against expected dates</small></div></div>
      ${plannedCompletedTrend()}
    </article>
  </section>`;
}

function deadlineHeatmap() {
  const rows = state.analytics?.deadlineHeatmap || [];
  if (!rows.length) return `<div class="empty compact-empty">Add expected dates to unlock the heatmap.</div>`;
  const max = Math.max(1, ...rows.map((r) => Number(r.count || 0)));
  return `<div class="heatmap-grid">${rows.slice(0, 36).map((r) => `<button class="heat-cell" style="--alpha:${0.18 + (Number(r.count || 0) / max) * 0.72}" data-bucket-filter="${escapeHtml(r.bucket)}"><strong>${escapeHtml(r.week)}</strong><span>${escapeHtml(r.bucket)}</span><em>${r.count}</em></button>`).join("")}</div>`;
}

function agencyThroughputChart() {
  const rows = state.analytics?.agencyThroughput || [];
  if (!rows.length) return `<div class="empty compact-empty">No agency work in this filter.</div>`;
  const max = Math.max(1, ...rows.map((r) => Number(r.active || 0) + Number(r.completed || 0) + Number(r.published || 0)));
  return `<div class="throughput-list">${rows.slice(0, 8).map((r) => {
    const active = Math.round((Number(r.active || 0) / max) * 100);
    const completed = Math.round((Number(r.completed || 0) / max) * 100);
    const published = Math.round((Number(r.published || 0) / max) * 100);
    return `<button class="throughput-row" data-agency-filter="${escapeHtml(r.agency === "Unassigned" ? "" : r.agency)}"><strong>${escapeHtml(r.agency)}</strong><div class="stack-bar"><i class="active" style="width:${active}%"></i><i class="complete" style="width:${completed}%"></i><i class="published" style="width:${published}%"></i></div><span>${r.active} active · ${r.stuck} stuck · ${r.completed + r.published} shipped</span></button>`;
  }).join("")}</div>`;
}

function reviewAgingChart() {
  const rows = state.analytics?.reviewAging || [];
  const max = Math.max(1, ...rows.map((r) => Number(r.count || 0)));
  return `<div class="aging-bars">${rows.map((r) => `<button class="aging-row" data-quick="in-review"><span>${escapeHtml(r.bucket)}</span><div class="bar-track"><div class="bar-fill amber" style="width:${Math.round((Number(r.count || 0) / max) * 100)}%"></div></div><strong>${r.count}</strong></button>`).join("")}</div>`;
}

function plannedCompletedTrend() {
  const rows = state.analytics?.plannedVsCompleted || [];
  if (!rows.length) return `<div class="empty compact-empty">Expected dates are needed for planning trends.</div>`;
  const max = Math.max(1, ...rows.flatMap((r) => [Number(r.planned || 0), Number(r.completed || 0), Number(r.published || 0)]));
  return `<div class="trend-bars">${rows.map((r) => `<div class="trend-row"><span>${escapeHtml(r.period)}</span><div><i class="planned" style="height:${Math.max(6, Math.round((Number(r.planned || 0) / max) * 72))}px"></i><i class="complete" style="height:${Math.max(6, Math.round(((Number(r.completed || 0) + Number(r.published || 0)) / max) * 72))}px"></i></div><em>${r.planned} planned · ${Number(r.completed || 0) + Number(r.published || 0)} shipped</em></div>`).join("")}</div>`;
}

function commandCharts() {
  return `<section class="chart-command-grid">
    <article class="panel flow-panel">
      <div class="panel-head"><div><h2>Production Flow</h2><small>Where the work is sitting right now</small></div></div>
      ${productionFlowChart()}
    </article>
    <article class="panel mix-panel">
      <div class="panel-head"><div><h2>Status Mix</h2><small>Pipeline shape across all tasks</small></div></div>
      ${statusMixChart()}
    </article>
    <article class="panel owner-load-panel">
      <div class="panel-head"><div><h2>Owner Load</h2><small>Active, complete, and setup-blocked work</small></div></div>
      ${ownerLoadChart()}
    </article>
    <article class="panel date-readiness-panel">
      <div class="panel-head"><div><h2>Planning Readiness</h2><small>Expected-date coverage by bucket</small></div></div>
      ${dateReadinessChart()}
    </article>
  </section>`;
}

function productionFlowChart() {
  const stages = [
    ["Concept Stage", "Concept", "concept"],
    ["Scripting", "Script", "script"],
    ["In Production", "Production", "production"],
    ["In Review", "Review", "review"],
    ["Ready", "Ready", "ready"],
    ["Completed", "Completed", "completed"],
    ["Published", "Published", "published"],
  ].map(([status, label, key]) => ({ status, label, key, count: statusCount(status) }));
  const max = Math.max(1, ...stages.map((s) => s.count));
  const planned = statusCount("Concept Stage") + statusCount("Scripting");
  const moving = statusCount("In Production") + statusCount("In Review");
  const shipping = statusCount("Ready") + statusCount("Completed") + statusCount("Published");
  return `<div class="flow-chart">
    ${stages.map((s, index) => `<button class="flow-step ${s.key}" data-status-filter="${escapeHtml(s.status)}">
      <span>${s.label}</span>
      <strong>${s.count}</strong>
      <i style="height:${Math.max(8, Math.round((s.count / max) * 100))}%"></i>
      ${index < stages.length - 1 ? `<em aria-hidden="true"></em>` : ""}
    </button>`).join("")}
  </div>
  <div class="flow-takeaways">
    <button data-status-filter="Concept Stage"><strong>${planned}</strong><span>planned / not moving</span></button>
    <button data-quick="active"><strong>${moving}</strong><span>active in production or review</span></button>
    <button data-quick="ready-to-publish"><strong>${shipping}</strong><span>ready, completed, or published</span></button>
  </div>`;
}

function statusMixChart() {
  const statuses = STATUSES_FOR_UI.map((status) => ({ status, count: statusCount(status), color: statusColor(status) })).filter((s) => s.count);
  const total = Math.max(1, statuses.reduce((sum, s) => sum + s.count, 0));
  let cursor = 0;
  const stops = statuses.map((s) => {
    const start = cursor;
    cursor += (s.count / total) * 100;
    return `${s.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`;
  }).join(", ");
  return `<div class="status-mix">
    <div class="donut-chart" style="background:conic-gradient(${stops || "#e5e9ef 0 100%"});">
      <strong>${total}</strong>
      <span>tasks</span>
    </div>
    <div class="status-legend">
      ${statuses.map((s) => `<button data-status-filter="${escapeHtml(s.status)}">
        <i style="background:${s.color}"></i>
        <span>${escapeHtml(s.status)}</span>
        <strong>${s.count}</strong>
      </button>`).join("")}
    </div>
  </div>`;
}

function ownerLoadChart() {
  const rows = state.command?.ownerScorecards || [];
  if (!rows.length) return `<div class="empty compact-empty">No owner data yet.</div>`;
  const max = Math.max(1, ...rows.map((r) => Number(r.total || 0)));
  return `<div class="owner-load-chart">
    ${rows.map((r) => {
      const blocked = Math.round((Number(r.blocked || 0) / max) * 100);
      const active = Math.round((Number(r.active || 0) / max) * 100);
      const complete = Math.round((Number(r.complete || 0) / max) * 100);
      return `<button class="owner-load-row" data-owner-filter="${escapeHtml(r.owner === "Unassigned" ? "" : r.owner)}">
        <div><strong>${escapeHtml(r.owner)}</strong><span>${r.total} total</span></div>
        <div class="stack-bar"><i class="blocked" style="width:${blocked}%"></i><i class="active" style="width:${active}%"></i><i class="complete" style="width:${complete}%"></i></div>
        <em>${r.active} active · ${r.complete} done</em>
      </button>`;
    }).join("")}
  </div>`;
}

function peopleLoadCockpit() {
  const owners = state.command?.ownerScorecards || [];
  const admins = state.command?.adminHealth || [];
  if (!owners.length && !admins.length) return `<div class="empty compact-empty">No people data yet.</div>`;
  const maxOwner = Math.max(1, ...owners.map((r) => Number(r.total || 0)));
  const maxAdmin = Math.max(1, ...admins.map((r) => Number(r.total || 0)));
  return `<div class="people-cockpit">
    <div class="people-cockpit-section">
      <span class="cockpit-label">Primary ownership</span>
      ${owners.map((r) => {
        const blocked = Math.round((Number(r.blocked || 0) / maxOwner) * 100);
        const active = Math.round((Number(r.active || 0) / maxOwner) * 100);
        const complete = Math.round((Number(r.complete || 0) / maxOwner) * 100);
        return `<button class="people-cockpit-row" data-owner-filter="${escapeHtml(r.owner === "Unassigned" ? "" : r.owner)}">
          <div><strong>${escapeHtml(r.owner)}</strong><span>${r.total} tasks · ${r.active} active</span></div>
          <div class="stack-bar"><i class="blocked" style="width:${blocked}%"></i><i class="active" style="width:${active}%"></i><i class="complete" style="width:${complete}%"></i></div>
        </button>`;
      }).join("")}
    </div>
    <div class="people-cockpit-section">
      <span class="cockpit-label">Bucket admins</span>
      ${admins.map((r) => `<button class="admin-cockpit-row" data-admin-filter="${escapeHtml(r.admin === "Unassigned" ? "" : r.admin)}">
        <div><strong>${escapeHtml(r.admin)}</strong><span>${r.bucketCount} buckets · ${r.active} active</span></div>
        <div class="admin-meter"><i style="width:${Math.max(4, Math.round((Number(r.total || 0) / maxAdmin) * 100))}%"></i></div>
        <em>${r.total} tasks</em>
      </button>`).join("")}
    </div>
  </div>`;
}

function dateReadinessChart() {
  const rows = state.command?.bucketHealth || [];
  if (!rows.length) return `<div class="empty compact-empty">No bucket data yet.</div>`;
  return `<div class="date-readiness-chart">
    ${rows.map((r) => {
      const total = Math.max(1, Number(r.total || 0));
      const ready = Math.max(0, total - Number(r.missingDeadline || 0));
      const pct = Math.round((ready / total) * 100);
      return `<button class="date-bucket" data-bucket-filter="${escapeHtml(r.bucket)}">
        <div class="mini-ring" style="--pct:${pct * 3.6}deg"><strong>${pct}%</strong></div>
        <div><strong>${escapeHtml(r.bucket)}</strong><span>${r.missingDeadline} dates missing · ${escapeHtml(r.admin || "Unassigned")}</span></div>
      </button>`;
    }).join("")}
  </div>`;
}

const STATUSES_FOR_UI = ["Concept Stage", "Scripting", "In Production", "In Review", "Ready", "Completed", "Published", "On Hold"];

function statusColor(status) {
  return {
    "Concept Stage": "#8a95a8",
    Scripting: "#8b5cf6",
    "In Production": "#2563eb",
    "In Review": "#d98a08",
    Ready: "#16a36f",
    Completed: "#0f8f67",
    Published: "#111827",
    "On Hold": "#d04444",
  }[status] || "#8a95a8";
}

function triageCandidates() {
  const risky = state.tasks.filter((t) => t.risk?.missingPrimary || t.risk?.missingSecondary || t.risk?.missingDeadline);
  const sorted = risky.sort((a, b) => {
    const score = (t) => (t.risk?.missingPrimary ? 4 : 0) + (t.risk?.missingDeadline ? 2 : 0) + (t.risk?.missingSecondary ? 1 : 0) + (t.status === "In Review" ? 1 : 0);
    return score(b) - score(a) || Number(a.no || 0) - Number(b.no || 0);
  });
  return sorted;
}

function triageTable() {
  const rows = triageCandidates();
  const visible = rows.slice(state.triageOffset, state.triageOffset + 5);
  return `<div class="triage-table-wrap">
    <div class="triage-head">
      <div><h3>Quick triage · next ${visible.length} of ${rows.length}</h3><span>Assign inline. Changes autosave.</span></div>
      <button class="btn ghost" data-quick="needs-owner">Open all in table</button>
    </div>
    <div class="triage-table-scroll">
      <table class="triage-table">
        <thead>
          <tr><th>#</th><th>Item</th><th>Bucket</th><th>Primary owner</th><th>Secondary</th><th>Expected date</th></tr>
        </thead>
        <tbody>
          ${visible.map(triageRow).join("") || `<tr><td colspan="6">No triage rows in this filter.</td></tr>`}
        </tbody>
      </table>
    </div>
    <div class="triage-foot">
      <button class="btn ghost" data-triage-next ${rows.length <= 5 ? "disabled" : ""}>Next 5</button>
      <button class="btn ghost" data-apply-same-owner ${isViewer() || !visible.length ? "disabled" : ""}>Apply first owner to all 5</button>
      <span>Tip: filter by bucket first to triage one content bucket at a time.</span>
    </div>
  </div>`;
}

function ownerOptions(current = "") {
  return peopleOptions(current);
}

function triageRow(t) {
  return `<tr>
    <td class="triage-id">#${t.no}</td>
    <td><button class="triage-title" data-open-task="${t.id}">${escapeHtml(t.title)}</button></td>
    <td class="triage-bucket">${escapeHtml(t.bucket || t.zone || "")}</td>
    <td><select class="assign-select ${t.primaryOwner || t.owner ? "set" : ""}" data-edit="${t.id}:primaryOwner" ${isViewer() ? "disabled" : ""}>${ownerOptions(t.primaryOwner || t.owner || "")}</select></td>
    <td><select class="assign-select ${t.secondaryOwner ? "set" : ""}" data-edit="${t.id}:secondaryOwner" ${isViewer() ? "disabled" : ""}>${ownerOptions(t.secondaryOwner || "")}</select></td>
    <td><input class="assign-date ${t.deadline ? "set" : ""}" type="date" data-edit="${t.id}:deadline" value="${escapeHtml(t.deadline || "")}" ${isViewer() ? "disabled" : ""} /></td>
  </tr>`;
}

function operationsRow() {
  return `<div class="operations-row">
    <div class="operation-section">
      <div class="panel-head"><div><h2>Agency Load</h2><small>Active vs unowned work</small></div></div>
      ${agencyLoadRows(state.command?.agencyHealth || [])}
    </div>
    <div class="operation-section">
      <div class="panel-head"><div><h2>Review Bottleneck</h2><small>Items waiting for review</small></div></div>
      ${compactWorklist(state.command?.reviewBottlenecks || [])}
    </div>
    <div class="operation-section">
      <div class="panel-head"><div><h2>Ready To Publish</h2><small>Final-stage items</small></div></div>
      ${compactWorklist(state.command?.readyToPublish || [])}
    </div>
  </div>`;
}

function agencyLoadRows(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No agency data yet.</div>`;
  const max = Math.max(1, ...rows.map((r) => r.total));
  return `<div class="agency-load">${rows.slice(0, 4).map((r) => {
    const activePct = Math.round((r.active / max) * 100);
    const missingPct = Math.round((r.missingOwner / max) * 100);
    return `<button class="agency-load-row" data-agency-filter="${escapeHtml(r.agency === "Unassigned" ? "" : r.agency)}">
      <strong>${escapeHtml(r.agency)}</strong>
      <div class="agency-load-bar"><i class="blue" style="width:${activePct}%"></i><i class="amber" style="width:${missingPct}%"></i></div>
      <span>${r.active} active · ${r.missingOwner} no owner</span>
    </button>`;
  }).join("")}</div>`;
}

function productionHealth(h) {
  const tone = healthTone(h.score);
  return `<article class="health-panel ${tone}">
    <div class="health-ring" style="--score:${h.score * 3.6}deg"><strong>${h.score}</strong><span>/100</span></div>
    <div>
      <h2>Production Health</h2>
      <p>${h.score < 55 ? "Weak because ownership and expected dates are incomplete." : h.score < 80 ? "Improving, but cleanup still affects forecasting." : "Strong operating hygiene."}</p>
      <div class="health-metrics">
        ${coverageMetric("Primary", h.primary)}
        ${coverageMetric("Secondary", h.secondary)}
        ${coverageMetric("Expected date", h.deadline, "deadline")}
        ${coverageMetric("Admin", h.admin)}
      </div>
    </div>
  </article>`;
}

function coverageMetric(label, value, key = "") {
  return `<button class="coverage" data-health-filter="${key || label.toLowerCase()}">
    <span>${label}</span>
    <strong class="mono">${value}%</strong>
  </button>`;
}

function priorityQueue() {
  return `<article class="priority-panel">
    <div class="panel-head"><div><h2>Fix These First</h2><small>Ranked work that moves production forward today</small></div></div>
    ${priorityQueueList()}
  </article>`;
}

function priorityQueueList() {
  const ready = state.command?.readyToPublish || [];
  const review = state.command?.reviewBottlenecks || [];
  const missingPrimary = state.tasks.filter((t) => t.risk?.missingPrimary).slice(0, 3);
  const missingDeadline = state.tasks.filter((t) => t.risk?.missingDeadline && !t.risk?.missingPrimary).slice(0, 3);
  const items = [
    ...ready.slice(0, 2).map((t) => ({ task: t, action: "Publish", quick: "ready-to-publish", tone: "green" })),
    ...review.slice(0, 3).map((t) => ({ task: t, action: "Review", quick: "in-review", tone: "amber" })),
    ...missingPrimary.map((t) => ({ task: t, action: "Assign primary", quick: "needs-owner", tone: "red" })),
    ...missingDeadline.map((t) => ({ task: t, action: "Set expected date", quick: "needs-deadline", tone: "amber" })),
  ].slice(0, 7);
  return `<div class="priority-list">
      ${items.length ? items.map(({ task, action, quick, tone }) => `<button class="priority-item" data-open-task="${task.id}">
        <span>#${task.no}</span>
        <strong>${escapeHtml(task.title)}</strong>
        <em class="${tone}" data-quick="${quick}">${action}</em>
      </button>`).join("") : `<div class="empty compact-empty">No urgent work in the current filter.</div>`}
    </div>`;
}

function guidedFixPanel() {
  const options = state.options || {};
  return `<article class="fix-panel">
    <div class="panel-head"><div><h2>Guided Bulk Fix</h2><small>Choose once, apply to every matching task</small></div></div>
    <div class="fix-grid">
      ${fixAction("primaryOwner", "Assign primary", "needs-owner", "primaryOwner", "Owner name", options.primaryOwner)}
      ${fixAction("secondaryOwner", "Assign secondary", "needs-secondary", "secondaryOwner", "Backup owner", options.secondaryOwner)}
      ${fixAction("deadline", "Set expected dates", "needs-deadline", "deadline", "yyyy-mm-dd", [], "date")}
      ${fixAction("bucketAdmin", "Assign admin", "needs-admin", "bucketAdmin", "Admin name", options.bucketAdmin)}
    </div>
  </article>`;
}

function fixAction(type, title, quickFilter, field, placeholder, options = [], inputType = "text") {
  const listId = `${type}-suggestions`;
  return `<div class="fix-action">
    <div><strong>${title}</strong><span>${escapeHtml(labelForQuick(quickFilter))}</span></div>
    <input type="${inputType}" value="${escapeHtml(state.fix[type] || "")}" placeholder="${placeholder}" data-fix-field="${type}" ${options.length ? `list="${listId}"` : ""} />
    ${options.length ? `<datalist id="${listId}">${options.map((o) => `<option value="${escapeHtml(o)}"></option>`).join("")}</datalist>` : ""}
    <button class="btn ghost" data-guided-apply="${type}" data-guided-filter="${quickFilter}" data-guided-field="${field}" ${isViewer() ? "disabled" : ""}>Apply</button>
  </div>`;
}

function savedView(title, quickFilter, subtitle) {
  return `<button class="saved-view" data-quick="${quickFilter}">
    <strong>${title}</strong>
    <span>${subtitle}</span>
  </button>`;
}

function ownerScorecards(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No owner data yet.</div>`;
  const max = Math.max(1, ...rows.map((r) => r.total));
  return `<div class="scorecards">${rows.map((r) => `
    <button class="score-row" data-owner-filter="${escapeHtml(r.owner === "Unassigned" ? "" : r.owner)}">
      <div><strong>${escapeHtml(r.owner)}</strong><span>${r.total} total · ${r.active} active · ${r.complete} complete</span></div>
      <div class="healthbar">
        <i style="width:${(r.blocked / max) * 100}%;background:#d04444"></i>
        <i style="width:${(r.active / max) * 100}%;background:#2563eb"></i>
        <i style="width:${(r.complete / max) * 100}%;background:#12a36d"></i>
      </div>
      <em class="mono">${r.blocked} blocked</em>
    </button>
  `).join("")}</div>`;
}

function peoplePanel(ownerRows, adminRows) {
  const owners = ownerRows || [];
  const admins = adminRows || [];
  if (!owners.length && !admins.length) return `<div class="empty compact-empty">No people data yet.</div>`;
  return `<div class="people-list">
    ${owners.slice(0, 5).map((r) => `
      <button class="person-row" data-owner-filter="${escapeHtml(r.owner === "Unassigned" ? "" : r.owner)}">
        <div><strong>${escapeHtml(r.owner)}</strong><span>Primary owner</span></div>
        <em>${r.total} total</em>
        <em>${r.active} active</em>
        <em class="${r.blocked ? "red" : "green"}">${r.blocked} needs setup</em>
      </button>
    `).join("")}
    ${admins.slice(0, 5).map((r) => `
      <button class="person-row" data-admin-filter="${escapeHtml(r.admin === "Unassigned" ? "" : r.admin)}">
        <div><strong>${escapeHtml(r.admin)}</strong><span>Bucket admin</span></div>
        <em>${r.bucketCount} buckets</em>
        <em>${r.active} active</em>
        <em class="${r.needsAttention ? "amber" : "green"}">${r.needsAttention ? `${r.needsAttention} needs attention` : "Healthy"}</em>
      </button>
    `).join("")}
  </div>`;
}

function agencyHealth(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No agency data yet.</div>`;
  return `<div class="agency-grid">${rows.slice(0, 6).map((r) => `
    <button class="agency-tile" data-agency-filter="${escapeHtml(r.agency === "Unassigned" ? "" : r.agency)}">
      <strong>${escapeHtml(r.agency)}</strong>
      <span>${r.total} total</span>
      <div><b>${r.active}</b> active <b>${r.stuck}</b> stuck <b>${r.missingOwner}</b> no owner</div>
    </button>
  `).join("")}</div>`;
}

function bucketHealth(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No bucket data yet.</div>`;
  return `<div class="bucket-grid">${rows.slice(0, 6).map((r) => {
    const gaps = (r.missingPrimary || 0) + (r.missingSecondary || 0) + (r.missingDeadline || 0);
    return `<button class="bucket-tile" data-bucket-filter="${escapeHtml(r.bucket)}">
      <strong>${escapeHtml(r.bucket)}</strong>
      <span>Admin: ${escapeHtml(r.admin)}</span>
      <div class="bucket-metrics">
        <em>${r.total} total</em><em>${r.active} active</em><em>${gaps} gaps</em><em>${r.ready} ready</em>
      </div>
      <small>${r.missingPrimary} no primary · ${r.missingSecondary} no secondary · ${r.missingDeadline} no expected date</small>
    </button>`;
  }).join("")}</div>`;
}

function bucketHealthTable(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No bucket data yet.</div>`;
  const totalTasks = rows.reduce((sum, r) => sum + Number(r.total || 0), 0);
  const readyTasks = rows.reduce((sum, r) => sum + Number(r.ready || 0), 0);
  const missingDates = rows.reduce((sum, r) => sum + Number(r.missingDeadline || 0), 0);
  const activeTasks = rows.reduce((sum, r) => sum + Number(r.active || 0), 0);
  const max = Math.max(1, ...rows.map((r) => Number(r.total || 0)));
  const adminMap = rows.reduce((map, r) => {
    const admin = r.admin || "Unassigned";
    const current = map.get(admin) || { admin, buckets: 0, total: 0, active: 0, ready: 0, missingDeadline: 0 };
    current.buckets += 1;
    current.total += Number(r.total || 0);
    current.active += Number(r.active || 0);
    current.ready += Number(r.ready || 0);
    current.missingDeadline += Number(r.missingDeadline || 0);
    map.set(admin, current);
    return map;
  }, new Map());
  const adminRows = [...adminMap.values()].sort((a, b) => b.total - a.total);
  return `<div class="bucket-command">
    <div class="bucket-summary">
      ${bucketSummaryMetric("Buckets", rows.length, `${totalTasks} tasks`)}
      ${bucketSummaryMetric("Ready", readyTasks, "final-stage")}
      ${bucketSummaryMetric("Active", activeTasks, "in motion")}
      ${bucketSummaryMetric("Need dates", missingDates, "planning gap", "amber")}
    </div>
    <div class="bucket-admin-strip">
      ${adminRows.map((r) => `
        <button class="bucket-admin-card" data-admin-filter="${escapeHtml(r.admin === "Unassigned" ? "" : r.admin)}">
          <span>${escapeHtml(r.admin)}</span>
          <strong>${r.total}</strong>
          <small>${r.buckets} buckets · ${r.active} active · ${r.ready} ready</small>
        </button>
      `).join("")}
    </div>
    <div class="bucket-focus-list">
      ${rows.map((r) => bucketFocusRow(r, max)).join("")}
    </div>
  </div>`;
}

function bucketSummaryMetric(label, value, helper, tone = "") {
  return `<div class="bucket-summary-metric ${tone}">
    <span>${label}</span>
    <strong>${value}</strong>
    <small>${helper}</small>
  </div>`;
}

function bucketFocusRow(r, max) {
  const total = Number(r.total || 0);
  const ready = Number(r.ready || 0);
  const active = Number(r.active || 0);
  const missingDeadline = Number(r.missingDeadline || 0);
  const totalWidth = Math.max(4, Math.round((total / max) * 100));
  const readyWidth = total ? Math.round((ready / total) * totalWidth) : 0;
  const activeWidth = total ? Math.round((active / total) * totalWidth) : 0;
  const dateText = missingDeadline ? `${missingDeadline} need dates` : "Dates ready";
  return `<button class="bucket-focus-row" data-bucket-filter="${escapeHtml(r.bucket)}">
    <div class="bucket-focus-main">
      <strong>${escapeHtml(r.bucket)}</strong>
      <span>${escapeHtml(r.admin || "Unassigned")} · ${total} tasks</span>
    </div>
    <div class="bucket-focus-bar" aria-hidden="true">
      <i class="base" style="width:${totalWidth}%"></i>
      <i class="active" style="width:${activeWidth}%"></i>
      <i class="ready" style="width:${readyWidth}%"></i>
    </div>
    <div class="bucket-focus-meta">
      <em>${active} active</em>
      <em class="${ready ? "green" : ""}">${ready} ready</em>
      <em class="${missingDeadline ? "amber" : "green"}">${dateText}</em>
    </div>
  </button>`;
}

function adminHealth(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No admin data yet.</div>`;
  return `<div class="admin-list">${rows.slice(0, 7).map((r) => `
    <button class="admin-row" data-admin-filter="${escapeHtml(r.admin === "Unassigned" ? "" : r.admin)}">
      <strong>${escapeHtml(r.admin)}</strong>
      <span>${r.bucketCount} buckets · ${r.active} active</span>
      <em class="mono">${r.needsAttention} attention</em>
    </button>
  `).join("")}</div>`;
}

function compactWorklist(rows) {
  if (!rows.length) return `<div class="empty compact-empty">No tasks in this list.</div>`;
  return `<div class="worklist">${rows.slice(0, 7).map((t) => {
    const [label, tone] = riskLabel(t);
    return `<button class="workitem" data-open-task="${t.id}">
      <span class="mono">#${t.no}</span>
      <strong>${escapeHtml(t.title)}</strong>
      <em class="${tone}">${label}</em>
    </button>`;
  }).join("")}</div>`;
}

function simpleBar(rows, labelKey, valueKey, color = "#2563eb", limit = 8) {
  const data = (rows || []).slice(0, limit);
  const max = Math.max(1, ...data.map((r) => Number(r[valueKey]) || 0));
  if (!data.length) return `<div class="empty compact-empty">No data for this filter.</div>`;
  return `<div class="mini-list">${data.map((r) => {
    const v = Number(r[valueKey]) || 0;
    const pct = Math.round((v / max) * 100);
    return `<div class="mini-row"><div><div>${escapeHtml(r[labelKey])}</div><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div></div><strong class="mono">${v}</strong></div>`;
  }).join("")}</div>`;
}

function renderBoard() {
  const grouped = Object.fromEntries(STATUSES.map((s) => [s, []]));
  state.tasks.forEach((t) => (grouped[t.status] || grouped["Concept Stage"]).push(t));
  return `
    <section class="board premium-board">
      ${STATUSES.map((status) => `
        <div class="column" data-drop="${status}">
          <div class="column-head"><span class="dot" style="background:${STATUS_COLORS[status]}"></span><strong>${status}</strong><span class="count mono">${grouped[status].length}</span></div>
          <div class="cards">
            ${grouped[status].map(compactTaskCard).join("")}
            <button class="add-card" data-add-status="${status}" ${isViewer() ? "disabled" : ""}>${icon("plus")} Add task</button>
          </div>
        </div>
      `).join("")}
    </section>
  `;
}

function compactTaskCard(task) {
  const [label, tone] = riskLabel(task);
  return `
    <article class="task-card compact ${state.selectedTaskId === task.id ? "selected" : ""}" draggable="${!isViewer()}" data-drag-id="${task.id}" data-open-task="${task.id}">
      <div class="card-top"><span class="num mono">#${task.no}</span><span class="chip">${escapeHtml(task.zone || "No zone")}</span>${priorityChip(task.priority)}</div>
      <h3>${escapeHtml(task.title || "Untitled video")}</h3>
      <div class="compact-meta">
        ${statusPill(task.status)}
        <span>${escapeHtml(task.primaryOwner || task.owner || "No primary")}</span>
        <span>${escapeHtml(task.secondaryOwner || "No secondary")}</span>
        <span>${escapeHtml(task.agency || "No agency")}</span>
      </div>
      <div class="flagline"><span class="flag ${tone}">${label}</span><span>${task.risk?.stageAgeDays || 0}d in stage</span></div>
      <div class="quick-edit-row" data-no-open>
        <select class="edit micro" data-edit="${task.id}:status" ${isViewer() ? "disabled" : ""}>${STATUSES.map((s) => `<option value="${s}" ${task.status === s ? "selected" : ""}>${s}</option>`).join("")}</select>
        <input class="edit micro" type="date" data-edit="${task.id}:deadline" value="${escapeHtml(task.deadline || "")}" ${isViewer() ? "disabled" : ""} />
      </div>
    </article>
  `;
}

function renderTable() {
  if (!state.tasks.length) return `<div class="empty">No tasks match these filters.</div>`;
  return `
    ${renderBulkbar()}
    <div class="table-wrap premium-table">
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" data-select-all ${state.selectedIds.size === state.tasks.length ? "checked" : ""} /></th>
            <th>#</th><th class="sticky-title">Title</th><th>Risk</th><th>Admin</th><th>Primary</th><th>Secondary</th><th>Status</th><th>Priority</th><th>Expected date</th><th>Agency</th><th>Bucket</th><th></th>
          </tr>
        </thead>
        <tbody>
          ${state.tasks.map((t) => tableRow(t)).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderBulkbar() {
  const disabled = isViewer() || state.selectedIds.size === 0;
  return `<section class="bulkbar">
    <strong>${state.selectedIds.size} selected</strong>
    <input placeholder="Admin" data-bulk="bucketAdmin" value="${escapeHtml(state.bulk.bucketAdmin || "")}" ${disabled ? "disabled" : ""} />
    <input placeholder="Primary" data-bulk="primaryOwner" value="${escapeHtml(state.bulk.primaryOwner || "")}" ${disabled ? "disabled" : ""} />
    <input placeholder="Secondary" data-bulk="secondaryOwner" value="${escapeHtml(state.bulk.secondaryOwner || "")}" ${disabled ? "disabled" : ""} />
    <input placeholder="Agency" data-bulk="agency" value="${escapeHtml(state.bulk.agency)}" ${disabled ? "disabled" : ""} />
    <input type="date" data-bulk="deadline" value="${escapeHtml(state.bulk.deadline)}" ${disabled ? "disabled" : ""} />
    <select data-bulk="status" ${disabled ? "disabled" : ""}><option value="">Status</option>${STATUSES.map((s) => `<option value="${s}" ${state.bulk.status === s ? "selected" : ""}>${s}</option>`).join("")}</select>
    <select data-bulk="priority" ${disabled ? "disabled" : ""}><option value="">Priority</option>${PRIORITIES.map((p) => `<option value="${p}" ${state.bulk.priority === p ? "selected" : ""}>${p}</option>`).join("")}</select>
    <button class="btn" data-bulk-apply ${disabled ? "disabled" : ""}>Apply bulk edit</button>
  </section>`;
}

function tableRow(t) {
  const [label, tone] = riskLabel(t);
  return `
    <tr class="${state.selectedTaskId === t.id ? "selected-row" : ""}">
      <td><input type="checkbox" data-select-row="${t.id}" ${state.selectedIds.has(t.id) ? "checked" : ""} /></td>
      <td class="mono">${t.no}</td>
      <td class="td-title sticky-title"><button data-open-task="${t.id}">${escapeHtml(t.title)}</button></td>
      <td><span class="flag ${tone}">${label}</span></td>
      <td><input class="edit table-edit" data-edit="${t.id}:bucketAdmin" value="${escapeHtml(t.bucketAdmin)}" placeholder="Admin" ${isViewer() ? "disabled" : ""} /></td>
      <td><input class="edit table-edit" data-edit="${t.id}:primaryOwner" value="${escapeHtml(t.primaryOwner || t.owner)}" placeholder="Primary" ${isViewer() ? "disabled" : ""} /></td>
      <td><input class="edit table-edit" data-edit="${t.id}:secondaryOwner" value="${escapeHtml(t.secondaryOwner)}" placeholder="Secondary" ${isViewer() ? "disabled" : ""} /></td>
      <td><select class="edit table-edit" data-edit="${t.id}:status" ${isViewer() ? "disabled" : ""}>${STATUSES.map((s) => `<option value="${s}" ${t.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></td>
      <td><select class="edit table-edit" data-edit="${t.id}:priority" ${isViewer() ? "disabled" : ""}>${PRIORITIES.map((p) => `<option value="${p}" ${t.priority === p ? "selected" : ""}>${p}</option>`).join("")}</select></td>
      <td><input class="edit table-edit mono" type="date" data-edit="${t.id}:deadline" value="${escapeHtml(t.deadline)}" ${isViewer() ? "disabled" : ""} /></td>
      <td><input class="edit table-edit" data-edit="${t.id}:agency" value="${escapeHtml(t.agency)}" ${isViewer() ? "disabled" : ""} /></td>
      <td>${escapeHtml(t.bucket || t.zone)}</td>
      <td><div class="row-actions"><button class="btn ghost icon" data-activity="${t.id}">${icon("history")}</button><button class="btn ghost icon" data-duplicate="${t.id}" ${isViewer() ? "disabled" : ""}>${icon("copy")}</button><button class="btn ghost icon" data-delete="${t.id}" ${!isAdmin() ? "disabled" : ""}>${icon("trash")}</button></div></td>
    </tr>
  `;
}

function renderInspector() {
  const t = selectedTask();
  if (!t) return "";
  return `<aside class="inspector">
    <div class="inspector-head">
      <div><span class="mono">#${t.no}</span><h2>${escapeHtml(t.title)}</h2></div>
      <button class="btn ghost icon" data-close-inspector>${icon("close")}</button>
    </div>
    <div class="inspector-flags">${riskBadges(t)}</div>
    <div class="inspector-grid">
      ${field(t, "Title", "title", "textarea", [], "wide")}
      ${field(t, "Bucket", "bucket")}
      ${field(t, "Status", "status", "select", STATUSES)}
      ${field(t, "Priority", "priority", "select", PRIORITIES)}
      ${!isAgencyUser() ? personField(t, "Bucket Admin", "bucketAdmin") : ""}
      ${personField(t, "Primary Owner", "primaryOwner")}
      ${personField(t, "Secondary Owner", "secondaryOwner")}
      ${!isAgencyUser() ? personField(t, "Reviewer", "reviewer") : ""}
      ${field(t, "Assignment Status", "assignmentStatus", "select", ["assigned", "accepted", "blocked"])}
      ${field(t, "Planned Start", "plannedStart", "date")}
      ${field(t, "Expected Completion Date", "deadline", "date")}
      ${field(t, "Actual Completion", "actualCompletionDate", "date")}
      ${field(t, "Publish Date", "publishDate", "date")}
      ${field(t, "Agency", "agency", "select", state.options.agency || [])}
      ${field(t, "Brand", "brand")}
      ${field(t, "Zone", "zone")}
      ${field(t, "Length", "length")}
      ${!isAgencyUser() ? field(t, "Delay Reason", "delayReason", "textarea", [], "wide") : ""}
      ${!isAgencyUser() ? field(t, "Hook", "hook", "textarea", [], "wide") : ""}
      ${!isAgencyUser() ? field(t, "Notes", "notes", "textarea", [], "wide") : ""}
    </div>
    ${renderTaskCollaboration(t)}
    <div class="inspector-actions">
      <button class="btn ghost" data-duplicate="${t.id}" ${isViewer() ? "disabled" : ""}>${icon("copy")} Duplicate</button>
      <button class="btn ghost" data-activity="${t.id}">${icon("history")} History</button>
      <button class="btn danger" data-delete="${t.id}" ${!isAdmin() ? "disabled" : ""}>${icon("trash")} Delete</button>
    </div>
  </aside>`;
}

function riskBadges(t) {
  const r = t.risk || {};
  const badges = [];
  if (r.missingPrimary) badges.push(["No primary", "red"]);
  if (r.missingSecondary) badges.push(["No secondary", "amber"]);
  if (r.missingAdmin) badges.push(["No admin", "red"]);
  if (r.missingDeadline) badges.push(["No expected date", "amber"]);
  if (r.stuck) badges.push([`Stuck ${r.stageAgeDays}d`, "red"]);
  if (r.readyToPublish) badges.push(["Ready to publish", "green"]);
  if (r.overdue) badges.push(["Overdue", "red"]);
  if (!badges.length) badges.push(["Healthy", "green"]);
  return badges.map(([label, tone]) => `<span class="flag ${tone}">${label}</span>`).join("");
}

function field(task, label, key, type = "text", options = [], cls = "") {
  let control = "";
  if (type === "select") {
    control = `<select class="edit" data-edit="${task.id}:${key}" ${isViewer() ? "disabled" : ""}>${options.map((o) => `<option value="${escapeHtml(o)}" ${task[key] === o ? "selected" : ""}>${escapeHtml(o)}</option>`).join("")}</select>`;
  } else if (type === "textarea") {
    control = `<textarea class="edit" data-edit="${task.id}:${key}" ${isViewer() ? "disabled" : ""}>${escapeHtml(task[key] || "")}</textarea>`;
  } else {
    control = `<input class="edit" type="${type}" data-edit="${task.id}:${key}" value="${escapeHtml(task[key] || "")}" ${isViewer() ? "disabled" : ""} />`;
  }
  return `<label class="field ${cls}">${label}${control}</label>`;
}

function personField(task, label, key) {
  return `<label class="field">${label}<select class="edit" data-edit="${task.id}:${key}" ${isViewer() || isAgencyUser() ? "disabled" : ""}>${peopleOptions(task[key] || "")}</select></label>`;
}

function renderReports() {
  const exportUrl = `/api/tasks/export.csv?${params()}`;
  return `
    <section class="reports">
      <article class="panel"><div class="panel-head"><div><h2>Export Filtered Tasks</h2><small>Downloads the same command-filtered worklist.</small></div></div><a class="btn" href="${exportUrl}">Download CSV</a></article>
      <article class="panel"><div class="panel-head"><div><h2>Import CSV</h2><small>Super-admin only bulk create/update. Existing IDs are updated.</small></div></div><div class="dropzone"><input type="file" accept=".csv,text/csv" data-import ${!isAdmin() ? "disabled" : ""} /><button class="btn ghost" data-reset ${!isAdmin() ? "disabled" : ""}>${icon("reset")} Reset to seed tasks</button>${!isAdmin() ? '<span class="viewer-lock">Super admin access required for import/reset.</span>' : ""}</div></article>
      <article class="panel wide"><div class="panel-head"><div><h2>Activity Timeline</h2><small>Status, owner, expected date, priority, and publish events.</small></div></div>${renderActivity()}</article>
    </section>`;
}

function renderActivity() {
  if (!state.activityTask) return `<div class="empty compact-empty">Select history from any row or card.</div>`;
  if (!state.activity.length) return `<div class="empty compact-empty">No history recorded yet.</div>`;
  return `<div class="activity">${state.activity.map((a) => `<div class="activity-item"><strong>${escapeHtml(a.action)} <span class="mono">by ${escapeHtml(a.actorRole)}</span></strong><span>${escapeHtml(a.changedAt)} | task ${escapeHtml(a.taskId)}</span></div>`).join("")}</div>`;
}

function renderMyWork() {
  const tasks = state.myWork.tasks || [];
  return `<section class="workspace-grid">
    <article class="panel wide"><div class="panel-head"><div><h2>My Work</h2><small>One-click updates for work assigned to you</small></div></div>
      ${renderDigestStrip()}
      ${tasks.length ? `<div class="mywork-list large">${tasks.slice(0, 80).map(myWorkRow).join("")}</div>` : `<div class="empty compact-empty">No assigned work for you yet. When someone assigns you as primary, secondary, reviewer, or bucket admin, it will appear here.</div>`}
    </article>
    <article class="panel"><div class="panel-head"><div><h2>Notifications</h2><small>Mentions, assignments, approvals</small></div></div>${renderNotifications()}</article>
  </section>`;
}

function renderDigestStrip() {
  const s = state.digest?.summary || {};
  return `<div class="digest-strip">
    <button data-quick="needs-deadline"><strong>${s.blocked || 0}</strong><span>blocked/stuck</span></button>
    <button data-quick="in-review"><strong>${s.waitingForReview || 0}</strong><span>waiting review</span></button>
    <button data-quick="ready-to-publish"><strong>${s.readyToPublish || 0}</strong><span>ready to publish</span></button>
    <button data-filter-due="soon"><strong>${(s.dueToday || 0) + (s.dueSoon || 0)}</strong><span>due soon</span></button>
  </div>`;
}

function myWorkRow(t) {
  const [label, tone] = riskLabel(t);
  return `<div class="mywork-row">
    <button class="mywork-main" data-open-task="${t.id}">
      <span class="mono">#${t.no}</span>
      <strong>${escapeHtml(t.title)}</strong>
      <em class="${tone}">${label}</em>
    </button>
    <div class="mywork-actions" data-no-open>
      <select data-quick-update="${t.id}:status" ${isViewer() ? "disabled" : ""}>${STATUSES.map((s) => `<option value="${s}" ${t.status === s ? "selected" : ""}>${s}</option>`).join("")}</select>
      <input type="date" data-quick-update="${t.id}:deadline" value="${escapeHtml(t.deadline || "")}" ${isViewer() ? "disabled" : ""} />
      <button class="btn ghost" data-open-task="${t.id}">Details</button>
    </div>
  </div>`;
}

function renderNotifications() {
  const rows = state.notifications || [];
  if (!rows.length) return `<div class="empty compact-empty">No notifications.</div>`;
  return `<div class="notification-list">${rows.map((n) => `<button class="notification ${n.isRead ? "read" : ""}" data-read-notification="${n.id}" ${n.taskId ? `data-open-task="${escapeHtml(n.taskId)}"` : ""}><strong>${escapeHtml(n.title)}</strong><span>${escapeHtml(n.body || "")}</span><em>${escapeHtml(n.createdAt)}</em></button>`).join("")}</div>`;
}

function renderPlanning() {
  const p = state.planning || { calendar: [], missingDates: [], timeline: [] };
  return `<section class="workspace-grid">
    <article class="panel wide"><div class="panel-head"><div><h2>Calendar Plan</h2><small>Planned, expected, and publish dates</small></div></div>
      ${p.calendar.length ? `<div class="planning-list">${p.calendar.map(planningRow).join("")}</div>` : `<div class="empty compact-empty">Add expected dates to populate the calendar.</div>`}
    </article>
    <article class="panel"><div class="panel-head"><div><h2>Date Gaps</h2><small>Highest priority planning cleanup</small></div></div>
      <div class="worklist">${(p.missingDates || []).slice(0, 20).map((t) => `<button class="workitem" data-open-task="${t.id}"><span class="mono">#${t.no}</span><strong>${escapeHtml(t.title)}</strong><em>Set date</em></button>`).join("")}</div>
    </article>
    <article class="panel wide"><div class="panel-head"><div><h2>Timeline</h2><small>Bucket-wise production schedule</small></div></div>${renderTimeline(p.timeline || [])}</article>
  </section>`;
}

function planningRow(t) {
  const date = t.deadline || t.publishDate || t.plannedStart || "No date";
  return `<button class="planning-row" data-open-task="${t.id}"><span class="mono">${escapeHtml(date)}</span><strong>${escapeHtml(t.title)}</strong><em>${escapeHtml(t.status)}</em><small>${escapeHtml(t.bucket || t.zone || "")}</small></button>`;
}

function renderTimeline(tasks) {
  if (!tasks.length) return `<div class="empty compact-empty">Timeline appears once planning dates exist.</div>`;
  return `<div class="timeline-list">${tasks.slice(0, 60).map((t) => `<button class="timeline-row" data-open-task="${t.id}"><strong>${escapeHtml(t.bucket || "Unassigned")}</strong><span>${escapeHtml(t.title)}</span><em>${escapeHtml(t.plannedStart || "start ?")} → ${escapeHtml(t.deadline || "due ?")} → ${escapeHtml(t.publishDate || "publish ?")}</em></button>`).join("")}</div>`;
}

function renderAdmin() {
  if (!isAdmin()) return `<div class="error">Super admin access required.</div>`;
  return `<section class="workspace-grid">
    <article class="panel wide"><div class="panel-head"><div><h2>User Management</h2><small>Aniket is the single super admin. Owner names are protected from duplicates.</small></div></div>${renderUsers()}</article>
    <article class="panel"><div class="panel-head"><div><h2>Create User</h2><small>Temporary password defaults to Taskmaster@2026</small></div></div>
      <div class="admin-form">
        <input placeholder="User ID" data-new-user="username" />
        <input placeholder="Display name" data-new-user="displayName" />
        <input placeholder="Email" data-new-user="email" />
        <input placeholder="Phone" data-new-user="phone" />
        <input placeholder="Team / department" data-new-user="team" />
        <input placeholder="Agency name" data-new-user="agencyName" />
        <select data-new-user="role">${["editor", "admin", "reviewer", "agency", "viewer"].map((r) => `<option value="${r}">${r}</option>`).join("")}</select>
        <select data-new-user="accessType"><option value="bucket">Bucket scope</option><option value="agency">Agency scope</option></select>
        <input placeholder="Scope value" data-new-user="accessValue" list="scope-values" />
        <datalist id="scope-values">${[...(state.options.bucket || []), ...(state.options.agency || [])].map((v) => `<option value="${escapeHtml(v)}"></option>`).join("")}</datalist>
        <label class="checkbox-line"><input type="checkbox" data-new-user="isAgencyUser" /> Agency user</label>
        <button class="btn" data-create-user>Create user</button>
      </div>
    </article>
    <article class="panel wide"><div class="panel-head"><div><h2>Access Matrix</h2><small>What each user can see and do</small></div></div>${renderAccessMatrix()}</article>
    <article class="panel"><div class="panel-head"><div><h2>Deployment Readiness</h2><small>Hosted rollout checklist</small></div></div>${renderDeployment()}</article>
    <article class="panel wide"><div class="panel-head"><div><h2>Audit Trail</h2><small>Login, user, import, reset, and destructive events</small></div></div>${renderAudit()}</article>
  </section>`;
}

function renderUsers() {
  return `<div class="user-table">${(state.users || []).map((u) => `<div class="user-row">
    <strong>${escapeHtml(u.displayName)}</strong><span>${escapeHtml(u.username)} · ${escapeHtml(u.email || "no email")}</span><em>${escapeHtml(u.role)}</em><small>${u.isActive ? "Active" : "Inactive"}${u.agencyName ? ` · ${escapeHtml(u.agencyName)}` : ""}</small>
    <button class="btn ghost" data-reset-password="${u.id}" ${u.username === "aniket" ? "" : ""}>Reset password</button>
  </div>`).join("")}</div>`;
}

function renderAccessMatrix() {
  const rows = state.accessMatrix || [];
  if (!rows.length) return `<div class="empty compact-empty">No access matrix loaded.</div>`;
  return `<div class="access-matrix">${rows.map((r) => `<div class="access-row">
    <div><strong>${escapeHtml(r.user.displayName)}</strong><span>${escapeHtml(r.user.role)} · ${r.visibleTasks} visible tasks</span></div>
    <em>${r.canEdit ? "Edit" : "Read only"}</em>
    <em>${r.canReview ? "Review" : "No review"}</em>
    <em>${r.canImport ? "Import/delete" : "No destructive access"}</em>
    <small>${(r.scope || []).map((s) => `${escapeHtml(s.accessType)}: ${escapeHtml(s.accessValue)}`).join(" · ")}</small>
  </div>`).join("")}</div>`;
}

function renderDeployment() {
  const d = state.deployment;
  if (!d) return `<div class="empty compact-empty">Deployment status is available to super admin.</div>`;
  return `<div class="deploy-list">
    ${(d.checks || []).map((c) => `<div class="deploy-check ${c.ok ? "ok" : "warn"}"><strong>${escapeHtml(c.label)}</strong><span>${c.ok ? "Ready" : "Needs setup"}</span></div>`).join("")}
    <div class="deploy-meta"><span>App URL</span><strong>${escapeHtml(d.appUrl)}</strong></div>
    <div class="deploy-meta"><span>Backup script</span><strong>${escapeHtml(d.backupScript)}</strong></div>
  </div>`;
}

function renderAudit() {
  const rows = state.auditEvents || [];
  if (!rows.length) return `<div class="empty compact-empty">Audit events will appear after logins, imports, user changes, and task operations.</div>`;
  return `<div class="audit-list">${rows.slice(0, 60).map((e) => `<div class="audit-row"><strong>${escapeHtml(e.action)}</strong><span>${escapeHtml(e.actorName || "System")} · ${escapeHtml(e.subjectType)} ${escapeHtml(e.subjectId)}</span><em>${escapeHtml(e.createdAt)}</em></div>`).join("")}</div>`;
}

function renderTaskCollaboration(t) {
  const data = state.collaboration[t.id] || { comments: [], assets: [], approvals: [] };
  return `<div class="collab">
    <section><h3>Checklist</h3>${renderChecklist(t.id, data.checklist || [])}</section>
    <section><h3>Review</h3>
      <div class="review-actions">
        <input placeholder="Review note" data-form="reviewNote" value="${escapeHtml(state.forms.reviewNote)}" />
        <button class="btn ghost" data-review="changes_requested" data-task-action="${t.id}" ${isViewer() ? "disabled" : ""}>Changes</button>
        <button class="btn ghost" data-review="approved" data-task-action="${t.id}" ${isViewer() ? "disabled" : ""}>Approve</button>
        <button class="btn ghost" data-review="published" data-task-action="${t.id}" ${isViewer() ? "disabled" : ""}>Publish</button>
      </div>
      <div class="activity compact">${data.approvals.map((a) => `<div class="activity-item"><strong>${escapeHtml(a.decision)} by ${escapeHtml(a.displayName)}</strong><span>${escapeHtml(a.note || "")}</span></div>`).join("") || "No review events yet."}</div>
    </section>
    <section><h3>Comments</h3>
      <div class="comment-box"><textarea data-form="comment" placeholder="Add a comment..." ${isViewer() ? "disabled" : ""}>${escapeHtml(state.forms.comment)}</textarea><button class="btn ghost" data-add-comment="${t.id}" ${isViewer() ? "disabled" : ""}>Comment</button></div>
      <div class="activity compact">${data.comments.map((c) => `<div class="activity-item"><strong>${escapeHtml(c.displayName)}</strong><span>${escapeHtml(c.body)} · ${escapeHtml(c.createdAt)}</span></div>`).join("") || "No comments yet."}</div>
    </section>
    <section><h3>Assets</h3>
      <div class="asset-box"><select data-form="assetType">${(state.options.assetTypes || ["Script", "Raw Footage", "Edit Link", "Final Video", "Thumbnail", "Published URL", "Reference", "Other"]).map((a) => `<option value="${escapeHtml(a)}" ${state.forms.assetType === a ? "selected" : ""}>${escapeHtml(a)}</option>`).join("")}</select><input data-form="assetLabel" value="${escapeHtml(state.forms.assetLabel)}" placeholder="Label" /><input data-form="assetUrl" value="${escapeHtml(state.forms.assetUrl)}" placeholder="URL" /><button class="btn ghost" data-add-asset="${t.id}" ${isViewer() ? "disabled" : ""}>Add asset</button></div>
      <div class="asset-list">${data.assets.map((a) => `<a href="${escapeHtml(a.url)}" target="_blank" rel="noreferrer"><strong>${escapeHtml(a.label)}</strong><span>${escapeHtml(a.assetType)} · ${escapeHtml(a.displayName)}</span></a>`).join("") || "No assets yet."}</div>
    </section>
    <section><h3>History</h3><div class="activity compact">${(data.activity || []).map((a) => `<div class="activity-item"><strong>${escapeHtml(a.action)}</strong><span>${escapeHtml(a.actorRole)} · ${escapeHtml(a.changedAt)}</span></div>`).join("") || "No history yet."}</div></section>
  </div>`;
}

function renderChecklist(taskId, rows) {
  const byStep = new Map((rows || []).map((r) => [r.step, r]));
  const steps = state.options.checklistSteps || ["script", "shoot/design", "edit", "review", "publish"];
  return `<div class="checklist">${steps.map((step) => {
    const row = byStep.get(step) || { isDone: 0 };
    return `<label class="check-step"><input type="checkbox" data-checklist="${taskId}:${escapeHtml(step)}" ${row.isDone ? "checked" : ""} ${isViewer() ? "disabled" : ""} /><span>${escapeHtml(step)}</span><em>${row.updatedBy ? escapeHtml(row.updatedBy) : ""}</em></label>`;
  }).join("")}</div>`;
}

function renderMain() {
  if (state.loading) return `<div class="loading">Loading production command center...</div>`;
  if (state.error) return `<div class="error">${escapeHtml(state.error)}</div>`;
  if (state.view === "dashboard") return renderDashboard();
  if (state.view === "mywork") return renderMyWork();
  if (state.view === "planning") return renderPlanning();
  if (state.view === "board") return renderBoard();
  if (state.view === "table") return renderTable();
  if (state.view === "admin") return renderAdmin();
  return renderReports();
}

function render() {
  if (!state.currentUser) {
    app.innerHTML = renderLogin();
    return;
  }
  app.innerHTML = `
    <div class="app ${selectedTask() ? "has-inspector" : ""}">
      ${renderTopbar()}
      <main class="shell">
        ${renderPasswordNotice()}
        ${state.view !== "reports" ? renderFilters() : ""}
        ${renderMain()}
      </main>
      ${renderInspector()}
      ${state.toast ? `<div class="toast">${escapeHtml(state.toast)}</div>` : ""}
    </div>`;
}

async function patchTask(id, field, value) {
  const task = taskById(id);
  if (!task || task[field] === value) return;
  const previous = task[field];
  task[field] = value;
  render();
  try {
    await api(`/api/tasks/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ [field]: value }) });
    toast("Saved");
    await loadAll();
  } catch (err) {
    task[field] = previous;
    state.error = err.message;
    render();
  }
}

async function createTask(status = "Concept Stage") {
  try {
    const body = { brand: state.filters.brand || "Astral Pipes", zone: state.filters.zone || "NON-AI Product Video", title: "Untitled video", status, priority: "Medium", agency: state.filters.agency || "", owner: state.filters.owner || "", deadline: "" };
    body.bucket = state.filters.bucket || body.zone;
    body.bucketAdmin = state.filters.bucketAdmin || "";
    body.primaryOwner = state.filters.primaryOwner || body.owner || "";
    body.secondaryOwner = state.filters.secondaryOwner || "";
    body.reviewer = state.filters.reviewer || "";
    const res = await api("/api/tasks", { method: "POST", body: JSON.stringify(body) });
    state.selectedTaskId = res.task.id;
    toast("Task created");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function duplicateTask(id) {
  const source = taskById(id);
  if (!source) return;
  const copy = { ...source, risk: undefined, title: `${source.title} (copy)`, id: undefined, no: undefined, createdAt: undefined, updatedAt: undefined, completedAt: undefined, lastStageChangedAt: undefined };
  try {
    const res = await api("/api/tasks", { method: "POST", body: JSON.stringify(copy) });
    state.selectedTaskId = res.task.id;
    toast("Task duplicated");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function deleteTask(id) {
  if (!confirm("Delete this task? This requires Super Admin access.")) return;
  try {
    await api(`/api/tasks/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (state.selectedTaskId === id) state.selectedTaskId = "";
    state.selectedIds.delete(id);
    toast("Task deleted");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function bulkApply() {
  const changes = {};
  Object.entries(state.bulk).forEach(([k, v]) => { if (v) changes[k] = v; });
  if (!Object.keys(changes).length || !state.selectedIds.size) return;
  try {
    const res = await api("/api/tasks/bulk", { method: "PATCH", body: JSON.stringify({ ids: [...state.selectedIds], changes }) });
    state.bulk = { bucketAdmin: "", primaryOwner: "", secondaryOwner: "", deadline: "", agency: "", status: "", priority: "" };
    state.selectedIds.clear();
    toast(`Updated ${res.updated} tasks`);
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function guidedApply(type, quickFilter, field) {
  const value = state.fix[type];
  if (!value || isViewer()) {
    toast(isViewer() ? "Viewer mode cannot edit" : "Enter a value first");
    return;
  }
  try {
    const res = await api(`/api/tasks?${queryWithQuickFilter(quickFilter)}`);
    const ids = (res.tasks || []).map((t) => t.id);
    if (!ids.length) {
      toast("No tasks matched that guided fix");
      return;
    }
    const bulk = await api("/api/tasks/bulk", { method: "PATCH", body: JSON.stringify({ ids, changes: { [field]: value } }) });
    state.fix[type] = "";
    toast(`Updated ${bulk.updated} tasks`);
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function applySameOwnerToVisible() {
  if (isViewer()) return;
  const visible = triageCandidates().slice(state.triageOffset, state.triageOffset + 5);
  if (!visible.length) return;
  const select = document.querySelector('.triage-table select[data-edit$=":primaryOwner"]');
  const owner = select?.value || visible.find((t) => t.primaryOwner || t.owner)?.primaryOwner || visible.find((t) => t.primaryOwner || t.owner)?.owner || "";
  if (!owner) {
    toast("Set the first primary owner first");
    return;
  }
  try {
    const res = await api("/api/tasks/bulk", { method: "PATCH", body: JSON.stringify({ ids: visible.map((t) => t.id), changes: { primaryOwner: owner } }) });
    toast(`Assigned ${owner} to ${res.updated} tasks`);
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function loadActivity(id) {
  state.activityTask = id;
  state.view = "reports";
  try {
    const res = await api(`/api/activity?taskId=${encodeURIComponent(id)}`);
    state.activity = res.activity;
  } catch (err) {
    state.error = err.message;
  }
  render();
}

async function loadCollaboration(id) {
  if (!id) return;
  try {
    state.collaboration[id] = await api(`/api/tasks/${encodeURIComponent(id)}/collaboration`);
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function addComment(id) {
  const body = state.forms.comment.trim();
  if (!body) return;
  try {
    state.collaboration[id] = await api(`/api/tasks/${encodeURIComponent(id)}/comments`, { method: "POST", body: JSON.stringify({ body }) });
    state.forms.comment = "";
    toast("Comment added");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function addAsset(id) {
  const payload = { assetType: state.forms.assetType, label: state.forms.assetLabel || state.forms.assetType, url: state.forms.assetUrl };
  if (!payload.url) return;
  try {
    state.collaboration[id] = await api(`/api/tasks/${encodeURIComponent(id)}/assets`, { method: "POST", body: JSON.stringify(payload) });
    state.forms.assetLabel = "";
    state.forms.assetUrl = "";
    toast("Asset added");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function reviewTask(id, decision) {
  try {
    const res = await api(`/api/tasks/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify({ decision, note: state.forms.reviewNote }) });
    state.forms.reviewNote = "";
    state.collaboration[id] = { comments: res.comments || [], assets: res.assets || [], approvals: res.approvals || [] };
    toast("Review updated");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function updateChecklist(id, step, isDone) {
  try {
    state.collaboration[id] = await api(`/api/tasks/${encodeURIComponent(id)}/checklist`, { method: "POST", body: JSON.stringify({ step, isDone }) });
    toast("Checklist updated");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function markNotification(id) {
  try {
    await api(`/api/notifications/${encodeURIComponent(id)}`, { method: "PATCH", body: "{}" });
    state.notifications = state.notifications.map((n) => String(n.id) === String(id) ? { ...n, isRead: 1 } : n);
  } catch (err) {
    state.error = err.message;
  }
}

async function createUser() {
  try {
    const payload = { ...state.newUser };
    if (payload.accessType && payload.accessValue) payload.access = [{ accessType: payload.accessType, accessValue: payload.accessValue }];
    const res = await api("/api/users", { method: "POST", body: JSON.stringify(payload) });
    state.users = res.users;
    state.newUser = { username: "", displayName: "", role: "editor", email: "", phone: "", team: "", agencyName: "", isAgencyUser: false, accessType: "bucket", accessValue: "" };
    toast("User created");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function resetUserPassword(id) {
  try {
    const res = await api(`/api/users/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ password: "Taskmaster@2026" }) });
    state.users = res.users;
    toast("Password reset to Taskmaster@2026");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function importCsv(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const res = await fetch("/api/tasks/import", { method: "POST", headers: { "Content-Type": "text/csv" }, body: text });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Import failed");
    toast(`Imported ${data.imported} rows`);
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function login(username, password) {
  state.error = "";
  try {
    const res = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    state.currentUser = res.user;
    state.role = res.user.role;
    state.login = { username: "", password: "" };
    toast(`Welcome, ${res.user.displayName}`);
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function changePassword(currentPassword, newPassword, confirmPassword) {
  if (newPassword !== confirmPassword) {
    state.error = "New passwords do not match.";
    render();
    return;
  }
  try {
    const res = await api("/api/me/password", { method: "PATCH", body: JSON.stringify({ currentPassword, newPassword }) });
    state.currentUser = res.user;
    state.role = res.user.role;
    state.password = { currentPassword: "", newPassword: "", confirmPassword: "" };
    toast("Password updated");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST", body: "{}" });
  } catch (err) {
    // Still clear local state if the session has already expired.
  }
  state.currentUser = null;
  state.role = "viewer";
  state.tasks = [];
  state.analytics = null;
  state.command = null;
  state.selectedTaskId = "";
  state.selectedIds.clear();
  render();
}

async function resetSeed() {
  if (!confirm("Reset to the seed task list? Current edits will be removed.")) return;
  try {
    await api("/api/tasks/reset", { method: "POST", body: "{}" });
    state.selectedTaskId = "";
    state.selectedIds.clear();
    toast("Seed data restored");
    await loadAll();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

let filterTimer = null;
document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-login-form]");
  const passwordForm = event.target.closest("[data-password-form]");
  if (form) {
    event.preventDefault();
    const data = new FormData(form);
    const username = String(data.get("username") || "").trim();
    const password = String(data.get("password") || "");
    state.login = { username, password };
    login(username, password);
    return;
  }
  if (passwordForm) {
    event.preventDefault();
    const data = new FormData(passwordForm);
    const currentPassword = String(data.get("currentPassword") || "");
    const newPassword = String(data.get("newPassword") || "");
    const confirmPassword = String(data.get("confirmPassword") || "");
    state.password = { currentPassword, newPassword, confirmPassword };
    changePassword(currentPassword, newPassword, confirmPassword);
  }
});

document.addEventListener("input", (event) => {
  const filter = event.target.closest("[data-filter]");
  if (filter) {
    state.filters[filter.dataset.filter] = filter.value;
    clearTimeout(filterTimer);
    filterTimer = setTimeout(loadAll, filter.dataset.filter === "q" ? 250 : 0);
  }
  const bulk = event.target.closest("[data-bulk]");
  if (bulk) state.bulk[bulk.dataset.bulk] = bulk.value;
  const fix = event.target.closest("[data-fix-field]");
  if (fix) state.fix[fix.dataset.fixField] = fix.value;
  const formField = event.target.closest("[data-form]");
  if (formField) state.forms[formField.dataset.form] = formField.value;
  const newUser = event.target.closest("[data-new-user]");
  if (newUser) state.newUser[newUser.dataset.newUser] = newUser.type === "checkbox" ? newUser.checked : newUser.value;
  const loginInput = event.target.closest("[data-login-form] input");
  if (loginInput) state.login[loginInput.name] = loginInput.value;
  const passwordInput = event.target.closest("[data-password-form] input");
  if (passwordInput) state.password[passwordInput.name] = passwordInput.value;
});

document.addEventListener("change", (event) => {
  const role = event.target.closest("[data-role]");
  if (role) setRole(role.value);
  const edit = event.target.closest("[data-edit]");
  if (edit) {
    const [id, field] = edit.dataset.edit.split(":");
    patchTask(id, field, edit.value);
  }
  const quickUpdate = event.target.closest("[data-quick-update]");
  if (quickUpdate) {
    const [id, field] = quickUpdate.dataset.quickUpdate.split(":");
    patchTask(id, field, quickUpdate.value);
  }
  const input = event.target.closest("[data-import]");
  if (input) importCsv(input.files[0]);
  const newUser = event.target.closest("[data-new-user]");
  if (newUser) state.newUser[newUser.dataset.newUser] = newUser.type === "checkbox" ? newUser.checked : newUser.value;
  const formField = event.target.closest("[data-form]");
  if (formField) state.forms[formField.dataset.form] = formField.value;
  const bulk = event.target.closest("[data-bulk]");
  if (bulk) {
    state.bulk[bulk.dataset.bulk] = bulk.value;
    render();
  }
  const selectAll = event.target.closest("[data-select-all]");
  if (selectAll) {
    state.selectedIds = selectAll.checked ? new Set(state.tasks.map((t) => t.id)) : new Set();
    render();
  }
  const selectRow = event.target.closest("[data-select-row]");
  if (selectRow) {
    selectRow.checked ? state.selectedIds.add(selectRow.dataset.selectRow) : state.selectedIds.delete(selectRow.dataset.selectRow);
    render();
  }
  const checklist = event.target.closest("[data-checklist]");
  if (checklist) {
    const [id, step] = checklist.dataset.checklist.split(":");
    updateChecklist(id, step, checklist.checked);
  }
});

document.addEventListener("blur", (event) => {
  const edit = event.target.closest("[data-edit]");
  if (edit) {
    const [id, field] = edit.dataset.edit.split(":");
    patchTask(id, field, edit.value);
  }
}, true);

document.addEventListener("click", (event) => {
  const noOpen = event.target.closest("[data-no-open]");
  if (event.target.closest("[data-logout]")) {
    logout();
    return;
  }
  const view = event.target.closest("[data-view]");
  if (view) setView(view.dataset.view);
  if (event.target.closest("[data-toggle-filters]")) {
    state.mobileFiltersOpen = !state.mobileFiltersOpen;
    render();
  }
  const quick = event.target.closest("[data-quick]");
  if (quick && quick.dataset.quick) {
    applyQuickFilter(quick.dataset.quick);
    return;
  }
  if (event.target.closest("[data-filter-due]")) {
    state.filters.overdue = "";
    state.filters.deadlineFrom = new Date().toISOString().slice(0, 10);
    const soon = new Date(Date.now() + 6 * 86400000);
    state.filters.deadlineTo = soon.toISOString().slice(0, 10);
    state.view = "table";
    loadAll();
    return;
  }
  const healthFilter = event.target.closest("[data-health-filter]");
  if (healthFilter) {
    const map = { primary: "needs-owner", secondary: "needs-secondary", deadline: "needs-deadline", admin: "needs-admin" };
    applyQuickFilter(map[healthFilter.dataset.healthFilter] || "needs-owner");
    return;
  }
  const statusFilter = event.target.closest("[data-status-filter]");
  if (statusFilter) {
    state.filters.status = statusFilter.dataset.statusFilter;
    state.view = "table";
    loadAll();
    return;
  }
  const guided = event.target.closest("[data-guided-apply]");
  if (guided) {
    guidedApply(guided.dataset.guidedApply, guided.dataset.guidedFilter, guided.dataset.guidedField);
    return;
  }
  if (event.target.closest("[data-triage-next]")) {
    const total = triageCandidates().length;
    state.triageOffset = total ? (state.triageOffset + 5) % total : 0;
    render();
    return;
  }
  if (event.target.closest("[data-apply-same-owner]")) {
    applySameOwnerToVisible();
    return;
  }
  const openTask = event.target.closest("[data-open-task]");
  if (openTask && !noOpen) {
    state.selectedTaskId = openTask.dataset.openTask;
    render();
    loadCollaboration(state.selectedTaskId);
  }
  const close = event.target.closest("[data-close-inspector]");
  if (close) {
    state.selectedTaskId = "";
    render();
  }
  const ownerFilter = event.target.closest("[data-owner-filter]");
  if (ownerFilter) {
    state.filters.primaryOwner = ownerFilter.dataset.ownerFilter;
    state.view = "table";
    loadAll();
  }
  const bucketFilter = event.target.closest("[data-bucket-filter]");
  if (bucketFilter) {
    state.filters.bucket = bucketFilter.dataset.bucketFilter;
    state.view = "table";
    loadAll();
  }
  const adminFilter = event.target.closest("[data-admin-filter]");
  if (adminFilter) {
    state.filters.bucketAdmin = adminFilter.dataset.adminFilter;
    state.view = "table";
    loadAll();
  }
  const agencyFilter = event.target.closest("[data-agency-filter]");
  if (agencyFilter) {
    state.filters.agency = agencyFilter.dataset.agencyFilter;
    state.view = "table";
    loadAll();
  }
  if (event.target.closest("[data-clear]")) clearFilters();
  if (event.target.closest("[data-new]")) createTask();
  const addStatus = event.target.closest("[data-add-status]");
  if (addStatus) createTask(addStatus.dataset.addStatus);
  const duplicate = event.target.closest("[data-duplicate]");
  if (duplicate) duplicateTask(duplicate.dataset.duplicate);
  const del = event.target.closest("[data-delete]");
  if (del) deleteTask(del.dataset.delete);
  const activity = event.target.closest("[data-activity]");
  if (activity) loadActivity(activity.dataset.activity);
  const addCommentBtn = event.target.closest("[data-add-comment]");
  if (addCommentBtn) addComment(addCommentBtn.dataset.addComment);
  const addAssetBtn = event.target.closest("[data-add-asset]");
  if (addAssetBtn) addAsset(addAssetBtn.dataset.addAsset);
  const reviewBtn = event.target.closest("[data-review]");
  if (reviewBtn) reviewTask(reviewBtn.dataset.taskAction, reviewBtn.dataset.review);
  const notif = event.target.closest("[data-read-notification]");
  if (notif) markNotification(notif.dataset.readNotification);
  if (event.target.closest("[data-create-user]")) createUser();
  const resetPassword = event.target.closest("[data-reset-password]");
  if (resetPassword) resetUserPassword(resetPassword.dataset.resetPassword);
  if (event.target.closest("[data-reset]")) resetSeed();
  if (event.target.closest("[data-bulk-apply]")) bulkApply();
});

let draggingId = "";
document.addEventListener("dragstart", (event) => {
  const card = event.target.closest("[data-drag-id]");
  if (!card || isViewer()) return;
  draggingId = card.dataset.dragId;
  card.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
});
document.addEventListener("dragend", (event) => {
  const card = event.target.closest("[data-drag-id]");
  if (card) card.classList.remove("dragging");
  draggingId = "";
});
document.addEventListener("dragover", (event) => {
  const col = event.target.closest("[data-drop]");
  if (!col || isViewer()) return;
  event.preventDefault();
  col.classList.add("over");
});
document.addEventListener("dragleave", (event) => {
  const col = event.target.closest("[data-drop]");
  if (col) col.classList.remove("over");
});
document.addEventListener("drop", (event) => {
  const col = event.target.closest("[data-drop]");
  if (!col || !draggingId || isViewer()) return;
  event.preventDefault();
  col.classList.remove("over");
  patchTask(draggingId, "status", col.dataset.drop);
});

boot();
