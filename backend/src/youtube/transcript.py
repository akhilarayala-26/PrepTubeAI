"""
YouTube Transcript Fetcher.
Fetches and cleans video transcripts using the youtube-transcript-api library (v1.2+).
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from youtube_transcript_api import YouTubeTranscriptApi


# ── Data Models ───────────────────────────────────────────────────────────────

class TranscriptSegment(BaseModel):
    """A single segment of a video transcript with timestamp."""
    text: str
    start: float = Field(description="Start time in seconds")
    duration: float = Field(description="Duration in seconds")


class VideoTranscript(BaseModel):
    """Full transcript for a YouTube video."""
    video_id: str
    segments: List[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    language: str = "en"
    is_auto_generated: bool = False
    error: Optional[str] = None


# ── Fetcher ───────────────────────────────────────────────────────────────────

def fetch_transcript(video_id: str) -> VideoTranscript:
    """
    Fetch the transcript for a YouTube video.

    Uses the youtube-transcript-api v1.2+ object-oriented API.

    Args:
        video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')

    Returns:
        VideoTranscript with segments and full text.
        If transcript is unavailable, returns object with error message.
    """
    try:
        # v1.2+: instantiate the API client
        api = YouTubeTranscriptApi()

        # Fetch the transcript (prefers manual, falls back to auto-generated)
        transcript_data = api.fetch(video_id, languages=["en"])

        segments = []
        for entry in transcript_data:
            segments.append(TranscriptSegment(
                text=entry.text,
                start=entry.start,
                duration=entry.duration,
            ))

        # Build full text
        full_text = " ".join(seg.text for seg in segments)

        return VideoTranscript(
            video_id=video_id,
            segments=segments,
            full_text=full_text,
            language="en",
        )

    except Exception as e:
        return VideoTranscript(
            video_id=video_id,
            error=f"Failed to fetch transcript: {str(e)}",
        )


def fetch_transcripts_batch(
    video_ids: List[str],
) -> Dict[str, VideoTranscript]:
    """
    Fetch transcripts for multiple videos.

    Args:
        video_ids: List of YouTube video IDs.

    Returns:
        Dictionary mapping video_id → VideoTranscript.
    """
    results = {}
    for vid_id in video_ids:
        results[vid_id] = fetch_transcript(vid_id)
    return results


def format_transcript_with_timestamps(transcript: VideoTranscript) -> str:
    """
    Format a transcript with timestamps for display.

    Args:
        transcript: VideoTranscript object.

    Returns:
        Formatted string with timestamps like '[00:05:30] text here...'
    """
    if transcript.error:
        return f"[Error: {transcript.error}]"

    lines = []
    for seg in transcript.segments:
        minutes = int(seg.start // 60)
        seconds = int(seg.start % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {seg.text}")

    return "\n".join(lines)
