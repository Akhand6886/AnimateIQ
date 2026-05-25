# AnimateIQ

AnimateIQ is a premium, 7-layer multi-agent content engine built for anime and manga content automation. Powered by Google Gemini, the engine dynamically decomposes high-level requests (such as review prompts or recap scripts) into structured execution plans, coordinates specialized worker agents, performs strict factual evaluation loops, and manages a local Obsidian-compatible Markdown Semantic Knowledge Vault.

---

## ⚡ Key Highlights
- **7-Layer Multi-Agent Architecture:** Dynamic planning, research, scriptwriting, lore auditing, thumbnail generation, voice timing synthesis, style checking, and automated publishing.
- **SQLite Database Concurrency Optimizations:** Enabled **WAL mode**, `busy_timeout` retries, and `synchronous=NORMAL` to handle parallel database writes from background agents and web workers safely.
- **Obsidian-Style Semantic Knowledge Vault:** Syncs project memory guidelines and completed scripts into raw, linkable Markdown files under a local `vault/` directory.
- **Embedded Vector Search (RAG):** Automatically parses, chunks, and indexes vault files using Gemini embeddings. Runs a lightweight, pure-Python cosine-similarity vector search engine for agent retrieval.
- **Clean Git Workflow:** Clean file-by-file commit progression.

---

## 📁 Workspace Directory Layout
```
datausingIDE/
├── vault/                  # Local Obsidian-Compatible Semantic Vault
│   ├── memories/           # Syncs preferred_tone, banned_phrases, etc. as .md files
│   ├── scripts/            # Completed agent video/blog scripts as .md files
│   └── characters/         # Character reference profiles used for lore auditing
├── services/
│   ├── gemini_service.py   # Handles Gemini LLM completion & embedding APIs
│   ├── vault_service.py    # Manages markdown file creation, chunking, and cosine search
│   └── tool_layer.py       # Helper tools for agents
├── workers/
│   ├── planner.py          # Executive planner decomposes prompts on the fly
│   └── harness_workers.py  # Specialized agents (researcher, writer, auditor, publisher)
├── static/                 # Frontend dashboard assets (HTML, CSS, JS)
├── data/
│   └── gemini_harness.db   # Main SQLite database (contains jobs, memories, and vector index)
├── database.py             # Database engine setup and SQLite pragma connections
├── models.py               # SQLAlchemy models (Series, Job, ProjectMemory, SemanticChunk)
├── schemas.py              # Request/response models and worker schemas
├── config.py               # Pydantic Settings env loader
└── main.py                 # FastAPI orchestrator server startup & pipeline runner
```

---

## 🚀 Setup and Installation

### 1. Prerequisites
- Python 3.10 or higher
- A Google Gemini API Key (obtained from [Google AI Studio](https://aistudio.google.com/))

### 2. Environment Setup
Clone the repository, open the project directory, and initialize the virtual environment:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Variables
Create a `.env` file in the root of the project directory based on `.env.example`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_DEFAULT_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=60
DATABASE_URL=sqlite:///./data/gemini_harness.db
LOG_LEVEL=INFO
DRY_RUN=True
```

---

## 🛠️ Running the Application

Start the FastAPI backend and dashboard:
```bash
python main.py
```
By default, the server will start at `http://localhost:8000`. You can visit this address in your browser to view the **AnimateIQ Visual Dashboard**.

---

## ⚡ Core Database & Vault Engineering

### 1. SQLite Optimization (Concurrency & Performance)
The database connections configured in `database.py` listener are optimized for multi-agent workloads:
- **WAL Mode (`PRAGMA journal_mode=WAL`)**: Allows readers and writers to access the database file simultaneously, preventing locking crashes.
- **Busy Timeout (`PRAGMA busy_timeout=5000`)**: Forces SQLite to wait up to 5 seconds to resolve database file locks before raising a locked error.
- **Synchronous Normal (`PRAGMA synchronous=NORMAL`)**: Significantly increases database write speeds under WAL mode safely.
- **Foreign Keys (`PRAGMA foreign_keys=ON`)**: Enforces database relational mapping integrity.
- **Fast Indexes**: Added database indexes on `Job.created_at`, `Job.series_id`, and `Series.created_at` for rapid query sorting and joining.

### 2. Semantic Vault & Cosine Search
- **Markdown Storage**: Completed scripts are saved to `vault/scripts/{series_slug}_{job_id}.md` with YAML frontmatter linking back to the parent series. Memory guidelines are saved to `vault/memories/` as bulleted lists.
- **RAG Injection**: Prior to writing a script, the orchestrator queries the vector database for relevant historical information about the topic and injects the results into the prompt context.
- **Manual Syncing**: You can trigger a full sync of the vault to re-index all Markdown files via:
  ```bash
  curl -X POST http://localhost:8000/api/vault/sync
  ```
- **Semantic Searching**: You can test querying the vector database via:
  ```bash
  curl "http://localhost:8000/api/vault/search?query=your_concept&top_k=3"
  ```

---

## 🧪 Running Verification Scripts
We have included dedicated verification scripts to assert system health and verify optimizations:

### 1. Database Connections & Index Verification
Verifies WAL mode, synchronous speeds, busy timeout, and the presence of database optimization indexes:
```bash
./venv/bin/python scratch/verify_db_optimizations.py
```

### 2. Semantic Vault Indexing & RAG Verification
Creates mock character pages, chunks them, inserts their vectors into the database, runs cosine-similarity searches, and tests indexing cleanup:
```bash
./venv/bin/python scratch/verify_semantic_vault.py
```
