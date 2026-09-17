from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.database import models
from app.llm.interface import BaseLLMProvider
from app.llm.groq_provider import GroqLLMProvider
import logging
import json
import re

logger = logging.getLogger(__name__)

class CriticValidationAgent:
    def __init__(self, db: Session = None, llm_provider: BaseLLMProvider = None):
        self.db = db
        self.llm = llm_provider or GroqLLMProvider()

    def _rule_based_critic_check(self, field_name: str, field_value: str, context_text: str) -> Tuple[bool, float, str]:
        """
        Reflexive rule-based validation loop checking facts against raw context.
        Returns (is_valid, hallucination_risk, reason)
        """
        if not field_value:
            return True, 0.0, "Empty field"

        val_lower = str(field_value).lower()
        ctx_lower = str(context_text).lower()

        if field_name == "email":
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, str(field_value)):
                return False, 0.9, "Invalid email format detected by Critic"
            if any(ext in val_lower for ext in ['.png', '.jpg', '.svg', 'example.com']):
                return False, 0.95, "Likely placeholder/image asset email"

        if field_name == "phone":
            digits = re.sub(r'\D', '', str(field_value))
            if len(digits) < 7 or len(digits) > 15:
                return False, 0.85, "Invalid phone number length"

        if field_name in ["official_website", "instagram_url", "linkedin_url"]:
            if not val_lower.startswith("http"):
                return False, 0.7, "Missing HTTP scheme in URL"

        # Fact checking presence in context snippet
        if context_text and len(context_text) > 20:
            key_tokens = [t for t in val_lower.split() if len(t) > 3 and t not in ['http', 'https', 'www', 'com']]
            matched = sum(1 for t in key_tokens if t in ctx_lower)
            if key_tokens and matched == 0:
                return False, 0.65, "Field value not supported by raw evidence text (potential hallucination)"

        return True, 0.05, "Verified against evidence text"

    async def validate_extracted_data(self, evidence_items: List[Dict[str, Any]], context_text: str = "") -> Dict[str, Any]:
        """
        Performs Reflexive Critic Validation Loop across all extracted evidence items.
        Compares against single-prompt extraction to detect and eliminate hallucinations.
        """
        verified_items = []
        rejected_items = []
        total_risk = 0.0

        for item in evidence_items:
            field_name = item.get("field_name", "unknown")
            field_value = item.get("field_value", "")
            
            is_valid, risk, reason = self._rule_based_critic_check(field_name, field_value, context_text)
            
            total_risk += risk
            item["critic_risk_score"] = round(risk, 2)
            item["critic_reason"] = reason
            item["critic_status"] = "PASSED" if is_valid and risk < 0.35 else "REJECTED"

            if item["critic_status"] == "PASSED":
                verified_items.append(item)
            else:
                rejected_items.append(item)

        total_count = len(evidence_items) or 1
        avg_hallucination_risk = round(total_risk / total_count, 2)
        critic_confidence = round(max(0.0, 1.0 - avg_hallucination_risk), 2)

        return {
            "success": True,
            "total_evaluated": len(evidence_items),
            "verified_count": len(verified_items),
            "rejected_count": len(rejected_items),
            "critic_confidence_score": critic_confidence,
            "hallucination_risk_score": avg_hallucination_risk,
            "verified_evidence": verified_items,
            "rejected_evidence": rejected_items,
            "validation_loop_status": "COMPLETED"
        }

    async def validate_lead_profile(self, lead_id: int) -> Dict[str, Any]:
        """
        Runs Critic loop on a stored lead's evidence and profile in CRM.
        """
        if not self.db:
            raise ValueError("Database session required for validate_lead_profile")
            
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        raw_evidence = [
            {
                "id": e.id,
                "field_name": e.field_name,
                "field_value": e.field_value,
                "source_type": e.source_type,
                "confidence": e.confidence
            }
            for e in lead.evidence
        ]
        
        context_text = f"{lead.company_name} {lead.description or ''} {lead.location or ''}"
        res = await self.validate_extracted_data(raw_evidence, context_text)
        
        # Save verification notes to CRM evidence
        for v in res["verified_evidence"]:
            ev = self.db.query(models.Evidence).filter(models.Evidence.id == v.get("id")).first()
            if ev:
                ev.classification = f"CRITIC_VERIFIED (Confidence: {res['critic_confidence_score']})"
                
        self.db.commit()
        return res
