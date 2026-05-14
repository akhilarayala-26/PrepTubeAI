"""
MCP Server for Second Brain.
Exposes 4 tools via the Model Context Protocol so any MCP-compatible
client (Claude Desktop, Cursor, etc.) can use the study agent.
"""

import json
import asyncio
from mcp.server.fastmcp import FastMCP

from src.syllabus.parser import extract_text_from_pdf
from src.syllabus.topic_extractor import extract_topics
from src.graph.workflow import run_study_agent


# ── Initialize MCP Server ────────────────────────────────────────────────────

mcp = FastMCP("preptube", instructions=(
    "PrepTube.AI is an AI study agent that analyzes exam syllabi, "
    "finds the best YouTube videos covering each topic, and generates "
    "study notes. Upload a syllabus PDF to get started."
))


# ── Tool 1: Analyze Syllabus ─────────────────────────────────────────────────

@mcp.tool()
async def analyze_syllabus(file_path: str) -> str:
    """
    Parse a syllabus PDF and extract all topics with keywords.

    Args:
        file_path: Absolute path to the syllabus PDF file.

    Returns:
        JSON string with extracted topics, subtopics, and search keywords.
    """
    try:
        raw_text = extract_text_from_pdf(file_path)
        analysis = await extract_topics(raw_text)

        result = {
            "subject": analysis.subject,
            "total_topics": analysis.total_topics,
            "topics": [
                {
                    "id": t.id,
                    "name": t.name,
                    "subtopics": t.subtopics,
                    "keywords": t.keywords,
                    "description": t.description,
                }
                for t in analysis.topics
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 2: Find Videos ──────────────────────────────────────────────────────

@mcp.tool()
async def find_videos(syllabus_path: str) -> str:
    """
    Find the best YouTube videos for a syllabus. Returns a two-tier
    recommendation: combo videos that cover multiple topics (Tier 1)
    and dedicated videos for any gaps (Tier 2).

    Args:
        syllabus_path: Absolute path to the syllabus PDF file.

    Returns:
        JSON with Tier 1 combo videos, Tier 2 gap fillers, and coverage report.
    """
    try:
        state = await run_study_agent(syllabus_path=syllabus_path)

        result = {
            "tier1_combo_videos": state.get("tier1_videos", []),
            "tier2_gap_fillers": state.get("tier2_videos", []),
            "coverage_report": state.get("coverage_report", []),
            "recommendation": state.get("recommendation", {}),
        }

        return json.dumps(result, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 3: Generate Notes ───────────────────────────────────────────────────

@mcp.tool()
async def generate_notes(syllabus_path: str) -> str:
    """
    Generate study notes for each topic in the syllabus.
    Notes are based on the best matching YouTube video transcripts.

    Args:
        syllabus_path: Absolute path to the syllabus PDF file.

    Returns:
        JSON with topic-wise study notes in markdown format.
    """
    try:
        state = await run_study_agent(syllabus_path=syllabus_path)

        return json.dumps({
            "study_notes": state.get("study_notes", {}),
            "topics_covered": len(state.get("study_notes", {})),
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool 4: Check Coverage ───────────────────────────────────────────────────

@mcp.tool()
async def check_coverage(syllabus_path: str) -> str:
    """
    Check which syllabus topics are covered by available YouTube videos
    and which have gaps.

    Args:
        syllabus_path: Absolute path to the syllabus PDF file.

    Returns:
        JSON coverage report showing each topic's coverage score and status.
    """
    try:
        state = await run_study_agent(syllabus_path=syllabus_path)

        coverage = state.get("coverage_report", [])
        recommendation = state.get("recommendation", {})

        result = {
            "total_topics": recommendation.get("total_topics", 0),
            "covered_topics": recommendation.get("covered_topics", 0),
            "coverage_percentage": recommendation.get("coverage_percentage", 0),
            "topic_details": [
                {
                    "topic": c.get("topic_name", ""),
                    "score": c.get("coverage_score", 0),
                    "covered": c.get("is_covered", False),
                    "best_video": c.get("best_video_title", ""),
                }
                for c in coverage
            ],
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
