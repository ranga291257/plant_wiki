from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.change_tracker import build_snapshot, diff_snapshots, load_snapshot, save_snapshot
from app.llm_ingest import DEFAULT_MODEL, run_ingest
from app.llm_lint import run_llm_lint
from app.llm_query import run_query, write_analysis
from app.wiki_runner import run_convert, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "raw_snapshot.json"
RAW_DIR = ROOT / "raw"
ASSETS_DIR = ROOT / "raw" / "assets"
WIKI_DIR = ROOT / "wiki"

app = FastAPI(title="Plant Wiki Control Panel")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "app" / "templates"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def api_config() -> dict[str, str]:
    return {
        "default_model": os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        "ollama_url": os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate"),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/changes")
def api_changes() -> dict[str, object]:
    current = build_snapshot(ROOT)
    baseline = load_snapshot(STATE_PATH)
    return {
        "baseline_files": len(baseline),
        "current_files": len(current),
        "changes": diff_snapshots(baseline, current),
    }


@app.post("/api/upload")
async def api_upload(
    file: UploadFile = File(...),
    destination: str = Form("raw"),
) -> dict[str, str]:
    if destination not in {"raw", "assets"}:
        raise HTTPException(status_code=400, detail="destination must be raw or assets")

    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="missing filename")
    if filename.startswith("."):
        raise HTTPException(status_code=400, detail="hidden filenames are not allowed")

    target_dir = RAW_DIR if destination == "raw" else ASSETS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    if target.exists():
        raise HTTPException(status_code=409, detail=f"file already exists: {filename}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="empty file not allowed")

    target.write_bytes(content)
    return {"status": "ok", "path": target.relative_to(ROOT).as_posix()}


@app.get("/api/raw-files")
def api_raw_files() -> dict[str, list[str]]:
    files = sorted(
        p.relative_to(ROOT).as_posix()
        for p in RAW_DIR.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )
    return {"files": files}


@app.post("/api/ingest")
def api_ingest(
    raw_file: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
) -> dict[str, object]:
    target = (ROOT / raw_file).resolve()
    if not str(target).startswith(str(RAW_DIR.resolve())):
        raise HTTPException(status_code=400, detail="path must be inside raw/")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"file not found: {raw_file}")

    result = run_ingest(target, WIKI_DIR, model=model, conversion_only=True)
    success, steps = run_pipeline(ROOT, conversion_only=True)

    return {
        "pipeline_success": success,
        "pipeline_steps": [
            {
                "command": " ".join(step.command),
                "exit_code": step.exit_code,
                "stdout": step.stdout,
                "stderr": step.stderr,
            }
            for step in steps
        ],
        "source_summary": result.source_summary_path,
        "concept_pages_created": result.concept_pages_created,
        "concept_pages_updated": result.concept_pages_updated,
        "entity_pages_created": result.entity_pages_created,
        "entity_pages_updated": result.entity_pages_updated,
        "errors": result.errors,
    }


@app.post("/api/convert-full")
def api_convert_full(
    model: str = Form(DEFAULT_MODEL),
    scaffold_only: str = Form("false"),
) -> dict[str, object]:
    do_scaffold = scaffold_only.strip().lower() in {"true", "1", "yes"}
    success, steps = run_convert(ROOT, model=model, scaffold_only=do_scaffold)
    if success:
        save_snapshot(STATE_PATH, build_snapshot(ROOT))
    return {
        "success": success,
        "steps": [
            {
                "command": " ".join(step.command),
                "exit_code": step.exit_code,
                "stdout": step.stdout,
                "stderr": step.stderr,
            }
            for step in steps
        ],
    }


@app.post("/api/query")
def api_query(
    question: str = Form(...),
    model: str = Form(DEFAULT_MODEL),
) -> dict[str, object]:
    result = run_query(question, WIKI_DIR, model=model)
    return {
        "answer": result.answer,
        "citations": result.citations,
        "suggested_slug": result.suggested_slug,
        "selected_pages": result.selected_pages,
    }


@app.post("/api/file-analysis")
def api_file_analysis(
    question: str = Form(...),
    answer: str = Form(...),
    citations: str = Form("[]"),
    slug: str = Form("analysis"),
    model: str = Form(DEFAULT_MODEL),
) -> dict[str, str]:
    try:
        parsed_citations = json.loads(citations)
        if not isinstance(parsed_citations, list):
            parsed_citations = []
    except json.JSONDecodeError:
        parsed_citations = []

    path = write_analysis(
        WIKI_DIR,
        question=question,
        answer=answer,
        citations=[str(c) for c in parsed_citations],
        slug=slug,
        model=model,
    )
    run_pipeline(ROOT, conversion_only=True)
    return {"analysis_path": path.relative_to(ROOT).as_posix()}


@app.post("/api/lint-llm")
def api_lint_llm(model: str = Form(DEFAULT_MODEL)) -> dict[str, object]:
    issues = run_llm_lint(WIKI_DIR, model=model)
    return {"issues": issues}


@app.post("/api/update")
def api_update() -> dict[str, object]:
    success, steps = run_pipeline(ROOT, conversion_only=True)
    if success:
        save_snapshot(STATE_PATH, build_snapshot(ROOT))
    return {
        "success": success,
        "steps": [
            {
                "command": " ".join(step.command),
                "exit_code": step.exit_code,
                "stdout": step.stdout,
                "stderr": step.stderr,
            }
            for step in steps
        ],
    }
