# 🎓 PrepTube.AI — AI Study Agent

> Upload your exam syllabus → Get the best YouTube videos for every topic → Receive AI-generated study notes.

**Built with:** LangGraph • RAG (ChromaDB) • MCP Servers • Ollama • FastAPI • React

---

## ✨ Features

- **📄 Syllabus Parser** — Upload a PDF, AI extracts all topics and subtopics
- **🔍 Smart YouTube Search** — Finds candidate videos for each topic via YouTube Data API
- **🧠 Semantic Matching** — Uses RAG embeddings to score how well each video covers your syllabus
- **🎯 Two-Tier Recommendations**
  - **Tier 1:** Combo videos (minimum set covering maximum topics)
  - **Tier 2:** Gap fillers (dedicated videos for any uncovered topics)
- **🔄 Self-Correcting Agent** — LangGraph rewrites queries and retries if coverage is low
- **📝 Study Notes** — AI-generated notes from video transcripts, organized by topic
- **🔌 MCP Server** — 4 tools exposed for Claude Desktop / Cursor integration
- **💰 100% Free** — Runs entirely on local models (Ollama) + free YouTube API

---

## 🏗️ Architecture

```
Student → Upload PDF → [LangGraph Agent]
                            ├─ Parse Syllabus (Ollama)
                            ├─ Search YouTube (Data API v3)
                            ├─ Fetch Transcripts
                            ├─ Score Coverage (ChromaDB + RAG)
                            ├─ Self-Correct (retry with rewritten queries)
                            ├─ Fallback Search (dedicated videos for gaps)
                            └─ Generate Notes (RAG + Ollama)
                                → Tier 1 + Tier 2 Videos + Study Notes
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** (for local LLM)
- **YouTube API Key** (free from Google Cloud Console)

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd AgenticAI

# Copy environment template
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

### 2. Install & Start Ollama

```bash
brew install ollama
ollama serve  # Start the server (keep this running)

# In a new terminal, pull required models:
ollama pull llama3.1:8b          # Main LLM (~4.7GB)
ollama pull nomic-embed-text     # Embedding model (~274MB)
```

### 3. Start Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the server
python main.py
# → API available at http://localhost:8000
# → Docs at http://localhost:8000/docs
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
# → UI available at http://localhost:5173
```

### 5. Get YouTube API Key (Free)

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project
3. Enable **YouTube Data API v3**
4. Create an **API Key** under Credentials
5. Add it to your `.env` file: `YOUTUBE_API_KEY=your-key-here`

---

## 🔌 MCP Server (Claude Desktop Integration)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "preptube": {
      "command": "python",
      "args": ["/absolute/path/to/AgenticAI/backend/src/mcp_server/server.py"]
    }
  }
}
```

Then restart Claude Desktop. You'll see 4 tools available:
- `analyze_syllabus` — Parse a PDF and extract topics
- `find_videos` — Find best YouTube videos
- `generate_notes` — Generate study notes
- `check_coverage` — Check topic coverage

---

## 🛠️ Tech Stack

| Component | Technology | Cost |
|---|---|---|
| LLM | Ollama (llama3.1:8b) | Free |
| Embeddings | Ollama (nomic-embed-text) | Free |
| Vector DB | ChromaDB | Free |
| Orchestration | LangGraph | Free |
| YouTube Search | YouTube Data API v3 | Free (10K units/day) |
| Transcripts | youtube-transcript-api | Free |
| Backend | FastAPI + Uvicorn | Free |
| Frontend | React + Vite | Free |
| MCP Server | FastMCP (mcp Python SDK) | Free |

---

## 📁 Project Structure

```
AgenticAI/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── api/routes.py           # REST API endpoints
│   └── src/
│       ├── syllabus/           # PDF parsing + topic extraction
│       ├── youtube/            # YouTube search + transcript fetching
│       ├── rag/                # ChromaDB embeddings + coverage scoring
│       ├── graph/              # LangGraph state machine (7 nodes)
│       ├── notes/              # Study notes generator
│       └── mcp_server/         # MCP Server (4 tools)
│
└── frontend/
    └── src/
        ├── pages/              # Home + Results pages
        ├── components/         # Upload, VideoCard, Notes, Progress
        └── api/                # Axios API client
```


