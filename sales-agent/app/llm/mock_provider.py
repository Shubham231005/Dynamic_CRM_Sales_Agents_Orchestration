from typing import Dict, Any
import json
from app.llm.interface import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    async def generate_json(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        Returns hardcoded JSON responses based on keywords in the prompt for deterministic testing.
        """
        prompt_lower = prompt.lower()
        
        # Determine Strategic Fit
        if "strategic fit" in prompt_lower or "matching engine" in prompt_lower:
            if "healthcare" in prompt_lower:
                return {
                    "fit_score": 0.85,
                    "reasoning": "High alignment with healthcare compliance needs.",
                    "recommended_play": {
                        "strategy": "Compliance-first Outreach",
                        "channels": ["Email", "LinkedIn"],
                        "evidence_required": ["ISO 27001", "HIPAA Compliance"]
                    }
                }
            elif "supermarket" in prompt_lower or "retail" in prompt_lower:
                return {
                    "fit_score": 0.90,
                    "reasoning": "Perfect match for our retail volume solutions.",
                    "recommended_play": {
                        "strategy": "Volume Discount & ROI Outreach",
                        "channels": ["WhatsApp", "Phone"],
                        "evidence_required": ["Case Study: BonBon Supermarket ROI"]
                    }
                }
            else:
                return {
                    "fit_score": 0.60,
                    "reasoning": "Generic fit, standard approach recommended.",
                    "recommended_play": {
                        "strategy": "Standard Outreach",
                        "channels": ["Email"],
                        "evidence_required": []
                    }
                }
                
        # Default fallback
        return {"status": "success", "message": "Mocked JSON response"}

    async def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        if "email" in prompt.lower():
            return "Subject: Enhancing your operations\n\nHi there, I noticed your business and think we can help."
        return "This is a mock text response from the LLM."
