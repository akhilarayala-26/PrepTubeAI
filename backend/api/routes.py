"""
FastAPI Routes.
REST API endpoints for the Second Brain frontend.
"""

import uuid
import asyncio
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.config import UPLOAD_DIR
from src.graph.workflow import run_study_agent


router = APIRouter(prefix="/api", tags=["study-agent"])

# ── In-Memory Job Store ───────────────────────────────────────────────────────
# In production, use Redis or a database. For this project, in-memory is fine.

jobs: Dict[str, dict] = {}


class JobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    current_step: str = ""
    progress_messages: list = []
    error: str = ""


# ── Background Task Runner ───────────────────────────────────────────────────

async def _run_analysis(job_id: str, syllabus_path: str):
    """Run the full study agent pipeline as a background task."""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["current_step"] = "starting"

        final_state = await run_study_agent(
            syllabus_path=syllabus_path,
            job_id=job_id,
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["current_step"] = "done"
        jobs[job_id]["result"] = final_state
        jobs[job_id]["progress_messages"] = final_state.get("progress_messages", [])

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_syllabus(file: UploadFile = File(...)):
    """
    Upload a syllabus PDF file.

    Returns the file path and a job_id for subsequent operations.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # Save file
    file_id = str(uuid.uuid4())[:8]
    filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    content = await file.read()
    file_path.write_bytes(content)

    return {
        "file_path": str(file_path),
        "filename": file.filename,
        "size_kb": round(len(content) / 1024, 1),
    }


@router.post("/analyze")
async def start_analysis(
    file_path: str,
    background_tasks: BackgroundTasks,
):
    """
    Start the full analysis pipeline for an uploaded syllabus.

    This runs in the background. Use /api/status/{job_id} to check progress.
    """
    # Validate file exists
    if not Path(file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}. Upload a file first.",
        )

    job_id = str(uuid.uuid4())[:8]

    # Initialize job
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "file_path": file_path,
        "current_step": "queued",
        "progress_messages": [],
        "result": None,
        "error": "",
    }

    # Run analysis in background
    background_tasks.add_task(_run_analysis, job_id, file_path)

    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Get the current status and progress of an analysis job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        current_step=job.get("current_step", ""),
        progress_messages=job.get("progress_messages", []),
        error=job.get("error", ""),
    )


@router.get("/results/{job_id}")
async def get_results(job_id: str):
    """
    Get the final results of a completed analysis.

    Returns Tier 1 + Tier 2 video recommendations and coverage data.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Status: {job['status']}",
        )

    result = job.get("result", {})

    return {
        "job_id": job_id,
        "syllabus_analysis": result.get("syllabus_analysis", {}),
        "topics": result.get("topics", []),
        "tier1_videos": result.get("tier1_videos", []),
        "tier2_videos": result.get("tier2_videos", []),
        "recommendation": result.get("recommendation", {}),
        "coverage_report": result.get("coverage_report", []),
    }


@router.get("/notes/{job_id}")
async def get_notes(job_id: str):
    """Get generated study notes for a completed analysis."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Status: {job['status']}",
        )

    result = job.get("result", {})

    return {
        "job_id": job_id,
        "study_notes": result.get("study_notes", {}),
    }


@router.get("/topics/{job_id}")
async def get_topics(job_id: str):
    """Get extracted topics from a completed or running analysis."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    result = job.get("result", {})

    return {
        "job_id": job_id,
        "syllabus_analysis": result.get("syllabus_analysis", {}),
        "topics": result.get("topics", []),
    }
