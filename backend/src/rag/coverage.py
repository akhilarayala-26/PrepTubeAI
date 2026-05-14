"""
Coverage Scorer + Two-Tier Recommendation System.

Tier 1: Greedy set cover — find minimum videos covering maximum topics.
Tier 2: Fallback — dedicated videos for any remaining uncovered topics.
"""

from typing import List, Dict, Set, Optional, Tuple
from pydantic import BaseModel, Field

from src.rag.retriever import TranscriptRetriever, RetrievalResult
from src.config import COVERAGE_THRESHOLD


# ── Data Models ───────────────────────────────────────────────────────────────

class TopicCoverage(BaseModel):
    """Coverage analysis for a single topic."""
    topic_id: str
    topic_name: str
    coverage_score: float = Field(
        description="0.0 to 1.0 — how well this topic is covered"
    )
    is_covered: bool = False
    best_video_id: str = ""
    best_video_title: str = ""
    matched_chunks: int = 0
    relevant_timestamps: List[str] = Field(default_factory=list)


class VideoRecommendation(BaseModel):
    """A video recommendation with coverage info."""
    video_id: str
    video_title: str
    video_url: str = ""
    channel: str = ""
    duration_seconds: int = 0
    covers_topics: List[str] = Field(default_factory=list)
    coverage_scores: Dict[str, float] = Field(default_factory=dict)
    thumbnail_url: str = ""


class TieredRecommendation(BaseModel):
    """Final two-tier recommendation output."""
    tier1_combo_videos: List[VideoRecommendation] = Field(default_factory=list)
    tier2_gap_fillers: List[Dict] = Field(default_factory=list)
    coverage_report: List[TopicCoverage] = Field(default_factory=list)
    total_topics: int = 0
    covered_topics: int = 0
    coverage_percentage: float = 0.0
    total_watch_time_seconds: int = 0


# ── Coverage Scorer ───────────────────────────────────────────────────────────

def score_topic_coverage(
    topic_id: str,
    topic_name: str,
    subtopics: List[str],
    retrieval_results: List[RetrievalResult],
    threshold: float = COVERAGE_THRESHOLD,
) -> TopicCoverage:
    """
    Score how well a topic is covered by the retrieved transcript chunks.

    Uses a combination of:
    1. Average similarity score of top-K results
    2. Subtopic matching (how many subtopics are mentioned in retrieved text)

    Args:
        topic_id: Unique topic ID.
        topic_name: Topic name.
        subtopics: List of subtopics to check coverage for.
        retrieval_results: Results from semantic search.
        threshold: Minimum score to consider "covered".

    Returns:
        TopicCoverage with score and coverage status.
    """
    if not retrieval_results:
        return TopicCoverage(
            topic_id=topic_id,
            topic_name=topic_name,
            coverage_score=0.0,
            is_covered=False,
        )

    # Average similarity of top results
    avg_similarity = sum(r.similarity_score for r in retrieval_results) / len(
        retrieval_results
    )

    # Subtopic coverage: check how many subtopics appear in retrieved text
    combined_text = " ".join(r.text.lower() for r in retrieval_results)
    subtopic_hits = 0
    for sub in subtopics:
        # Check if any significant word from the subtopic appears
        sub_words = [w.lower() for w in sub.split() if len(w) > 3]
        if any(word in combined_text for word in sub_words):
            subtopic_hits += 1

    subtopic_coverage = subtopic_hits / max(len(subtopics), 1)

    # Combined score: 60% semantic similarity + 40% subtopic coverage
    final_score = 0.6 * avg_similarity + 0.4 * subtopic_coverage

    # Best video info
    best_result = max(retrieval_results, key=lambda r: r.similarity_score)

    # Relevant timestamps
    timestamps = []
    for r in retrieval_results[:3]:
        if r.start_time > 0:
            mins = int(r.start_time // 60)
            secs = int(r.start_time % 60)
            timestamps.append(f"{mins:02d}:{secs:02d}")

    return TopicCoverage(
        topic_id=topic_id,
        topic_name=topic_name,
        coverage_score=round(final_score, 3),
        is_covered=final_score >= threshold,
        best_video_id=best_result.video_id,
        best_video_title=best_result.video_title,
        matched_chunks=len(retrieval_results),
        relevant_timestamps=timestamps,
    )


# ── Tier 1: Greedy Set Cover ─────────────────────────────────────────────────

def find_minimum_video_set(
    video_topic_map: Dict[str, Set[str]],
    all_topics: Set[str],
    video_info: Dict[str, Dict],
) -> Tuple[List[VideoRecommendation], Set[str]]:
    """
    Greedy set cover: find the minimum set of videos that covers
    the maximum number of topics.

    Args:
        video_topic_map: video_id → set of topic_ids it covers.
        all_topics: Set of all topic_ids to cover.
        video_info: video_id → dict with title, url, duration, etc.

    Returns:
        Tuple of (selected videos, set of covered topic IDs).
    """
    covered: Set[str] = set()
    selected: List[VideoRecommendation] = []
    remaining_videos = dict(video_topic_map)

    while covered != all_topics and remaining_videos:
        # Find the video that covers the most uncovered topics
        best_vid = max(
            remaining_videos,
            key=lambda v: len(remaining_videos[v] - covered),
        )
        new_coverage = remaining_videos[best_vid] - covered

        if not new_coverage:
            break  # No video can cover any more topics

        info = video_info.get(best_vid, {})
        rec = VideoRecommendation(
            video_id=best_vid,
            video_title=info.get("title", "Unknown"),
            video_url=info.get("url", f"https://www.youtube.com/watch?v={best_vid}"),
            channel=info.get("channel", ""),
            duration_seconds=info.get("duration_seconds", 0),
            covers_topics=list(new_coverage | (remaining_videos[best_vid] & covered)),
            thumbnail_url=info.get("thumbnail_url", ""),
        )

        selected.append(rec)
        covered |= new_coverage
        del remaining_videos[best_vid]

    return selected, covered


# ── Tier 2: Gap Fillers ───────────────────────────────────────────────────────

def identify_gaps(
    all_topics: Set[str],
    covered_topics: Set[str],
    topic_names: Dict[str, str],
) -> List[Dict]:
    """
    Identify topics not covered by Tier 1 and prepare them for fallback search.

    Args:
        all_topics: Set of all topic IDs.
        covered_topics: Set of topic IDs covered by Tier 1.
        topic_names: Mapping of topic_id → topic_name.

    Returns:
        List of dicts with 'topic_id' and 'topic_name' for uncovered topics.
    """
    uncovered = all_topics - covered_topics
    return [
        {"topic_id": tid, "topic_name": topic_names.get(tid, "Unknown")}
        for tid in sorted(uncovered)
    ]


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def build_tiered_recommendation(
    coverage_reports: List[TopicCoverage],
    video_info: Dict[str, Dict],
    topic_names: Dict[str, str],
) -> TieredRecommendation:
    """
    Build the complete two-tier recommendation from coverage data.

    Args:
        coverage_reports: Coverage analysis for each topic.
        video_info: video_id → dict with title, url, duration, channel, etc.
        topic_names: topic_id → topic_name.

    Returns:
        TieredRecommendation with Tier 1 combo videos and Tier 2 gap info.
    """
    all_topics = {c.topic_id for c in coverage_reports}

    # Build video → topics map from coverage data
    video_topic_map: Dict[str, Set[str]] = {}
    for report in coverage_reports:
        if report.is_covered and report.best_video_id:
            vid = report.best_video_id
            if vid not in video_topic_map:
                video_topic_map[vid] = set()
            video_topic_map[vid].add(report.topic_id)

    # Tier 1: Greedy set cover
    tier1_videos, covered = find_minimum_video_set(
        video_topic_map, all_topics, video_info
    )

    # Tier 2: Identify gaps
    gaps = identify_gaps(all_topics, covered, topic_names)

    # Calculate totals
    total_watch = sum(v.duration_seconds for v in tier1_videos)

    return TieredRecommendation(
        tier1_combo_videos=tier1_videos,
        tier2_gap_fillers=gaps,
        coverage_report=coverage_reports,
        total_topics=len(all_topics),
        covered_topics=len(covered),
        coverage_percentage=round(len(covered) / max(len(all_topics), 1) * 100, 1),
        total_watch_time_seconds=total_watch,
    )
