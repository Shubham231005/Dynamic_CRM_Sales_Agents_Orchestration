from sqlalchemy.orm import Session
from app.database import models
from app.agents.matching_engine import MatchingEngine
from app.llm.groq_provider import GroqLLMProvider
import logging

logger = logging.getLogger(__name__)

class SalesOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = GroqLLMProvider()
        self.matching_engine = MatchingEngine(db, self.llm_provider)

    async def orchestrate_lead(self, lead_id: int, sales_context: str = None):
        """
        The main workflow for Integration 2.
        Assumes WebDiscovery and Research have already been performed or triggered elsewhere.
        1. Determine Strategic Fit (Matching Engine)
        2. Queue Human Approval
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError("Lead not found")
            
        logger.info(f"Orchestrating sales play for lead: {lead.company_name}")
        
        # 1. Strategic Fit
        fit = await self.matching_engine.determine_strategic_fit(lead_id, sales_context=sales_context)
        
        # 2. Queue actions requiring human approval based on the recommended play
        recommended_play = fit.recommended_play or {}
        channels = recommended_play.get("channels", [])
        
        for channel in channels:
            action_type = f"SEND_{channel.upper()}"
            
            # Check if this action is already queued
            existing = self.db.query(models.ApprovalQueue).filter(
                models.ApprovalQueue.lead_id == lead_id,
                models.ApprovalQueue.action_type == action_type
            ).first()
            
            if not existing:
                draft_prompt = f"Write a personalized, highly converting {channel} message for {lead.company_name} (Industry: {lead.industry}) based on this strategy: {recommended_play.get('strategy')}."
                if sales_context:
                    draft_prompt += f" Ensure it completely strictly adheres to this Sales Context rules: {sales_context}"
                
                try:
                    actual_draft = await self.llm_provider.generate_text(draft_prompt, "You are a top 1% salesperson. Output ONLY the message content.")
                except Exception as e:
                    logger.error(f"Failed to draft message: {e}")
                    actual_draft = f"Could not generate draft for {channel}."

                approval = models.ApprovalQueue(
                    lead_id=lead_id,
                    action_type=action_type,
                    proposed_content=actual_draft
                )
                self.db.add(approval)
                
        self.db.commit()
        return fit
