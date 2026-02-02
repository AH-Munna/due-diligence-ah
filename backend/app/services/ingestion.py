"""Document ingestion service - PDF parsing and chunking."""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

import pdfplumber
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.database import Document, DocumentStatus
from app.services.indexer import index_chunks
from app.config import get_settings

settings = get_settings()

# Upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


async def ingest_document(file: UploadFile, db: Session) -> Document:
    """
    Ingest a PDF document:
    1. Save file to disk
    2. Extract text with page/position metadata
    3. Chunk the text
    4. Index chunks in ChromaDB
    """
    doc_id = str(uuid.uuid4())
    
    # Create document record
    doc = Document(
        id=doc_id,
        filename=file.filename,
        status=DocumentStatus.INDEXING.value,
    )
    db.add(doc)
    db.commit()
    
    try:
        # Save file
        file_path = UPLOAD_DIR / f"{doc_id}.pdf"
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        doc.original_path = str(file_path)
        
        # Extract text and chunks
        chunks = extract_pdf_chunks(file_path, doc_id, file.filename)
        
        # Count pages
        with pdfplumber.open(file_path) as pdf:
            doc.page_count = len(pdf.pages)
        
        # Index in ChromaDB
        index_chunks(chunks)
        doc.chunk_count = len(chunks)
        
        # Update status
        doc.status = DocumentStatus.INDEXED.value
        doc.indexed_at = datetime.utcnow()
        
    except Exception as e:
        doc.status = DocumentStatus.FAILED.value
        doc.error_message = str(e)
    
    db.commit()
    db.refresh(doc)
    return doc


def extract_pdf_chunks(
    file_path: Path,
    doc_id: str,
    doc_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Extract text chunks from PDF with metadata for citations.
    
    Returns list of chunks with:
    - id: unique chunk id
    - text: chunk content
    - metadata: {doc_id, doc_name, page, chunk_index}
    """
    chunks = []
    
    with pdfplumber.open(file_path) as pdf:
        full_text_by_page = []
        
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            full_text_by_page.append({
                "page": page_num,
                "text": text,
            })
        
        # Simple chunking: split by page, then by chunk_size
        chunk_index = 0
        for page_data in full_text_by_page:
            page_text = page_data["text"]
            page_num = page_data["page"]
            
            # Split long pages into chunks
            words = page_text.split()
            current_chunk = []
            current_length = 0
            
            for word in words:
                current_chunk.append(word)
                current_length += len(word) + 1
                
                if current_length >= chunk_size:
                    chunk_text = " ".join(current_chunk)
                    chunks.append({
                        "id": f"{doc_id}_chunk_{chunk_index}",
                        "text": chunk_text,
                        "metadata": {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page": page_num,
                            "chunk_index": chunk_index,
                        }
                    })
                    chunk_index += 1
                    
                    # Overlap: keep last N words
                    overlap_words = int(chunk_overlap / 5)  # Approximate words
                    current_chunk = current_chunk[-overlap_words:] if overlap_words > 0 else []
                    current_length = sum(len(w) + 1 for w in current_chunk)
            
            # Don't forget remaining text
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text.strip()) > 50:  # Minimum chunk size
                    chunks.append({
                        "id": f"{doc_id}_chunk_{chunk_index}",
                        "text": chunk_text,
                        "metadata": {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page": page_num,
                            "chunk_index": chunk_index,
                        }
                    })
                    chunk_index += 1
    
    return chunks
