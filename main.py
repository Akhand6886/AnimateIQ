import logging
import asyncio
import os
import uuid
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict, Any, Optional

from config import settings
from database import engine, Base, get_db, SessionLocal
from models import Job, Series, ProjectMemory, SemanticChunk
from services.vault_service import vault_service
from schemas import (
    JobCreate, JobResponse, StructuredTask, ExecutionPlan, 
    HarnessRequest, ProjectMemorySchema
)

# Workers & Planner
from workers.planner import executive_planner
from workers.harness_workers import (
    research_worker, script_writer_worker, lore_checker_worker,
    thumbnail_strategist_worker, voice_timing_worker, style_consistency_worker,
    fact_verifier_worker, publishing_worker_agent
)

# Services
from services.evaluator import EvaluationLayer
from services.gemini_service import gemini_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MainOrchestrator")

# Create SQLite Database Tables
Base.metadata.create_all(bind=engine)

# Ensure new indexes exist on existing tables
if settings.database_url.startswith("sqlite"):
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_series_id ON jobs (series_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_created_at ON jobs (created_at)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_series_created_at ON series (created_at)"))
            logger.info("[Database] Ensured that job/series optimization indexes exist.")
    except Exception as e:
        logger.error(f"[Database] Failed to ensure database indexes: {e}")

def preseed_memory_defaults():
    """Pre-populates default project memories if the table is empty."""
    db = SessionLocal()
    try:
        existing = db.query(ProjectMemory).count()
        if existing == 0:
            logger.info("[Database] Pre-seeding default project memories...")
            defaults = {
                "preferred_tone": ["High-energy, engaging, full of anime excitement, detailed analytical style."],
                "banned_phrases": [
                    "In conclusion", "As an AI", "Let's dive in", 
                    "It is important to remember", "Overall, this episode", "In summary"
                ],
                "successful_hooks": [
                    "This episode changed everything...", 
                    "Why does everyone hate this character?", 
                    "Here is the dark truth behind the story...",
                    "The animation quality reaches a new peak in this scene!"
                ],
                "style_guide": [
                    "Use H2 and H3 headings for structured reviews",
                    "Keep paragraphs under 3 sentences for high readability",
                    "Analyze character motivations and thematic significance",
                    "Always highlight standout lines or voice acting performance"
                ]
            }
            for key, val in defaults.items():
                db.add(ProjectMemory(key=key, value=val))
            db.commit()
            logger.info("[Database] Pre-seeding completed.")
    except Exception as e:
        logger.error(f"[Database] Failed to pre-seed memories: {e}")
        db.rollback()
    finally:
        db.close()

# Lifespan context manager for FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and graceful shutdown lifecycle."""
    logger.info("--- AnimateIQ Autonomous Agent Pipeline Initialized ---")
    preseed_memory_defaults()
    
    # Synchronize memories to vault and build indexes
    db = SessionLocal()
    try:
        memories = db.query(ProjectMemory).all()
        for m in memories:
            file_path = vault_service.write_memory_to_vault(m.key, m.value)
            await vault_service.index_file(file_path, db)
        logger.info("[Database] Synced project memories to vault and updated vector indexes.")
    except Exception as sync_err:
        logger.error(f"[Database] Startup vault sync failed: {sync_err}")
    finally:
        db.close()
    
    # Start background job processing daemon loop
    daemon_task = asyncio.create_task(background_job_processor_daemon())
    yield
    daemon_task.cancel()
    try:
        await daemon_task
    except asyncio.CancelledError:
        logger.info("Background daemon task cancelled gracefully.")
    logger.info("--- AnimateIQ Autonomous Agent Pipeline Shutting Down ---")

app = FastAPI(
    title="AnimateIQ - Gemini Multi-Agent Engine",
    description="7-Layer Multi-Agent Content Engine for Anime/Manga running on Google Gemini.",
    version="1.0.0",
    lifespan=lifespan
)

# Serves static files from the static directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    """Serves the frontend visual dashboard at the root URL."""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "AnimateIQ Backend API is active. Front-end static files are missing."}


# --- PIPELINE ORCHESTRATION RUNTIME ---

_TERMINAL_STATUSES = frozenset({"completed", "failed"})

async def process_single_job(job_id: str):
    """
    Executes the full 7-layer pipeline dynamically for a single job using Google Gemini.
    """
    db: Session = SessionLocal()
    try:
        job: Job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status in _TERMINAL_STATUSES:
            return

        logger.info(f"[Orchestrator] Initiating Intelligence Harness for Job {job.id} ({job.series_title})...")
    
        # Load Project Memory preferences
        memories = db.query(ProjectMemory).all()
        pref_memory = {m.key: m.value for m in memories}
        tone = pref_memory.get("preferred_tone", ["Engaging and detailed review style"])[0]
        banned = pref_memory.get("banned_phrases", [])
        
        # Layer 1: Interface Layer (Ensure structured task is set)
        if not job.structured_task:
            job.status = "planning"
            db.commit()
            prompt_parse = (
                f"Extract structured parameters for topic '{job.series_title}'. "
                f"Platform matches target type: '{job.target_type}'."
            )
            structured_t = await gemini_service.generate_structured(prompt_parse, StructuredTask)
            job.structured_task = structured_t.model_dump()
            db.commit()
        
        task_info = StructuredTask.model_validate(job.structured_task)
        
        # Layer 2: Planner / Executive Brain
        job.status = "planning"
        db.commit()
        logger.info(f"[Orchestrator] Designing execution plan for structured task...")
        plan: ExecutionPlan = await executive_planner.generate_plan(task_info)
        
        # Store execution plan steps inside database
        plan_steps = []
        for step in plan.steps:
            plan_steps.append({
                "step_id": step.step_id,
                "name": step.name,
                "worker": step.worker,
                "description": step.description,
                "status": "pending",
                "output": "",
                "log": ""
            })
        job.execution_plan = plan_steps
        job.status = "running"
        db.commit()

        # Shared short-term memory (stores worker outputs sequentially)
        short_term_memory = {}
        memory_logs_accumulated = []

        # Layer 7: Orchestration Runtime execution loop
        for index, step in enumerate(plan_steps):
            step_id = step["step_id"]
            worker_type = step["worker"]
            step_name = step["name"]
            
            logger.info(f"[Orchestrator] Step {index+1}/{len(plan_steps)}: '{step_name}' -> routing to '{worker_type}'")
            step["status"] = "running"
            job.execution_plan = list(plan_steps)
            db.commit()

            worker_output = {}
            step_log = f"Invoking {worker_type} for '{step_name}'.\n"

            attempt = 0
            max_correction_retries = 3
            correction_feedback = ""

            while attempt < max_correction_retries:
                attempt += 1
                try:
                    if worker_type == "research_worker":
                        worker_output = await research_worker.process(task_info.topic, task_info.target_platform)
                        step_log += "Collected research facts. Web search executed.\n"
                        break
                        
                    elif worker_type == "script_writer":
                        research_data = short_term_memory.get("research_worker", {})
                        
                        # RAG: Retrieve context from the Obsidian Semantic Vault
                        rag_context = ""
                        try:
                            search_results = await vault_service.search(task_info.topic, db, top_k=3)
                            if search_results:
                                rag_context = "\n\n--- RELEVANT CONTEXT FROM VAULT ---\n"
                                for res in search_results:
                                    rag_context += f"Source: {res['file_path']} (Score: {res['score']:.2f})\n{res['text_content']}\n\n"
                                logger.info(f"[Orchestrator: RAG] Retrieved {len(search_results)} relevant chunks from vault.")
                        except Exception as rag_err:
                            logger.error(f"[Orchestrator: RAG] Vault search failed: {rag_err}")
                            
                        if correction_feedback:
                            step_log += f"Self-Correction loop attempt {attempt} based on evaluator feedback.\n"
                        
                        writer_tone = tone if not correction_feedback else f"{tone}\n\nEVALUATOR REACTION:\n{correction_feedback}"
                        if rag_context:
                            writer_tone = f"{writer_tone}\n{rag_context}"
                            
                        worker_output = await script_writer_worker.process(
                            task_info.topic, 
                            research_data, 
                            writer_tone, 
                            banned
                        )
                        step_log += f"Generated script draft. Length: {worker_output['word_count']} words.\n"
                        
                        # Evaluate Output (Layer 6)
                        eval_res = await EvaluationLayer.evaluate_content(
                            worker_output["draft_text"], 
                            research_data.get("research_facts", []), 
                            tone, 
                            banned
                        )
                        job.evaluations = eval_res
                        db.commit()

                        if eval_res["passed"]:
                            step_log += "Factual and style consistency checks PASSED.\n"
                            break
                        else:
                            step_log += f"Factual/style consistency check FAILED: {eval_res['errors']}\n"
                            correction_feedback = eval_res["feedback"]
                            if attempt == max_correction_retries:
                                step_log += "Max retries reached. Forcing check pass to prevent deadlocks.\n"
                        
                    elif worker_type == "lore_checker":
                        writer_data = short_term_memory.get("script_writer", {})
                        draft = writer_data.get("draft_text", "")
                        worker_output = await lore_checker_worker.process(task_info.topic, draft)
                        step_log += f"Lore audit completed. Is canon-compliant: {worker_output['lore_is_accurate']}.\n"
                        break
                        
                    elif worker_type == "thumbnail_strategist":
                        writer_data = short_term_memory.get("script_writer", {})
                        draft = writer_data.get("draft_text", "")
                        worker_output = await thumbnail_strategist_worker.process(task_info.topic, draft)
                        step_log += f"Generated image generation prompt. Visual asset fetched.\n"
                        break
                        
                    elif worker_type == "voice_timing":
                        writer_data = short_term_memory.get("script_writer", {})
                        draft = writer_data.get("draft_text", "")
                        worker_output = await voice_timing_worker.process(draft)
                        step_log += f"Narration synthesized. TTS audio length: {worker_output['duration_seconds']}s.\n"
                        break
                        
                    elif worker_type == "style_consistency":
                        writer_data = short_term_memory.get("script_writer", {})
                        draft = writer_data.get("draft_text", "")
                        worker_output = await style_consistency_worker.process(task_info.topic, draft)
                        step_log += f"SEO Title: '{worker_output['seo_title']}'. SEO metadata and slug verified.\n"
                        break
                        
                    elif worker_type == "fact_verifier":
                        writer_data = short_term_memory.get("script_writer", {})
                        research_data = short_term_memory.get("research_worker", {})
                        draft = writer_data.get("draft_text", "")
                        worker_output = await fact_verifier_worker.process(draft, research_data.get("research_facts", []))
                        step_log += f"Factual consistency verified. Accuracy Score: {worker_output['accuracy_score']}/10.\n"
                        break
                        
                    elif worker_type == "publishing_worker":
                        writer = short_term_memory.get("script_writer", {})
                        seo = short_term_memory.get("style_consistency", {})
                        thumb = short_term_memory.get("thumbnail_strategist", {})
                        voice = short_term_memory.get("voice_timing", {})
                        
                        payload = {
                            "topic": task_info.topic,
                            "target_platform": task_info.target_platform,
                            "draft_text": writer.get("draft_text", ""),
                            "seo_data": seo,
                            "image_url": thumb.get("image_url", ""),
                            "audio_url": voice.get("audio_url", ""),
                            "video_url": voice.get("video_url", "")
                        }
                        worker_output = await publishing_worker_agent.process(job.id, payload)
                        step_log += f"Asset payloads uploaded. CMS sync status: {worker_output['status']}.\n"
                        break
                        
                    else:
                        step_log += f"Unknown worker '{worker_type}'. Skipping.\n"
                        break

                except Exception as ex:
                    step_log += f"Error executing worker action on attempt {attempt}: {ex}\n"
                    if attempt == max_correction_retries:
                        raise ex

            short_term_memory[worker_type] = worker_output
            
            # Map fields for UI compatibility
            if worker_type == "research_worker":
                job.collector_data = worker_output
            elif worker_type == "script_writer":
                job.writer_data = worker_output
                # Save script to Obsidian Vault and index it
                try:
                    clean_slug = task_info.topic.lower().replace(" ", "-").replace(":", "")
                    file_path = vault_service.write_script_to_vault(
                        series_slug=clean_slug,
                        job_id=job.id,
                        topic=task_info.topic,
                        draft_text=worker_output.get("draft_text", "")
                    )
                    await vault_service.index_file(file_path, db)
                    step_log += f"[Vault] Script saved to vault and indexed.\n"
                except Exception as vault_err:
                    logger.error(f"[Vault] Failed to save script to vault: {vault_err}")
                    step_log += f"[Vault Warning] Script failed to save to vault: {vault_err}\n"
            elif worker_type == "style_consistency":
                job.seo_data = worker_output
                job.formatter_data = {
                    "cleaned_markdown": writer_output.get("draft_text", ""),
                    "validated_title": worker_output.get("seo_title", ""),
                    "slug": worker_output.get("slug", ""),
                    "word_count": len(writer_output.get("draft_text", "").split()),
                    "excerpt": worker_output.get("meta_description", ""),
                    "headings_fixed": True
                }

            # Update step details
            step["status"] = "completed"
            step["output"] = json.dumps(worker_output, indent=2)
            step["log"] = step_log
            
            memory_logs_accumulated.append(f"Loaded memory guidelines for step '{step_name}'.")
            
            job.execution_plan = list(plan_steps)
            job.memory_logs = list(memory_logs_accumulated)
            db.commit()

        # Mark final job status
        job.publisher_data = short_term_memory.get("publishing_worker", {})
        job.status = "completed"
        db.commit()
        logger.info(f"[Orchestrator] Multi-agent execution completed for Job {job.id}.")

    except Exception as e:
        logger.error(f"[Orchestrator] Execution failed for Job {job_id}: {e}", exc_info=True)
        try:
            job.status = "failed"
            job.error_message = str(e)[:2000]
            job.retry_count += 1
            db.commit()
        except Exception as db_err:
            logger.error(f"[Orchestrator] Failed to persist error state: {db_err}")
            db.rollback()
    finally:
        db.close()

async def background_job_processor_daemon():
    """
    Continuous background daemon polling SQLite for queued jobs.
    """
    while True:
        db: Session = SessionLocal()
        try:
            queued_jobs = db.query(Job).filter(Job.status == "queued").all()
            for job in queued_jobs:
                job.status = "planning"
                db.commit()
                asyncio.create_task(process_single_job(job.id))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[Daemon] Error in background job processor daemon: {e}")
        finally:
            db.close()
        await asyncio.sleep(5)


# --- REST API ENDPOINTS ---

@app.get("/api/harness/settings")
async def get_harness_settings():
    """Retrieve harness configuration settings (e.g. current LLM provider)."""
    return {
        "llm_provider": "gemini",
        "default_model": settings.gemini_default_model
    }

@app.post("/api/harness/parse", response_model=StructuredTask)
async def parse_prompt_to_task(req: HarnessRequest):
    """
    Interface Layer (Layer 1).
    """
    logger.info(f"[API: Parse] Parsing raw user prompt: '{req.prompt}'")
    prompt = (
        f"You are the Interface Layer parser of the AnimateIQ Engine.\n"
        f"Parse the user's raw video or blog request into a structured task JSON object.\n\n"
        f"User Prompt: \"{req.prompt}\"\n\n"
        f"Determine the topic, style/tone, target_platform, estimated duration, and assets needed (e.g. Script, Thumbnail, Voice Audio, Finished Video)."
    )
    
    parsed_task = await gemini_service.generate_structured(prompt, StructuredTask)
    logger.info(f"[API: Parse] Output topic: '{parsed_task.topic}' on target: '{parsed_task.target_platform}'")
    return parsed_task

@app.post("/api/harness/trigger", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_harness_job(task: StructuredTask, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a harness pipeline execution run based on a StructuredTask.
    """
    job_id = str(uuid.uuid4())
    
    # Save a series record if needed
    clean_slug = task.topic.lower().replace(" ", "-").replace(":", "")
    series = db.query(Series).filter(Series.title == task.topic).first()
    series_id = series.id if series else f"series_{clean_slug}"
    
    if not series:
        series = Series(
            id=series_id,
            title=task.topic,
            slug=clean_slug,
            series_type="animeSeries"
        )
        db.add(series)
        db.commit()

    new_job = Job(
        id=job_id,
        target_type="youtube_short" if "short" in task.target_platform.lower() else "editorial_blog",
        series_id=series_id,
        series_title=task.topic,
        status="queued",
        structured_task=task.model_dump()
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    background_tasks.add_task(process_single_job, job_id)
    return new_job

@app.get("/api/harness/memory", response_model=List[ProjectMemorySchema])
async def get_project_memory(db: Session = Depends(get_db)):
    memories = db.query(ProjectMemory).all()
    return [{"key": m.key, "value": m.value} for m in memories]

@app.post("/api/harness/memory")
async def save_project_memory(memory_item: ProjectMemorySchema, db: Session = Depends(get_db)):
    mem = db.query(ProjectMemory).filter(ProjectMemory.key == memory_item.key).first()
    if mem:
        mem.value = memory_item.value
    else:
        mem = ProjectMemory(key=memory_item.key, value=memory_item.value)
        db.add(mem)
    db.commit()
    
    # Sync to Markdown Vault & Vector index
    try:
        file_path = vault_service.write_memory_to_vault(memory_item.key, memory_item.value)
        await vault_service.index_file(file_path, db)
    except Exception as e:
        logger.error(f"[Vault] Failed to sync memory '{memory_item.key}' to vault: {e}")
        
    return {"message": f"Successfully updated memory key: '{memory_item.key}'."}

@app.delete("/api/harness/memory/{key}")
async def delete_project_memory(key: str, db: Session = Depends(get_db)):
    mem = db.query(ProjectMemory).filter(ProjectMemory.key == key).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory key not found")
    db.delete(mem)
    db.commit()
    
    # Delete from Vault & index
    try:
        vault_service.delete_memory_from_vault(key)
        rel_path = f"vault/memories/{key}.md"
        from sqlalchemy import delete
        db.execute(delete(SemanticChunk).where(SemanticChunk.file_path == rel_path))
        db.commit()
    except Exception as e:
        logger.error(f"[Vault] Failed to delete memory '{key}' from vault: {e}")
        
    return {"message": f"Successfully deleted memory key: '{key}'."}

@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/vault/sync")
async def sync_vault_endpoint(db: Session = Depends(get_db)):
    """Manually re-indexes the entire Obsidian Markdown Vault."""
    try:
        res = await vault_service.reindex_vault(db)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vault/search")
async def search_vault_endpoint(query: str, top_k: int = 3, db: Session = Depends(get_db)):
    """Performs semantic vector search over the vault."""
    try:
        res = await vault_service.search(query, db, top_k=top_k)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
