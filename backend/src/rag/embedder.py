"""
Embedder.
Chunks text and stores embeddings in ChromaDB using Ollama's nomic-embed-text model.
"""

from typing import List, Dict, Optional
import chromadb
from langchain_ollama import OllamaEmbeddings

from src.config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    CHROMA_PERSIST_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


# ── Text Chunking ─────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text into overlapping chunks by word count.

    Args:
        text: The text to split.
        chunk_size: Approximate number of words per chunk.
        overlap: Number of overlapping words between chunks.

    Returns:
        List of text chunks.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks


def chunk_transcript_with_timestamps(
    segments: list,
    chunk_size: int = CHUNK_SIZE,
) -> List[Dict]:
    """
    Chunk transcript segments into larger pieces while preserving timestamps.

    Args:
        segments: List of TranscriptSegment objects with text, start, duration.
        chunk_size: Approximate number of words per chunk.

    Returns:
        List of dicts with 'text', 'start_time', 'end_time' keys.
    """
    chunks = []
    current_words = []
    current_start = 0.0
    current_end = 0.0

    for seg in segments:
        # Segments can be dicts (from model_dump()) or objects
        if isinstance(seg, dict):
            seg_words = seg["text"].split()
            seg_start = seg["start"]
            seg_duration = seg["duration"]
        else:
            seg_words = seg.text.split()
            seg_start = seg.start
            seg_duration = seg.duration

        if not current_words:
            current_start = seg_start

        current_words.extend(seg_words)
        current_end = seg_start + seg_duration

        if len(current_words) >= chunk_size:
            chunks.append({
                "text": " ".join(current_words),
                "start_time": current_start,
                "end_time": current_end,
            })
            current_words = []

    # Don't forget the last chunk
    if current_words:
        chunks.append({
            "text": " ".join(current_words),
            "start_time": current_start,
            "end_time": current_end,
        })

    return chunks


# ── ChromaDB Manager ──────────────────────────────────────────────────────────

class EmbeddingStore:
    """Manages ChromaDB collections for storing and querying embeddings."""

    def __init__(self, collection_name: str = "transcripts"):
        self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self._embeddings = OllamaEmbeddings(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_EMBED_MODEL,
        )
        self._collection_name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: List[str],
        metadatas: List[Dict],
        id_prefix: str = "chunk",
    ) -> int:
        """
        Embed and store text chunks in ChromaDB.

        Args:
            chunks: List of text strings to embed.
            metadatas: List of metadata dicts (one per chunk).
            id_prefix: Prefix for generated IDs.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        # Generate embeddings via Ollama
        embeddings = self._embeddings.embed_documents(chunks)

        # Generate unique IDs
        ids = [f"{id_prefix}_{i}" for i in range(len(chunks))]

        # Store in ChromaDB
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:
        """
        Query ChromaDB for similar chunks.

        Args:
            query_text: The text to find similar chunks for.
            n_results: Number of results to return.
            where: Optional metadata filter.

        Returns:
            Dict with 'documents', 'metadatas', 'distances' keys.
        """
        query_embedding = self._embeddings.embed_query(query_text)

        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        return {
            "documents": results.get("documents", [[]])[0],
            "metadatas": results.get("metadatas", [[]])[0],
            "distances": results.get("distances", [[]])[0],
        }

    def clear(self):
        """Delete and recreate the collection."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        """Number of items in the collection."""
        return self._collection.count()
