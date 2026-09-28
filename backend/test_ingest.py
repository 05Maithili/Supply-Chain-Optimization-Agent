import os
import traceback
from pathlib import Path
from rag.pipeline import ingest_document

backend_dir = Path(__file__).resolve().parent
upload_dir = backend_dir / "uploads" / "documents"
sample_files = list(upload_dir.glob("*.docx")) + list(upload_dir.glob("*.pdf")) + list(upload_dir.glob("*.txt"))

if sample_files:
    sample_file = sample_files[0]
    ext = sample_file.suffix.lstrip(".")
    try:
        res = ingest_document(str(sample_file), ext, sample_file.name)
        print("INGEST SUCCESS:", res)
    except Exception:
        traceback.print_exc()
else:
    print("No sample documents found in", upload_dir)
