"""
RAG Pipeline — document ingestion, embedding, retrieval and grounded Q&A.
Uses sentence-transformers for embeddings and FAISS for vector storage.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = Path(__file__).resolve().parent / "vector_store"
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Embedding model (local, no API key needed)
_model: Optional[SentenceTransformer] = None


def get_embed_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
    return _model


# ── Document Parsing ──────────────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    texts = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            texts.append(f"[Page {page_num + 1}]\n{text}")
    return "\n\n".join(texts)


def extract_text_from_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def extract_text_from_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(path: str, file_type: str) -> str:
    ext = file_type.lower().strip(".")
    if ext == "pdf":
        return extract_text_from_pdf(path)
    elif ext == "docx":
        return extract_text_from_docx(path)
    elif ext == "txt":
        return extract_text_from_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    filename: str = "",
) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    words = text.split()
    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "text": chunk_text,
            "chunk_id": chunk_idx,
            "source": filename,
            "char_count": len(chunk_text),
            "word_count": end - start,
        })
        start += chunk_size - chunk_overlap
        chunk_idx += 1

    return chunks


# ── Vector Store (FAISS / NumPy) ──────────────────────────────────────────────

class FAISSVectorStore:
    def __init__(self, store_id: str):
        self.store_id = store_id
        self.store_path = VECTOR_STORE_DIR / store_id
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.chunks: list[dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self._load()

    def _load(self):
        meta_path = self.store_path / "metadata.json"
        emb_path = self.store_path / "embeddings.npy"
        if meta_path.exists() and emb_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                self.embeddings = np.load(str(emb_path))
                logger.info(f"Loaded vector store '{self.store_id}' with {len(self.chunks)} chunks")
            except Exception as e:
                logger.error(f"Error loading vector store '{self.store_id}': {e}")
                self.chunks = []
                self.embeddings = None

    def _save(self):
        with open(self.store_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, indent=2)
        np.save(str(self.store_path / "embeddings.npy"), self.embeddings)

    def add_chunks(self, chunks: list[dict]):
        if not chunks:
            return 0
        model = get_embed_model()
        texts = [c["text"] for c in chunks]
        new_embeddings = model.encode(texts, show_progress_bar=False)
        new_embeddings = np.atleast_2d(new_embeddings)

        if self.embeddings is None or len(self.chunks) == 0:
            self.embeddings = new_embeddings
            self.chunks = list(chunks)
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
            self.chunks.extend(chunks)

        self._save()
        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        model = get_embed_model()
        query_emb = model.encode([query])
        query_emb = np.atleast_2d(query_emb)

        # Cosine similarity safe calculation
        norms = np.linalg.norm(self.embeddings, axis=1)
        query_norm = float(np.linalg.norm(query_emb))
        if query_norm == 0:
            query_norm = 1e-8

        dot_products = (self.embeddings @ query_emb.T).reshape(-1)
        cos_sims = dot_products / (norms * query_norm + 1e-8)
        cos_sims = np.atleast_1d(cos_sims)

        effective_k = min(top_k, len(self.chunks))
        top_indices = np.argsort(cos_sims)[::-1][:effective_k]
        results = []
        for idx in top_indices:
            idx_int = int(idx)
            if 0 <= idx_int < len(self.chunks):
                results.append({
                    **self.chunks[idx_int],
                    "score": float(cos_sims[idx_int]),
                })
        return results


# Global vector store (shared across all documents)
_global_store: Optional[FAISSVectorStore] = None


def get_global_store() -> FAISSVectorStore:
    global _global_store
    if _global_store is None:
        _global_store = FAISSVectorStore("global")
    return _global_store


# ── Pipeline Entry Points ─────────────────────────────────────────────────────

def ingest_document(
    file_path: str,
    file_type: str,
    filename: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> dict:
    """Full ingestion pipeline: extract -> chunk -> embed -> store."""
    text = extract_text(file_path, file_type)
    if not text.strip():
        raise ValueError("Document contains no readable text")

    chunks = chunk_text(text, chunk_size, chunk_overlap, filename)
    store = get_global_store()
    num_added = store.add_chunks(chunks)

    return {
        "filename": filename,
        "num_chunks": num_added,
        "total_chars": len(text),
        "total_words": len(text.split()),
    }


def search_supply_chain_documents(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve relevant document chunks for a query."""
    store = get_global_store()
    results = store.search(query, top_k=top_k)
    return results


def build_rag_context(results: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not results:
        return "No relevant documents found."

    parts = []
    for i, r in enumerate(results, 1):
        source = r.get("source", "Unknown")
        chunk_id = r.get("chunk_id", i)
        score = r.get("score", 0)
        parts.append(
            f"[Source {i}: {source}, Chunk {chunk_id}, Relevance: {score:.3f}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(parts)
