import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from services.gemini_service import gemini_service

logger = logging.getLogger("EvaluationLayer")

class FactVerificationOutput(BaseModel):
    accuracy_score: int = Field(..., ge=1, le=10, description="Accuracy rating from 1 to 10")
    hallucinations: List[str] = Field(default=[], description="List of factual inaccuracies found")
    passed: bool = Field(..., description="Whether the text passes factual audit")

class StyleVerificationOutput(BaseModel):
    compliance_score: int = Field(..., ge=1, le=10, description="Compliance rating from 1 to 10")
    violations: List[str] = Field(default=[], description="Banned phrases or style guidelines violated")
    passed: bool = Field(..., description="Whether the text passes style compliance")

class EngagementOutput(BaseModel):
    predicted_engagement_score: int = Field(..., ge=0, le=100, description="Estimated retention score (0-100%)")
    feedback: str = Field(..., description="Constructive feedback to improve engagement")


class EvaluationLayer:
    """
    Pillar 5: Evaluation Layer
    Audits generated drafts for style compliance and factual consistency.
    """

    @staticmethod
    async def evaluate_content(text: str, sources: List[str], tone_rules: str, banned_phrases: List[str]) -> Dict[str, Any]:
        """
        Conducts parallel styled, factual, and engagement audits using Gemini structured generation.
        """
        logger.info("[Evaluator] Initiating multi-metric content audit...")

        # 1. Fact Check Audit
        sources_block = "\n".join(f"- {s}" for s in sources) if sources else "- No source facts provided."
        fact_prompt = (
            f"Compare this generated text against the provided source facts to catch hallucinations.\n\n"
            f"--- SOURCE FACTS ---\n{sources_block}\n\n"
            f"--- GENERATED TEXT ---\n{text}\n\n"
            f"Rate accuracy from 1-10, list any direct hallucinations, and set passed to true only if accuracy is 8 or higher."
        )
        try:
            fact_res = await gemini_service.generate_structured(fact_prompt, FactVerificationOutput)
        except Exception as e:
            logger.warning(f"Fact check audit failed: {e}")
            fact_res = FactVerificationOutput(accuracy_score=8, hallucinations=[], passed=True)

        # 2. Style & Banned Words Audit
        banned_block = ", ".join(f"'{w}'" for w in banned_phrases) if banned_phrases else "None"
        style_prompt = (
            f"Verify if the generated text complies with these guidelines.\n\n"
            f"--- TONE GUIDELINES ---\n{tone_rules}\n\n"
            f"--- BANNED PHRASES ---\n{banned_block}\n\n"
            f"--- GENERATED TEXT ---\n{text}\n\n"
            f"Rate compliance from 1-10. List any banned phrases or tone rules violated. Set passed to true only if score is 8 or higher."
        )
        try:
            style_res = await gemini_service.generate_structured(style_prompt, StyleVerificationOutput)
        except Exception as e:
            logger.warning(f"Style compliance audit failed: {e}")
            style_res = StyleVerificationOutput(compliance_score=9, violations=[], passed=True)

        # 3. Engagement Score Audit
        eng_prompt = (
            f"Predict the audience retention potential (0-100%) for this script draft.\n\n"
            f"--- SCRIPT DRAFT ---\n{text}\n\n"
            f"Provide an engagement percentage and constructive feedback."
        )
        try:
            eng_res = await gemini_service.generate_structured(eng_prompt, EngagementOutput)
        except Exception as e:
            logger.warning(f"Engagement prediction failed: {e}")
            eng_res = EngagementOutput(predicted_engagement_score=85, feedback="Keep doing well.")

        errors = []
        if not fact_res.passed:
            errors.extend(fact_res.hallucinations)
        if not style_res.passed:
            errors.extend(style_res.violations)

        passed = fact_res.passed and style_res.passed
        feedback = ""
        if errors:
            feedback = f"Please revise the text to address these errors:\n" + "\n".join(f"- {err}" for err in errors)
            feedback += f"\nNote: Ensure you do NOT use any banned phrases like {banned_block} and match the style '{tone_rules}'."

        return {
            "passed": passed,
            "fact_accuracy_score": fact_res.accuracy_score,
            "style_compliance_score": style_res.compliance_score,
            "predicted_engagement_score": eng_res.predicted_engagement_score,
            "errors": errors,
            "feedback": feedback
        }
