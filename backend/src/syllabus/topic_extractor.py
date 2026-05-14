"""
Topic Extractor.
Uses Ollama (local LLM) to extract structured topics, subtopics,
and search keywords from raw syllabus text.
"""

import json
import re
from typing import List, Optional

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL


# ── Data Models ───────────────────────────────────────────────────────────────

class Topic(BaseModel):
    """A single topic extracted from the syllabus."""
    id: str = Field(description="Short unique ID like T1, T2, etc.")
    name: str = Field(description="Topic name, e.g. 'Process Management'")
    subtopics: List[str] = Field(
        default_factory=list,
        description="List of subtopics under this topic",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="5-8 YouTube search keywords for this topic",
    )
    description: str = Field(
        default="",
        description="Brief description of what this topic covers",
    )


class SyllabusAnalysis(BaseModel):
    """Complete analysis of a syllabus."""
    subject: str = Field(description="Subject name, e.g. 'Operating Systems'")
    topics: List[Topic] = Field(default_factory=list)
    total_topics: int = 0


# ── Extraction Prompt ─────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are an expert academic syllabus analyzer. 

Given the following syllabus text, extract ALL topics and subtopics that a student would need to study for their exam.

For each topic, provide:
1. A unique ID (T1, T2, T3, ...)
2. The topic name (clear and concise)
3. A list of subtopics
4. 5-8 YouTube search keywords that would help find educational videos about this topic
5. A brief one-line description

IMPORTANT RULES:
- Extract EVERY topic mentioned in the syllabus — don't skip anything
- Keywords should be specific enough to find relevant YouTube videos
- Include the subject name in keywords (e.g., "process scheduling operating systems")
- Make keywords student-friendly (how a student would actually search)

Return your response as valid JSON with this exact structure:
{{
    "subject": "Subject Name",
    "topics": [
        {{
            "id": "T1",
            "name": "Topic Name",
            "subtopics": ["Subtopic 1", "Subtopic 2"],
            "keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
            "description": "Brief description"
        }}
    ]
}}

SYLLABUS TEXT:
{syllabus_text}

Return ONLY valid JSON. No markdown, no code blocks, no explanation."""


# ── Extractor ─────────────────────────────────────────────────────────────────

def _get_llm() -> ChatOllama:
    """Create an Ollama LLM instance."""
    return ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_LLM_MODEL,
        temperature=0.1,  # Low temp for structured extraction
        num_predict=4096,  # Allow long JSON responses
    )


def _clean_json_response(text: str) -> str:
    """
    Clean LLM response to extract valid JSON.
    Handles cases where LLM wraps JSON in markdown code blocks.
    """
    # Remove markdown code blocks if present
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()

    # Find the JSON object boundaries
    start = text.find("{")
    end = text.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError("No JSON object found in LLM response")

    return text[start:end]


async def extract_topics(syllabus_text: str) -> SyllabusAnalysis:
    """
    Extract structured topics from syllabus text using Ollama.

    Args:
        syllabus_text: Raw text extracted from the syllabus PDF.

    Returns:
        SyllabusAnalysis containing all extracted topics with keywords.

    Raises:
        ValueError: If the LLM response cannot be parsed.
    """
    llm = _get_llm()

    # Format the prompt
    prompt = EXTRACTION_PROMPT.format(syllabus_text=syllabus_text[:8000])  # Limit input size

    # Call Ollama
    response = await llm.ainvoke(prompt)
    raw_response = response.content

    # Parse JSON from response
    try:
        cleaned = _clean_json_response(raw_response)
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(
            f"Failed to parse LLM response as JSON: {e}\n"
            f"Raw response: {raw_response[:500]}"
        )

    # Build structured output
    topics = []
    for topic_data in data.get("topics", []):
        topics.append(Topic(
            id=topic_data.get("id", f"T{len(topics)+1}"),
            name=topic_data.get("name", "Unknown Topic"),
            subtopics=topic_data.get("subtopics", []),
            keywords=topic_data.get("keywords", []),
            description=topic_data.get("description", ""),
        ))

    analysis = SyllabusAnalysis(
        subject=data.get("subject", "Unknown Subject"),
        topics=topics,
        total_topics=len(topics),
    )

    return analysis


def extract_topics_sync(syllabus_text: str) -> SyllabusAnalysis:
    """Synchronous wrapper for extract_topics."""
    import asyncio
    return asyncio.run(extract_topics(syllabus_text))
