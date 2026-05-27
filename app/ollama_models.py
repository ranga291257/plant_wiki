from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.llm_ingest import OLLAMA_URL

EMBED_FAMILIES = frozenset({"nomic-bert", "bert"})


@dataclass
class OllamaModelsResult:
    models: list[str]
    default_model: str
    ollama_reachable: bool
    error: str | None = None


def ollama_base_url(generate_url: str | None = None) -> str:
    url = (generate_url or OLLAMA_URL).rstrip("/")
    if url.endswith("/api/generate"):
        return url[: -len("/api/generate")]
    if "/api/" in url:
        return url.split("/api/")[0]
    return url


def is_cloud_model(name: str) -> bool:
    lower = name.lower()
    return ":cloud" in lower or lower.endswith("-cloud")


def is_embedding_model(name: str, family: str = "") -> bool:
    lower = name.lower()
    if "embed" in lower:
        return True
    fam = family.lower()
    return fam in EMBED_FAMILIES


def filter_chat_models(entries: list[dict]) -> list[str]:
    kept: list[str] = []
    for entry in entries:
        name = (entry.get("name") or entry.get("model") or "").strip()
        if not name:
            continue
        details = entry.get("details") or {}
        family = str(details.get("family") or "")
        if is_cloud_model(name) or is_embedding_model(name, family):
            continue
        kept.append(name)
    return sorted(set(kept))


def pick_default_model(models: list[str], env_model: str | None = None) -> str:
    env = (env_model or os.environ.get("LLM_MODEL") or "").strip()
    if env and env in models:
        return env
    if env and not is_cloud_model(env) and "embed" not in env.lower():
        return env
    return models[0] if models else ""


def fetch_ollama_models(generate_url: str | None = None) -> OllamaModelsResult:
    base = ollama_base_url(generate_url)
    tags_url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(tags_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        env = os.environ.get("LLM_MODEL", "").strip()
        return OllamaModelsResult(
            models=[],
            default_model=env,
            ollama_reachable=False,
            error=str(exc.reason if hasattr(exc, "reason") else exc),
        )
    except (json.JSONDecodeError, TimeoutError, OSError) as exc:
        env = os.environ.get("LLM_MODEL", "").strip()
        return OllamaModelsResult(
            models=[],
            default_model=env,
            ollama_reachable=False,
            error=str(exc),
        )

    entries = payload.get("models") or []
    models = filter_chat_models(entries)
    default = pick_default_model(models)
    return OllamaModelsResult(
        models=models,
        default_model=default,
        ollama_reachable=True,
        error=None,
    )
