"""
PrepTube.AI — FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from src.config import BACKEND_HOST, BACKEND_PORT


# ── Create FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(
    title="PrepTube.AI",
    description=(
        "🎓 AI Study Agent — Upload your syllabus, find the best YouTube videos, "
        "and generate study notes. Powered by Ollama, LangGraph, and RAG."
    ),
    version="1.0.0",
)

# ── CORS (allow frontend to connect) ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routes ────────────────────────────────────────────────────────────

app.include_router(router)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "app": "PrepTube.AI",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )
