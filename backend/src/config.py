"""
Central configuration for PrepTube.
Loads environment variables and provides defaults for Ollama, ChromaDB, and YouTube API.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")


# ── Ollama Configuration ──────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ── YouTube API ───────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).parent.parent / "chroma_db"),
)

# ── Paths ─────────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "coverage_reports").mkdir(exist_ok=True)
(OUTPUT_DIR / "study_notes").mkdir(exist_ok=True)

# ── Server ────────────────────────────────────────────────────────────────────
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

# ── RAG Settings ──────────────────────────────────────────────────────────────
CHUNK_SIZE = 500          # tokens per chunk
CHUNK_OVERLAP = 50        # token overlap between chunks
TOP_K_RESULTS = 5         # number of results to retrieve per query
COVERAGE_THRESHOLD = 0.6  # minimum coverage score to consider a topic "covered"
MAX_RETRIES = 2           # max query rewrite retries in LangGraph

# ── YouTube Search Settings ───────────────────────────────────────────────────
MAX_VIDEOS_PER_TOPIC = 10  # candidates per topic from YouTube search
MIN_VIEW_COUNT = 1000      # minimum views to consider a video
MIN_VIDEO_LENGTH = 300     # seconds (5 minutes)
MAX_VIDEO_LENGTH = 3600    # seconds (60 minutes)
