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

VECTOR_STORE_DIR = Path("rag/vector_store")
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


# ── Vector Store (FAISS) ──────────────────────────────────────────────────────

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
            with open(meta_path, "r") as f:
                self.chunks = json.load(f)
            self.embeddings = np.load(str(emb_path))
            logger.info(f"Loaded vector store '{self.store_id}' with {len(self.chunks)} chunks")

    def _save(self):
        with open(self.store_path / "metadata.json", "w") as f:
            json.dump(self.chunks, f, indent=2)
        np.save(str(self.store_path / "embeddings.npy"), self.embeddings)

    def add_chunks(self, chunks: list[dict]):
        model = get_embed_model()
        texts = [c["text"] for c in chunks]
        new_embeddings = model.encode(texts, show_progress_bar=False)

        if self.embeddings is None:
            self.embeddings = new_embeddings
            self.chunks = chunks
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

        # Cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        query_norm = np.linalg.norm(query_emb)
        cos_sims = (self.embeddings @ query_emb.T).squeeze() / (norms.squeeze() * query_norm + 1e-8)

        top_indices = np.argsort(cos_sims)[::-1][:top_k]
        results = []
        for idx in top_indices:
            results.append({
                **self.chunks[int(idx)],
                "score": float(cos_sims[int(idx)]),
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
