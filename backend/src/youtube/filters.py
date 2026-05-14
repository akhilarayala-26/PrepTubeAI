"""
YouTube Video Filters.
Filters candidate videos by duration, view count, and caption availability.
"""

from typing import List
from src.youtube.searcher import VideoResult
from src.config import MIN_VIEW_COUNT, MIN_VIDEO_LENGTH, MAX_VIDEO_LENGTH


def filter_videos(
    videos: List[VideoResult],
    min_views: int = MIN_VIEW_COUNT,
    min_duration: int = MIN_VIDEO_LENGTH,
    max_duration: int = MAX_VIDEO_LENGTH,
) -> List[VideoResult]:
    """
    Filter videos based on quality criteria.

    Args:
        videos: List of VideoResult from YouTube search.
        min_views: Minimum view count (default: 1000).
        min_duration: Minimum video length in seconds (default: 300 = 5 min).
        max_duration: Maximum video length in seconds (default: 3600 = 60 min).

    Returns:
        Filtered list of VideoResult that meet all criteria.
    """
    filtered = []

    for video in videos:
        # Skip if missing critical metadata
        if video.duration_seconds is None or video.view_count is None:
            continue

        # Duration filter
        if video.duration_seconds < min_duration:
            continue
        if video.duration_seconds > max_duration:
            continue

        # View count filter
        if video.view_count < min_views:
            continue

        filtered.append(video)

    # Sort by view count (most popular first) as a quality signal
    filtered.sort(key=lambda v: v.view_count or 0, reverse=True)

    return filtered


def format_duration(seconds: int) -> str:
    """Format seconds to human-readable duration string."""
    if seconds is None:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
