"""
Documents API router — file upload, listing, and RAG query.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database.connection import get_db
from database.models import SupplyChainDocument
from rag.pipeline import ingest_document, search_supply_chain_documents, build_rag_context
from services.llm_client import get_llm_client, ORCHESTRATOR_SYSTEM_PROMPT

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a supply chain document for RAG."""
    # Validate file extension
    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: .{extension}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Validate file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f} MB. Max: {MAX_FILE_SIZE_MB} MB"
        )

    # Save file
    safe_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = SupplyChainDocument(
        filename=safe_name,
        original_filename=file.filename,
        file_type=extension,
        file_size_bytes=len(content),
        status="Processing",
        description=description,
    )
    db.add(doc)
    await db.flush()

    # Ingest into RAG pipeline
    try:
        ingest_result = ingest_document(
            str(file_path),
            extension,
            file.filename,
        )
        doc.num_chunks = ingest_result["num_chunks"]
        doc.status = "Ready"
    except Exception as e:
        doc.status = "Failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")

    await db.commit()

    return {
        "message": "Document uploaded and ingested successfully",
        "filename": file.filename,
        "file_type": extension,
        "file_size_mb": round(size_mb, 2),
        "num_chunks": doc.num_chunks,
        "status": doc.status,
    }


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SupplyChainDocument).order_by(SupplyChainDocument.upload_date.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.original_filename,
            "file_type": d.file_type,
            "file_size_bytes": d.file_size_bytes,
            "upload_date": d.upload_date.isoformat(),
            "num_chunks": d.num_chunks,
            "status": d.status,
            "description": d.description,
        }
        for d in docs
    ]


@router.post("/rag/query")
async def query_documents(request: RAGQueryRequest):
    """Run a RAG query over uploaded documents and return grounded answer."""
    # Retrieve relevant chunks
    results = search_supply_chain_documents(request.query, top_k=request.top_k)

    if not results:
        return {
            "answer": "No relevant documents found. Please upload supply chain policy documents first.",
            "sources": [],
            "num_chunks_retrieved": 0,
        }

    context = build_rag_context(results)

    # Generate LLM answer grounded in retrieved context
    llm = get_llm_client()
    prompt = (
        f"Based ONLY on the following retrieved supply chain documents, answer the question.\n"
        f"Do NOT use information outside the provided context.\n\n"
        f"QUESTION: {request.query}\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        f"ANSWER (cite sources):"
    )

    try:
        answer = await llm.generate(prompt, system=ORCHESTRATOR_SYSTEM_PROMPT)
    except Exception as e:
        answer = f"LLM unavailable. Retrieved {len(results)} relevant chunks. Context: {context[:500]}..."

    sources = [
        {
            "source": r.get("source", "Unknown"),
            "chunk_id": r.get("chunk_id"),
            "relevance_score": round(r.get("score", 0), 3),
            "excerpt": r.get("text", "")[:200] + "...",
        }
        for r in results
    ]

    return {
        "answer": answer,
        "sources": sources,
        "num_chunks_retrieved": len(results),
    }
