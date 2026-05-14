"""
LangGraph State Schema.
Defines the state that flows through the agent's graph nodes.
"""

from typing import Dict, List, Optional, Any
from typing_extensions import TypedDict

from src.syllabus.topic_extractor import Topic, SyllabusAnalysis
from src.youtube.searcher import VideoResult
from src.youtube.transcript import VideoTranscript
from src.rag.coverage import TopicCoverage, TieredRecommendation


class StudyAgentState(TypedDict, total=False):
    """
    State schema for the LangGraph study agent workflow.

    This state is passed through all nodes and accumulates data
    as the agent progresses through the pipeline.
    """

    # ── Input ─────────────────────────────────────────────────────────────
    syllabus_path: str                              # Path to uploaded PDF
    job_id: str                                     # Unique job identifier

    # ── Syllabus Parsing ──────────────────────────────────────────────────
    syllabus_text: str                              # Raw extracted text
    syllabus_analysis: Optional[dict]               # Parsed SyllabusAnalysis as dict
    topics: List[dict]                              # List of Topic dicts

    # ── YouTube Search ────────────────────────────────────────────────────
    search_results: Dict[str, List[dict]]           # topic_id → list of VideoResult dicts
    all_video_ids: List[str]                        # All unique video IDs found

    # ── Transcripts ───────────────────────────────────────────────────────
    transcripts: Dict[str, dict]                    # video_id → VideoTranscript dict
    videos_with_transcripts: List[str]              # IDs that have valid transcripts

    # ── Coverage ──────────────────────────────────────────────────────────
    coverage_report: List[dict]                     # List of TopicCoverage dicts
    uncovered_topics: List[dict]                    # Topics needing retry/fallback

    # ── Retry Loop ────────────────────────────────────────────────────────
    retry_count: int                                # Current retry iteration (max 2)

    # ── Recommendations ───────────────────────────────────────────────────
    tier1_videos: List[dict]                        # Best combo videos
    tier2_videos: List[dict]                        # Fallback gap fillers
    recommendation: Optional[dict]                  # Full TieredRecommendation dict

    # ── Notes ─────────────────────────────────────────────────────────────
    study_notes: Dict[str, str]                     # topic_id → generated notes

    # ── Progress Tracking ─────────────────────────────────────────────────
    current_step: str                               # Current step name
    progress_messages: List[str]                    # Log of progress messages
    error: Optional[str]                            # Error message if any
