"""
Study Notes Generator.
Uses RAG (retrieved transcript chunks) + Ollama to generate
concise, well-structured study notes for each syllabus topic.
"""

from typing import List
from langchain_ollama import ChatOllama

from src.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL


# ── Notes Generation Prompt ───────────────────────────────────────────────────

NOTES_PROMPT = """You are an expert study assistant helping a student prepare for their exam.

Based on the following VIDEO TRANSCRIPT content about "{topic_name}", generate comprehensive study notes.

REQUIREMENTS:
1. Organize notes with clear headings and subheadings
2. Cover these subtopics if mentioned in the transcript: {subtopics}
3. Include key definitions, concepts, and formulas
4. Use bullet points for clarity
5. Add "Key Points to Remember" at the end
6. Keep it concise but thorough — exam-focused
7. If the transcript doesn't cover a subtopic, note it as "Not covered in video"

FORMAT your response in Markdown.

VIDEO TRANSCRIPT CONTENT:
{context}

Generate the study notes now:"""


# ── Generator ─────────────────────────────────────────────────────────────────

async def generate_topic_notes(
    topic_name: str,
    subtopics: List[str],
    context: str,
) -> str:
    """
    Generate study notes for a single topic using LLM + transcript context.

    Args:
        topic_name: Name of the topic.
        subtopics: List of subtopics to cover.
        context: Relevant transcript text (from RAG retrieval).

    Returns:
        Markdown-formatted study notes.
    """
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_LLM_MODEL,
        temperature=0.3,
        num_predict=2048,
    )

    subtopics_str = ", ".join(subtopics) if subtopics else "General concepts"

    prompt = NOTES_PROMPT.format(
        topic_name=topic_name,
        subtopics=subtopics_str,
        context=context[:5000],  # Limit context to avoid token overflow
    )

    response = await llm.ainvoke(prompt)

    return response.content


async def generate_notes_batch(
    topics_with_context: List[dict],
) -> dict:
    """
    Generate notes for multiple topics.

    Args:
        topics_with_context: List of dicts with 'topic_id', 'topic_name',
                           'subtopics', and 'context' keys.

    Returns:
        Dict mapping topic_id → markdown notes string.
    """
    results = {}

    for item in topics_with_context:
        topic_id = item["topic_id"]
        notes = await generate_topic_notes(
            topic_name=item["topic_name"],
            subtopics=item.get("subtopics", []),
            context=item.get("context", ""),
        )
        results[topic_id] = notes

    return results
