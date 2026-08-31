const API = "/v1";
const TERMINAL = new Set(["COMPLETED", "PARTIAL", "BLOCKED", "FAILED"]);
const FLOW = ["INTAKE", "CLAIMS_EXTRACTED", "PLAN_READY", "EXECUTING", "VERIFYING", "COMPLETED"];
const descriptions = {
  "reproducible-mean": "Reported 5.0. The isolated run should agree within tolerance.",
  "parameter-drift": "Reported 4.8. Current declared data should expose a mismatch.",
  "ambiguous-spread": "Sample or population spread? The workflow must stop for judgment.",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let activeJob = null;
let pollTimer = null;

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 4500);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await response.text();
  let payload = null;
  try { payload = text ? JSON.parse(text) : null; } catch { payload = { detail: text }; }
  if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status})`);
  return payload;
}

function idempotencyKey() {
  return `web-${crypto.randomUUID()}`;
}

async function loadHealth() {
  try {
    const health = await fetch("/health").then((response) => response.json());
    $("#runtime-chip").classList.add("online");
    const mode = health.runtime_mode === "agentcore" ? "AgentCore live" : `${health.runtime_mode} provenance`;
    $("#runtime-label").textContent = mode;
  } catch {
    $("#runtime-label").textContent = "Runtime unavailable";
  }
}

function fixtureName(id) {
  return id.split("-").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

async function loadFixtures() {
  const list = $("#fixture-list");
  try {
    const fixtures = await api("/fixtures");
    list.replaceChildren(...fixtures.map((fixture) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fixture-card";
      button.dataset.runFixture = fixture.fixture_id;
      const header = document.createElement("header");
      const title = document.createElement("strong");
      title.textContent = fixtureName(fixture.fixture_id);
      const verdict = document.createElement("span");
      verdict.className = "fixture-verdict";
      verdict.textContent = fixture.requires_approval ? "HUMAN GATE" : `EXPECT ${fixture.expected_verdict}`;
      header.append(title, verdict);
      const copy = document.createElement("p");
      copy.textContent = descriptions[fixture.fixture_id] || fixture.title;
      button.append(header, copy);
      return button;
    }));
  } catch (error) {
    list.textContent = `Could not load demos: ${error.message}`;
  }
}

function switchTab(name) {
  $$("[data-tab]").forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  $$("[data-panel]").forEach((panel) => {
    const active = panel.dataset.panel === name;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}

async function createJob(payload) {
  window.clearTimeout(pollTimer);
  $("#empty-state").hidden = true;
  $("#job-view").hidden = false;
  $("#job-alert").hidden = true;
  $("#decision-card").hidden = true;
  $("#download-actions").hidden = true;
  activeJob = await api("/jobs", { method: "POST", body: JSON.stringify(payload) });
  renderJob(activeJob);
  pollJob(activeJob.job_id);
  $("#workspace").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function pollJob(jobId) {
  try {
    activeJob = await api(`/jobs/${jobId}`);
    renderJob(activeJob);
    if (!TERMINAL.has(activeJob.status) && activeJob.status !== "AWAITING_APPROVAL") {
      pollTimer = window.setTimeout(() => pollJob(jobId), 700);
    }
  } catch (error) {
    showAlert(error.message);
  }
}

function showAlert(message) {
  const alert = $("#job-alert");
  alert.textContent = message;
  alert.hidden = false;
}

function addDetail(container, label, value) {
  if (value === null || value === undefined || value === "") return;
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = String(value);
  wrapper.append(term, description);
  container.append(wrapper);
}

function renderRail(job) {
  const rail = $("#state-rail");
  const completed = new Set(job.transitions.map((item) => item.to_status));
  rail.replaceChildren(...FLOW.map((state) => {
    const item = document.createElement("li");
    if (completed.has(state)) item.classList.add("complete");
    if (job.status === state) item.classList.add("active");
    const label = document.createElement("span");
    label.textContent = state;
    item.append(label);
    return item;
  }));
}

function renderClaim(job) {
  const claim = job.claim_extraction?.claims?.find(
    (item) => item.claim_id === job.claim_extraction.selected_claim_id,
  );
  $("#claim-statement").textContent = claim?.statement || "Waiting for claim extraction…";
  const details = $("#claim-details");
  details.replaceChildren();
  if (!claim) return;
  addDetail(details, "Reported", `${claim.reported_value} ${claim.unit}`);
  addDetail(details, "Tolerance", claim.tolerance.absolute ? `±${claim.tolerance.absolute}` : `${claim.tolerance.relative * 100}%`);
  addDetail(details, "Source", claim.source.title);
  addDetail(details, "Content SHA", claim.source.content_sha256.slice(0, 16) + "…");
}

function renderPlan(job) {
  $("#plan-title").textContent = job.plan
    ? `${job.plan.timeout_seconds}s · network ${job.plan.network_access ? "requested" : "off"} · ${job.plan.requires_approval ? "approval required" : "policy cleared"}`
    : "Waiting for a policy-safe plan…";
  $("#plan-code").textContent = job.plan?.code || "No code generated.";
}

function renderResult(job) {
  const report = job.report;
  const execution = job.execution;
  const verdict = report?.verdict || (job.status === "FAILED" ? "FAILED" : "PENDING");
  $("#verdict").textContent = verdict;
  $("#result-card").dataset.verdict = verdict;
  $("#comparison-summary").textContent = report?.comparison?.rationale
    || execution?.failure_reason
    || "The sandbox has not returned an observation.";
  const details = $("#execution-details");
  details.replaceChildren();
  addDetail(details, "Observed", execution?.observed_value);
  addDetail(details, "Runtime", execution?.provenance);
  addDetail(details, "Service", execution?.service);
  addDetail(details, "Region", execution?.region);
  addDetail(details, "Duration", execution ? `${execution.duration_ms} ms` : null);
  addDetail(details, "Evidence SHA", report?.evidence_sha256 ? `${report.evidence_sha256.slice(0, 16)}…` : null);
  if (report) {
    $("#download-actions").hidden = false;
    $("#download-json").href = `${API}/jobs/${job.job_id}/evidence.json`;
    $("#download-markdown").href = `${API}/jobs/${job.job_id}/evidence.md`;
  }
}

function renderTrace(job) {
  const trace = job.trace || [];
  $("#trace-count").textContent = `${trace.length} event${trace.length === 1 ? "" : "s"}`;
  $("#trace-list").replaceChildren(...trace.map((event) => {
    const item = document.createElement("li");
    const ordinal = document.createElement("span");
    ordinal.className = "trace-ordinal";
    ordinal.textContent = String(event.ordinal).padStart(2, "0");
    const role = document.createElement("span");
    role.className = "trace-role";
    role.textContent = event.role;
    const name = document.createElement("span");
    name.className = "trace-name";
    name.textContent = `${event.event_type} · ${event.name}`;
    item.append(ordinal, role, name);
    return item;
  }));
}

function renderDecision(job) {
  const card = $("#decision-card");
  if (job.status !== "AWAITING_APPROVAL" || !job.decision) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  $("#decision-reason").textContent = job.decision.reason;
  $("#decision-actions").replaceChildren(...job.decision.options.map((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `button button-small ${option.option_id === "reject" ? "button-danger" : ""}`;
    button.textContent = option.label;
    button.title = option.impact;
    button.addEventListener("click", () => submitDecision(option.option_id));
    return button;
  }));
}

function renderJob(job) {
  $("#job-id").textContent = `${job.job_id} · ${job.trace_id}`;
  $("#job-status").textContent = job.status;
  $("#job-title").textContent = job.request.fixture_id
    ? fixtureName(job.request.fixture_id)
    : "Public paper evidence run";
  renderRail(job);
  renderClaim(job);
  renderPlan(job);
  renderResult(job);
  renderDecision(job);
  renderTrace(job);
  if (job.error_message) showAlert(`${job.error_code}: ${job.error_message}`);
}

async function submitDecision(optionId) {
  if (!activeJob) return;
  try {
    const note = $("#decision-note").value.trim() || null;
    activeJob = await api(`/jobs/${activeJob.job_id}/decision`, {
      method: "POST",
      body: JSON.stringify({ option_id: optionId, note }),
    });
    renderJob(activeJob);
    if (!TERMINAL.has(activeJob.status) && activeJob.status !== "AWAITING_APPROVAL") {
      pollJob(activeJob.job_id);
    }
  } catch (error) {
    showAlert(error.message);
  }
}

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab]");
  if (tab) switchTab(tab.dataset.tab);
  const fixture = event.target.closest("[data-run-fixture]");
  if (fixture) {
    createJob({
      fixture_id: fixture.dataset.runFixture,
      execution_budget_seconds: 30,
      idempotency_key: idempotencyKey(),
    }).catch((error) => showToast(error.message));
  }
});

$("#paper-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  createJob({
    paper_url: data.get("paper_url"),
    repo_url: data.get("repo_url") || null,
    claim_hint: data.get("claim_hint") || null,
    execution_budget_seconds: 90,
    idempotency_key: idempotencyKey(),
  }).catch((error) => showToast(error.message));
});

loadHealth();
loadFixtures();
