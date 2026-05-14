"""
Retriever.
Semantic search over embedded transcripts to find relevant content per topic.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from src.rag.embedder import EmbeddingStore
from src.config import TOP_K_RESULTS


# ── Data Models ───────────────────────────────────────────────────────────────

class RetrievalResult(BaseModel):
    """A single retrieval result from semantic search."""
    text: str
    video_id: str = ""
    video_title: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    similarity_score: float = 0.0  # 0 to 1, higher is better


# ── Retriever ─────────────────────────────────────────────────────────────────

class TranscriptRetriever:
    """Retrieves relevant transcript chunks for syllabus topics."""

    def __init__(self, store: Optional[EmbeddingStore] = None):
        self._store = store or EmbeddingStore(collection_name="transcripts")

    def retrieve_for_topic(
        self,
        topic_description: str,
        top_k: int = TOP_K_RESULTS,
        video_id_filter: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Find the most relevant transcript chunks for a given topic.

        Args:
            topic_description: Description or name of the topic to search for.
            top_k: Number of results to return.
            video_id_filter: Optional - only search within a specific video.

        Returns:
            List of RetrievalResult sorted by relevance (best first).
        """
        where = None
        if video_id_filter:
            where = {"video_id": video_id_filter}

        raw = self._store.query(
            query_text=topic_description,
            n_results=top_k,
            where=where,
        )

        results = []
        for i in range(len(raw["documents"])):
            doc = raw["documents"][i]
            meta = raw["metadatas"][i] if raw["metadatas"] else {}
            dist = raw["distances"][i] if raw["distances"] else 1.0

            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: 1 - (distance / 2)
            similarity = max(0.0, 1.0 - (dist / 2.0))

            results.append(RetrievalResult(
                text=doc,
                video_id=meta.get("video_id", ""),
                video_title=meta.get("video_title", ""),
                start_time=meta.get("start_time", 0.0),
                end_time=meta.get("end_time", 0.0),
                similarity_score=round(similarity, 4),
            ))

        return results

    def retrieve_for_multiple_topics(
        self,
        topics: List[Dict[str, str]],
        top_k: int = TOP_K_RESULTS,
    ) -> Dict[str, List[RetrievalResult]]:
        """
        Retrieve relevant chunks for multiple topics at once.

        Args:
            topics: List of dicts with 'id' and 'description' keys.
            top_k: Number of results per topic.

        Returns:
            Dict mapping topic_id → list of RetrievalResult.
        """
        results = {}
        for topic in topics:
            topic_id = topic.get("id", "unknown")
            description = topic.get("description", topic.get("name", ""))

            results[topic_id] = self.retrieve_for_topic(
                topic_description=description,
                top_k=top_k,
            )

        return results
