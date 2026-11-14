"""Bridge to the Day 6 code base (PDF loading, chunking, embedder, pgvector store).

Day 7 reuses Day 6 modules instead of copying them, so the query embedding is
guaranteed to come from the same model/dimension as the document index.
Set DAY6_STARTER in .env if the Day 6 repo is not a sibling folder.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

DAY6_STARTER = Path(
    os.getenv("DAY6_STARTER")
    or ROOT.parent / "K5-L3A-Day06-2A202603464-DataIngestionEngineering" / "starter"
).resolve()
if not (DAY6_STARTER / "src" / "store.py").exists():
    raise RuntimeError(f"Day 6 starter not found at {DAY6_STARTER}; set DAY6_STARTER in .env")
if str(DAY6_STARTER) not in sys.path:
    sys.path.insert(0, str(DAY6_STARTER))

# Day 6 package is called `src`; imported from the Day 6 starter folder.
from src.chunking import by_paragraph  # noqa: E402
from src.embeddings import build_embedder  # noqa: E402
from src.evaluation import normalize_for_match, tokenize_for_bm25  # noqa: E402
from src.models import Chunk, DocumentPage  # noqa: E402
from src.run import MANIFEST_PATH, load_corpus_from_manifest  # noqa: E402
from src.store import PgVectorStore  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "BAAI/bge-base-en-v1.5"
# Day 6 strategy B = paragraph chunks (max 800 chars), the best dense index in Day 6.
INDEX_STRATEGY = os.getenv("INDEX_STRATEGY", "B")
CHUNK_MAX_SIZE = 800

__all__ = [
    "ROOT", "DAY6_STARTER", "DATABASE_URL", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "INDEX_STRATEGY",
    "CHUNK_MAX_SIZE", "Chunk", "DocumentPage", "by_paragraph", "build_embedder", "normalize_for_match",
    "tokenize_for_bm25", "MANIFEST_PATH", "load_corpus_from_manifest", "PgVectorStore",
]
