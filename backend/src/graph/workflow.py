"""
LangGraph Workflow.
Assembles nodes and edges into a StateGraph with conditional routing.
"""

from langgraph.graph import StateGraph, END

from src.graph.state import StudyAgentState
from src.graph.nodes import (
    parse_syllabus,
    search_youtube,
    fetch_transcripts,
    score_coverage,
    rewrite_queries,
    fallback_search,
    generate_notes,
)
from src.config import MAX_RETRIES


# ── Conditional Edge: Should Retry? ───────────────────────────────────────────

def should_retry_or_proceed(state: StudyAgentState) -> str:
    """
    After scoring coverage, decide the next step:
    - All topics covered → generate notes
    - Uncovered topics + retries left → rewrite queries and retry
    - Uncovered topics + no retries left → fallback search for dedicated videos
    """
    uncovered = state.get("uncovered_topics", [])
    retry_count = state.get("retry_count", 0)

    if not uncovered:
        # All topics covered — proceed to notes
        return "generate_notes"
    elif retry_count < MAX_RETRIES:
        # Still have retries — rewrite queries and search again
        return "rewrite_queries"
    else:
        # Max retries reached, but still gaps — find dedicated videos
        return "fallback_search"


# ── Build the Graph ───────────────────────────────────────────────────────────

def build_study_agent_graph() -> StateGraph:
    """
    Build and compile the LangGraph workflow.

    Flow:
        parse_syllabus → search_youtube → fetch_transcripts → score_coverage
            → [all covered?] → generate_notes → END
            → [uncovered + retries left?] → rewrite_queries → search_youtube (loop)
            → [uncovered + no retries?] → fallback_search → generate_notes → END

    Returns:
        Compiled StateGraph ready to invoke.
    """
    # Create the graph
    graph = StateGraph(StudyAgentState)

    # Add nodes
    graph.add_node("parse_syllabus", parse_syllabus)
    graph.add_node("search_youtube", search_youtube)
    graph.add_node("fetch_transcripts", fetch_transcripts)
    graph.add_node("score_coverage", score_coverage)
    graph.add_node("rewrite_queries", rewrite_queries)
    graph.add_node("fallback_search", fallback_search)
    graph.add_node("generate_notes", generate_notes)

    # Set entry point
    graph.set_entry_point("parse_syllabus")

    # Linear edges
    graph.add_edge("parse_syllabus", "search_youtube")
    graph.add_edge("search_youtube", "fetch_transcripts")
    graph.add_edge("fetch_transcripts", "score_coverage")

    # Conditional edge after score_coverage
    graph.add_conditional_edges(
        "score_coverage",
        should_retry_or_proceed,
        {
            "generate_notes": "generate_notes",
            "rewrite_queries": "rewrite_queries",
            "fallback_search": "fallback_search",
        },
    )

    # Retry loop: rewrite → search again
    graph.add_edge("rewrite_queries", "search_youtube")

    # Fallback → generate notes
    graph.add_edge("fallback_search", "generate_notes")

    # End
    graph.add_edge("generate_notes", END)

    # Compile
    compiled = graph.compile()
    return compiled


# ── Run the Agent ─────────────────────────────────────────────────────────────

async def run_study_agent(
    syllabus_path: str,
    job_id: str = "default",
) -> StudyAgentState:
    """
    Run the full study agent pipeline.

    Args:
        syllabus_path: Path to the uploaded syllabus PDF.
        job_id: Unique identifier for this analysis job.

    Returns:
        Final StudyAgentState with all results.
    """
    graph = build_study_agent_graph()

    initial_state: StudyAgentState = {
        "syllabus_path": syllabus_path,
        "job_id": job_id,
        "retry_count": 0,
        "progress_messages": [],
        "current_step": "starting",
    }

    # Run the graph
    final_state = await graph.ainvoke(initial_state)

    return final_state
