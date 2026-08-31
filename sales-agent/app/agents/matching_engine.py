from sqlalchemy.orm import Session
from app.database import models
from app.llm.interface import BaseLLMProvider
import logging
import json

logger = logging.getLogger(__name__)

class MatchingEngine:
    def __init__(self, db: Session, llm_provider: BaseLLMProvider):
        self.db = db
        self.llm = llm_provider

    async def determine_strategic_fit(self, lead_id: int, capability_profile_name: str = "default", sales_context: str = None) -> models.StrategicFit:
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError("Lead not found")
            
        capability = self.db.query(models.CompanyCapabilityProfile).filter(
            models.CompanyCapabilityProfile.name == capability_profile_name
        ).first()
        
        # We assume IndustryPlaybook is already attached or we use heuristics.
        # For this integration, we'll construct a prompt for the LLM based on what we have.
        
        system_prompt = '''You are an expert sales strategist AI. Your task is to analyze the lead against our capabilities and sales context. 
GUARDRAILS:
1. You MUST strictly output a JSON object.
2. The JSON MUST contain EXACTLY these keys: "fit_score" (float between 0.0 and 1.0), "reasoning" (string, max 3 sentences), and "recommended_play" (object containing "strategy", "channels" list, "evidence_required" list).
3. Do not hallucinate capabilities we do not have.
4. Base the generated outreach strategy and channels specifically on the provided Sales Context (example emails/documents) if available.
'''
        
        lead_data = {
            "company_name": lead.company_name,
            "industry": lead.industry,
            "profile_completeness": lead.profile.profile_completeness if lead.profile else 0,
            "evidence": [e.field_name for e in lead.evidence]
        }
        
        capability_data = {
            "offerings": capability.offerings if capability else [],
            "target_industries": capability.target_industries if capability else []
        }
        
        prompt = f"Analyze Lead: {json.dumps(lead_data)}\nOur Capabilities: {json.dumps(capability_data)}\n"
        if sales_context:
            prompt += f"\nSales Context / Example Emails Provided by User:\n{sales_context}\n"
        prompt += "\nOutput JSON format strictly."
        
        try:
            llm_result = await self.llm.generate_json(prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            llm_result = {
                "fit_score": 0.5,
                "reasoning": "Fallback due to LLM error",
                "recommended_play": {"strategy": "Standard", "channels": ["Email"]}
            }
            
        fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead_id).first()
        if not fit:
            fit = models.StrategicFit(lead_id=lead_id)
            self.db.add(fit)
            
        fit.fit_score = llm_result.get("fit_score", 0.0)
        fit.reasoning = llm_result.get("reasoning", "")
        fit.recommended_play = llm_result.get("recommended_play", {})
        
        self.db.commit()
        self.db.refresh(fit)
        return fit
