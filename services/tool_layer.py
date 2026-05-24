import logging
import asyncio
from typing import Dict, List, Any
from services.gemini_service import gemini_service

logger = logging.getLogger("ToolLayer")

class ToolLayer:
    """
    Programmatic tools invoked by worker agents during task execution.
    """

    @staticmethod
    async def web_search(query: str) -> Dict[str, Any]:
        """Simulates web search and extracts facts using Gemini API helper."""
        logger.info(f"[Tool: Search] Running web search query: '{query}'")
        
        prompt = (
            f"You are a web search helper. Extract 3-5 factual sentences about this query:\n"
            f"Query: {query}\n\n"
            f"Respond with a plain text list of facts, one per line."
        )
        facts_text = await gemini_service.generate_text(prompt)
        facts = [line.strip("- * ") for line in facts_text.split("\n") if line.strip()]
        
        return {
            "query": query,
            "research_facts": facts[:5]
        }

    @staticmethod
    async def generate_image(prompt: str) -> str:
        """Simulates context-relevant cover image generation."""
        logger.info(f"[Tool: ImageGen] Generating image cover for prompt: '{prompt[:60]}...'")
        await asyncio.sleep(1)  # Simulate API latency
        
        # Determine a high-quality context-relevant Unsplash visual based on keywords
        prompt_lower = prompt.lower()
        if "naruto" in prompt_lower or "ninja" in prompt_lower:
            return "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800"
        elif "one piece" in prompt_lower or "pirate" in prompt_lower or "luffy" in prompt_lower:
            return "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800"
        elif "demon slayer" in prompt_lower or "hashira" in prompt_lower or "sword" in prompt_lower:
            return "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800"
        else:
            return "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800"

    @staticmethod
    async def text_to_speech(text: str) -> str:
        """Simulates voice audio synthesis."""
        logger.info(f"[Tool: TTS] Synthesizing narration audio: '{text[:60]}...'")
        await asyncio.sleep(1)  # Simulate audio compilation latency
        return "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"

    @staticmethod
    async def assemble_slides(script: str, image_url: str, duration: int) -> Dict[str, Any]:
        """Simulates compiling media elements into a synchronized video timeline storyboard."""
        logger.info(f"[Tool: FFmpeg] Synchronizing slides with voice timing duration: {duration}s")
        await asyncio.sleep(1.5)
        
        # Break script into short subtitle timings
        sentences = [s.strip() for s in script.split(".") if s.strip()]
        timing_map = []
        if not sentences:
            sentences = ["Narration draft compiled successfully."]
            
        sec_per_slide = max(1, duration // len(sentences))
        for idx, sentence in enumerate(sentences):
            timing_map.append({
                "slide_id": f"slide_{idx+1}",
                "start": idx * sec_per_slide,
                "end": (idx + 1) * sec_per_slide,
                "subtitle": sentence
            })
            
        return {
            "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",
            "duration": duration,
            "timing_map": timing_map
        }

tool_layer = ToolLayer()
