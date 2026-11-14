"""Retrieval-only benchmark (no LLM): Hit@1, Evidence Hit@3, MRR@k, Context Evidence Rate.

    python -m rag.eval_retrieval --split dev
    python -m rag.eval_retrieval --split dev --methods dense,hybrid --top-k 5 --budget 4000 --tag k5

Uses the original question text as query and the user-supplied filter (if
any). Unanswerable questions are excluded from the denominators but their
top-3 is still saved in traces for inspection.
"""
from __future__ import annotations

import argparse
import json

from . import day6
from .retrieval import METHODS, Retriever, format_context, is_hit, pack_context

QUESTIONS = day6.ROOT / "data" / "benchmark" / "questions.json"


def run_eval(
    retr: Retriever,
    *,
    split: str,
    methods: list[str] | tuple[str, ...] = METHODS,
    top_k: int = 3,
    budget: int = 3000,
    pack_mode: str = "fifo",
    no_filter: bool = False,
    tag: str = "",
) -> dict:
    questions = [q for q in json.loads(QUESTIONS.read_text(encoding="utf-8")) if q["split"] == split]
    out_dir = day6.ROOT / "results" / "retrieval" / (f"{split}-{tag}" if tag else split)
    out_dir.mkdir(parents=True, exist_ok=True)
    k = max(3, top_k)

    summary = {"split": split, "top_k_context": top_k, "budget_chars": budget,
               "pack_mode": pack_mode,
               "filters": "none" if no_filter else "user-provided", "query": "original question",
               "embedding_model": day6.EMBEDDING_MODEL, "index_strategy": day6.INDEX_STRATEGY, "methods": {}}
    traces = []
    for method in methods:
        n = hit1 = hit3 = ctx = 0
        rr = 0.0
        lat = []
        errors = []
        for q in questions:
            flt = None if no_filter else q.get("filter")
            try:
                res, dt = retr.timed_search(method, q["question"], top_k=k, filters=flt)
            except Exception as exc:
                errors.append({"query_id": q["id"], "error": str(exc)})
                traces.append({"method": method, "query_id": q["id"], "status": "error", "error": str(exc)})
                continue
            lat.append(dt)
            context, dropped = pack_context(res[:top_k], budget, mode=pack_mode, all_chunks=retr.chunks)
            formatted_ctx = format_context(context)
            row = {"method": method, "query_id": q["id"], "answerable": q["answerable"], "filter": flt,
                   "latency_s": round(dt, 4),
                   "results": [{"rank": c["rank"], "id": c["id"], "source_id": c["source_id"], "page": c["page"],
                                "score": c["score"], "hit": is_hit(c, q["gold"]) if q["answerable"] else None}
                               for c in res],
                   "context_ids": [c["id"] for c in context], "dropped_ids": dropped,
                   "context_chars": sum(len(c["text"]) for c in context),
                   "formatted_context_chars": len(formatted_ctx)}
            if q["answerable"]:
                hits = [r["hit"] for r in row["results"]]
                n += 1
                hit1 += bool(hits[:1] and hits[0])
                hit3 += any(hits[:3])
                first = next((i for i, h in enumerate(hits, 1) if h), None)
                rr += 1 / first if first else 0
                row["context_has_evidence"] = any(is_hit(c, q["gold"]) for c in context)
                ctx += row["context_has_evidence"]
            traces.append(row)
        summary["methods"][method] = {
            "n_answerable": n,
            "hit_at_1": f"{hit1}/{n}", "hit_at_1_rate": round(hit1 / n, 4) if n else None,
            "evidence_hit_at_3": f"{hit3}/{n}", "evidence_hit_at_3_rate": round(hit3 / n, 4) if n else None,
            f"mrr_at_{k}": round(rr / n, 4) if n else None,
            "context_evidence": f"{ctx}/{n}", "context_evidence_rate": round(ctx / n, 4) if n else None,
            "avg_latency_s": round(sum(lat) / len(lat), 4) if lat else None,
            "errors": errors,
            "cost_usd": 0.0,
        }

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {out_dir.name} (top_k={top_k}, budget={budget}, pack_mode={pack_mode}, filters={summary['filters']}) ===", flush=True)
    print(f"| method | Hit@1 | Evidence Hit@3 | MRR@{k} | Context Evidence | avg latency (s) |")
    print("|---|---|---|---|---|---|")
    for m, s in summary["methods"].items():
        print(f"| {m} | {s['hit_at_1']} ({s['hit_at_1_rate']}) | {s['evidence_hit_at_3']} ({s['evidence_hit_at_3_rate']}) "
              f"| {s[f'mrr_at_{k}']} | {s['context_evidence']} ({s['context_evidence_rate']}) | {s['avg_latency_s']} |", flush=True)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--top-k", type=int, default=3, help="context top-k (ranking metrics always use top-3)")
    ap.add_argument("--budget", type=int, default=3000, help="context budget in characters")
    ap.add_argument("--pack-mode", choices=["fifo", "score_dedup", "neighbor_expand"], default="fifo")
    ap.add_argument("--no-filter", action="store_true", help="ignore user-provided filters")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    retr = Retriever()
    run_eval(
        retr,
        split=args.split,
        methods=args.methods.split(","),
        top_k=args.top_k,
        budget=args.budget,
        pack_mode=args.pack_mode,
        no_filter=args.no_filter,
        tag=args.tag,
    )


if __name__ == "__main__":
    main()
