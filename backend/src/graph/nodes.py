"""
LangGraph Nodes.
Each function is a node in the agent's state machine.
Nodes read from and write to the shared StudyAgentState.
"""

from typing import Dict, Any
from src.graph.state import StudyAgentState
from src.syllabus.parser import extract_text_from_pdf
from src.syllabus.topic_extractor import extract_topics
from src.youtube.searcher import search_videos_for_topic
from src.youtube.transcript import fetch_transcript
from src.youtube.filters import filter_videos
from src.rag.embedder import EmbeddingStore, chunk_transcript_with_timestamps
from src.rag.retriever import TranscriptRetriever
from src.rag.coverage import (
    score_topic_coverage,
    build_tiered_recommendation,
    identify_gaps,
    find_minimum_video_set,
)
from src.notes.generator import generate_topic_notes
from src.config import MAX_RETRIES


# ── Node 1: Parse Syllabus ────────────────────────────────────────────────────

async def parse_syllabus(state: StudyAgentState) -> Dict[str, Any]:
    """
    Extract text from PDF and use LLM to identify topics.
    """
    syllabus_path = state["syllabus_path"]

    # Extract raw text from PDF
    raw_text = extract_text_from_pdf(syllabus_path)

    # Use Ollama to extract structured topics
    analysis = await extract_topics(raw_text)

    return {
        "syllabus_text": raw_text,
        "syllabus_analysis": analysis.model_dump(),
        "topics": [t.model_dump() for t in analysis.topics],
        "current_step": "parse_syllabus",
        "progress_messages": [
            f"✅ Parsed syllabus: {analysis.total_topics} topics extracted "
            f"({analysis.subject})"
        ],
        "retry_count": 0,
        "uncovered_topics": [],
    }


# ── Node 2: Search YouTube ───────────────────────────────────────────────────

async def search_youtube(state: StudyAgentState) -> Dict[str, Any]:
    """
    Search YouTube for candidate videos for each topic.
    On retry, only searches for uncovered topics.
    """
    topics = state.get("topics", [])
    retry_count = state.get("retry_count", 0)
    uncovered = state.get("uncovered_topics", [])
    existing_results = state.get("search_results", {})

    # On first run, search all topics. On retry, only uncovered ones.
    topics_to_search = topics
    if retry_count > 0 and uncovered:
        uncovered_ids = {t["topic_id"] for t in uncovered}
        topics_to_search = [t for t in topics if t["id"] in uncovered_ids]

    search_results = dict(existing_results)
    all_video_ids = list(state.get("all_video_ids", []))

    for topic in topics_to_search:
        topic_id = topic["id"]
        keywords = topic.get("keywords", [])
        name = topic.get("name", "")

        try:
            raw_results = search_videos_for_topic(
                topic_name=name,
                keywords=keywords,
            )
            filtered = filter_videos(raw_results)
            search_results[topic_id] = [v.model_dump() for v in filtered]
            all_video_ids.extend(v.video_id for v in filtered)
        except Exception as e:
            search_results[topic_id] = []

    # Deduplicate video IDs
    all_video_ids = list(set(all_video_ids))

    return {
        "search_results": search_results,
        "all_video_ids": all_video_ids,
        "current_step": "search_youtube",
        "progress_messages": [
            f"✅ YouTube search complete: {len(all_video_ids)} candidate videos found"
        ],
    }


# ── Node 3: Fetch Transcripts ────────────────────────────────────────────────

async def fetch_transcripts(state: StudyAgentState) -> Dict[str, Any]:
    """
    Fetch transcripts for all candidate videos.
    """
    all_video_ids = state.get("all_video_ids", [])
    existing_transcripts = state.get("transcripts", {})

    # Only fetch transcripts we don't already have
    new_ids = [vid for vid in all_video_ids if vid not in existing_transcripts]

    transcripts = dict(existing_transcripts)
    videos_with_transcripts = list(state.get("videos_with_transcripts", []))

    for vid_id in new_ids:
        transcript = fetch_transcript(vid_id)
        transcripts[vid_id] = transcript.model_dump()
        if not transcript.error:
            videos_with_transcripts.append(vid_id)

    videos_with_transcripts = list(set(videos_with_transcripts))

    return {
        "transcripts": transcripts,
        "videos_with_transcripts": videos_with_transcripts,
        "current_step": "fetch_transcripts",
        "progress_messages": [
            f"✅ Transcripts fetched: {len(videos_with_transcripts)}/{len(all_video_ids)} available"
        ],
    }


# ── Node 4: Score Coverage ────────────────────────────────────────────────────

async def score_coverage(state: StudyAgentState) -> Dict[str, Any]:
    """
    Embed transcripts, score coverage for each topic,
    and build Tier 1 recommendations via greedy set cover.
    """
    topics = state.get("topics", [])
    transcripts = state.get("transcripts", {})
    search_results = state.get("search_results", {})

    # Initialize embedding store and add transcript chunks
    store = EmbeddingStore(collection_name="transcripts")
    store.clear()  # Fresh start for each analysis

    video_info = {}  # video_id → metadata
    chunk_count = 0

    for vid_id, transcript_data in transcripts.items():
        if transcript_data.get("error"):
            continue

        segments = transcript_data.get("segments", [])
        if not segments:
            continue

        # Find video metadata from search results
        vid_meta = {}
        for topic_id, results in search_results.items():
            for r in results:
                if r.get("video_id") == vid_id:
                    vid_meta = r
                    break
            if vid_meta:
                break

        video_info[vid_id] = {
            "title": vid_meta.get("title", "Unknown"),
            "url": vid_meta.get("url", f"https://www.youtube.com/watch?v={vid_id}"),
            "channel": vid_meta.get("channel", ""),
            "duration_seconds": vid_meta.get("duration_seconds", 0),
            "thumbnail_url": vid_meta.get("thumbnail_url", ""),
        }

        # Chunk transcript and embed
        chunks = chunk_transcript_with_timestamps(segments)
        texts = [c["text"] for c in chunks]
        metadatas = [
            {
                "video_id": vid_id,
                "video_title": vid_meta.get("title", ""),
                "start_time": c["start_time"],
                "end_time": c["end_time"],
            }
            for c in chunks
        ]

        if texts:
            store.add_chunks(
                chunks=texts,
                metadatas=metadatas,
                id_prefix=f"vid_{vid_id}",
            )
            chunk_count += len(texts)

    # Score coverage for each topic
    retriever = TranscriptRetriever(store=store)
    coverage_reports = []
    topic_names = {}

    for topic in topics:
        topic_id = topic["id"]
        topic_name = topic["name"]
        topic_names[topic_id] = topic_name
        subtopics = topic.get("subtopics", [])
        description = topic.get("description", topic_name)

        # Retrieve relevant chunks for this topic
        results = retriever.retrieve_for_topic(
            topic_description=f"{topic_name}: {description}. {' '.join(subtopics)}",
            top_k=5,
        )

        coverage = score_topic_coverage(
            topic_id=topic_id,
            topic_name=topic_name,
            subtopics=subtopics,
            retrieval_results=results,
        )
        coverage_reports.append(coverage)

    # Build Tier 1 recommendation
    recommendation = build_tiered_recommendation(
        coverage_reports=coverage_reports,
        video_info=video_info,
        topic_names=topic_names,
    )

    # Identify uncovered topics
    covered_ids = {
        c.topic_id for c in coverage_reports if c.is_covered
    }
    uncovered = [
        {"topic_id": t["id"], "topic_name": t["name"], "keywords": t.get("keywords", [])}
        for t in topics
        if t["id"] not in covered_ids
    ]

    return {
        "coverage_report": [c.model_dump() for c in coverage_reports],
        "tier1_videos": [v.model_dump() for v in recommendation.tier1_combo_videos],
        "tier2_videos": recommendation.tier2_gap_fillers,
        "recommendation": recommendation.model_dump(),
        "uncovered_topics": uncovered,
        "current_step": "score_coverage",
        "progress_messages": [
            f"✅ Coverage scored: {len(covered_ids)}/{len(topics)} topics covered "
            f"({recommendation.coverage_percentage}%)"
        ],
    }


# ── Node 5: Rewrite Queries ──────────────────────────────────────────────────

async def rewrite_queries(state: StudyAgentState) -> Dict[str, Any]:
    """
    Use LLM to rewrite search queries for uncovered topics.
    This gives YouTube search a second chance with better keywords.
    """
    from langchain_ollama import ChatOllama
    from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL

    uncovered = state.get("uncovered_topics", [])
    retry_count = state.get("retry_count", 0)
    topics = state.get("topics", [])

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_LLM_MODEL,
        temperature=0.3,
    )

    updated_topics = list(topics)

    for unc in uncovered:
        topic_id = unc["topic_id"]
        topic_name = unc["topic_name"]
        old_keywords = unc.get("keywords", [])

        prompt = (
            f"I searched YouTube for '{topic_name}' using these keywords: "
            f"{', '.join(old_keywords[:5])}. "
            f"But I couldn't find good educational videos. "
            f"Please suggest 5 alternative, more specific search queries "
            f"that a student would use to find YouTube tutorials about this topic. "
            f"Return ONLY a comma-separated list of search queries, nothing else."
        )

        response = await llm.ainvoke(prompt)
        new_keywords = [
            kw.strip().strip('"').strip("'")
            for kw in response.content.split(",")
            if kw.strip()
        ][:5]

        # Update the topic's keywords
        for i, t in enumerate(updated_topics):
            if t["id"] == topic_id:
                updated_topics[i] = {**t, "keywords": new_keywords}
                break

    return {
        "topics": updated_topics,
        "retry_count": retry_count + 1,
        "current_step": "rewrite_queries",
        "progress_messages": [
            f"🔄 Retry {retry_count + 1}/{MAX_RETRIES}: "
            f"Rewriting queries for {len(uncovered)} uncovered topics"
        ],
    }


# ── Node 6: Fallback Search ──────────────────────────────────────────────────

async def fallback_search(state: StudyAgentState) -> Dict[str, Any]:
    """
    For topics still uncovered after retries, search for dedicated
    single-topic videos (Tier 2 gap fillers).
    """
    uncovered = state.get("uncovered_topics", [])
    existing_transcripts = state.get("transcripts", {})
    search_results = state.get("search_results", {})

    tier2_videos = []

    for topic_info in uncovered:
        topic_name = topic_info["topic_name"]
        keywords = topic_info.get("keywords", [])

        # More specific search for just this topic
        query = f"{topic_name} tutorial explained"
        try:
            results = search_videos_for_topic(
                topic_name=topic_name,
                keywords=keywords[:2],
                max_results=5,
            )
            filtered = filter_videos(results)

            # Find the best one with a transcript
            best_video = None
            for video in filtered[:3]:
                transcript = fetch_transcript(video.video_id)
                if not transcript.error:
                    existing_transcripts[video.video_id] = transcript.model_dump()
                    best_video = video
                    break

            tier2_videos.append({
                "topic_id": topic_info["topic_id"],
                "topic_name": topic_name,
                "video": best_video.model_dump() if best_video else None,
                "status": "found" if best_video else "not_found",
            })

        except Exception as e:
            tier2_videos.append({
                "topic_id": topic_info["topic_id"],
                "topic_name": topic_name,
                "video": None,
                "status": "error",
                "error": str(e),
            })

    return {
        "tier2_videos": tier2_videos,
        "transcripts": existing_transcripts,
        "uncovered_topics": [],  # Clear — we've handled them
        "current_step": "fallback_search",
        "progress_messages": [
            f"✅ Fallback search: found dedicated videos for "
            f"{sum(1 for v in tier2_videos if v.get('status') == 'found')}"
            f"/{len(tier2_videos)} uncovered topics"
        ],
    }


# ── Node 7: Generate Notes ───────────────────────────────────────────────────

async def generate_notes(state: StudyAgentState) -> Dict[str, Any]:
    """
    Generate study notes for each topic using RAG.
    Retrieves relevant transcript chunks and uses LLM to summarize.
    """
    topics = state.get("topics", [])
    transcripts = state.get("transcripts", {})

    study_notes = {}

    for topic in topics:
        topic_id = topic["id"]
        topic_name = topic["name"]
        subtopics = topic.get("subtopics", [])

        # Gather transcript text for this topic
        context_texts = []

        # From Tier 1 coverage
        for coverage in state.get("coverage_report", []):
            if coverage.get("topic_id") == topic_id and coverage.get("best_video_id"):
                vid_id = coverage["best_video_id"]
                if vid_id in transcripts and not transcripts[vid_id].get("error"):
                    context_texts.append(transcripts[vid_id].get("full_text", ""))

        # From Tier 2 fallback
        for tier2 in state.get("tier2_videos", []):
            if tier2.get("topic_id") == topic_id and tier2.get("video"):
                vid_id = tier2["video"]["video_id"]
                if vid_id in transcripts and not transcripts[vid_id].get("error"):
                    context_texts.append(transcripts[vid_id].get("full_text", ""))

        if context_texts:
            # Use RAG to generate notes
            combined_context = "\n\n".join(context_texts)[:6000]  # Limit context size
            notes = await generate_topic_notes(
                topic_name=topic_name,
                subtopics=subtopics,
                context=combined_context,
            )
            study_notes[topic_id] = notes
        else:
            study_notes[topic_id] = (
                f"# {topic_name}\n\n"
                f"⚠️ No video content found for this topic. "
                f"Consider searching YouTube manually for: {topic_name}"
            )

    return {
        "study_notes": study_notes,
        "current_step": "generate_notes",
        "progress_messages": [
            f"✅ Study notes generated for {len(study_notes)} topics"
        ],
    }
