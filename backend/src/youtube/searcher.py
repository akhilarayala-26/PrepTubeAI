"""
YouTube Video Searcher.
Uses YouTube Data API v3 to search for educational videos by keyword.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from googleapiclient.discovery import build

from src.config import YOUTUBE_API_KEY, MAX_VIDEOS_PER_TOPIC


# ── Data Models ───────────────────────────────────────────────────────────────

class VideoResult(BaseModel):
    """A single YouTube video search result."""
    video_id: str
    title: str
    channel: str
    description: str = ""
    thumbnail_url: str = ""
    published_at: str = ""
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    has_captions: Optional[bool] = None
    url: str = ""


# ── Searcher ──────────────────────────────────────────────────────────────────

def _get_youtube_client():
    """Create a YouTube Data API client."""
    if not YOUTUBE_API_KEY:
        raise ValueError(
            "YouTube API key not set. "
            "Please add YOUTUBE_API_KEY to your .env file. "
            "See the setup guide in the README."
        )
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def _parse_duration(duration_str: str) -> int:
    """
    Parse ISO 8601 duration string to seconds.
    Example: 'PT1H2M30S' → 3750
    """
    import re
    pattern = re.compile(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    )
    match = pattern.match(duration_str or "")
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def search_videos(
    query: str,
    max_results: int = MAX_VIDEOS_PER_TOPIC,
) -> List[VideoResult]:
    """
    Search YouTube for videos matching a query.

    Args:
        query: Search keywords (e.g., "process scheduling operating systems")
        max_results: Maximum number of results to return.

    Returns:
        List of VideoResult with basic info (title, channel, ID).
    """
    youtube = _get_youtube_client()

    # Step 1: Search for videos (costs 100 quota units)
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results,
        relevanceLanguage="en",
        videoCaption="closedCaption",  # Only videos with captions
        order="relevance",
    ).execute()

    video_ids = []
    basic_info = {}

    for item in search_response.get("items", []):
        vid_id = item["id"]["videoId"]
        video_ids.append(vid_id)
        snippet = item["snippet"]
        basic_info[vid_id] = {
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "published_at": snippet.get("publishedAt", ""),
        }

    if not video_ids:
        return []

    # Step 2: Get detailed video info (costs 1 quota unit for up to 50 videos)
    details_response = youtube.videos().list(
        id=",".join(video_ids),
        part="contentDetails,statistics",
    ).execute()

    details_map = {}
    for item in details_response.get("items", []):
        vid_id = item["id"]
        content = item.get("contentDetails", {})
        stats = item.get("statistics", {})
        details_map[vid_id] = {
            "duration_seconds": _parse_duration(content.get("duration", "")),
            "view_count": int(stats.get("viewCount", 0)),
            "has_captions": content.get("caption", "false") == "true",
        }

    # Step 3: Combine into VideoResult objects
    results = []
    for vid_id in video_ids:
        info = basic_info.get(vid_id, {})
        details = details_map.get(vid_id, {})

        results.append(VideoResult(
            video_id=vid_id,
            title=info.get("title", ""),
            channel=info.get("channel", ""),
            description=info.get("description", ""),
            thumbnail_url=info.get("thumbnail_url", ""),
            published_at=info.get("published_at", ""),
            duration_seconds=details.get("duration_seconds"),
            view_count=details.get("view_count"),
            has_captions=details.get("has_captions"),
            url=f"https://www.youtube.com/watch?v={vid_id}",
        ))

    return results


def search_videos_for_topic(
    topic_name: str,
    keywords: List[str],
    max_results: int = MAX_VIDEOS_PER_TOPIC,
) -> List[VideoResult]:
    """
    Search YouTube for videos covering a specific syllabus topic.
    Combines the topic name with keywords for better results.

    Args:
        topic_name: The topic name (e.g., "Process Scheduling")
        keywords: List of search keywords from the topic extractor.
        max_results: Maximum results to return.

    Returns:
        List of VideoResult matching the topic.
    """
    # Use the first 2-3 keywords for the search query
    query_parts = [topic_name] + keywords[:2]
    query = " ".join(query_parts)

    return search_videos(query=query, max_results=max_results)
