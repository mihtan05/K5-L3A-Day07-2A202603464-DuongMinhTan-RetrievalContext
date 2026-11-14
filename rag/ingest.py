"""(Re)build the Day 6 pgvector index and export chunks for Day 7.

    python -m rag.ingest

Uses the Day 6 manifest, PDF normalizer and paragraph chunker (strategy B,
max 800 chars) with BAAI/bge-base-en-v1.5 (768 dims, local). Writes
data/chunks.json (Day 7 chunk schema) and data/index_manifest.json.
Upsert is idempotent: re-running replaces rows with the same chunk_id and
deletes obsolete ones.
"""
from __future__ import annotations

import hashlib
import json
import time

from . import day6

OUT_CHUNKS = day6.ROOT / "data" / "chunks.json"
OUT_MANIFEST = day6.ROOT / "data" / "index_manifest.json"


def main() -> None:
    t0 = time.perf_counter()
    pages, _logs, manifest = day6.load_corpus_from_manifest(day6.MANIFEST_PATH)
    chunks = [c for p in pages for c in day6.by_paragraph(p, max_size=day6.CHUNK_MAX_SIZE, strategy_label=day6.INDEX_STRATEGY)]
    print(f"{len(pages)} pages -> {len(chunks)} chunks")

    embedder = day6.build_embedder(provider=day6.EMBEDDING_PROVIDER, model_name=day6.EMBEDDING_MODEL)
    t1 = time.perf_counter()
    vectors = embedder.embed_documents([c.text for c in chunks])
    embed_s = time.perf_counter() - t1

    store = day6.PgVectorStore(day6.DATABASE_URL, dimensions=embedder.dimensions)
    store.create_schema()
    res = store.upsert(day6.INDEX_STRATEGY, chunks, vectors)
    stored = store.count_chunks(day6.INDEX_STRATEGY)

    out = [
        {"id": c.chunk_id, "text": c.text, "source_id": c.document_id, "source": c.source,
         "page": c.page, "metadata": c.metadata}
        for c in chunks
    ]
    OUT_CHUNKS.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(out, ensure_ascii=False, indent=1)
    OUT_CHUNKS.write_text(blob, encoding="utf-8")
    info = {
        "corpus": manifest["corpus_topic"],
        "documents": [{"source_id": d["source_id"], "url": d["source_path_or_url"],
                       "license": d["license_or_permission"]} for d in manifest["documents"]],
        "pages": len(pages),
        "chunks": len(chunks),
        "stored_rows": stored,
        "index_strategy": day6.INDEX_STRATEGY,
        "chunker": f"Day 6 by_paragraph(max_size={day6.CHUNK_MAX_SIZE})",
        "embedding_provider": day6.EMBEDDING_PROVIDER,
        "embedding_model": day6.EMBEDDING_MODEL,
        "dimensions": embedder.dimensions,
        "vector_store": "PostgreSQL + pgvector (exact cosine, Day 6 docker-compose)",
        "chunks_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "upsert": res,
        "embed_seconds": round(embed_s, 2),
        "total_seconds": round(time.perf_counter() - t0, 2),
    }
    OUT_MANIFEST.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, indent=2))
    if stored != len(chunks):
        raise RuntimeError(f"store has {stored} rows but {len(chunks)} chunks were built")


if __name__ == "__main__":
    main()
