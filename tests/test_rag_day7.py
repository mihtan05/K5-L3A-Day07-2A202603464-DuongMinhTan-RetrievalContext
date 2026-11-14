"""Unit tests for Day 7 retrieval context packing and agentic RAG loop."""
from __future__ import annotations

import json
import unittest

from rag.agent import (
    AgentConfig,
    ProviderError,
    _sanitize_filter,
    _validate_citations,
    baseline_config,
    improved_config,
    run_agentic_rag,
)
from rag.retrieval import RetrievalError, format_chunk, format_context, pack_context


def _mk_chunk(cid: str, text: str, page: int = 1, score: float = 0.5, rank: int = 1) -> dict:
    return {
        "id": cid,
        "text": text,
        "source_id": "doc_a",
        "source": "doc_a.pdf",
        "page": page,
        "metadata": {"year": 2024, "section": "overview"},
        "score": score,
        "rank": rank,
    }


class ContextPackingTests(unittest.TestCase):
    def test_fifo_vs_score_dedup_and_pack_score(self):
        c1 = _mk_chunk("c1", "Low score first chunk.", score=0.2, rank=1)
        c2 = _mk_chunk("c2", "High score second chunk.", score=0.9, rank=2)
        c2_dup = _mk_chunk("c2", "High score second chunk.", score=0.95, rank=1)
        budget = len(format_chunk(c2)) + 10

        kept_fifo, dropped_fifo = pack_context([c1, c2], budget, mode="fifo")
        self.assertEqual([c["id"] for c in kept_fifo], ["c1"])
        self.assertEqual(dropped_fifo, ["c2"])

        c1_ps = {**c1, "pack_score": 0.1}
        c2_ps = {**c2_dup, "pack_score": 0.8}
        kept_score, dropped_score = pack_context([c1_ps, c2_ps], budget, mode="score_dedup")
        self.assertEqual([c["id"] for c in kept_score], ["c2"])
        self.assertEqual(dropped_score, ["c1"])
        self.assertLessEqual(len(format_context(kept_score)), budget)

    def test_neighbor_expand_respects_page_and_budget(self):
        all_chunks = [
            _mk_chunk("p1_0", "Page 1 chunk 0.", page=1),
            _mk_chunk("p1_1", "Page 1 chunk 1.", page=1),
            _mk_chunk("p2_0", "Page 2 chunk 0.", page=2),
        ]
        seed = {**all_chunks[1], "score": 0.9, "rank": 1}
        kept, _ = pack_context([seed], 1000, mode="neighbor_expand", all_chunks=all_chunks)
        self.assertEqual([c["id"] for c in kept], ["p1_1", "p1_0"])


class AgentHelperTests(unittest.TestCase):
    def test_sanitize_filter_and_validate_citations(self):
        self.assertIsNone(_sanitize_filter({"year": 2024}, allow_inference=False, user_filter=None))
        self.assertEqual(
            _sanitize_filter({"year": 2025, "section": "overview"}, allow_inference=True, user_filter=None),
            {"year": 2025, "section": "overview"},
        )
        self.assertIsNone(_sanitize_filter({"year": 2099, "section": "bad"}, allow_inference=True, user_filter=None))

        ok, issues = _validate_citations("GDP grew 6.4% [c1].", ["c1"], {"c1", "c2"})
        self.assertTrue(ok, issues)
        ok_bad, _ = _validate_citations("GDP grew 6.4% [c9].", ["c9"], {"c1"})
        self.assertFalse(ok_bad)
        ok_no_inline, _ = _validate_citations("GDP grew 6.4%.", ["c1"], {"c1"})
        self.assertFalse(ok_no_inline)


class FakeLLM:
    def __init__(self, responses: list[dict]):
        self._iter = iter(responses)

    def complete(self, messages, tools=None, *, temperature=0.0, max_tokens=1024):
        resp = next(self._iter)
        if isinstance(resp, Exception):
            raise resp
        return {
            "message": resp,
            "tool_calls": resp.get("tool_calls") or [],
            "content": resp.get("content") or "",
            "finish_reason": "tool_calls",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "cost_usd": 0.0,
        }


class FakeRetriever:
    def __init__(self, chunks_by_call: list[list[dict]] | Exception):
        self.chunks = [_mk_chunk("c1", "GDP grew 6.4% in H1-2024.", page=13)]
        self._data = chunks_by_call
        self.calls: list[tuple] = []
        self._idx = 0

    def timed_search(self, method: str, query: str, *, top_k: int, filters=None):
        self.calls.append((method, query, top_k, filters))
        if isinstance(self._data, Exception):
            raise self._data
        hits = self._data[min(self._idx, len(self._data) - 1)]
        self._idx += 1
        return hits, 0.01


def _tc(tc_id: str, name: str, args: dict) -> dict:
    return {"id": tc_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class AgentLoopTests(unittest.TestCase):
    def test_multi_tool_search_and_submit_answer(self):
        cfg = improved_config(retrieval_method="hybrid_rerank", budget_chars=2000, max_searches=3)
        llm = FakeLLM([
            {"role": "assistant", "tool_calls": [_tc("t1", "search_documents", {"query": "GDP H1 2024", "year": 2024})]},
            {"role": "assistant", "tool_calls": [_tc("t2", "submit_answer", {"answer": "GDP grew 6.4% [c1].", "citations": ["c1"]})]},
        ])
        retr = FakeRetriever([[_mk_chunk("c1", "GDP grew 6.4% in H1-2024.", page=13, score=0.9, rank=1)]])
        trace = run_agentic_rag({"id": "q01", "question": "GDP H1-2024?"}, retr, llm, cfg)
        self.assertEqual(trace["status"], "answered")
        self.assertEqual(trace["citations"], ["c1"])
        self.assertEqual(retr.calls[0][0], "hybrid_rerank")
        self.assertEqual(retr.calls[0][3], {"year": 2024})
        self.assertEqual(trace["events"][0]["event"], "search")
        self.assertEqual(trace["events"][0]["tool_name"], "search_documents")

    def test_abstain_after_search(self):
        cfg = baseline_config()
        llm = FakeLLM([
            {"role": "assistant", "tool_calls": [_tc("t1", "search_documents", {"query": "Q1 2025 GDP"})]},
            {"role": "assistant", "tool_calls": [_tc("t2", "abstain", {"reason": "No Q1-2025 figure."})]},
        ])
        retr = FakeRetriever([[]])
        trace = run_agentic_rag({"id": "u01", "question": "Q1 2025 GDP?"}, retr, llm, cfg)
        self.assertEqual(trace["status"], "abstain")
        self.assertEqual(trace["citations"], [])

    def test_errors_propagate(self):
        cfg = baseline_config()
        llm = FakeLLM([{"role": "assistant", "tool_calls": [_tc("t1", "search_documents", {"query": "GDP"})]}])
        with self.assertRaises(RetrievalError):
            run_agentic_rag({"id": "q01", "question": "GDP?"}, FakeRetriever(RetrievalError("db down")), llm, cfg)

        llm_err = FakeLLM([ProviderError("429 quota")])
        with self.assertRaises(ProviderError):
            run_agentic_rag({"id": "q01", "question": "GDP?"}, FakeRetriever([[]]), llm_err, cfg)

    def test_bonus_modality_filter_and_lookup_visual_asset(self):
        self.assertEqual(
            _sanitize_filter({"modality": "chart"}, allow_inference=True, user_filter=None, corpus_mode="bonus"),
            {"modality": "chart"},
        )
        self.assertIsNone(
            _sanitize_filter({"modality": "invalid"}, allow_inference=True, user_filter=None, corpus_mode="bonus")
        )

        cfg = improved_config(retrieval_method="hybrid", corpus_mode="bonus", budget_chars=3000, max_searches=4)
        fig_chunk = {
            "id": "BONUS__wb_vn_plastic_2022__p039__fig_05",
            "text": "[FIGURE 5 | chart | Page 39] Plastic = 93.6% of total waste items.",
            "source_id": "wb_vn_plastic_2022",
            "source": "data/bonus/wb_vietnam_plastic_2022.pdf",
            "page": 39,
            "metadata": {"modality": "chart", "asset_id": "fig_05", "crop_path": None},
            "score": 0.95,
            "rank": 1,
        }
        retr = FakeRetriever([[fig_chunk]])
        retr.chunks = [fig_chunk]
        llm = FakeLLM([
            {"role": "assistant", "tool_calls": [_tc("t1", "lookup_visual_asset", {"asset_id": "fig_05", "page": 39})]},
            {
                "role": "assistant",
                "tool_calls": [
                    _tc(
                        "t2",
                        "submit_answer",
                        {
                            "answer": "Plastic accounted for 93.6% of items [BONUS__wb_vn_plastic_2022__p039__fig_05].",
                            "citations": ["BONUS__wb_vn_plastic_2022__p039__fig_05"],
                        },
                    )
                ],
            },
        ])
        trace = run_agentic_rag({"id": "bd_q07", "question": "Figure 5 plastic share?"}, retr, llm, cfg)
        self.assertEqual(trace["status"], "answered")
        self.assertEqual(trace["events"][0]["tool_name"], "lookup_visual_asset")
        self.assertEqual(trace["citations"], ["BONUS__wb_vn_plastic_2022__p039__fig_05"])


class BonusAndServerTests(unittest.TestCase):
    def test_compute_bonus_summary_and_server_payloads(self):
        from rag.eval_bonus import compute_bonus_summary, load_bonus_questions
        from rag.server import build_overview_payload, build_questions_payload

        dev_qs = load_bonus_questions("dev")
        self.assertEqual(len(dev_qs), 18)
        test_qs = load_bonus_questions("test")
        self.assertEqual(len(test_qs), 30)

        fake_traces = [
            {
                "query_id": q["id"],
                "status": "abstain" if not q["answerable"] else "answered",
                "answer": "ok [c1]" if q["answerable"] else "abstain",
                "citations": ["c1"] if q["answerable"] else [],
                "final_context_ids": ["c1"],
                "num_searches": 1,
                "api_calls": 2,
                "latency_s": 1.0,
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
                "cost_usd": 0.0,
            }
            for q in test_qs
        ]
        fake_reviews = [{"query_id": q["id"], "passed": True, "audit_note": "verified"} for q in test_qs]
        summary = compute_bonus_summary("test", improved_config(retrieval_method="hybrid", corpus_mode="bonus"), fake_traces, fake_reviews)
        self.assertEqual(summary["total_questions"], 30)
        self.assertEqual(summary["total_passed"], 30)
        self.assertEqual(summary["overall_pass_rate_pct"], 100.0)
        self.assertTrue(summary["meets_90pct_threshold"])
        self.assertEqual(summary["by_category"]["table"]["total"], 6)
        self.assertEqual(summary["by_category"]["unanswerable"]["total"], 6)

        overview = build_overview_payload()
        self.assertIn("core_manifest", overview)
        self.assertIn("bonus_manifest", overview)
        self.assertEqual(len(overview["visual_assets"]), 80)
        self.assertEqual(len(build_questions_payload("bonus", "test")), 30)


if __name__ == "__main__":
    unittest.main()

