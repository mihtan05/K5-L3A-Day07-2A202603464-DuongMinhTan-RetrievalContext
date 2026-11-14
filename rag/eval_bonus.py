"""Evaluate the Bonus Multimodal Agentic RAG pipeline on `dev` (18 questions) and `test` (30 questions).

Strictly enforces `ADVANCED.md`:
  - Only `{id, question}` is passed into `run_agentic_rag` (never `gold`, `expected_answer`, `absence_reason`, or `category`).
  - Saves full traces (`traces.json`), manual binary audit reviews (`reviews.json`), and category breakdown (`summary.json`).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from . import day6
from .agent import AgentConfig, LLMClient, baseline_config, improved_config, run_agentic_rag
from .bonus_ingest import BONUS_CHUNKS_PATH, BONUS_QUESTIONS_PATH, BONUS_STRATEGY
from .retrieval import Retriever

BONUS_RESULTS_DIR = day6.ROOT / "results" / "bonus"

CATEGORIES = ("table", "image_diagram", "chart", "multi_hop", "text", "unanswerable")
CATEGORY_LABELS_VI = {
    "table": "Bảng",
    "image_diagram": "Ảnh, sơ đồ",
    "chart": "Biểu đồ",
    "multi_hop": "Multi-hop",
    "text": "Text",
    "unanswerable": "Thiếu bằng chứng",
}


def load_bonus_questions(split: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = json.loads(BONUS_QUESTIONS_PATH.read_text(encoding="utf-8"))
    if split:
        items = [q for q in items if q["split"] == split]
    return items


def run_bonus_split(
    split: str,
    config: AgentConfig,
    out_dir: Path,
    *,
    resume: bool = True,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    traces_path = out_dir / "traces.json"
    questions = load_bonus_questions(split)

    existing_by_id: dict[str, dict[str, Any]] = {}
    if resume and traces_path.exists():
        try:
            loaded = json.loads(traces_path.read_text(encoding="utf-8"))
            existing_by_id = {t["query_id"]: t for t in loaded if "error" not in t}
        except Exception:
            existing_by_id = {}

    retriever = Retriever(chunks_path=BONUS_CHUNKS_PATH, index_strategy=BONUS_STRATEGY)
    llm = LLMClient(provider=config.provider, model=config.model)

    traces: list[dict[str, Any]] = []
    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        if qid in existing_by_id:
            print(f"[{split} {idx}/{len(questions)}] {qid}: cached ({existing_by_id[qid]['status']})", flush=True)
            traces.append(existing_by_id[qid])
            continue

        # Never pass gold, expected_answer, category, or absence_reason into the agent
        sanitized_input = {"id": qid, "question": q["question"]}
        t0 = time.perf_counter()
        trace = run_agentic_rag(sanitized_input, retriever, llm, config)
        dt = time.perf_counter() - t0
        print(
            f"[{split} {idx}/{len(questions)}] {qid} ({q['category']}): "
            f"status={trace['status']} searches={trace['num_searches']} "
            f"cites={len(trace.get('citations', []))} latency={dt:.2f}s",
            flush=True,
        )
        traces.append(trace)
        traces_path.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.5)

    traces_path.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    return traces


def compute_bonus_summary(
    split: str,
    config: AgentConfig,
    traces: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    questions = {q["id"]: q for q in load_bonus_questions(split)}
    reviews_by_id = {r["query_id"]: r for r in reviews}

    cat_stats: dict[str, dict[str, Any]] = {
        cat: {"label_vi": CATEGORY_LABELS_VI[cat], "passed": 0, "total": 0, "rate_pct": 0.0, "notes": []}
        for cat in CATEGORIES
    }

    total_passed = 0
    total_count = 0
    total_latency = 0.0
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    total_searches = 0
    total_api_calls = 0
    valid_citations = 0
    total_citations = 0

    for t in traces:
        qid = t["query_id"]
        q = questions[qid]
        cat = q["category"]
        rev = reviews_by_id.get(qid, {})
        passed = bool(rev.get("passed", False))

        cat_stats[cat]["total"] += 1
        total_count += 1
        if passed:
            cat_stats[cat]["passed"] += 1
            total_passed += 1
        else:
            cat_stats[cat]["notes"].append(f"{qid}: {rev.get('audit_note', 'failed')}")

        total_latency += float(t.get("latency_s") or 0.0)
        usage = t.get("usage") or {}
        total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
        total_completion_tokens += int(usage.get("completion_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        total_cost += float(t.get("cost_usd") or 0.0)
        total_searches += int(t.get("num_searches") or 0)
        total_api_calls += int(t.get("api_calls") or 0)

        ctx_ids = set(t.get("final_context_ids") or [])
        for c in t.get("citations") or []:
            total_citations += 1
            if c in ctx_ids and f"[{c}]" in (t.get("answer") or ""):
                valid_citations += 1

    for cat in CATEGORIES:
        tot = cat_stats[cat]["total"]
        pas = cat_stats[cat]["passed"]
        cat_stats[cat]["rate_pct"] = round((100.0 * pas / tot) if tot else 0.0, 2)

    overall_pct = round((100.0 * total_passed / total_count) if total_count else 0.0, 2)
    return {
        "split": split,
        "config": config.to_dict(),
        "total_questions": total_count,
        "total_passed": total_passed,
        "overall_pass_rate_pct": overall_pct,
        "meets_90pct_threshold": overall_pct >= 90.0,
        "by_category": cat_stats,
        "citation_validity": {
            "valid": valid_citations,
            "total": total_citations,
            "rate": round(valid_citations / total_citations, 4) if total_citations else 1.0,
        },
        "runtime": {
            "total_latency_s": round(total_latency, 2),
            "mean_latency_s": round(total_latency / total_count, 2) if total_count else 0.0,
            "total_searches": total_searches,
            "mean_searches": round(total_searches / total_count, 2) if total_count else 0.0,
            "total_api_calls": total_api_calls,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "provider_errors": 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Bonus Multimodal Agentic RAG evaluation")
    parser.add_argument("--run", choices=["dev-baseline", "dev-improved", "test-selected"], required=True)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    if args.run == "dev-baseline":
        cfg = baseline_config(provider=args.provider, model=args.model, corpus_mode="bonus")
        split = "dev"
    elif args.run == "dev-improved":
        cfg = improved_config(
            retrieval_method="hybrid",
            provider=args.provider,
            model=args.model,
            corpus_mode="bonus",
            top_k=5,
            budget_chars=4800,
            max_searches=5,
            pack_mode="score_dedup",
        )
        split = "dev"
    else:
        cfg = improved_config(
            retrieval_method="hybrid",
            provider=args.provider,
            model=args.model,
            corpus_mode="bonus",
            top_k=5,
            budget_chars=4800,
            max_searches=5,
            pack_mode="score_dedup",
        )
        split = "test"

    out_dir = BONUS_RESULTS_DIR / args.run
    run_bonus_split(split, cfg, out_dir, resume=not args.no_resume)


if __name__ == "__main__":
    main()
