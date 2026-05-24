from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- JOB SCHEMAS ---

class JobBase(BaseModel):
    target_type: str = Field(..., description="youtube_short or editorial_blog")
    series_id: Optional[str] = Field(None, description="Contentful SysID or local UUID of Series")
    series_title: str = Field(..., min_length=1, description="Name of the anime/manga series")

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: str
    status: str
    collector_data: Dict[str, Any]
    theme_data: Dict[str, Any]
    writer_data: Dict[str, Any]
    seo_data: Dict[str, Any]
    formatter_data: Dict[str, Any]
    publisher_data: Dict[str, Any]
    
    # Intelligence Harness extensions
    structured_task: Optional[Dict[str, Any]] = None
    execution_plan: Optional[List[Dict[str, Any]]] = None
    evaluations: Optional[Dict[str, Any]] = None
    memory_logs: Optional[List[str]] = None

    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- WORKER STRUCTURED OUTPUT SCHEMAS ---

class CollectorOutput(BaseModel):
    title: str = Field(..., description="Full title of the target episode or series")
    series_id: Optional[str] = Field(None, description="Series identifier")
    summary: str = Field(..., description="Raw synopsis or plot summary")
    subtitles: str = Field(..., description="Cleaned transcript chunks or subtitle text")
    characters: List[str] = Field(default=[], description="List of major characters involved")
    raw_synopsis: Optional[str] = Field(None, description="Original synopsis text")
    media_url: Optional[str] = Field(None, description="Cover or thumbnail image URL")


class ThemeExtractorOutput(BaseModel):
    main_theme: str = Field(..., description="Primary emotional or narrative theme identified")
    tone: str = Field(..., description="Overall tone (e.g., intense, melancholic, comedic)")
    strengths: List[str] = Field(..., description="Key storytelling or production strengths")
    weaknesses: List[str] = Field(..., description="Noted pacing flaws or narrative weaknesses")
    standout_moments: List[str] = Field(..., description="Bullet points of standout scenes")
    pacing_analysis: str = Field(..., description="Brief analysis of episode/series pacing")
    narrative_direction: str = Field(..., description="Summary of where the plot is heading")


class ReviewWriterOutput(BaseModel):
    draft_title: str = Field(..., description="Engaging working title for the article/review")
    score: int = Field(..., ge=1, le=10, description="Numerical score from 1 to 10")
    positive_summary: str = Field(..., description="Short summary of pros/successes")
    negative_summary: str = Field(..., description="Short summary of cons/failures")
    verdict: str = Field(..., description="One-sentence final judgment")
    review_body_markdown: str = Field(..., description="Detailed multi-paragraph body text in markdown")
    impactful_lines: List[str] = Field(default=[], description="Up to 3 memorable quotes")


class SEOWorkerOutput(BaseModel):
    seo_title: str = Field(..., description="SEO-optimized title (under 60 characters)")
    slug: str = Field(..., description="URL-friendly slug (kebab-case)")
    meta_description: str = Field(..., description="Compelling meta description (under 160 characters)")
    keywords: List[str] = Field(..., description="List of high-value SEO keywords")
    tags: List[str] = Field(..., description="List of category tags")


class FormatterOutput(BaseModel):
    cleaned_markdown: str = Field(..., description="Fully cleaned and structured markdown body")
    validated_title: str = Field(..., description="Final clean title")
    slug: str = Field(..., description="Verified URL slug")
    word_count: int = Field(..., description="Calculated word count")
    excerpt: str = Field(..., description="Extracted 1-2 sentence hook excerpt")
    headings_fixed: bool = Field(..., description="Whether heading hierarchy was normalized")


class PublisherOutput(BaseModel):
    contentful_entry_id: str = Field(..., description="Contentful SysID or local UUID of the published entry")
    published_url: Optional[str] = Field(None, description="Public URL of entry")
    status: str = Field(..., description="Published status (Published, Draft, DryRun)")
    published_at: str = Field(..., description="ISO timestamp of publishing")


# --- INTELLIGENCE HARNESS SCHEMAS ---

class StructuredTask(BaseModel):
    topic: str = Field(..., min_length=1, description="Topic of the task (e.g. Solo Leveling Episode 5)")
    style: str = Field(..., description="Editorial tone or style guidelines (e.g. fast-paced, analytical)")
    target_platform: str = Field(..., description="Target platform (e.g. YouTube Short, TikTok, Editorial Blog, Contentful Recap)")
    duration: str = Field(..., description="Estimated duration or length constraints")
    assets_needed: List[str] = Field(default=[], description="List of assets to generate: Script, Thumbnail, Narration, Video")

class ExecutionStep(BaseModel):
    step_id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Short name of step")
    worker: str = Field(..., description="Worker type (e.g. research_worker, script_writer, fact_verifier)")
    description: str = Field(..., description="Detailed instructions for the worker")

class ExecutionPlan(BaseModel):
    plan_title: str = Field(..., description="Short title of execution plan")
    steps: List[ExecutionStep] = Field(..., description="Ordered list of steps to execute")

class HarnessRequest(BaseModel):
    prompt: str = Field(..., min_length=3, description="Raw request string from the user")

class ProjectMemorySchema(BaseModel):
    key: str = Field(..., min_length=1, description="Memory identifier (preferred_tone, banned_phrases, style_guide, successful_hooks)")
    value: List[str] = Field(..., description="Array of strings representing memory content")
