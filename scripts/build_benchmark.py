"""Build the Day 7 benchmark from the Day 6 benchmark + 4 unanswerable questions.

Usage:
    python scripts/build_benchmark.py --day6 ../K5-L3A-Day06-2A202603464-DataIngestionEngineering/benchmark/questions.json

Day 6 answerable questions are converted to the Day 7 schema (data/README.md):
the primary gold and every `alternative_gold` become entries of `gold`.
Unanswerable questions were written to be close to the corpus topics; their
absence was checked by keyword search over the full text of both PDFs
(see `absence_check`), not only by retrieval top-k.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "benchmark" / "questions.json"

UNANSWERABLE = [
    {
        "id": "u01",
        "split": "dev",
        "question": "What was Viet Nam's real GDP growth rate (y/y) in the first quarter of 2025?",
        "near_topic": "q08 (full-year 2024 GDP growth, Mar-2025 report)",
        "absence_reason": "The Mar-2025 report covers data up to Q4-2024 and gives forecasts for 2025, but no realized Q1-2025 GDP figure.",
        "absence_check": "Full-text search of both PDFs for 'Q1-2025', 'Q1 2025', 'first quarter of 2025', '2025Q1': 0 matches (only Q1-19..Q1-24 chart labels).",
    },
    {
        "id": "u02",
        "split": "dev",
        "question": "What was the non-performing loan ratio of Vietcombank, Viet Nam's largest state-owned commercial bank, at end-2023?",
        "near_topic": "q04 (system-wide NPL ratio 4.6% / problem loans 7.9%)",
        "absence_reason": "The reports discuss NPLs at banking-system level only; no individual bank is named.",
        "absence_check": "Full-text search for 'Vietcombank', 'BIDV', 'VietinBank', 'Agribank', 'Techcombank': 0 matches.",
    },
    {
        "id": "u03",
        "split": "test",
        "question": "How many electric two-wheelers did VinFast sell in Viet Nam in 2024?",
        "near_topic": "q11/q18 (e-mobility special focus, e-2Ws)",
        "absence_reason": "The e-mobility section discusses the market and pathways, not sales of a specific company.",
        "absence_check": "Full-text search for 'VinFast': 0 matches in both PDFs.",
    },
    {
        "id": "u04",
        "split": "test",
        "question": "By what percentage did Viet Nam raise the regional minimum wage for private-sector workers from July 2024?",
        "near_topic": "q10 (public-sector wage hike from July 2024)",
        "absence_reason": "The reports mention the public-sector/civil-service wage increase, not the private-sector regional minimum wage.",
        "absence_check": "Full-text search for 'minimum wage' and 'regional minimum': 0 matches; 'wage' hits refer to public wages/wage growth only.",
    },
]


def convert(q: dict) -> dict:
    gold = [{"source_id": q["gold_source_id"], "page": q["gold_page"], "evidence": q["evidence_quote"]}]
    for alt in q.get("alternative_gold") or []:
        gold.append({"source_id": alt["source_id"], "page": alt["page"], "evidence": alt["evidence_quote"]})
    return {
        "id": q["id"],
        "split": q["split"],
        "type": q.get("type"),
        "question": q["question"],
        "answerable": True,
        "expected_answer": q["expected_answer"],
        "gold": gold,
        "filter": q.get("filter"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day6", required=True, type=Path)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    day6 = json.loads(args.day6.read_text(encoding="utf-8"))
    answerable = [convert(q) for q in day6["questions"]]
    unanswerable = [
        {**u, "answerable": False, "expected_behavior": "search_and_abstain", "filter": None}
        for u in UNANSWERABLE
    ]
    questions = answerable + unanswerable

    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for split, need_a, need_u in (("dev", 15, 2), ("test", 5, 2)):
        a = sum(q["split"] == split and q["answerable"] for q in questions)
        u = sum(q["split"] == split and not q["answerable"] for q in questions)
        assert a >= need_a and u >= need_u, f"{split}: {a} answerable / {u} unanswerable"
        print(f"{split}: {a} answerable + {u} unanswerable")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(questions)} questions -> {args.output}")


if __name__ == "__main__":
    main()
