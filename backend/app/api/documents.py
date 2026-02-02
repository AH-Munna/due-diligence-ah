"""Document management API routes."""
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import DocumentResponse

router = APIRouter()


@router.get("", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents with their indexing status."""
    from app.models.database import Document
    return db.query(Document).all()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a PDF document for indexing."""
    from app.services.ingestion import ingest_document
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    result = await ingest_document(file, db)
    return result


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    """Get document details by ID."""
    from app.models.database import Document
    
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete a document and its indexed chunks."""
    from app.models.database import Document
    from app.services.indexer import delete_document_chunks
    
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    delete_document_chunks(doc_id)
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return {"status": "deleted", "id": doc_id}
