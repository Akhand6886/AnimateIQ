import logging
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from services.gemini_service import gemini_service
from services.tool_layer import tool_layer
from schemas import (
    CollectorOutput, ThemeExtractorOutput, ReviewWriterOutput, 
    SEOWorkerOutput, FormatterOutput, PublisherOutput
)

logger = logging.getLogger("SpecializedWorkers")

# Sub-schemas for validation audits
class LoreCheckResult(BaseModel):
    lore_is_accurate: bool = Field(..., description="Whether content is canon-compliant")
    errors_found: List[str] = Field(default=[], description="List of anime/manga lore discrepancies")

class ThumbnailStrategy(BaseModel):
    image_prompt: str = Field(..., description="DALL-E or Midjourney style prompt for cover asset")
    layout_style: str = Field(..., description="Visual description of fonts and layout overlay")

class VerificationResult(BaseModel):
    accuracy_score: int = Field(..., ge=1, le=10)
    corrections_needed: List[str] = Field(default=[])


class ResearchWorker:
    async def process(self, topic: str, target_platform: str) -> Dict[str, Any]:
        logger.info(f"[ResearchWorker] Scraping facts for '{topic}' on platform: '{target_platform}'")
        search_res = await tool_layer.web_search(topic)
        
        collector_out = CollectorOutput(
            title=f"Spotlight: {topic}",
            summary=f"Factual research profile generated for {topic}.",
            subtitles="\n".join(f"[Research Fact] {f}" for f in search_res["research_facts"]),
            characters=["Protagonist", "Supporting Cast", "Rival"],
            raw_synopsis=f"Raw research synopses for {topic}",
            media_url="https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800"
        )
        return collector_out.model_dump()


class ScriptWriterWorker:
    async def process(self, topic: str, research: Dict[str, Any], tone: str, banned_phrases: List[str]) -> Dict[str, Any]:
        logger.info(f"[ScriptWriterWorker] Drafting narrative for '{topic}' with style tone '{tone}'")
        
        banned_block = ", ".join(f"'{p}'" for p in banned_phrases) if banned_phrases else "None"
        prompt = (
            f"Draft a high-retention narration script or article topic: '{topic}'\n\n"
            f"--- RESEARCH CONTEXT ---\n"
            f"Subtitles / Summary:\n{research.get('subtitles', '')}\n\n"
            f"--- TONE GUIDE ---\n"
            f"{tone}\n\n"
            f"--- BANNED PHRASES ---\n"
            f"Do NOT use any of these phrases: {banned_block}\n\n"
            f"Write the narration script draft below. Format it in clean paragraphs without conversational setup."
        )
        
        draft_text = await gemini_service.generate_text(prompt, system="You are an expert anime/manga scriptwriter.")
        
        word_count = len(draft_text.split())
        return {
            "draft_text": draft_text,
            "word_count": word_count,
            "topic": topic
        }


class LoreCheckerWorker:
    async def process(self, topic: str, draft: str) -> Dict[str, Any]:
        logger.info(f"[LoreCheckerWorker] Auditing draft canon accuracy for: {topic}")
        
        prompt = (
            f"Evaluate this draft for lore consistency within the franchise universe of '{topic}':\n\n"
            f"Draft:\n{draft}\n\n"
            f"Determine if the content is accurate to anime/manga canon and list any errors found."
        )
        res = await gemini_service.generate_structured(prompt, LoreCheckResult)
        return res.model_dump()


class ThumbnailStrategistWorker:
    async def process(self, topic: str, draft: str) -> Dict[str, Any]:
        logger.info(f"[ThumbnailStrategistWorker] Conceptualizing graphic visual cover for: {topic}")
        
        prompt = (
            f"Design a high-clickthrough thumbnail concept for this draft on topic '{topic}':\n\n"
            f"Draft Preview:\n{draft[:300]}...\n\n"
            f"Provide an image generation prompt and layout guidelines."
        )
        res = await gemini_service.generate_structured(prompt, ThumbnailStrategy)
        
        # Trigger tool layer mock asset retrieval
        url = await tool_layer.generate_image(res.image_prompt)
        
        return {
            "image_url": url,
            "prompt_used": res.image_prompt,
            "layout_instructions": res.layout_style
        }


class VoiceTimingWorker:
    async def process(self, draft: str) -> Dict[str, Any]:
        logger.info("[VoiceTimingWorker] Synthesizing TTS narration track...")
        audio_url = await tool_layer.text_to_speech(draft)
        
        # Calculate duration based on reading speed (approx 150 words per minute)
        words = len(draft.split())
        duration = max(5, int((words / 150) * 60))
        
        # Trigger FFmpeg slide assembler simulation
        video_package = await tool_layer.assemble_slides(draft, "placeholder_image.png", duration)
        
        return {
            "audio_url": audio_url,
            "duration_seconds": duration,
            "video_url": video_package["video_url"],
            "timing_map": video_package["timing_map"]
        }


class StyleConsistencyWorker:
    async def process(self, topic: str, draft: str) -> Dict[str, Any]:
        logger.info(f"[StyleConsistencyWorker] Formatting headers and generating metadata for: {topic}")
        
        prompt = (
            f"Generate SEO metadata and URL slugs for the topic '{topic}' based on this draft:\n\n"
            f"Draft:\n{draft[:500]}...\n\n"
            f"Ensure title is under 60 chars and slug is lowercase kebab-case."
        )
        meta = await gemini_service.generate_structured(prompt, SEOWorkerOutput)
        
        return meta.model_dump()


class FactVerifierWorker:
    async def process(self, draft: str, sources: List[str]) -> Dict[str, Any]:
        logger.info("[FactVerifierWorker] Checking draft facts against search collector...")
        sources_block = "\n".join(f"- {s}" for s in sources)
        
        prompt = (
            f"Conduct a direct factual audit. Compare the draft text to the source list.\n\n"
            f"--- SOURCE FACTS ---\n{sources_block}\n\n"
            f"--- DRAFT TEXT ---\n{draft}\n\n"
            f"Rate draft accuracy out of 10 and list corrections needed."
        )
        res = await gemini_service.generate_structured(prompt, VerificationResult)
        return res.model_dump()


class PublishingWorker:
    async def process(self, job_id: str, assets: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[PublishingWorker] Compiling package deliverables for Job {job_id}")
        
        # Mock CMS uploading
        pub_out = PublisherOutput(
            contentful_entry_id=f"entry_{job_id[:8]}",
            published_url=f"https://mangamotive.com/posts/{assets.get('seo_data', {}).get('slug', 'post-slug')}",
            status="DryRun",
            published_at=f"2026-05-23T22:15:00Z"
        )
        
        return {
            "published_url": pub_out.published_url,
            "contentful_entry_id": pub_out.contentful_entry_id,
            "status": pub_out.status,
            "published_at": pub_out.published_at,
            "assets": {
                "thumbnail": assets.get("image_url"),
                "audio": assets.get("audio_url"),
                "video": assets.get("video_url")
            }
        }


# Instantiations of worker singletons
research_worker = ResearchWorker()
script_writer_worker = ScriptWriterWorker()
lore_checker_worker = LoreCheckerWorker()
thumbnail_strategist_worker = ThumbnailStrategistWorker()
voice_timing_worker = VoiceTimingWorker()
style_consistency_worker = StyleConsistencyWorker()
fact_verifier_worker = FactVerifierWorker()
publishing_worker_agent = PublishingWorker()
