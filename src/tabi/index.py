"""Indexado: PDFs -> chunks -> Chroma (embeddings Ollama) + BM25 en memoria."""
import logging
import re
import threading
from functools import lru_cache

import chromadb
import ollama
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

logging.getLogger("pypdf").setLevel(logging.ERROR)  # silencia warnings de fuentes

from .config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION, DATA_DIR, EMBEDDING


def _split(text: str) -> list[str]:
    step = CHUNK_SIZE - CHUNK_OVERLAP
    return [c for i in range(0, len(text), step) if (c := text[i : i + CHUNK_SIZE].strip())]


@lru_cache
def chunks() -> list[dict]:
    out = []
    for pdf in sorted(DATA_DIR.glob("*.pdf")):
        for page, p in enumerate(PdfReader(pdf).pages):
            for c in _split(p.extract_text() or ""):
                out.append({"text": c, "source": pdf.name, "page": page + 1})
    return out


def embed(texts: list[str]) -> list[list[float]]:
    return ollama.embed(model=EMBEDDING, input=texts).embeddings


_lock = threading.Lock()
_chroma = None


def _client():
    """Un solo cliente por proceso. Con lock: crear varios a la vez (evals en paralelo) falla con 'tenant default_tenant'."""
    global _chroma
    with _lock:
        if _chroma is None:
            _chroma = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return _chroma


def collection():
    return _client().get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def rebuild() -> int:
    """Borra la colección y vuelve a indexar."""
    try:
        _client().delete_collection(COLLECTION)
    except Exception:  # no existía
        pass
    return build()


def build(batch: int = 50) -> int:
    col = collection()
    if col.count():
        return col.count()
    cs = chunks()
    for i in range(0, len(cs), batch):
        b = cs[i : i + batch]
        col.add(
            ids=[str(i + j) for j in range(len(b))],
            documents=[c["text"] for c in b],
            metadatas=[{"source": c["source"], "page": c["page"]} for c in b],
            embeddings=embed([c["text"] for c in b]),
        )
    return col.count()


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower())


@lru_cache
def _bm25() -> BM25Okapi:
    return BM25Okapi([_tok(c["text"]) for c in chunks()])


def search_bm25(q: str, k: int) -> list[dict]:
    scores = _bm25().get_scores(_tok(q))
    top = sorted(range(len(scores)), key=scores.__getitem__, reverse=True)[:k]
    return [{**chunks()[i], "id": str(i)} for i in top]


def search_vector(q: str, k: int) -> list[dict]:
    r = collection().query(query_embeddings=embed([q]), n_results=k)
    return [
        {"text": t, **m, "id": i} for i, t, m in zip(r["ids"][0], r["documents"][0], r["metadatas"][0])
    ]


def search_ensemble(q: str, k: int, w_bm25: float = 0.5) -> list[dict]:
    """Reciprocal Rank Fusion ponderado (mismo 50/50 del repo 2024)."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for w, hits in ((w_bm25, search_bm25(q, k * 2)), (1 - w_bm25, search_vector(q, k * 2))):
        for rank, d in enumerate(hits):
            scores[d["id"]] = scores.get(d["id"], 0) + w / (60 + rank)
            docs[d["id"]] = d
    return [docs[i] for i in sorted(scores, key=scores.get, reverse=True)[:k]]
