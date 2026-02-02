"""ChromaDB vector store operations."""
from typing import List, Dict, Any
import chromadb

from app.config import get_settings

settings = get_settings()

# Initialize ChromaDB with persistent storage
chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

# Get or create collection
COLLECTION_NAME = "doc_chunks"


def get_collection():
    """Get the document chunks collection."""
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Document chunks for RAG retrieval"}
    )


def index_chunks(chunks: List[Dict[str, Any]]) -> None:
    """
    Index document chunks in ChromaDB.
    
    ChromaDB will automatically generate embeddings using its default model.
    """
    if not chunks:
        return
    
    collection = get_collection()
    
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def search_chunks(query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for relevant chunks given a query.
    
    Returns list of chunks with their metadata.
    """
    collection = get_collection()
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )
    
    chunks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "id": results["ids"][0][i],
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    
    return chunks


def delete_document_chunks(doc_id: str) -> None:
    """Delete all chunks for a document."""
    collection = get_collection()
    
    # ChromaDB requires querying first to get chunk IDs
    # We'll use the where filter
    try:
        collection.delete(
            where={"doc_id": doc_id}
        )
    except Exception:
        # If no chunks exist, ignore
        pass
