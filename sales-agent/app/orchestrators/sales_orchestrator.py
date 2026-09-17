from sqlalchemy.orm import Session
from app.database import models
from app.agents.matching_engine import MatchingEngine
from app.agents.lead_scoring_agent import LeadScoringAgent
from app.research.research_orchestrator import ResearchOrchestrator
from app.services.lead_service import LeadService
from app.llm.groq_provider import GroqLLMProvider
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SalesOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = GroqLLMProvider()
        self.matching_engine = MatchingEngine(db, self.llm_provider)
        self.scoring_agent = LeadScoringAgent(db, self.llm_provider)
        self.research_orchestrator = ResearchOrchestrator(db)
        self.lead_service = LeadService(db)

    async def orchestrate_lead(self, lead_id: int, sales_context: str = None, force_research: bool = False) -> models.StrategicFit:
        """
        Main end-to-end Orchestrator pipeline for a single lead:
        1. Research & Profile Building (if incomplete or forced) -> Stage: RESEARCHED
        2. Multi-dimensional Scoring & Alignment -> Stage: SCORED
        3. Drafting Outreach & Human Approval Queueing -> Stage: APPROVAL_PENDING
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")
            
        logger.info(f"Orchestrating end-to-end sales pipeline for lead: {lead.company_name} (ID: {lead.id})")
        
        # --- Stage 1: Discovery & Research ---
        if force_research or not lead.profile or lead.profile.profile_status in ["NOT_STARTED", "FAILED"]:
            lead.status = "RESEARCHING"
            self.db.commit()
            logger.info(f"Triggering research orchestrator for lead {lead.id}")
            research_res = await self.research_orchestrator.research_lead(lead.id, force_refresh=force_research)
            self.db.refresh(lead)
            
        if lead.status == "NEW" or lead.status == "RESEARCHING":
            lead.status = "RESEARCHED"
            self.db.commit()

        # --- Stage 2: Scoring & Strategic Alignment ---
        score_res = await self.scoring_agent.score_lead(lead.id, sales_context=sales_context)
        fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead.id).first()
        
        # --- Stage 3: Outreach Drafting & Approval Queueing ---
        recommended_play = (fit.recommended_play or {}) if fit else {}
        channels = recommended_play.get("channels", ["Email"])
        strategy_desc = recommended_play.get("strategy", "Standard Outreach")
        
        queued_count = 0
        for channel in channels:
            action_type = f"SEND_{channel.upper()}"
            
            # Check if this action is already queued
            existing = self.db.query(models.ApprovalQueue).filter(
                models.ApprovalQueue.lead_id == lead_id,
                models.ApprovalQueue.action_type == action_type
            ).first()
            
            if not existing:
                draft_prompt = (
                    f"Write a personalized, highly converting {channel} message for {lead.company_name} "
                    f"(Industry: {lead.industry}, Location: {lead.location}) based on this strategy: {strategy_desc}."
                )
                if sales_context:
                    draft_prompt += f" Ensure it completely adheres to this Sales Context: {sales_context}"
                
                try:
                    actual_draft = await self.llm_provider.generate_text(
                        draft_prompt, 
                        "You are a top 1% salesperson. Output ONLY the raw message content, without greeting prefixes or meta text."
                    )
                except Exception as e:
                    logger.error(f"Failed to draft {channel} message for lead {lead.id}: {e}")
                    actual_draft = f"Hello {lead.company_name}, we would love to connect and share how we can support your {lead.industry} business."

                approval = models.ApprovalQueue(
                    lead_id=lead_id,
                    action_type=action_type,
                    proposed_content=actual_draft,
                    status="PENDING"
                )
                self.db.add(approval)
                queued_count += 1
                
        # Transition lead status to APPROVAL_PENDING
        lead.status = "APPROVAL_PENDING"
        self.db.commit()
        self.db.refresh(fit)
        
        logger.info(f"Orchestration completed for {lead.company_name}: queued {queued_count} outreach actions.")
        return fit

    async def orchestrate_batch(self, lead_ids: List[int], sales_context: str = None) -> Dict[str, Any]:
        """
        Orchestrates pipeline across a batch of lead IDs.
        """
        total = len(lead_ids)
        successful = 0
        failed = 0
        details = []

        for lid in lead_ids:
            try:
                fit = await self.orchestrate_lead(lid, sales_context=sales_context)
                successful += 1
                details.append({
                    "lead_id": lid,
                    "success": True,
                    "fit_score": fit.fit_score,
                    "strategy": (fit.recommended_play or {}).get("strategy")
                })
            except Exception as e:
                failed += 1
                logger.error(f"Batch orchestration error for lead {lid}: {e}")
                details.append({
                    "lead_id": lid,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "total_processed": total,
            "successful": successful,
            "failed": failed,
            "details": details
        }

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        Returns aggregated sales pipeline statistics across all stages.
        """
        counts = self.lead_service.get_pipeline_stage_counts()
        pending_approvals = self.db.query(models.ApprovalQueue).filter(models.ApprovalQueue.status == "PENDING").count()
        return {
            "pipeline_stages": counts,
            "pending_approvals_count": pending_approvals
        }

    def get_lead_pipeline_state(self, lead_id: int) -> Optional[Dict[str, Any]]:
        """
        Returns current state snapshot for a given lead.
        """
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            return None
            
        fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead_id).first()
        approvals = self.db.query(models.ApprovalQueue).filter(models.ApprovalQueue.lead_id == lead_id).all()
        buyers = self.db.query(models.BuyerIntelligence).filter(models.BuyerIntelligence.lead_id == lead_id).all()

        return {
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "industry": lead.industry,
            "status": lead.status,
            "enrichment_status": lead.enrichment_status,
            "profile_completeness": lead.profile.profile_completeness if lead.profile else 0,
            "strategic_fit": {
                "fit_score": fit.fit_score if fit else 0.0,
                "reasoning": fit.reasoning if fit else None,
                "recommended_play": fit.recommended_play if fit else None
            } if fit else None,
            "buyers": [{"role": b.role_name, "seniority": b.seniority} for b in buyers],
            "approvals": [{"id": a.id, "action_type": a.action_type, "status": a.status} for a in approvals]
        }
