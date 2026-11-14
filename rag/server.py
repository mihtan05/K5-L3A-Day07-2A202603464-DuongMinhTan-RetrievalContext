"""Interactive Web Demo Server for Day 7 Agentic RAG & Bonus Multimodal Track.

Run:
    python -m rag.server --port 8765

Serves:
  - Static UI (`ui/index.html`, `ui/styles.css`, `ui/app.js`)
  - Cropped visual assets (`/crops/<asset_id>.png`)
  - REST API:
      GET  /api/overview
      GET  /api/questions?corpus=core|bonus&split=all|dev|test
      GET  /api/traces?corpus=core|bonus&run=<run_name>
      POST /api/ask  (live Agentic RAG + 4-method retrieval comparison)
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import day6
from .agent import LLMClient, baseline_config, improved_config, run_agentic_rag
from .bonus_ingest import BONUS_CHUNKS_PATH, BONUS_CROPS_DIR, BONUS_MANIFEST_PATH, BONUS_QUESTIONS_PATH, BONUS_STRATEGY
from .retrieval import METHODS, Retriever

UI_DIR = day6.ROOT / "ui"
CORE_CHUNKS_PATH = day6.ROOT / "data" / "chunks.json"
CORE_MANIFEST_PATH = day6.ROOT / "data" / "index_manifest.json"
CORE_QUESTIONS_PATH = day6.ROOT / "data" / "benchmark" / "questions.json"
RESULTS_DIR = day6.ROOT / "results"


class _State:
    core_retriever: Retriever | None = None
    bonus_retriever: Retriever | None = None
    llm: LLMClient | None = None

    @classmethod
    def get_retriever(cls, corpus: str) -> Retriever:
        if corpus == "bonus":
            if cls.bonus_retriever is None:
                cls.bonus_retriever = Retriever(chunks_path=BONUS_CHUNKS_PATH, index_strategy=BONUS_STRATEGY)
            return cls.bonus_retriever
        if cls.core_retriever is None:
            cls.core_retriever = Retriever(chunks_path=CORE_CHUNKS_PATH, index_strategy=day6.INDEX_STRATEGY)
        return cls.core_retriever

    @classmethod
    def get_llm(cls) -> LLMClient:
        if cls.llm is None:
            cls.llm = LLMClient(provider="gemini", model="gemini-3.5-flash-lite")
        return cls.llm


def _read_json_safe(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _enrich_chunk_meta(chunk_id: str, by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ch = by_id.get(chunk_id)
    if not ch:
        return {"id": chunk_id}
    meta = ch.get("metadata") or {}
    crop_rel = meta.get("crop_path")
    crop_url = f"/crops/{Path(crop_rel).name}" if crop_rel and (BONUS_CROPS_DIR / Path(crop_rel).name).exists() else None
    return {
        "id": ch["id"],
        "source_id": ch.get("source_id"),
        "page": ch.get("page"),
        "text": ch.get("text"),
        "modality": meta.get("modality", "text"),
        "asset_id": meta.get("asset_id"),
        "title": meta.get("title") or meta.get("section") or f"Page {ch.get('page')}",
        "section": meta.get("section"),
        "bbox": meta.get("bbox"),
        "crop_url": crop_url,
    }


def build_overview_payload() -> dict[str, Any]:
    core_manifest = _read_json_safe(CORE_MANIFEST_PATH, {})
    bonus_manifest = _read_json_safe(BONUS_MANIFEST_PATH, {})

    retrieval_runs = {}
    ret_dir = RESULTS_DIR / "retrieval"
    if ret_dir.exists():
        for p in sorted(ret_dir.glob("*.json")):
            retrieval_runs[p.stem] = _read_json_safe(p, {})
        for d in sorted(ret_dir.iterdir()):
            if d.is_dir() and (d / "summary.json").exists():
                retrieval_runs[d.name] = _read_json_safe(d / "summary.json", {})

    core_agent_runs = {}
    ag_dir = RESULTS_DIR / "agent"
    if ag_dir.exists():
        for d in sorted(ag_dir.iterdir()):
            if d.is_dir() and (d / "summary.json").exists():
                core_agent_runs[d.name] = _read_json_safe(d / "summary.json", {})

    bonus_runs = {}
    bn_dir = RESULTS_DIR / "bonus"
    if bn_dir.exists():
        for d in sorted(bn_dir.iterdir()):
            if d.is_dir() and (d / "summary.json").exists():
                bonus_runs[d.name] = _read_json_safe(d / "summary.json", {})

    # List visual assets from bonus chunks for the Asset Gallery
    bonus_chunks = _read_json_safe(BONUS_CHUNKS_PATH, []) or []
    visual_assets = []
    for c in bonus_chunks:
        meta = c.get("metadata") or {}
        if meta.get("modality") in ("table", "image_diagram", "chart") and meta.get("asset_id"):
            crop_rel = meta.get("crop_path")
            crop_url = f"/crops/{Path(crop_rel).name}" if crop_rel and (BONUS_CROPS_DIR / Path(crop_rel).name).exists() else None
            visual_assets.append(
                {
                    "chunk_id": c["id"],
                    "asset_id": meta.get("asset_id"),
                    "modality": meta.get("modality"),
                    "title": meta.get("title"),
                    "page": c.get("page"),
                    "section": meta.get("section"),
                    "bbox": meta.get("bbox"),
                    "crop_url": crop_url,
                    "text": c.get("text"),
                }
            )

    return {
        "core_manifest": core_manifest,
        "bonus_manifest": bonus_manifest,
        "retrieval_runs": retrieval_runs,
        "core_agent_runs": core_agent_runs,
        "bonus_runs": bonus_runs,
        "visual_assets": visual_assets,
    }


def build_questions_payload(corpus: str, split: str) -> list[dict[str, Any]]:
    path = BONUS_QUESTIONS_PATH if corpus == "bonus" else CORE_QUESTIONS_PATH
    items = _read_json_safe(path, []) or []
    if split in ("dev", "test"):
        items = [q for q in items if q.get("split") == split]
    return items


def build_traces_payload(corpus: str, run_name: str) -> dict[str, Any]:
    base_dir = (RESULTS_DIR / "bonus" / run_name) if corpus == "bonus" else (RESULTS_DIR / "agent" / run_name)
    traces = _read_json_safe(base_dir / "traces.json", []) or []
    reviews = _read_json_safe(base_dir / "reviews.json", []) or []
    summary = _read_json_safe(base_dir / "summary.json", {}) or {}

    q_path = BONUS_QUESTIONS_PATH if corpus == "bonus" else CORE_QUESTIONS_PATH
    questions = {q["id"]: q for q in (_read_json_safe(q_path, []) or [])}
    chunks_path = BONUS_CHUNKS_PATH if corpus == "bonus" else CORE_CHUNKS_PATH
    chunks_by_id = {c["id"]: c for c in (_read_json_safe(chunks_path, []) or [])}
    reviews_by_id = {r.get("query_id") or r.get("id"): r for r in reviews}

    enriched = []
    for t in traces:
        qid = t["query_id"]
        q = questions.get(qid, {})
        rev = reviews_by_id.get(qid, {})
        cited_details = [_enrich_chunk_meta(cid, chunks_by_id) for cid in (t.get("citations") or [])]
        context_details = [_enrich_chunk_meta(cid, chunks_by_id) for cid in (t.get("final_context_ids") or [])]
        enriched.append(
            {
                **t,
                "question": q.get("question", ""),
                "category": q.get("category") or ("unanswerable" if not q.get("answerable", True) else "answerable"),
                "answerable": q.get("answerable", True),
                "expected_answer": q.get("expected_answer") or q.get("absence_reason") or "",
                "gold": q.get("gold", []),
                "review": rev,
                "cited_chunks": cited_details,
                "context_chunks": context_details,
            }
        )
    return {"corpus": corpus, "run": run_name, "summary": summary, "traces": enriched}


def handle_live_ask(body: dict[str, Any]) -> dict[str, Any]:
    corpus = str(body.get("corpus") or "bonus").strip().lower()
    question = str(body.get("question") or "").strip()
    if not question:
        raise ValueError("Question must not be empty.")

    mode = str(body.get("config_mode") or "improved").strip().lower()
    method = str(body.get("retrieval_method") or "hybrid").strip().lower()
    if method not in METHODS:
        method = "hybrid"

    retriever = _State.get_retriever(corpus)
    by_id = retriever.by_id

    # Also compare top-3 retrieval across dense, bm25, hybrid for the UI comparison panel
    retrieval_comparison: dict[str, Any] = {}
    for m in ("dense", "bm25", "hybrid"):
        hits, dt = retriever.timed_search(m, question, top_k=3)
        retrieval_comparison[m] = {
            "latency_ms": round(dt * 1000.0, 2),
            "hits": [
                {
                    **_enrich_chunk_meta(h["id"], by_id),
                    "rank": h["rank"],
                    "score": h["score"],
                }
                for h in hits
            ],
        }

    llm = _State.get_llm()
    if mode == "baseline":
        cfg = baseline_config(provider=llm.provider, model=llm.model, corpus_mode=corpus)
    else:
        cfg = improved_config(
            retrieval_method=method,
            provider=llm.provider,
            model=llm.model,
            corpus_mode=corpus,
            top_k=5 if corpus == "bonus" else 4,
            budget_chars=4800 if corpus == "bonus" else 3200,
            max_searches=5 if corpus == "bonus" else 4,
            pack_mode="score_dedup",
        )

    trace = run_agentic_rag({"id": "live_query", "question": question}, retriever, llm, cfg)
    trace["cited_chunks"] = [_enrich_chunk_meta(cid, by_id) for cid in (trace.get("citations") or [])]
    trace["context_chunks"] = [_enrich_chunk_meta(cid, by_id) for cid in (trace.get("final_context_ids") or [])]
    return {
        "corpus": corpus,
        "config": cfg.to_dict(),
        "trace": trace,
        "retrieval_comparison": retrieval_comparison,
    }


class DemoRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return  # Keep console clean

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        mime, _ = mimetypes.guess_type(str(path))
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        qs = parse_qs(parsed.query)

        if route == "/api/overview":
            self._send_json(build_overview_payload())
            return
        if route == "/api/questions":
            corpus = (qs.get("corpus") or ["bonus"])[0]
            split = (qs.get("split") or ["all"])[0]
            self._send_json(build_questions_payload(corpus, split))
            return
        if route == "/api/traces":
            corpus = (qs.get("corpus") or ["bonus"])[0]
            default_run = "test-selected" if corpus == "bonus" else "test-improved"
            run_name = (qs.get("run") or [default_run])[0]
            self._send_json(build_traces_payload(corpus, run_name))
            return
        if route.startswith("/crops/"):
            fname = Path(route.removeprefix("/crops/")).name
            self._send_file(BONUS_CROPS_DIR / fname)
            return

        if route in ("/", "/index.html"):
            self._send_file(UI_DIR / "index.html")
            return
        rel = route.lstrip("/")
        candidate = (UI_DIR / rel).resolve()
        if str(candidate).startswith(str(UI_DIR.resolve())) and candidate.is_file():
            self._send_file(candidate)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/ask":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            body = json.loads(raw)
            result = handle_live_ask(body)
            self._send_json(result)
        except Exception as exc:
            traceback.print_exc()
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), DemoRequestHandler)
    print(f"Day 7 Agentic RAG & Multimodal Demo UI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start Day 7 Agentic RAG Demo UI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)

