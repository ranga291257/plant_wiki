const MODEL_STORAGE_KEY = "plant_wiki_llm_model";

let defaultModel = "";
let ollamaReachable = false;
let lastConfirmedModel = "";
let syncingModels = false;
let lastRunState = "idle";
let lastQuery = null;

const LLM_BUTTON_IDS = ["convert-full-btn", "ingest-btn", "query-btn", "ai-lint-btn"];

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function spinner() {
  return `<span class="spinner"></span>`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getGlobalModelSelect() {
  return document.getElementById("global-model-input");
}

function getSelectedModel() {
  const el = getGlobalModelSelect();
  return (el && el.value.trim()) || defaultModel;
}

function setLlmButtonsEnabled(enabled) {
  for (const id of LLM_BUTTON_IDS) {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = !enabled;
  }
  const scaffoldBtn = document.getElementById("convert-scaffold-btn");
  if (scaffoldBtn) scaffoldBtn.disabled = false;
}

function populateSelect(selectEl, models, selected) {
  if (!selectEl) return;
  if (!models.length) {
    selectEl.innerHTML = '<option value="">No local chat models</option>';
    selectEl.disabled = true;
    return;
  }
  selectEl.disabled = false;
  selectEl.innerHTML = models.map((m) => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join("");
  if (selected && models.includes(selected)) {
    selectEl.value = selected;
  } else {
    selectEl.value = models[0];
  }
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((b) => b.setAttribute("aria-selected", "false"));
  const panel = document.getElementById(`panel-${tabId}`);
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  if (panel) panel.classList.add("active");
  if (btn) btn.setAttribute("aria-selected", "true");
}

function setRunState(state) {
  lastRunState = state;
  const chip = document.getElementById("last-run-chip");
  const tabBtn = document.getElementById("tab-btn-run-log");
  tabBtn.classList.remove("tab-fail", "tab-warn");
  if (state === "fail") tabBtn.classList.add("tab-fail");
  if (state === "warn") tabBtn.classList.add("tab-warn");

  if (!chip) return;
  chip.classList.remove("visible", "state-ok", "state-warn", "state-fail");
  if (state === "idle") return;
  chip.classList.add("visible");
  if (state === "ok") {
    chip.classList.add("state-ok");
    chip.textContent = "Last run: OK";
  } else if (state === "warn") {
    chip.classList.add("state-warn");
    chip.textContent = "Last run: Warning";
  } else if (state === "fail") {
    chip.classList.add("state-fail");
    chip.textContent = "Last run: Failed";
  }
}

function renderStepsTable(steps) {
  if (!steps || !steps.length) return "";
  const rows = steps
    .map((s) => {
      const fail = s.exit_code !== 0;
      const cmd = escapeHtml(typeof s.command === "string" ? s.command : (s.command || []).join(" "));
      const out = escapeHtml(`${s.stdout || ""}${s.stderr ? "\n" + s.stderr : ""}`.trim() || "(no output)");
      return `<tr class="${fail ? "exit-fail" : ""}">
        <td>${fail ? "Failed" : "OK"}</td>
        <td><code>${cmd}</code></td>
        <td>${s.exit_code}</td>
        <td><details><summary>Output</summary><pre>${out}</pre></details></td>
      </tr>`;
    })
    .join("");
  return `<table class="run-log-table"><thead><tr><th>Status</th><th>Command</th><th>Exit</th><th>Output</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function publishRunLog({ title, success, level, steps, extrasHtml, autoSwitch = true }) {
  const lvl = level || (success ? "ok" : "fail");
  setRunState(lvl === "ok" ? "ok" : lvl === "warn" ? "warn" : "fail");

  const summary = document.getElementById("run-log-summary");
  const body = document.getElementById("run-log-body");
  if (summary) {
    summary.innerHTML = `<h3 class="${lvl === "ok" ? "ok" : lvl === "warn" ? "warn" : "bad"}">${escapeHtml(title)}</h3>`;
  }
  if (body) {
    body.innerHTML = (extrasHtml || "") + renderStepsTable(steps);
  }
  if (autoSwitch && lvl === "fail") {
    switchTab("run-log");
  }
}

function setActionStatus(elementId, html) {
  const el = document.getElementById(elementId);
  if (el) el.innerHTML = html;
}

function logLinkHtml() {
  return '<a href="#" data-goto-run-log>Run log</a>';
}

function renderChangeList(title, items) {
  if (!items.length) {
    return `<details class="change-block"><summary>${title} (0)</summary><p>None</p></details>`;
  }
  const lis = items.map((i) => `<li><code>${escapeHtml(i)}</code></li>`).join("");
  return `<details class="change-block"><summary>${title} (${items.length})</summary><ul>${lis}</ul></details>`;
}

function updateOllamaBanner(data) {
  const banner = document.getElementById("ollama-models-banner");
  if (!banner) return;
  if (!data.ollama_reachable) {
    banner.innerHTML = `<p class="hint"><span class="bad">Ollama not reachable</span>${data.error ? ` — ${escapeHtml(data.error)}` : ""}. Start Ollama and reload this page.</p>`;
    setLlmButtonsEnabled(false);
    return;
  }
  const count = (data.models || []).length;
  banner.innerHTML = count
    ? `<p class="hint"><span class="ok">${count} local chat model(s)</span> loaded (cloud and embedding models hidden).</p>`
    : `<p class="hint"><span class="warn">Ollama is running but no chat models matched the filter.</span></p>`;
  setLlmButtonsEnabled(count > 0);
}

function onGlobalModelChange() {
  if (syncingModels) return;
  const select = getGlobalModelSelect();
  if (!select) return;
  const next = select.value;
  if (!next || next === lastConfirmedModel) return;

  if (!confirm(`Use "${next}" for all LLM actions (convert, ingest, query, AI lint)?`)) {
    syncingModels = true;
    select.value = lastConfirmedModel || defaultModel;
    syncingModels = false;
    return;
  }

  lastConfirmedModel = next;
  sessionStorage.setItem(MODEL_STORAGE_KEY, next);
  syncingModels = true;
  loadOllamaModels();
}

async function loadOllamaModels() {
  const select = getGlobalModelSelect();
  const stored = sessionStorage.getItem(MODEL_STORAGE_KEY) || "";
  const prefer = syncingModels ? lastConfirmedModel : stored || (select && select.value) || lastConfirmedModel || defaultModel;

  try {
    const data = await getJson("/api/ollama/models");
    ollamaReachable = data.ollama_reachable;
    defaultModel = data.default_model || "";
    const models = data.models || [];
    syncingModels = true;
    populateSelect(select, models, prefer || defaultModel);
    if (select && select.value) {
      lastConfirmedModel = select.value;
      sessionStorage.setItem(MODEL_STORAGE_KEY, select.value);
    }
    syncingModels = false;
    updateOllamaBanner(data);
  } catch (err) {
    ollamaReachable = false;
    defaultModel = "";
    syncingModels = true;
    if (select) {
      select.innerHTML = '<option value="">Failed to load models</option>';
      select.disabled = true;
    }
    syncingModels = false;
    const banner = document.getElementById("ollama-models-banner");
    if (banner) {
      banner.innerHTML = `<p class="hint"><span class="bad">${escapeHtml(err.message)}</span></p>`;
    }
    setLlmButtonsEnabled(false);
  }
}

async function loadRawFiles() {
  const sel = document.getElementById("raw-file-select");
  if (!sel) return;
  try {
    const data = await getJson("/api/raw-files");
    sel.innerHTML = data.files.length
      ? data.files.map((f) => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("")
      : '<option value="">No raw files found</option>';
  } catch {
    sel.innerHTML = '<option value="">Error loading files</option>';
  }
}

async function runConvertFull(scaffoldOnly) {
  const model = getSelectedModel();
  const btnFull = document.getElementById("convert-full-btn");
  const btnScaffold = document.getElementById("convert-scaffold-btn");
  const card = document.getElementById("convert-card");

  if (!scaffoldOnly && !confirm("Run full LLM conversion on all raw/ markdown? This may take several minutes and rebuilds wiki pages.")) {
    return;
  }

  btnFull.disabled = true;
  btnScaffold.disabled = true;
  card.classList.remove("convert-card--fail");
  setActionStatus("convert-status", `${spinner()} Running ${scaffoldOnly ? "scaffold-only" : "full"} conversion...`);

  const formData = new FormData();
  formData.append("model", model);
  formData.append("scaffold_only", scaffoldOnly ? "true" : "false");

  try {
    const data = await getJson("/api/convert-full", { method: "POST", body: formData });
    const ok = data.success;
    if (!ok) card.classList.add("convert-card--fail");

    publishRunLog({
      title: ok ? "Full conversion completed" : "Full conversion failed",
      success: ok,
      level: ok ? "ok" : "fail",
      steps: data.steps,
      autoSwitch: !ok,
    });

    setActionStatus(
      "convert-status",
      ok
        ? `<span class="ok">Conversion finished.</span>`
        : `<span class="bad">Conversion failed — see ${logLinkHtml()}.</span>`
    );
    await loadRawFiles();
    await refreshChanges();
  } catch (err) {
    card.classList.add("convert-card--fail");
    publishRunLog({
      title: "Full conversion error",
      success: false,
      level: "fail",
      steps: [],
      extrasHtml: `<pre>${escapeHtml(err.message)}</pre>`,
    });
    setActionStatus("convert-status", `<span class="bad">${escapeHtml(err.message)} — see ${logLinkHtml()}.</span>`);
  } finally {
    btnFull.disabled = false;
    btnScaffold.disabled = false;
  }
}

async function uploadFile(event) {
  event.preventDefault();
  const input = document.getElementById("file");
  const destination = document.getElementById("destination").value;
  if (!input.files.length) {
    setActionStatus("upload-status", `<span class="bad">Select a file first.</span>`);
    return;
  }
  setActionStatus("upload-status", `${spinner()} Uploading...`);
  const formData = new FormData();
  formData.append("file", input.files[0]);
  formData.append("destination", destination);
  try {
    const data = await getJson("/api/upload", { method: "POST", body: formData });
    setActionStatus("upload-status", `<span class="ok">Uploaded: <code>${escapeHtml(data.path)}</code></span>`);
    input.value = "";
    await loadRawFiles();
    await refreshChanges();
  } catch (err) {
    setActionStatus("upload-status", `<span class="bad">${escapeHtml(err.message)}</span>`);
  }
}

function buildIngestExtras(data) {
  let html = "";
  if (data.source_summary) {
    html += `<h4>Source summary</h4><ul><li><code>${escapeHtml(data.source_summary)}</code></li></ul>`;
  }
  for (const [label, key] of [
    ["Concept pages created", "concept_pages_created"],
    ["Concept pages updated", "concept_pages_updated"],
    ["Entity pages created", "entity_pages_created"],
    ["Entity pages updated", "entity_pages_updated"],
  ]) {
    const items = data[key] || [];
    if (items.length) {
      html += `<h4>${label} (${items.length})</h4><ul>`;
      items.forEach((p) => {
        html += `<li><code>${escapeHtml(p)}</code></li>`;
      });
      html += "</ul>";
    }
  }
  const errors = data.errors || [];
  if (errors.length) {
    html += `<h4 class="warn">Warnings</h4><ul>`;
    errors.forEach((e) => {
      html += `<li class="warn">${escapeHtml(e)}</li>`;
    });
    html += "</ul>";
  }
  return html;
}

async function runIngest() {
  const rawFile = document.getElementById("raw-file-select").value;
  const model = getSelectedModel();
  const btn = document.getElementById("ingest-btn");

  if (!rawFile) {
    setActionStatus("ingest-status", `<span class="bad">Select a raw file first.</span>`);
    return;
  }

  btn.disabled = true;
  setActionStatus("ingest-status", `${spinner()} Ingesting <code>${escapeHtml(rawFile)}</code> (30–120s)...`);

  const formData = new FormData();
  formData.append("raw_file", rawFile);
  formData.append("model", model);

  try {
    const data = await getJson("/api/ingest", { method: "POST", body: formData });
    const errors = data.errors || [];
    const pipeOk = data.pipeline_success !== false;
    const level = !pipeOk ? "fail" : errors.length ? "warn" : "ok";

    publishRunLog({
      title: !pipeOk ? "Ingest failed (pipeline)" : errors.length ? "Ingest completed with warnings" : "Ingest completed",
      success: pipeOk && !errors.length,
      level,
      steps: data.pipeline_steps,
      extrasHtml: buildIngestExtras(data),
      autoSwitch: level === "fail",
    });

    setActionStatus(
      "ingest-status",
      level === "fail"
        ? `<span class="bad">Ingest ran but index/lint failed — see ${logLinkHtml()}.</span>`
        : level === "warn"
          ? `<span class="warn">Ingest done with ${errors.length} warning(s) — see ${logLinkHtml()}.</span>`
          : `<span class="ok">Ingest completed.</span>`
    );
    await refreshChanges();
  } catch (err) {
    publishRunLog({
      title: "Ingest failed",
      success: false,
      level: "fail",
      steps: [],
      extrasHtml: `<pre>${escapeHtml(err.message)}</pre>`,
    });
    setActionStatus("ingest-status", `<span class="bad">Ingest failed — see ${logLinkHtml()}.</span>`);
  } finally {
    btn.disabled = false;
  }
}

async function runQuery() {
  const question = document.getElementById("query-input").value.trim();
  const model = getSelectedModel();
  const resultEl = document.getElementById("query-result");
  const btn = document.getElementById("query-btn");

  if (!question) {
    setActionStatus("query-status", `<span class="bad">Enter a question first.</span>`);
    return;
  }

  btn.disabled = true;
  setActionStatus("query-status", `${spinner()} Querying wiki...`);
  resultEl.innerHTML = "";
  try {
    const formData = new FormData();
    formData.append("question", question);
    formData.append("model", model);
    const data = await getJson("/api/query", { method: "POST", body: formData });

    lastQuery = {
      question,
      answer: data.answer || "",
      citations: data.citations || [],
      suggested_slug: data.suggested_slug || "analysis",
      model,
    };
    document.getElementById("analysis-slug-input").value = lastQuery.suggested_slug;
    setActionStatus("query-status", `<span class="ok">Query complete.</span>`);
    const selected = (data.selected_pages || []).map((p) => `<li><code>${escapeHtml(p)}</code></li>`).join("");
    const citations = (lastQuery.citations || []).map((c) => `<li><code>${escapeHtml(c)}</code></li>`).join("");
    resultEl.innerHTML = `
      <h4>Answer</h4>
      <pre>${escapeHtml(lastQuery.answer)}</pre>
      <h4>Selected pages</h4>
      <ul>${selected || "<li>None</li>"}</ul>
      <h4>Citations</h4>
      <ul>${citations || "<li>None</li>"}</ul>
    `;
  } catch (err) {
    setActionStatus("query-status", `<span class="bad">${escapeHtml(err.message)}</span>`);
  } finally {
    btn.disabled = false;
  }
}

async function fileAnalysis() {
  const slug = document.getElementById("analysis-slug-input").value.trim();
  if (!lastQuery) {
    setActionStatus("file-analysis-status", `<span class="bad">Run a query first.</span>`);
    return;
  }
  setActionStatus("file-analysis-status", `${spinner()} Writing analysis page...`);
  try {
    const formData = new FormData();
    formData.append("question", lastQuery.question);
    formData.append("answer", lastQuery.answer);
    formData.append("citations", JSON.stringify(lastQuery.citations || []));
    formData.append("slug", slug || lastQuery.suggested_slug || "analysis");
    formData.append("model", lastQuery.model);
    const data = await getJson("/api/file-analysis", { method: "POST", body: formData });
    setActionStatus("file-analysis-status", `<span class="ok">Analysis written: <code>${escapeHtml(data.analysis_path)}</code></span>`);
    await refreshChanges();
  } catch (err) {
    setActionStatus("file-analysis-status", `<span class="bad">${escapeHtml(err.message)}</span>`);
  }
}

async function runAiLint() {
  setActionStatus("maintain-status", `${spinner()} Running AI lint...`);
  try {
    const model = getSelectedModel();
    const formData = new FormData();
    formData.append("model", model);
    const data = await getJson("/api/lint-llm", { method: "POST", body: formData });
    const issues = data.issues || [];
    if (!issues.length) {
      setRunState("ok");
      document.getElementById("run-log-summary").innerHTML = `<h3 class="ok">AI lint: no issues</h3>`;
      document.getElementById("run-log-body").innerHTML = "";
      setActionStatus("maintain-status", `<span class="ok">AI lint found no semantic issues. See ${logLinkHtml()}.</span>`);
      return;
    }
    const extras = `<h4 class="warn">AI lint issues (${issues.length})</h4><ul>${issues.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`;
    publishRunLog({
      title: `AI lint: ${issues.length} issue(s)`,
      success: false,
      level: "warn",
      steps: [],
      extrasHtml: extras,
      autoSwitch: true,
    });
    setActionStatus("maintain-status", `<span class="warn">AI lint found ${issues.length} issue(s) — see ${logLinkHtml()}.</span>`);
  } catch (err) {
    publishRunLog({
      title: "AI lint failed",
      success: false,
      level: "fail",
      steps: [],
      extrasHtml: `<pre>${escapeHtml(err.message)}</pre>`,
    });
    setActionStatus("maintain-status", `<span class="bad">AI lint failed — see ${logLinkHtml()}.</span>`);
  }
}

async function refreshChanges() {
  const summary = document.getElementById("changes-summary");
  const detail = document.getElementById("changes-detail");
  summary.innerHTML = `${spinner()} Loading changes...`;
  detail.innerHTML = "";
  try {
    const data = await getJson("/api/changes");
    const c = data.changes;
    summary.innerHTML =
      `Baseline: <b>${data.baseline_files}</b> | Current: <b>${data.current_files}</b> | ` +
      `Added: <b>${c.added.length}</b>, Modified: <b>${c.modified.length}</b>, Deleted: <b>${c.deleted.length}</b>`;
    detail.innerHTML =
      renderChangeList("Added", c.added) +
      renderChangeList("Modified", c.modified) +
      renderChangeList("Deleted", c.deleted);
  } catch (err) {
    summary.innerHTML = `<span class="bad">${escapeHtml(err.message)}</span>`;
  }
}

async function runUpdate() {
  setActionStatus("maintain-status", `${spinner()} Rebuilding index and linting...`);
  try {
    const data = await getJson("/api/update", { method: "POST" });
    const ok = data.success;
    publishRunLog({
      title: ok ? "Rebuild index + lint completed" : "Rebuild index + lint failed",
      success: ok,
      level: ok ? "ok" : "fail",
      steps: data.steps,
      autoSwitch: !ok,
    });
    setActionStatus(
      "maintain-status",
      ok
        ? `<span class="ok">Update completed.</span>`
        : `<span class="bad">Update failed — see ${logLinkHtml()}.</span>`
    );
    await refreshChanges();
  } catch (err) {
    publishRunLog({
      title: "Update error",
      success: false,
      level: "fail",
      steps: [],
      extrasHtml: `<pre>${escapeHtml(err.message)}</pre>`,
    });
    setActionStatus("maintain-status", `<span class="bad">${escapeHtml(err.message)} — see ${logLinkHtml()}.</span>`);
  }
}

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function initRunLogLinks() {
  document.body.addEventListener("click", (e) => {
    const link = e.target.closest("[data-goto-run-log]");
    if (link) {
      e.preventDefault();
      switchTab("run-log");
    }
  });
  const chip = document.getElementById("last-run-chip");
  if (chip) {
    chip.addEventListener("click", () => switchTab("run-log"));
    chip.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        switchTab("run-log");
      }
    });
  }
}

document.getElementById("upload-form").addEventListener("submit", uploadFile);
document.getElementById("refresh-btn").addEventListener("click", refreshChanges);
document.getElementById("update-btn").addEventListener("click", runUpdate);
document.getElementById("ai-lint-btn").addEventListener("click", runAiLint);
document.getElementById("ingest-btn").addEventListener("click", runIngest);
document.getElementById("query-btn").addEventListener("click", runQuery);
document.getElementById("file-analysis-btn").addEventListener("click", fileAnalysis);
document.getElementById("convert-full-btn").addEventListener("click", () => runConvertFull(false));
document.getElementById("convert-scaffold-btn").addEventListener("click", () => runConvertFull(true));
document.getElementById("open-graph-btn").addEventListener("click", () => {
  window.open("/wiki-graph", "_blank", "noopener");
});

const globalModelSelect = getGlobalModelSelect();
if (globalModelSelect) {
  globalModelSelect.addEventListener("change", onGlobalModelChange);
}

initTabs();
initRunLogLinks();

lastConfirmedModel = sessionStorage.getItem(MODEL_STORAGE_KEY) || "";

loadOllamaModels().then(() => {
  loadRawFiles();
  refreshChanges();
});
