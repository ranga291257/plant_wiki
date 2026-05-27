async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function renderChangeList(title, items) {
  if (!items.length) return `<h4>${title}</h4><p>None</p>`;
  const lis = items.map((i) => `<li><code>${i}</code></li>`).join("");
  return `<h4>${title}</h4><ul>${lis}</ul>`;
}

function spinner() {
  return `<span class="spinner"></span>`;
}

function renderSteps(steps) {
  return (steps || []).map((s) => {
    const cls = s.exit_code === 0 ? "ok" : "bad";
    return `<h4 class="${cls}">${s.command} (exit ${s.exit_code})</h4>
            <pre>${s.stdout || ""}${s.stderr ? "\n" + s.stderr : ""}</pre>`;
  }).join("");
}

let defaultModel = "gemma4:e2b";

async function loadConfig() {
  try {
    const cfg = await getJson("/api/config");
    defaultModel = cfg.default_model || defaultModel;
    for (const id of ["model-input", "query-model-input", "convert-model-input"]) {
      const el = document.getElementById(id);
      if (el && !el.value) el.value = defaultModel;
    }
  } catch (_) {
    /* keep fallback */
  }
}

async function loadRawFiles() {
  const sel = document.getElementById("raw-file-select");
  try {
    const data = await getJson("/api/raw-files");
    sel.innerHTML = data.files.length
      ? data.files.map((f) => `<option value="${f}">${f}</option>`).join("")
      : '<option value="">No raw files found</option>';
  } catch (err) {
    sel.innerHTML = `<option value="">Error loading files</option>`;
  }
}

async function runConvertFull(scaffoldOnly) {
  const model = document.getElementById("convert-model-input").value.trim() || defaultModel;
  const statusEl = document.getElementById("convert-status");
  const resultEl = document.getElementById("convert-result");
  const btnFull = document.getElementById("convert-full-btn");
  const btnScaffold = document.getElementById("convert-scaffold-btn");

  if (!scaffoldOnly && !confirm("Run full LLM conversion on all raw/ markdown? This may take several minutes and rebuilds wiki pages.")) {
    return;
  }

  btnFull.disabled = true;
  btnScaffold.disabled = true;
  statusEl.innerHTML = `${spinner()} Running ${scaffoldOnly ? "scaffold-only" : "full"} conversion...`;
  resultEl.innerHTML = "";

  const formData = new FormData();
  formData.append("model", model);
  formData.append("scaffold_only", scaffoldOnly ? "true" : "false");

  try {
    const data = await getJson("/api/convert-full", { method: "POST", body: formData });
    statusEl.innerHTML = data.success
      ? `<span class="ok">Conversion finished.</span>`
      : `<span class="bad">Conversion failed.</span>`;
    resultEl.innerHTML = renderSteps(data.steps);
    await loadRawFiles();
    await refreshChanges();
  } catch (err) {
    statusEl.innerHTML = `<span class="bad">${err.message}</span>`;
  } finally {
    btnFull.disabled = false;
    btnScaffold.disabled = false;
  }
}

async function uploadFile(event) {
  event.preventDefault();
  const status = document.getElementById("upload-status");
  const input = document.getElementById("file");
  const destination = document.getElementById("destination").value;
  if (!input.files.length) {
    status.innerHTML = `<span class="bad">Select a file first.</span>`;
    return;
  }
  status.innerHTML = `${spinner()} Uploading...`;
  const formData = new FormData();
  formData.append("file", input.files[0]);
  formData.append("destination", destination);
  try {
    const data = await getJson("/api/upload", { method: "POST", body: formData });
    status.innerHTML = `<span class="ok">Uploaded: <code>${data.path}</code></span>`;
    input.value = "";
    await loadRawFiles();
    await refreshChanges();
  } catch (err) {
    status.innerHTML = `<span class="bad">${err.message}</span>`;
  }
}

async function runIngest() {
  const rawFile = document.getElementById("raw-file-select").value;
  const model = document.getElementById("model-input").value.trim() || defaultModel;
  const statusEl = document.getElementById("ingest-status");
  const resultEl = document.getElementById("ingest-result");
  const btn = document.getElementById("ingest-btn");

  if (!rawFile) {
    statusEl.innerHTML = `<span class="bad">Select a raw file first.</span>`;
    return;
  }

  btn.disabled = true;
  statusEl.innerHTML = `${spinner()} Ingesting <code>${rawFile}</code> (30–120s)...`;
  resultEl.innerHTML = "";

  const formData = new FormData();
  formData.append("raw_file", rawFile);
  formData.append("model", model);

  try {
    const data = await getJson("/api/ingest", { method: "POST", body: formData });
    const errors = data.errors || [];
    const pipeOk = data.pipeline_success !== false;
    statusEl.innerHTML = !pipeOk
      ? `<span class="bad">Ingest ran but index/lint pipeline failed.</span>`
      : errors.length
        ? `<span class="warn">Ingest done with ${errors.length} warning(s).</span>`
        : `<span class="ok">Ingest completed.</span>`;

    let html = "";
    if (data.source_summary) {
      html += `<h4>Source summary</h4><ul><li><code>${data.source_summary}</code></li></ul>`;
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
        items.forEach((p) => { html += `<li><code>${p}</code></li>`; });
        html += "</ul>";
      }
    }
    if (data.pipeline_steps) html += `<h4>Pipeline</h4>${renderSteps(data.pipeline_steps)}`;
    if (errors.length) {
      html += `<h4 class="warn">Warnings</h4><ul>`;
      errors.forEach((e) => { html += `<li class="warn">${e}</li>`; });
      html += "</ul>";
    }
    resultEl.innerHTML = html;
    await refreshChanges();
  } catch (err) {
    statusEl.innerHTML = `<span class="bad">Ingest failed: ${err.message}</span>`;
  } finally {
    btn.disabled = false;
  }
}

let lastQuery = null;

async function runQuery() {
  const question = document.getElementById("query-input").value.trim();
  const model = document.getElementById("query-model-input").value.trim() || defaultModel;
  const statusEl = document.getElementById("query-status");
  const resultEl = document.getElementById("query-result");
  const btn = document.getElementById("query-btn");

  if (!question) {
    statusEl.innerHTML = `<span class="bad">Enter a question first.</span>`;
    return;
  }

  btn.disabled = true;
  statusEl.innerHTML = `${spinner()} Querying wiki...`;
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
    statusEl.innerHTML = `<span class="ok">Query complete.</span>`;
    const selected = (data.selected_pages || []).map((p) => `<li><code>${p}</code></li>`).join("");
    const citations = (lastQuery.citations || []).map((c) => `<li><code>${c}</code></li>`).join("");
    resultEl.innerHTML = `
      <h4>Answer</h4>
      <pre>${lastQuery.answer}</pre>
      <h4>Selected pages</h4>
      <ul>${selected || "<li>None</li>"}</ul>
      <h4>Citations</h4>
      <ul>${citations || "<li>None</li>"}</ul>
    `;
  } catch (err) {
    statusEl.innerHTML = `<span class="bad">Query failed: ${err.message}</span>`;
  } finally {
    btn.disabled = false;
  }
}

async function fileAnalysis() {
  const statusEl = document.getElementById("file-analysis-status");
  const slug = document.getElementById("analysis-slug-input").value.trim();
  if (!lastQuery) {
    statusEl.innerHTML = `<span class="bad">Run a query first.</span>`;
    return;
  }
  statusEl.innerHTML = `${spinner()} Writing analysis page...`;
  try {
    const formData = new FormData();
    formData.append("question", lastQuery.question);
    formData.append("answer", lastQuery.answer);
    formData.append("citations", JSON.stringify(lastQuery.citations || []));
    formData.append("slug", slug || lastQuery.suggested_slug || "analysis");
    formData.append("model", lastQuery.model);
    const data = await getJson("/api/file-analysis", { method: "POST", body: formData });
    statusEl.innerHTML = `<span class="ok">Analysis written: <code>${data.analysis_path}</code></span>`;
    await refreshChanges();
  } catch (err) {
    statusEl.innerHTML = `<span class="bad">${err.message}</span>`;
  }
}

async function runAiLint() {
  const status = document.getElementById("run-status");
  const stepsDiv = document.getElementById("run-steps");
  status.innerHTML = `${spinner()} Running AI lint...`;
  stepsDiv.innerHTML = "";
  try {
    const model = document.getElementById("query-model-input").value.trim() || defaultModel;
    const formData = new FormData();
    formData.append("model", model);
    const data = await getJson("/api/lint-llm", { method: "POST", body: formData });
    const issues = data.issues || [];
    if (!issues.length) {
      status.innerHTML = `<span class="ok">AI lint found no semantic issues.</span>`;
      return;
    }
    status.innerHTML = `<span class="warn">AI lint found ${issues.length} issue(s).</span>`;
    stepsDiv.innerHTML = `<h4 class="warn">AI lint issues</h4><ul>${issues.map((i) => `<li>${i}</li>`).join("")}</ul>`;
  } catch (err) {
    status.innerHTML = `<span class="bad">AI lint failed: ${err.message}</span>`;
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
    summary.innerHTML = `<span class="bad">${err.message}</span>`;
  }
}

async function runUpdate() {
  const status = document.getElementById("run-status");
  const stepsDiv = document.getElementById("run-steps");
  status.innerHTML = `${spinner()} Rebuilding index and linting...`;
  stepsDiv.innerHTML = "";
  try {
    const data = await getJson("/api/update", { method: "POST" });
    status.innerHTML = data.success
      ? `<span class="ok">Update completed.</span>`
      : `<span class="bad">Update failed — see lint output.</span>`;
    stepsDiv.innerHTML = renderSteps(data.steps);
    await refreshChanges();
  } catch (err) {
    status.innerHTML = `<span class="bad">${err.message}</span>`;
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

loadConfig().then(() => {
  loadRawFiles();
  refreshChanges();
});
