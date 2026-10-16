const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const human = value => String(value ?? "").replaceAll("_", " ");
const fmt = value => value === null || value === undefined ? "Unknown" : value !== 0 && (Math.abs(value) < 0.001 || Math.abs(value) >= 1e7) ? value.toExponential(3) : new Intl.NumberFormat(undefined, {maximumFractionDigits: 3}).format(value);
const date = value => new Date(value).toLocaleDateString(undefined, {month:"short",day:"numeric",year:"numeric"});
const datetime = value => new Date(value).toLocaleString(undefined, {dateStyle:"medium",timeStyle:"short"});
const state = {experiments:[], exp:null, comparison:null, filter:"all", search:"", revision:null, render:0};
const badge = (text, color="neutral") => `<span class="badge ${color}">${esc(text)}</span>`;
const statusBadge = value => badge(human(value), ({draft:"neutral",awaiting_review:"amber",reviewed:"green",improved:"green",regressed:"red",mixed:"amber",inconclusive:"blue"})[value] || "neutral");
const synthetic = exp => exp.runs.some(record => record.run.data_type === "synthetic");
const selectedRecords = exp => ["baseline","candidate"].map(role => exp.runs.find(record => record.record_id === exp.active_runs[role])).filter(Boolean);

async function api(path, method="GET", body) {
  let response;
  try { response = await fetch(`/api${path}`, {method, headers:body ? {"Content-Type":"application/json"} : {}, body:body ? JSON.stringify(body) : undefined}); }
  catch { throw new Error("The local server is unavailable. Run launch.cmd or launch.ps1, then reload this page. Your saved data stays on this computer."); }
  const payload = await response.json();
  if (!response.ok) { const error = new Error((payload.errors || ["Request failed."]).join("\n")); error.errors = payload.errors; throw error; }
  return payload;
}

let toastTimer;
function toast(message) { const el = $("#toast"); el.textContent = message; el.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 5000); }
function errors(element, error) { element.hidden = false; element.innerHTML = `<strong>Let’s fix this before saving.</strong><ul>${(error.errors || [error.message]).map(item => `<li>${esc(item)}</li>`).join("")}</ul>`; element.scrollIntoView({block:"nearest"}); }
function download(text, filename, type="application/json") { const url = URL.createObjectURL(new Blob([text], {type})); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 2000); }
function crumbs(items) { $("#breadcrumbs").innerHTML = `<a href="#/">Workspace</a>${items.map(item => `<span>/</span>${esc(item)}`).join("")}`; }
function heading(eyebrow, title, subtitle, actions="") { return `<div class="page-heading"><div><div class="eyebrow"><span class="line"></span>${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="heading-actions">${actions}</div></div>`; }
function exportActions(exp) { return `<a class="btn" href="/api/experiments/${esc(exp.id)}/export.json" download>↓ JSON</a><a class="btn" href="/api/experiments/${esc(exp.id)}/report.md" download>↓ Report</a>`; }
function tabs(exp, active) { return `<nav class="tabs" aria-label="Experiment views"><a class="tab ${active === "compare" ? "active" : ""}" href="#/experiment/${exp.id}/compare">Comparison</a><a class="tab ${active === "setup" ? "active" : ""}" href="#/experiment/${exp.id}/setup">Experiment setup</a><a class="tab ${active === "decision" ? "active" : ""}" href="#/experiment/${exp.id}/decision">Decision record <span class="tab-count">${exp.decisions.length}</span></a></nav>`; }
function experimentHeader(exp, subtitle, actions="") { return heading(`EXPERIMENT · ${exp.id.slice(0,8)}${synthetic(exp) ? " / SYNTHETIC DEMO" : ""}`, exp.setup.title, subtitle, actions); }

async function route() {
  const token = ++state.render;
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  try {
    state.experiments = await api("/experiments");
    if (token !== state.render) return;
    $("#experiment-count").textContent = state.experiments.length;
    if (!parts.length) { state.exp = null; crumbs(["Experiments"]); renderList(); }
    else if (parts[0] === "guide") { crumbs(["Import & export guide"]); renderGuide(); }
    else if (parts[0] === "new") { state.exp = null; crumbs(["Experiments","New experiment"]); renderSetup(); }
    else if (parts[0] === "experiment" && parts[1]) {
      const result = await api(`/experiments/${encodeURIComponent(parts[1])}`);
      if (token !== state.render) return;
      state.exp = result.experiment; state.comparison = result.comparison; state.revision = null;
      crumbs(["Experiments",state.exp.setup.title]);
      const view = parts[2] || "compare";
      if (view === "setup") renderSetup(state.exp);
      else if (view === "decision") renderDecision(state.exp);
      else renderComparison(state.exp, state.comparison);
    } else { throw new Error("This view does not exist. Return to the experiment list."); }
    document.title = `${state.exp?.setup.title || "Experiments"} · SOL Change Observatory`;
  } catch (error) { $("#main").innerHTML = `<div class="empty"><h2>Couldn’t open this view</h2><p>${esc(error.message)}</p><a class="btn primary" href="#/">Return to experiments</a></div>`; }
}

function renderList() {
  const pending = state.experiments.filter(e => e.review_status === "awaiting_review").length;
  const reviewed = state.experiments.filter(e => e.review_status === "reviewed").length;
  $("#main").innerHTML = heading("A WORKSPACE FOR BETTER CHANGES", "Is the change worth keeping?", "Compare agent runs. Follow the evidence. Make a decision you can explain.", `<button class="btn" id="import-continuum">↑ SOL packets</button><button class="btn" id="import-archive">↑ Import experiment</button><a class="btn primary" href="#/new"><span aria-hidden="true">＋</span> New experiment</a>`) +
    `<section class="overview" aria-label="Experiment overview"><div class="overview-card"><span class="symbol" aria-hidden="true">▦</span><div class="count">${state.experiments.length.toString().padStart(2,"0")}</div><div class="label">Total experiments</div></div><div class="overview-card"><span class="symbol" aria-hidden="true">◷</span><div class="count">${pending.toString().padStart(2,"0")}</div><div class="label">Awaiting your review</div></div><div class="overview-card"><span class="symbol" aria-hidden="true">✓</span><div class="count">${reviewed.toString().padStart(2,"0")}</div><div class="label">Decisions recorded</div></div></section>
    <div class="section-bar"><h2>Your experiments <span class="text-muted">/</span> <span class="text-muted">${state.experiments.length}</span></h2><div class="list-toolbar"><label><span class="screen-reader">Search experiments</span><input class="search" type="search" id="search" placeholder="Search experiments…" value="${esc(state.search)}"></label><div class="filters" aria-label="Filter by review status">${[["all","All"],["awaiting_review","To review"],["reviewed","Reviewed"]].map(([id,label]) => `<button data-filter="${id}" class="${state.filter === id ? "selected" : ""}" aria-pressed="${state.filter === id}">${label}</button>`).join("")}</div></div></div><section class="experiment-grid" id="experiment-grid" aria-label="Experiments"></section>
    <aside class="intro-strip"><div class="orbit" aria-hidden="true">◎</div><div><h3>A good comparison makes the tradeoffs visible.</h3><p>Start with the synthetic research-agent demo: stronger citations, a longer run, a higher cost, and one unanswered question. The evidence informs the decision. You make it.</p></div></aside>`;
  renderCards();
  $("#import-archive").onclick = () => openImport("archive");
  $("#import-continuum").onclick = openContinuumImport;
  $$("[data-filter]").forEach(button => button.onclick = () => { state.filter = button.dataset.filter; renderList(); });
  $("#search").oninput = event => { state.search = event.target.value; renderCards(); };
}

function renderCards() {
  const docs = state.experiments.filter(e => (state.filter === "all" || e.review_status === state.filter) && `${e.setup.title} ${e.setup.proposed_change}`.toLowerCase().includes(state.search.toLowerCase()));
  $("#experiment-grid").innerHTML = docs.map((exp) => {
    const index = state.experiments.indexOf(exp) + 1;
    const latest = exp.decisions.at(-1);
    const records = selectedRecords(exp);
    const citation = records.map(r => r.run.measurements.find(m => m.criterion_id === "citation_support")?.value);
    const incompatible = records.length === 2 && JSON.stringify(records[0].run.conditions) !== JSON.stringify(records[1].run.conditions);
    return `<article class="experiment-card"><div class="card-top"><span class="experiment-number">EXP ${String(index).padStart(3,"0")}</span>${statusBadge(exp.review_status)}</div><h3><a href="#/experiment/${exp.id}/compare">${esc(exp.setup.title)}</a></h3><p>${esc(exp.setup.proposed_change)}</p><div class="card-metrics">${synthetic(exp) ? badge("Synthetic demo","outline") : badge("Your experiment","outline")}${incompatible ? badge("Conditions differ","red") : citation.length === 2 && citation.every(v => v !== undefined) ? `<span>Citation support <strong>${fmt(citation[0])}% → ${fmt(citation[1])}%</strong></span>` : `<span>${exp.runs.length} run records · ${exp.setup.criteria.length} criteria</span>`}${latest ? statusBadge(latest.outcome) : ""}</div><div class="card-footer"><span>${latest ? `Latest: ${esc(human(latest.action))} · ${esc(latest.reviewer)}` : `Created ${date(exp.created_at)} · Criteria r${exp.current_revision}`}</span><a href="#/experiment/${exp.id}/compare">Open comparison <span aria-hidden="true">↗</span></a></div></article>`;
  }).join("") || `<div class="empty"><h3>No experiments here yet.</h3><p>Create an experiment to start your review loop.</p><a class="btn primary" href="#/new">New experiment</a></div>`;
}

function metricValue(measurement) {
  if (!measurement || measurement.value === null) return `<div class="metric-value text-muted">—</div><span class="metric-meta">Unmeasured</span>`;
  return `<div class="metric-value">${fmt(measurement.value)}<span class="unit">${esc(measurement.unit)}</span></div><span class="method-tag">${esc(human(measurement.method.kind))}</span>${measurement.evidence_ids.length ? "" : '<span class="metric-note">No linked evidence</span>'}`;
}

function metricRows(comparison) {
  return comparison.metrics.map(row => {
    const c = row.criterion;
    const color = ({improved:"green",regressed:"red",unchanged:"muted",unknown:"amber",incompatible:"red"})[row.status];
    const unit = c.unit === "%" ? "pp" : c.unit;
    const delta = row.delta === null ? "—" : `${row.delta > 0 ? "+" : ""}${fmt(row.delta)} ${esc(unit)}`;
    const pct = row.percent_change === null ? (row.delta !== null && row.baseline.value === 0 ? "Zero baseline · no %" : "Difference unknown") : `${row.percent_change > 0 ? "+" : ""}${fmt(row.percent_change)}% relative`;
    const check = (state, label) => `<div class="check-row ${state === "fail" ? "text-red" : state === "pass" ? "text-green" : "text-muted"}"><span class="check-icon">${state === "pass" ? "✓" : state === "fail" ? "×" : "·"}</span>${esc(label)}</div>`;
    return `<tr><td><span class="metric-name">${esc(c.label)}</span><div class="metric-meta">${c.direction === "higher" ? "↑ Higher" : "↓ Lower"} is better ${c.required ? "· Required" : "· Optional"}</div><details><summary class="metric-meta">Method &amp; notes</summary><div class="metric-note">${["baseline","candidate"].map(role => `${role}: ${esc(row[role]?.method.description || "No measurement")}<br>`).join("")}${row.notes.map(n => esc(n)).join("<br>")}</div></details></td><td>${metricValue(row.baseline)}${row.evidence.baseline.length ? `<button class="evidence-link" data-evidence="${esc(row.evidence.baseline[0])}">View evidence ↗</button>` : ""}</td><td>${metricValue(row.candidate)}${row.evidence.candidate.length ? `<button class="evidence-link" data-evidence="${esc(row.evidence.candidate[0])}">View evidence ↗</button>` : ""}</td><td><div class="metric-delta text-${color}">${delta}</div><div class="metric-meta">${pct}</div>${badge(human(row.status),color === "muted" ? "neutral" : color)}</td><td>${c.threshold !== null ? check(row.threshold_status, `${c.direction === "higher" ? "≥" : "≤"} ${fmt(c.threshold)} ${c.unit}: ${row.threshold_status}`) : `<div class="metric-meta">No target set</div>`}${c.max_regression_percent !== null ? check(row.guardrail_status, `≤ ${fmt(c.max_regression_percent)}% regression: ${row.guardrail_status}`) : ""}</td></tr>`;
  }).join("");
}

function runPanel(exp, role) {
  const records = exp.runs.filter(record => record.run.designation === role);
  const record = records.find(record => record.record_id === exp.active_runs[role]);
  const run = record?.run;
  const nativeSource = run?.configuration?.sol_continuum?.original_source_text;
  const configuration = structuredClone(run?.configuration || {});
  if (typeof nativeSource === "string") delete configuration.sol_continuum.original_source_text;
  return `<article class="panel run-panel"><div class="panel-header"><div><div class="run-label"><span class="role-dot ${role}"></span>${role.toUpperCase()}</div><div class="run-title">${esc(run?.workflow_version || (run ? "Workflow version unknown" : "No run imported"))}</div><div class="run-subtitle">${run ? `${esc(run.id)} · ${run.configuration?.sol_continuum?.timestamp_basis === "packet_generated_at" ? "Packet generated " : ""}${datetime(run.executed_at)}` : "Import a documented JSON run record"}</div></div>${run ? badge(run.data_type,run.data_type === "synthetic" ? "outline" : "blue") : ""}</div>${run ? `<div class="panel-body"><pre class="run-output">${esc(run.output) || "(Empty output)"}</pre><details class="run-details"><summary class="metric-meta">Input, configuration &amp; provenance</summary><div class="details-content"><p><strong>Input</strong><br>${esc(run.input)}</p><p><strong>Configuration</strong></p><pre>${esc(JSON.stringify(configuration,null,2))}</pre><p><strong>Comparison conditions</strong></p><pre>${esc(JSON.stringify(run.conditions,null,2))}</pre><p>Imported ${datetime(record.imported_at)} from ${esc(record.source_filename)}.</p><p>Source text SHA-256: <code>${esc(record.sha256)}</code></p>${record.supersedes_record_id ? `<p>Corrects ${esc(record.supersedes_record_id)}: ${esc(record.correction_reason)}</p>` : ""}<button class="btn small" data-original="${record.record_id}">↓ Imported run JSON</button>${typeof nativeSource === "string" ? `<button class="btn small" data-packet-source="${record.record_id}">↓ Source packet JSON</button>` : ""}</div></details></div>` : `<div class="empty-run"><div class="empty-symbol" aria-hidden="true">⇧</div><h3>Bring in the ${role}</h3><p>Your original JSON is preserved with a source hash and import timestamp.</p><button class="btn primary" data-import="${role}">Import ${role}</button></div>`}<div class="run-foot"><span>${run ? `${run.measurements.filter(m => m.value !== null).length} measurements · ${run.evidence.length} references` : "JSON schema v1.0"}</span><div class="inline">${records.length > 1 ? `<label><span class="screen-reader">Select ${role} run</span><select data-select-run="${role}">${records.map(r => `<option value="${r.record_id}" ${r.record_id === record?.record_id ? "selected" : ""}>${esc(r.run.id)}</option>`).join("")}</select></label>` : ""}${run ? `<button class="btn text small" data-import="${role}">↑ Import ${role}</button>` : ""}</div></div></article>`;
}

function evidenceList(exp, role) {
  const record = selectedRecords(exp).find(r => r.run.designation === role);
  if (!record) return `<div class="empty"><p>No ${role} evidence imported yet.</p></div>`;
  if (!record.run.evidence.length) return `<div class="empty"><p>No evidence references supplied. The measurements are self-reported.</p></div>`;
  return `<ul class="evidence-list">${record.run.evidence.map(item => `<li class="evidence-item" id="evidence-${esc(record.record_id)}-${esc(item.id)}">${badge(role,"outline")}<h4>${esc(item.title)}</h4><div class="evidence-ref">${esc(item.reference)}</div><p>${esc(item.provenance)}</p><span class="evidence-id">${esc(record.record_id)}:${esc(item.id)}</span></li>`).join("")}</ul>`;
}

function renderComparison(exp, comparison) {
  const hasPair = Boolean(exp.active_runs.baseline && exp.active_runs.candidate);
  const counts = comparison.counts;
  const viewingOld = comparison.criteria_revision !== exp.current_revision;
  $("#main").innerHTML = experimentHeader(exp, exp.setup.proposed_change, `${exportActions(exp)}<a class="btn primary" href="#/experiment/${exp.id}/decision">Record decision <span aria-hidden="true">↗</span></a>`) + tabs(exp,"compare") +
    `${synthetic(exp) ? `<div class="notice"><span class="notice-icon" aria-hidden="true">◈</span><p><strong>Synthetic demonstration.</strong> Invented runs, measurements, and evidence references. This is a review exercise, not a result from a real research agent.</p></div>` : ""}
    ${comparison.warnings.length ? `<div class="notice ${comparison.comparability === "incompatible" ? "error" : "info"}"><span class="notice-icon" aria-hidden="true">${comparison.comparability === "incompatible" ? "⚠" : "ⓘ"}</span><div><strong>${comparison.comparability === "incompatible" ? "These runs are not directly comparable." : "Comparison needs context."}</strong><ul>${comparison.warnings.map(w => `<li>${esc(w)}</li>`).join("")}</ul></div></div>` : ""}
    ${viewingOld ? `<div class="notice info"><p>Viewing criteria revision ${comparison.criteria_revision}. The selected runs are evaluated against these earlier criteria. New decisions always use current revision ${exp.current_revision}.</p></div>` : ""}
    <section class="comparison-summary" aria-label="Comparison summary"><div class="summary-main"><h3>${comparison.comparability === "incompatible" ? "Comparability is blocked" : hasPair ? "The tradeoffs at a glance" : "Build your comparison"}</h3><p>${hasPair ? "One pair of runs. No overall score." : "Start by importing both run records."}</p></div><div class="summary-stat"><div class="stat-value text-green">${counts.improved.toString().padStart(2,"0")}</div><p>Criteria improved</p></div><div class="summary-stat"><div class="stat-value text-red">${counts.regressed.toString().padStart(2,"0")}</div><p>Criteria regressed</p></div><div class="summary-stat"><div class="stat-value text-amber">${String(counts.unknown + counts.incompatible).padStart(2,"0")}</div><p>Unknown / incompatible</p></div></section>
    <section class="panel"><div class="panel-header"><div><h2>Measurements &amp; tradeoffs</h2><p>Changes are descriptive. Check each target and guardrail.</p></div><label class="revision-select">Criteria<select id="revision-select" aria-label="View criteria revision">${exp.criteria_revisions.map(r => `<option value="${r.revision}" ${r.revision === comparison.criteria_revision ? "selected" : ""}>r${r.revision}${r.revision === exp.current_revision ? " · current" : ""}${r.after_results ? " · after results" : ""}</option>`).join("")}</select></label></div><div class="table-scroll"><table class="metrics-table"><thead><tr><th scope="col">Evaluation criterion</th><th scope="col">Baseline</th><th scope="col">Candidate</th><th scope="col">Difference</th><th scope="col">Candidate checks</th></tr></thead><tbody>${metricRows(comparison)}</tbody></table></div><div class="table-footnote">A dash means unknown. Percentage-point differences use “pp”. Targets are inclusive. Measurements and ratings stay distinct.</div></section>
    <div class="section-bar"><h2>Run outputs <span class="text-muted">/</span> side by side</h2><span class="metric-meta">Original records retained · ${exp.runs.length} imports</span></div><section class="run-grid" aria-label="Baseline and candidate runs">${runPanel(exp,"baseline")}${runPanel(exp,"candidate")}</section>
    <section class="panel"><div class="panel-header"><div><h2>What changed in the output?</h2><p>Text differences preserve the original wording.</p></div>${badge("+ added / − removed","outline")}</div><div class="panel-body"><pre class="diff">${comparison.output_diff ? comparison.output_diff.split("\n").map(line => `<span class="diff-line ${line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@") ? "marker" : line.startsWith("+") ? "added" : line.startsWith("-") ? "removed" : ""}">${esc(line)}</span>`).join("") : `<span class="text-muted">${hasPair ? "The outputs are identical." : "Import both runs to see their output differences."}</span>`}</pre></div></section>
    <div class="section-bar" id="evidence-section"><h2>Follow the evidence</h2><span class="metric-meta">References are preserved. Contents are not fetched or verified.</span></div><section class="two-col"><article class="panel"><div class="panel-header"><h2>Baseline evidence</h2></div>${evidenceList(exp,"baseline")}</article><article class="panel"><div class="panel-header"><h2>Candidate evidence</h2></div>${evidenceList(exp,"candidate")}</article></section>
    <details class="limitations"><summary>What this comparison can and cannot tell you</summary><ul>${comparison.limitations.map(l => `<li>${esc(l)}</li>`).join("")}</ul></details>
    <div class="comparison-bottom"><div><h3>${exp.review_status === "reviewed" ? "A decision is on the record." : "The next step is your judgment."}</h3><p>${exp.review_status === "reviewed" ? "Review the rationale, record a new decision, or export the evidence trail." : "Weigh the improvement, the regressions, and what is still unknown."}</p></div><a class="btn primary" href="#/experiment/${exp.id}/decision">${exp.review_status === "reviewed" ? "View decision" : "Record your decision"} <span aria-hidden="true">→</span></a></div>`;
  bindImports();
  $("#revision-select").onchange = async event => {
    try { const result = await api(`/experiments/${exp.id}/comparison?revision=${event.target.value}`); renderComparison(exp,result); } catch(error) { toast(error.message); }
  };
  $$("[data-evidence]").forEach(button => button.onclick = () => {
    const [record,id] = button.dataset.evidence.split(":");
    const target = document.getElementById(`evidence-${record}-${id}`);
    if (target) { target.scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",block:"center"}); target.tabIndex = -1; target.focus({preventScroll:true}); }
  });
  $$("[data-original]").forEach(button => button.onclick = () => {
    const record = exp.runs.find(r => r.record_id === button.dataset.original);
    download(record.source_text, `${record.run.id}.json`);
  });
  $$("[data-packet-source]").forEach(button => button.onclick = () => {
    const record = exp.runs.find(r => r.record_id === button.dataset.packetSource);
    const metadata = record.run.configuration.sol_continuum;
    download(metadata.original_source_text, metadata.source_label.split(/[\\/]/).at(-1) || "source-packet.json");
  });
  $$("[data-select-run]").forEach(select => select.onchange = async event => {
    try { await api(`/experiments/${exp.id}/selections`,"POST",{...exp.active_runs,[event.target.dataset.selectRun]:event.target.value}); await route(); toast("Run selection saved. Review status updated; earlier decisions remain in history."); } catch(error) { toast(error.message); }
  });
}

const blankCriterion = () => ({id:"",label:"",unit:"",direction:"higher",threshold:null,max_regression_percent:null,required:true});
function criterionRow(c = blankCriterion()) {
  return `<tr class="criterion-row"><td><input data-field="id" aria-label="Criterion ID" value="${esc(c.id)}" placeholder="citation_support" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,99}" required></td><td><input data-field="label" aria-label="Criterion label" value="${esc(c.label)}" placeholder="Citation support" required></td><td><input data-field="unit" aria-label="Metric unit" value="${esc(c.unit)}" placeholder="%" required></td><td><select data-field="direction" aria-label="Better direction"><option value="higher" ${c.direction === "higher" ? "selected" : ""}>↑ Higher</option><option value="lower" ${c.direction === "lower" ? "selected" : ""}>↓ Lower</option></select></td><td><input data-field="threshold" aria-label="Target threshold" type="number" step="any" value="${c.threshold ?? ""}" placeholder="None"></td><td><input data-field="max_regression_percent" aria-label="Maximum regression percent" type="number" step="any" min="0" value="${c.max_regression_percent ?? ""}" placeholder="None"></td><td><input data-field="required" aria-label="Required criterion" type="checkbox" ${c.required ? "checked" : ""}></td><td><button class="remove-criterion" type="button" aria-label="Remove criterion">×</button></td></tr>`;
}

function renderSetup(exp) {
  const setup = exp?.setup || {title:"",task:"",proposed_change:"",hypothesis:"",intended_improvement:"",constraints:"",acceptable_tradeoffs:"",criteria:[blankCriterion()]};
  const field = (name,label,placeholder,optional=false,rows) => `<label class="field"><span>${label}${optional ? " <small>(optional)</small>" : ""}</span>${rows ? `<textarea name="${name}" rows="${rows}" placeholder="${esc(placeholder)}" ${optional ? "" : "required"} maxlength="20000">${esc(setup[name])}</textarea>` : `<input name="${name}" value="${esc(setup[name])}" placeholder="${esc(placeholder)}" required maxlength="200">`}</label>`;
  $("#main").innerHTML = (exp ? experimentHeader(exp,"Define what should improve and what must not regress.",exportActions(exp)) + tabs(exp,"setup") : heading("01 / DEFINE THE CHANGE","Start with a clear hypothesis.","Describe one meaningful change and the evidence you’ll use to judge it.")) +
    `${exp?.runs.length ? `<div class="notice"><span class="notice-icon" aria-hidden="true">◷</span><p>Runs have already been imported. Saving changes creates revision ${exp.current_revision + 1}, marked <strong>after results</strong>. Previous criteria and decisions remain in history.</p></div>` : ""}
    <form id="setup-form"><div id="setup-errors" class="error-list" role="alert" hidden></div><div class="form-layout"><div><section class="form-section"><h2>The experiment</h2><p>Give the comparison a purpose before looking at the results.</p>${field("title","Experiment title","e.g. A better sourced research agent")}${field("task","Task description","What task should both versions complete?",false,3)}${field("proposed_change","Proposed change","What exactly is different in the candidate?",false,2)}${field("hypothesis","Hypothesis","We expect this change to improve… because…",false,3)}${field("intended_improvement","Intended improvement","What does a worthwhile improvement look like?",false,2)}</section><section class="form-section"><h2>Boundaries &amp; tradeoffs</h2><p>Make the costs you can accept and the limits you cannot cross explicit.</p>${field("constraints","Constraints","e.g. Finish within 120 seconds. Do not reduce usefulness.",true,3)}${field("acceptable_tradeoffs","Acceptable tradeoffs","e.g. Up to 50% more cost if source support exceeds 85%.",true,3)}</section><section class="form-section"><h2>Evaluation criteria</h2><p>Use stable IDs to match measurements in your run files. A blank target or guardrail is unset, never zero.</p><div class="table-scroll"><table class="criteria-table"><thead><tr><th>ID</th><th>Label</th><th>Unit</th><th>Better</th><th>Target</th><th>Max regression %</th><th>Required</th><th></th></tr></thead><tbody id="criteria-rows">${setup.criteria.map(criterionRow).join("")}</tbody></table></div><button class="btn small" id="add-criterion" type="button">＋ Add criterion</button><p class="criterion-note">Targets are inclusive (≥ for higher, ≤ for lower). Guardrails limit deterioration from baseline. Units match exactly; the app does not convert them. Required criteria remain visible when unmeasured.</p></section><div class="form-actions"><a class="btn" href="${exp ? `#/experiment/${exp.id}/compare` : "#/"}">Cancel</a><button class="btn primary" type="submit">${exp ? "Save revision" : "Create experiment"} →</button></div></div><aside class="form-aside"><h3>Make it a fair comparison.</h3><p>Change one meaningful part of the workflow. Keep the task, source packet, environment, and evaluation method consistent.</p><hr><h3>Decide what matters.</h3><p>Higher quality may take more time or cost more. Set your boundaries now so those tradeoffs are visible later.</p><ul><li>Missing values stay unknown.</li><li>Imported runs stay intact.</li><li>Criteria revisions are retained.</li><li>The final call stays with you.</li></ul><hr><a href="#/guide">See the JSON import guide ↗</a>${exp ? `<p class="metric-meta">Created ${datetime(exp.created_at)}<br>Current criteria revision: ${exp.current_revision}</p>` : ""}</aside></div></form>`;
  $("#add-criterion").onclick = () => { if ($$(".criterion-row").length >= 30) { toast("The first version supports up to 30 criteria."); return; } $("#criteria-rows").insertAdjacentHTML("beforeend",criterionRow()); bindRemoveCriteria(); };
  bindRemoveCriteria();
  $("#setup-form").onsubmit = async event => {
    event.preventDefault();
    const form = event.target; const button = $("[type=submit]",form); button.disabled = true;
    const payload = Object.fromEntries(new FormData(form));
    payload.criteria = $$(".criterion-row").map(row => Object.fromEntries($$("[data-field]",row).map(input => [input.dataset.field,input.type === "checkbox" ? input.checked : input.type === "number" ? input.value === "" ? null : Number(input.value) : input.value.trim()])));
    try {
      const saved = await api(exp ? `/experiments/${exp.id}` : "/experiments", exp ? "PATCH" : "POST",payload);
      location.hash = `#/experiment/${saved.id}/compare`;
      toast(exp ? `Experiment saved at criteria revision ${saved.current_revision}.` : "Experiment created. Import your baseline and candidate runs.");
    } catch(error) { errors($("#setup-errors"),error); button.disabled = false; }
  };
}

function bindRemoveCriteria() { $$(".remove-criterion").forEach(button => button.onclick = () => { if ($$(".criterion-row").length === 1) { toast("Keep at least one evaluation criterion."); return; } button.closest("tr").remove(); }); }

function renderDecision(exp) {
  const latest = exp.decisions.at(-1);
  const hasPair = exp.active_runs.baseline && exp.active_runs.candidate;
  const outcomes = [["improved","Improved","The change is better on the criteria that matter."],["regressed","Regressed","The change makes the workflow worse."],["mixed","Mixed","Benefits come with meaningful tradeoffs."],["inconclusive","Inconclusive","The evidence does not support a clear verdict."]];
  $("#main").innerHTML = experimentHeader(exp,"Make the judgment explicit. Leave a trail someone else can review.",exportActions(exp)) + tabs(exp,"decision") +
    `${synthetic(exp) ? `<div class="notice"><p><strong>Synthetic review exercise.</strong> Your decision applies to invented demonstration data, not a real agent result.</p></div>` : ""}
    ${latest && exp.review_status !== "reviewed" ? `<div class="notice info"><p>The experiment has changed since its last decision. Earlier reviews are preserved; the current comparison is awaiting a new review.</p></div>` : ""}
    ${!hasPair ? `<div class="notice info"><p>Import both runs before recording a comparison decision. <a href="#/experiment/${exp.id}/compare">Return to the comparison →</a></p></div>` : ""}
    <div class="form-layout"><div><details ${latest ? "" : "open"} class="panel"><summary class="panel-header"><h2>${latest ? "Record another decision" : "Your decision"}</h2><span class="metric-meta">Criteria r${exp.current_revision}</span></summary><form class="panel-body" id="decision-form"><div id="decision-errors" class="error-list" role="alert" hidden></div><fieldset class="decision-fieldset"><legend class="screen-reader">Outcome</legend><div class="field"><span>What does the evidence tell you?</span></div><div class="decision-options">${outcomes.map(([id,label,desc]) => `<label class="choice"><input type="radio" name="outcome" value="${id}" required><span><strong>${label}</strong><small>${desc}</small></span></label>`).join("")}</div></fieldset><div class="field-row"><label class="field"><span>What happens next?</span><select name="action" required><option value="">Choose an action</option><option value="adopt">Adopt the change</option><option value="reject">Reject the change</option><option value="run_another_experiment">Run another experiment</option></select></label><label class="field"><span>Human reviewer</span><input name="reviewer" placeholder="Your name" required maxlength="200"><small>Self-reported reviewer; this local app has no authentication.</small></label></div><label class="field"><span>Why this decision?</span><textarea name="rationale" placeholder="Explain the benefits, costs, and unknowns that shaped your judgment." rows="5" required maxlength="20000"></textarea></label><div class="field"><span>Supporting evidence</span><small>Select the references that support your rationale. They stay tied to the selected run records.</small>${selectedRecords(exp).flatMap(record => record.run.evidence.map(item => `<label class="evidence-choice"><input type="checkbox" name="supporting_evidence" value="${esc(record.record_id)}:${esc(item.id)}"><span>${esc(item.title)} <small>${record.run.designation} · ${esc(item.reference)}</small></span></label>`)).join("") || `<p class="metric-meta">No evidence references supplied.</p>`}</div><label class="field"><span>Remaining questions</span><textarea name="unresolved_questions" placeholder="What still needs to be checked? One question per line." rows="3"></textarea></label><div class="form-actions"><a class="btn" href="#/experiment/${exp.id}/compare">← Back to evidence</a><button class="btn primary" type="submit" ${hasPair ? "" : "disabled"}>Save decision</button></div></form></details>
    ${latest ? `<section class="panel"><div class="panel-header"><h2>Decision history</h2>${badge(`${exp.decisions.length} ${exp.decisions.length === 1 ? "record" : "records"}`,"outline")}</div>${[...exp.decisions].reverse().map(d => {
      const current = d.criteria_revision === exp.current_revision && JSON.stringify(d.run_ids) === JSON.stringify(exp.active_runs);
      return `<article class="history-item"><div class="inline">${statusBadge(d.outcome)}${badge(human(d.action),"blue")}${badge(current ? "Current comparison" : "Earlier comparison","outline")}</div><p>${esc(d.rationale)}</p><div class="history-meta">${esc(d.reviewer)} · ${datetime(d.created_at)} · Criteria r${d.criteria_revision}</div><details><summary>Evidence, remaining questions &amp; comparison snapshot</summary><div class="details-content"><p><strong>Supporting evidence</strong></p>${d.supporting_evidence.map(key => `<p><code>${esc(key)}</code></p>`).join("") || "<p>None selected.</p>"}<p><strong>Remaining questions</strong></p>${d.unresolved_questions.map(q => `<p>• ${esc(q)}</p>`).join("") || "<p>None recorded.</p>"}<p><strong>Bound run records</strong></p><pre>${esc(JSON.stringify(d.run_ids,null,2))}</pre><p><strong>Comparison snapshot</strong></p><pre>${esc(JSON.stringify(d.comparison_snapshot,null,2))}</pre></div></details></article>`;
    }).join("")}</section>` : ""}</div><aside class="form-aside"><h3>The decision belongs to you.</h3><p>The software shows changes and criterion checks. It does not decide whether a quality gain is worth a slower or more expensive run.</p><hr><h3>Review the unknowns.</h3><ul>${state.comparison.metrics.filter(m => ["unknown","incompatible"].includes(m.status)).map(m => `<li>${esc(m.criterion.label)}: ${esc(m.status)}</li>`).join("") || "<li>No unknown criteria in this pair.</li>"}</ul><p>One pair does not establish statistical significance or a repeatable improvement.</p><hr><h3>Share a reviewable record.</h3><p>The report includes criteria, evidence references, limitations, and your decision. JSON also preserves the complete history.</p><a class="btn small" href="/api/experiments/${exp.id}/report.md" download>↓ Markdown report</a></aside></div>`;
  $("#decision-form").onsubmit = async event => {
    event.preventDefault(); const button = $("[type=submit]",event.target); button.disabled = true;
    const form = new FormData(event.target);
    const data = {outcome:form.get("outcome"),action:form.get("action"),reviewer:form.get("reviewer"),rationale:form.get("rationale"),supporting_evidence:form.getAll("supporting_evidence"),unresolved_questions:form.get("unresolved_questions").split("\n").map(q => q.trim()).filter(Boolean)};
    try { await api(`/experiments/${exp.id}/decisions`,"POST",data); await route(); toast("Human decision saved with its run records, criteria revision, and evidence links."); }
    catch(error) { errors($("#decision-errors"),error); button.disabled = false; }
  };
}

function bindImports() { $$("[data-import]").forEach(button => button.onclick = () => openImport(button.dataset.import)); }

function openContinuumImport() {
  const dialog = $("#import-dialog");
  dialog.innerHTML = `<div class="dialog-header"><div><h2 id="import-title">Compare SOL continuum packets</h2><p>Bring two saved SOL Lens v0.2 observations into the Observatory.</p></div><button class="dialog-close" type="button" aria-label="Close import">×</button></div><form class="dialog-body" id="continuum-form"><div class="notice info"><p>Each file contributes its primary observation. An embedded counterfactual baseline stays source material. Missing inputs, conditions, cost, and human review remain visible.</p></div><div id="continuum-errors" class="error-list" role="alert" hidden></div><label class="field"><span>Comparison title</span><input name="title" required maxlength="200" placeholder="e.g. SOL continuum packet review"></label><label class="field"><span>What change are you examining?</span><textarea name="proposed_change" required rows="2" placeholder="Describe the proposed change, or label this as an interoperability check."></textarea></label>${["baseline","candidate"].map(role => `<label class="field"><span>${role === "baseline" ? "Baseline" : "Candidate"} SOL packet</span><input type="file" id="continuum-${role}-file" accept=".json,application/json"><small>Saved proof-packet/v0.2 JSON, up to 1 MB. No live execution or URL fetching.</small></label><label class="field"><span>${role === "baseline" ? "Baseline" : "Candidate"} JSON</span><textarea id="continuum-${role}-source" rows="3" required spellcheck="false" placeholder="Or paste the original packet JSON here."></textarea></label>`).join("")}<div class="form-actions"><button class="btn" type="button" id="continuum-cancel">Cancel</button><button class="btn primary" type="submit">Validate &amp; create comparison</button></div></form>`;
  $(".dialog-close",dialog).onclick = () => dialog.close();
  $("#continuum-cancel").onclick = () => dialog.close();
  const labels = {baseline:"pasted-baseline-packet.json",candidate:"pasted-candidate-packet.json"};
  for (const role of ["baseline","candidate"]) $("#continuum-"+role+"-file").onchange = async event => {
    const file = event.target.files[0]; if (!file) return;
    if (file.size > 1_000_000) { errors($("#continuum-errors"),new Error("Native packet intake is limited to 1 MB per file.")); event.target.value = ""; return; }
    labels[role] = file.name; $("#continuum-"+role+"-source").value = await file.text();
  };
  $("#continuum-form").onsubmit = async event => {
    event.preventDefault(); const button = $("[type=submit]",event.target); button.disabled = true;
    const form = new FormData(event.target);
    try {
      const exp = await api("/continuum/experiments","POST",{title:form.get("title"),proposed_change:form.get("proposed_change"),baseline_source_text:$("#continuum-baseline-source").value,candidate_source_text:$("#continuum-candidate-source").value,baseline_label:labels.baseline,candidate_label:labels.candidate});
      dialog.close(); location.hash = `#/experiment/${exp.id}/compare`; toast("SOL packets imported with original sources and context warnings. No adoption decision was created.");
    } catch(error) { errors($("#continuum-errors"),error); button.disabled = false; }
  };
  dialog.showModal();
}

function openImport(mode) {
  const archive = mode === "archive";
  const existing = archive ? [] : state.exp.runs.filter(r => r.run.designation === mode);
  const dialog = $("#import-dialog");
  dialog.innerHTML = `<div class="dialog-header"><div><h2 id="import-title">Import ${archive ? "an experiment" : `a ${mode} run`}</h2><p>${archive ? "Restore a complete JSON export, including revisions and decisions." : "Original JSON is retained. Existing records are never overwritten."}</p></div><button class="dialog-close" type="button" aria-label="Close import">×</button></div><form class="dialog-body" id="import-form"><div id="import-errors" class="error-list" role="alert" hidden></div><label class="drop-area"><span class="screen-reader">Choose JSON file</span><input type="file" id="import-file" accept=".json,application/json"></label><label class="field"><span>Or paste the JSON</span><textarea id="import-source" rows="6" placeholder="{ &quot;schema_version&quot;: &quot;1.0&quot;, … }" spellcheck="false" required></textarea></label>${existing.length ? `<label class="field"><span>Import purpose</span><select id="correction-select"><option value="">A new run</option>${existing.map(r => `<option value="${r.record_id}">Correction of ${esc(r.run.id)}</option>`).join("")}</select></label><label class="field" id="correction-field" hidden><span>What was corrected?</span><textarea id="correction-reason" rows="2" placeholder="Explain the correction; use a new run ID in the JSON."></textarea></label>` : ""}<div class="form-actions"><button class="btn" type="button" id="cancel-import">Cancel</button><button class="btn primary" type="submit">Validate &amp; import</button></div><div class="example-links">${archive ? "The archive must use kind sol-change/experiment, schema_version 1.0. Duplicate experiment IDs are kept intact and reported." : `Download synthetic examples: <a href="/examples/baseline.json" download>Baseline ↓</a><a href="/examples/candidate.json" download>Candidate ↓</a><a href="/examples/incompatible-candidate.json" download>Incompatible candidate ↓</a>`}<br><a href="#/guide" id="dialog-guide">View format documentation ↗</a></div></form>`;
  $(".dialog-close",dialog).onclick = () => dialog.close();
  $("#cancel-import").onclick = () => dialog.close();
  $("#dialog-guide").onclick = () => dialog.close();
  let sourceFilename = archive ? "experiment.json" : "pasted-run.json";
  $("#import-file").onchange = async event => {
    const file = event.target.files[0]; if (!file) return;
    if (file.size > (archive ? 9_000_000 : 5_000_000)) { errors($("#import-errors"),new Error("This file exceeds the local import size limit.")); event.target.value = ""; return; }
    sourceFilename = file.name; $("#import-source").value = await file.text();
  };
  if ($("#correction-select")) $("#correction-select").onchange = event => { $("#correction-field").hidden = !event.target.value; $("#correction-reason").required = Boolean(event.target.value); };
  $("#import-form").onsubmit = async event => {
    event.preventDefault(); const button = $("[type=submit]",event.target); button.disabled = true;
    try {
      const source_text = $("#import-source").value;
      const parsed = JSON.parse(source_text.replace(/^\uFEFF/,""));
      if (!archive && parsed.designation !== mode) throw new Error(`This file is designated ${parsed.designation || "unknown"}. Choose a ${mode} file or import it into its matching slot.`);
      const result = await api(archive ? "/import-experiment" : `/experiments/${state.exp.id}/runs`,"POST",{source_text,source_filename:sourceFilename,...(!archive ? {supersedes_record_id:$("#correction-select")?.value || null,correction_reason:$("#correction-reason")?.value || ""} : {})});
      dialog.close();
      if (archive && location.hash !== `#/experiment/${result.id}/compare`) location.hash = `#/experiment/${result.id}/compare`; else await route();
      toast(archive ? "Experiment restored with its criteria and decision history." : `${human(mode)} imported. Original source text and SHA-256 preserved.`);
    } catch(error) { errors($("#import-errors"),error); button.disabled = false; }
  };
  dialog.showModal();
}

function continuumGuidePanel() {
  return `<section class="panel"><div class="panel-body"><h2>Connect the SOL continuum</h2><p>Use <strong>SOL packets</strong> on the experiment list to import two saved <code>techman.sol-lens.proof-packet/v0.2</code> files from SOL Decide, SOL Lens, or the live server’s saved output. Each file supplies its primary observation; an embedded counterfactual baseline remains source material.</p><p>Producer scores stay on their 0–1 scale and are labeled automated assessments. Missing execution input, evaluation context, time, cost, and human review remain visible. Different engineering tasks are flagged as incompatible.</p><p>SOL Change uses port <strong>8770</strong>; the SOL live server keeps <strong>8765</strong>. This bridge reads saved artifacts and makes no provider calls or execution approvals.</p><div class="actions"><button class="btn primary small" id="guide-continuum">Import SOL packets</button><a class="btn small" href="/schemas/continuum-context.schema.json" download>↓ Producer context schema</a><a class="btn small" href="/examples/continuum-context.example.json" download>↓ Synthetic context example</a></div></div></section>`;
}

function renderGuide() {
  $("#main").innerHTML = heading("PORTABLE BY DESIGN","Bring your runs. Keep the evidence.","A small, versioned JSON format connects the Observatory to your workflow.",`<a class="btn" href="#/">← Experiments</a>`) +
    `<div class="guide">${continuumGuidePanel()}<section class="panel"><div class="panel-body"><h2>1. Create an experiment</h2><p>Set the task, hypothesis, constraints, and criteria. Each criterion has a stable ID, an exact unit, a better direction, an optional inclusive target, and an optional maximum regression percentage. Set a guardrail of 0 to disallow deterioration.</p><h2>2. Import a baseline and a candidate</h2><p>Use <code>kind: "sol-change/run"</code> and <code>schema_version: "1.0"</code>. Each run supplies input, output, configuration, workflow version (or null), an execution timestamp with timezone, comparison conditions, measurements, evidence references, and a data origin: <code>imported</code>, <code>manual</code>, or <code>synthetic</code>.</p><div class="actions"><a class="btn small" href="/examples/baseline.json" download>↓ Baseline example</a><a class="btn small" href="/examples/candidate.json" download>↓ Candidate example</a><a class="btn small" href="/examples/incompatible-candidate.json" download>↓ Incompatible fixture</a><a class="btn small" href="/schemas/run.schema.json" download>↓ Run JSON Schema</a><a class="btn small" href="/schemas/experiment.schema.json" download>↓ Experiment JSON Schema</a></div><pre>${esc(JSON.stringify({criterion_id:"citation_support",value:92,unit:"%",method:{kind:"automated_assessment",description:"Supported claims divided by all claims using a frozen packet and rubric.",version:"claim-audit/1"},evidence_ids:["citation-audit"]},null,2))}</pre><p>Measurement kinds are <code>measured</code>, <code>human_rating</code>, and <code>automated_assessment</code>. A null value or omitted measurement stays unknown. Reference IDs must point to evidence in the same run.</p><p>Conditions such as dataset, source packet, environment, and seed should match exactly. Workflow configuration may differ because that is the change you are testing. Unknown conditions use <code>{}</code> and create a warning. Methods and units must match before metric differences are shown.</p><h2>3. Review and decide</h2><p>Inspect individual tradeoffs and the linked evidence. Record your outcome, next action, rationale, supporting references, and unresolved questions. The app never infers an adoption decision or claims statistical significance from one pair.</p><h2>4. Export a portable record</h2><p><strong>JSON</strong> includes every run’s original source text and SHA-256, criteria revisions, and decisions with bound run IDs and comparison snapshots. Import the archive into a fresh Observatory database to restore its history. Existing experiment IDs are never overwritten.</p><p><strong>Markdown</strong> is a readable review report containing the criteria, measurements, methods, evidence references, limitations, and human decision history.</p><h2>Corrections and revisions</h2><p>Import a corrected run with a new run ID, select “Correction of…” and explain what changed. The original remains available in the run selector. Saving setup changes creates a new criteria revision, including a flag if results were already present. A changed setup or run selection returns the experiment to review; previous decisions retain their original context.</p><h2>Local boundaries</h2><p>All example results are invented. Evidence references are treated as text and are never fetched or executed. Reviewer names and evidence provenance are self-reported. Data lives in <code>sol-change/data/observatory.sqlite3</code>; restart the app with the same database to keep working.</p><p>V1 compares one selected pair at a time. Repeated trials, provider integrations, live execution, and cloud deployment are outside this version.</p></div></section></div>`;
  $("#guide-continuum").onclick = openContinuumImport;
}

$(".skip-link").onclick = event => { event.preventDefault(); $("#main").focus(); $("#main").scrollIntoView({block:"start"}); };
window.addEventListener("hashchange",() => { window.scrollTo(0,0); route(); });
route();
