import traceback
from rag.pipeline import ingest_document

try:
    res = ingest_document(
        'uploads/documents/20260928_114134_SupplyChain_Procurement_Policy_Test_Document.docx',
        'docx',
        'SupplyChain_Procurement_Policy_Test_Document.docx'
    )
    print("SUCCESS:", res)
except Exception:
    traceback.print_exc()
