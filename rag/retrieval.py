"""Retrieval methods over the same corpus/index version.

Methods (all return the same normalized chunk dicts with rank + score):
  dense          pgvector exact cosine on Day 6 index (bge-base-en-v1.5)
  bm25           BM25Okapi over the same chunks (lexical)
  hybrid         Reciprocal Rank Fusion of dense top-N and bm25 top-N
  hybrid_rerank  hybrid top-N candidates re-scored by a cross-encoder

Filters are exact metadata matches supplied with the question by the user
(e.g. {"year": 2025}); they are never derived from gold labels.
"""
from __future__ import annotations

import json
import time
from typing import Any

from rank_bm25 import BM25Okapi

from . import day6

METHODS = ("dense", "bm25", "hybrid", "hybrid_rerank")


class RetrievalError(RuntimeError):
    """Vector store / model failure; surfaced to the trace, never replaced by fake results."""


def _matches(meta: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    return not filters or all(meta.get(k) == v for k, v in filters.items())


class Retriever:
    def __init__(
        self,
        chunks_path=None,
        *,
        index_strategy: str | None = None,
        reranker_model: str = "BAAI/bge-reranker-base",
    ) -> None:
        path = chunks_path or (day6.ROOT / "data" / "chunks.json")
        self.index_strategy = index_strategy or day6.INDEX_STRATEGY
        self.chunks: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        self.by_id = {c["id"]: c for c in self.chunks}
        self._bm25 = BM25Okapi([day6.tokenize_for_bm25(c["text"]) for c in self.chunks])
        self.embedder = day6.build_embedder(provider=day6.EMBEDDING_PROVIDER, model_name=day6.EMBEDDING_MODEL)
        self.store = day6.PgVectorStore(day6.DATABASE_URL, dimensions=self.embedder.dimensions)
        self.reranker_model = reranker_model
        self._reranker = None
        try:
            n = self.store.count_chunks(self.index_strategy)
        except Exception as exc:  # connection refused, missing table, ...
            raise RetrievalError(f"cannot reach vector store: {exc}") from exc
        if n != len(self.chunks):
            raise RetrievalError(
                f"index ({self.index_strategy}) has {n} rows but {path.name} has {len(self.chunks)}; run ingestion first"
            )

    # ---- individual methods -------------------------------------------------
    def dense(self, query: str, top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            vec = self.embedder.embed_query(query)
            rows = self.store.search(self.index_strategy, vec, top_k=top_k, filters=filters)
        except ValueError:
            raise
        except Exception as exc:
            raise RetrievalError(f"dense search failed: {exc}") from exc
        return [self._norm(self.by_id[r["chunk_id"]], r["rank"], r["score"]) for r in rows]

    def bm25(self, query: str, top_k: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        tokens = day6.tokenize_for_bm25(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        idx = [i for i in range(len(self.chunks)) if scores[i] > 0 and _matches(self.chunks[i]["metadata"], filters)]
        idx.sort(key=lambda i: (-float(scores[i]), self.chunks[i]["id"]))
        return [self._norm(self.chunks[i], r, float(scores[i])) for r, i in enumerate(idx[:top_k], 1)]

    def hybrid(self, query: str, top_k: int, filters: dict[str, Any] | None = None, *,
               candidates: int = 20, k_rrf: int = 60, w_dense: float = 1.0, w_bm25: float = 1.0) -> list[dict[str, Any]]:
        d = self.dense(query, candidates, filters)
        b = self.bm25(query, candidates, filters)
        fused: dict[str, float] = {}
        for w, hits in ((w_dense, d), (w_bm25, b)):
            for h in hits:
                fused[h["id"]] = fused.get(h["id"], 0.0) + w / (k_rrf + h["rank"])
        order = sorted(fused, key=lambda cid: (-fused[cid], cid))[:top_k]
        return [self._norm(self.by_id[cid], r, fused[cid]) for r, cid in enumerate(order, 1)]

    def hybrid_rerank(self, query: str, top_k: int, filters: dict[str, Any] | None = None, *,
                      candidates: int = 20) -> list[dict[str, Any]]:
        pool = self.hybrid(query, candidates, filters, candidates=candidates)
        if not pool:
            return []
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.reranker_model)
        scores = self._reranker.predict([(query, c["text"]) for c in pool], show_progress_bar=False)
        order = sorted(range(len(pool)), key=lambda i: (-float(scores[i]), pool[i]["id"]))[:top_k]
        return [self._norm(self.by_id[pool[i]["id"]], r, float(scores[i])) for r, i in enumerate(order, 1)]

    # ---- entry point --------------------------------------------------------
    def search(self, method: str, query: str, *, top_k: int, filters: dict[str, Any] | None = None,
               **params: Any) -> list[dict[str, Any]]:
        if method not in METHODS:
            raise ValueError(f"unknown retrieval method {method!r}; choose from {METHODS}")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        fn = getattr(self, method)
        return fn(query, top_k, filters, **params)

    def timed_search(self, method: str, query: str, **kw: Any) -> tuple[list[dict[str, Any]], float]:
        t0 = time.perf_counter()
        res = self.search(method, query, **kw)
        return res, time.perf_counter() - t0

    @staticmethod
    def _norm(chunk: dict[str, Any], rank: int, score: float) -> dict[str, Any]:
        return {**chunk, "rank": rank, "score": round(float(score), 6)}


# ---- context packing + evaluation helpers ----------------------------------
def format_chunk(c: dict[str, Any]) -> str:
    return f"[{c['id']}] (source: {c['source_id']}, page {c['page']})\n{c['text']}"


def format_context(chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(format_chunk(c) for c in chunks)


def _dedup_chunks(chunks: list[dict[str, Any]], *, keep_highest_score: bool = False) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for c in chunks:
        cid = c["id"]
        if cid not in by_id:
            by_id[cid] = c
            order.append(cid)
        elif keep_highest_score:
            new_s = float(c.get("pack_score", c.get("score", 0.0)))
            old_s = float(by_id[cid].get("pack_score", by_id[cid].get("score", 0.0)))
            if new_s > old_s:
                by_id[cid] = c
    return [by_id[cid] for cid in order]


def pack_context(
    chunks: list[dict[str, Any]],
    budget_chars: int,
    *,
    mode: str = "fifo",
    all_chunks: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pack unique chunks into `budget_chars` using `fifo`, `score_dedup`, or `neighbor_expand`."""
    if mode not in ("fifo", "score_dedup", "neighbor_expand"):
        raise ValueError(f"unknown pack mode: {mode!r}")

    ordered = _dedup_chunks(chunks, keep_highest_score=(mode != "fifo"))
    if mode in ("score_dedup", "neighbor_expand"):
        ordered = sorted(
            ordered,
            key=lambda c: (-float(c.get("pack_score", c.get("score", 0.0))), int(c.get("rank", 9999)), c["id"]),
        )

    kept: list[dict[str, Any]] = []
    kept_ids: set[str] = set()
    dropped: list[str] = []
    used = 0

    for c in ordered:
        sep = 2 if kept else 0
        n = sep + len(format_chunk(c))
        if used + n <= budget_chars:
            kept.append(c)
            kept_ids.add(c["id"])
            used += n
        else:
            dropped.append(c["id"])

    if mode == "neighbor_expand" and all_chunks and kept:
        idx_by_id = {c["id"]: i for i, c in enumerate(all_chunks)}
        seeds = list(kept)
        for seed in seeds:
            idx = idx_by_id.get(seed["id"])
            if idx is None:
                continue
            for offset in (-1, 1):
                nb_idx = idx + offset
                if 0 <= nb_idx < len(all_chunks):
                    nb = all_chunks[nb_idx]
                    if nb["id"] in kept_ids:
                        continue
                    if nb["source_id"] != seed["source_id"] or int(nb["page"]) != int(seed["page"]):
                        continue
                    nb_copy = {**nb, "rank": seed.get("rank", 0), "score": seed.get("score", 0.0), "neighbor_of": seed["id"]}
                    sep = 2 if kept else 0
                    n = sep + len(format_chunk(nb_copy))
                    if used + n <= budget_chars:
                        kept.append(nb_copy)
                        kept_ids.add(nb_copy["id"])
                        used += n

    return kept, dropped


def is_hit(chunk: dict[str, Any], gold: list[dict[str, Any]]) -> bool:
    """Same definition for every method: right source + page and the evidence quote inside the chunk
    (whitespace/case-normalized, as in Day 6)."""
    text = day6.normalize_for_match(chunk["text"])
    return any(chunk["source_id"] == g["source_id"] and int(chunk["page"]) == int(g["page"])
               and day6.normalize_for_match(g["evidence"]) in text for g in gold)
