"""Run the real Agentic RAG pipeline on dev or test and save traces compatible with starter/agent_metrics.py.

Usage:
    python -m rag.eval_agent --split dev --config baseline
    python -m rag.eval_agent --split dev --config improved --method hybrid_rerank
    python -m rag.eval_agent --split test --config baseline
    python -m rag.eval_agent --split test --config improved --method hybrid_rerank

Never exposes `gold`, `expected_answer`, `absence_reason`, or ground-truth `filter` to the agent.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from . import day6
from .agent import (
    AgentConfig,
    LLMClient,
    ProviderError,
    baseline_config,
    improved_config,
    run_agentic_rag,
)
from .retrieval import METHODS, RetrievalError, Retriever

QUESTIONS_PATH = day6.ROOT / "data" / "benchmark" / "questions.json"


def _build_config(args: argparse.Namespace) -> AgentConfig:
    provider = args.provider or os.getenv("PROVIDER") or "gemini"
    model = args.model or os.getenv("MODEL") or "gemini-2.5-flash-lite"
    if args.config == "baseline":
        base = baseline_config(provider=provider, model=model)
    else:
        base = improved_config(
            retrieval_method=args.method or "hybrid_rerank",
            provider=provider,
            model=model,
        )
    return AgentConfig(
        name=args.tag or base.name,
        retrieval_method=args.method or base.retrieval_method,
        top_k=args.top_k if args.top_k is not None else base.top_k,
        budget_chars=args.budget if args.budget is not None else base.budget_chars,
        max_searches=args.max_searches if args.max_searches is not None else base.max_searches,
        pack_mode=args.pack_mode or base.pack_mode,
        allow_filter_inference=(
            args.allow_filter_inference if args.allow_filter_inference is not None else base.allow_filter_inference
        ),
        enable_multi_tool=(
            args.enable_multi_tool if args.enable_multi_tool is not None else base.enable_multi_tool
        ),
        provider=provider,
        model=model,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--config", choices=["baseline", "improved"], required=True)
    ap.add_argument("--method", choices=list(METHODS), default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--max-searches", type=int, default=None)
    ap.add_argument("--pack-mode", choices=["fifo", "score_dedup", "neighbor_expand"], default=None)
    ap.add_argument("--allow-filter-inference", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--enable-multi-tool", action=argparse.BooleanOptionalAction, default=None)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--tag", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds to sleep between queries")
    ap.add_argument("--resume", action="store_true", help="skip queries that already succeeded in traces.json")
    args = ap.parse_args()

    cfg = _build_config(args)
    run_dir_name = f"{args.split}-{cfg.name}"
    out_dir = day6.ROOT / "results" / "agent" / run_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    all_questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = [q for q in all_questions if q["split"] == args.split]
    if args.limit > 0:
        questions = questions[: args.limit]

    cases = [{"id": q["id"], "split": q["split"], "answerable": q["answerable"]} for q in questions]
    (out_dir / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "config.json").write_text(
        json.dumps(
            {
                "split": args.split,
                "config": cfg.to_dict(),
                "n_questions": len(questions),
                "user_filters_passed_to_agent": False,
                "gold_exposed_to_agent": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    traces_path = out_dir / "traces.json"
    existing_by_id: dict[str, dict[str, Any]] = {}
    if args.resume and traces_path.exists():
        for t in json.loads(traces_path.read_text(encoding="utf-8")):
            if t.get("status") in ("answered", "abstain"):
                existing_by_id[t["query_id"]] = t

    retriever = Retriever()
    llm = LLMClient(provider=cfg.provider, model=cfg.model)

    traces_by_id: dict[str, dict[str, Any]] = dict(existing_by_id)
    for idx, q in enumerate(questions, start=1):
        qid = q["id"]
        if qid in traces_by_id:
            print(f"[{idx}/{len(questions)}] {qid}: cached ({traces_by_id[qid]['status']})", flush=True)
            continue

        # Never leak gold, expected_answer, absence_reason, or benchmark filter into agent loop
        public_item = {"id": qid, "question": q["question"]}
        try:
            trace = run_agentic_rag(public_item, retriever, llm, cfg, user_filter=None)
            trace["split"] = q["split"]
            trace["question"] = q["question"]
            trace["answerable"] = q["answerable"]
            traces_by_id[qid] = trace
            print(
                f"[{idx}/{len(questions)}] {qid}: status={trace['status']} "
                f"searches={trace['num_searches']} cites={trace['citations']} "
                f"latency={trace['latency_s']}s tokens={trace['usage']['total_tokens']}",
                flush=True,
            )
        except (ProviderError, RetrievalError, Exception) as exc:
            traces_by_id[qid] = {
                "query_id": qid,
                "split": q["split"],
                "question": q["question"],
                "answerable": q["answerable"],
                "status": "error",
                "error": str(exc),
                "answer": "",
                "citations": [],
                "events": [],
                "num_searches": 0,
                "api_calls": 0,
                "latency_s": 0.0,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "cost_usd": 0.0,
            }
            print(f"[{idx}/{len(questions)}] {qid}: ERROR -> {exc}", flush=True)

        ordered_traces = [traces_by_id[item["id"]] for item in questions if item["id"] in traces_by_id]
        traces_path.write_text(json.dumps(ordered_traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if idx < len(questions) and args.sleep > 0:
            time.sleep(args.sleep)

    ordered_traces = [traces_by_id[item["id"]] for item in questions if item["id"] in traces_by_id]
    n_ans = sum(t["status"] == "answered" for t in ordered_traces)
    n_abs = sum(t["status"] == "abstain" for t in ordered_traces)
    n_err = sum(t["status"] == "error" for t in ordered_traces)
    total_tok = sum(t.get("usage", {}).get("total_tokens", 0) for t in ordered_traces)
    total_cost = sum(t.get("cost_usd", 0.0) for t in ordered_traces)
    total_lat = sum(t.get("latency_s", 0.0) for t in ordered_traces)
    print(
        f"Done -> {out_dir} | answered={n_ans} abstain={n_abs} error={n_err} "
        f"| total_tokens={total_tok} cost_usd={total_cost:.6f} total_s={total_lat:.2f}"
    )


if __name__ == "__main__":
    main()

