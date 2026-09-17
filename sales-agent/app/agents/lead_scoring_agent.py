from sqlalchemy.orm import Session
from app.database import models
from app.llm.interface import BaseLLMProvider
from app.llm.groq_provider import GroqLLMProvider
from app.agents.matching_engine import MatchingEngine
import logging
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class LeadScoringAgent:
    def __init__(self, db: Session, llm_provider: BaseLLMProvider = None):
        self.db = db
        self.llm = llm_provider or GroqLLMProvider()
        self.matching_engine = MatchingEngine(db, self.llm)

    def _calculate_completeness_score(self, lead: models.Lead) -> Tuple[float, List[str]]:
        reasons = []
        score = 0.0
        
        profile = lead.profile
        completeness = profile.profile_completeness if profile else 0
        score += (completeness / 100.0) * 15.0 # Max 15 pts for profile completeness
        reasons.append(f"Profile completeness {completeness}% (+{round((completeness / 100.0) * 15.0, 1)} pts)")
        
        # Additional 10 pts for key structured fields
        if lead.description or (profile and profile.description):
            score += 2.5
            reasons.append("Company description available (+2.5 pts)")
            
        services = (profile.services if profile else None) or (lead.services if hasattr(lead, 'services') else None)
        if services and len(services) > 0:
            score += 2.5
            reasons.append(f"Identified {len(services)} services/offerings (+2.5 pts)")
            
        if lead.website or (profile and profile.official_website):
            score += 2.5
            reasons.append("Official website verified (+2.5 pts)")
            
        if lead.address or (profile and profile.address):
            score += 2.5
            reasons.append("Physical address verified (+2.5 pts)")
            
        return min(25.0, score), reasons

    def _calculate_digital_reputation_score(self, lead: models.Lead) -> Tuple[float, List[str]]:
        reasons = []
        score = 0.0
        
        # Google Rating (Max 15 pts)
        rating = lead.google_rating or 0.0
        if rating > 0:
            rating_score = (rating / 5.0) * 15.0
            score += rating_score
            reasons.append(f"Google rating {rating}/5.0 (+{round(rating_score, 1)} pts)")
        else:
            reasons.append("No Google rating available (+0 pts)")
            
        # Social Presence (Max 10 pts: 2.5 pts per social network)
        socials_count = 0
        if lead.instagram_url or (lead.profile and lead.profile.instagram_url):
            socials_count += 1
        if lead.linkedin_url or (lead.profile and lead.profile.linkedin_url):
            socials_count += 1
        if lead.facebook_url or (lead.profile and lead.profile.facebook_url):
            socials_count += 1
        if lead.youtube_url or (lead.profile and lead.profile.youtube_url):
            socials_count += 1
            
        social_score = socials_count * 2.5
        score += social_score
        reasons.append(f"Active across {socials_count} social channels (+{social_score} pts)")
        
        return min(25.0, score), reasons

    def _calculate_contactability_score(self, lead: models.Lead) -> Tuple[float, List[str]]:
        reasons = []
        score = 0.0
        
        email = lead.email or lead.business_email or (lead.profile and lead.profile.email)
        if email:
            score += 7.0
            reasons.append(f"Direct email available ({email}) (+7 pts)")
            
        phone = lead.phone or (lead.profile and lead.profile.phone)
        if phone:
            score += 6.0
            reasons.append(f"Phone number available (+6 pts)")
            
        whatsapp = lead.profile and lead.profile.whatsapp_url
        if whatsapp or phone: # Phone can be used for WhatsApp outreach
            score += 4.0
            reasons.append("WhatsApp channel active (+4 pts)")
            
        social_dm = lead.instagram_url or (lead.profile and lead.profile.instagram_url)
        if social_dm:
            score += 3.0
            reasons.append("Instagram DM handle active (+3 pts)")
            
        return min(20.0, score), reasons

    async def _calculate_strategic_alignment_score(
        self, lead: models.Lead, sales_context: str = None
    ) -> Tuple[float, Dict[str, Any], str]:
        # Delegate to MatchingEngine
        try:
            fit = await self.matching_engine.determine_strategic_fit(lead.id, sales_context=sales_context)
            ai_score = (fit.fit_score or 0.5) * 30.0 # Max 30 pts
            play = fit.recommended_play or {}
            reasoning = fit.reasoning or "Strategic alignment calculated via LLM Matching Engine."
            return min(30.0, ai_score), play, reasoning
        except Exception as e:
            logger.error(f"Error evaluating strategic alignment for lead {lead.id}: {e}")
            return 15.0, {"strategy": "Standard Outreach", "channels": ["Email"]}, "Fallback alignment score due to error."

    async def extract_buyer_intelligence(self, lead: models.Lead) -> List[models.BuyerIntelligence]:
        """
        Infers buyer personas (Decision Maker, Technical Lead, Operations Lead) from company profile & evidence.
        """
        existing_buyers = self.db.query(models.BuyerIntelligence).filter(models.BuyerIntelligence.lead_id == lead.id).all()
        if existing_buyers:
            return existing_buyers
            
        # Determine buyer roles based on industry & profile
        industry_lower = (lead.industry or "").lower()
        buyers_to_create = []
        
        if "tech" in industry_lower or "software" in industry_lower or "it" in industry_lower:
            buyers_to_create = [
                {"role_name": "CTO / Head of Engineering", "seniority": "Executive", "inferred_needs": ["Scalability", "Security", "Developer Productivity"]},
                {"role_name": "VP of Product", "seniority": "Senior VP", "inferred_needs": ["Feature velocity", "User engagement", "Integration capability"]}
            ]
        elif "clinic" in industry_lower or "dental" in industry_lower or "health" in industry_lower or "medical" in industry_lower:
            buyers_to_create = [
                {"role_name": "Clinic Director / Practice Owner", "seniority": "Owner", "inferred_needs": ["Patient acquisition", "Appointment automation", "Local SEO"]},
                {"role_name": "Practice Manager", "seniority": "Management", "inferred_needs": ["Staff scheduling", "Billing efficiency", "Patient follow-ups"]}
            ]
        else:
            buyers_to_create = [
                {"role_name": "Chief Executive Officer / Founder", "seniority": "Executive", "inferred_needs": ["Revenue growth", "Operational efficiency", "Market expansion"]},
                {"role_name": "Head of Sales / Marketing", "seniority": "Director", "inferred_needs": ["Lead conversion", "Pipeline automation", "Brand visibility"]}
            ]
            
        created = []
        for b in buyers_to_create:
            buyer = models.BuyerIntelligence(
                lead_id=lead.id,
                role_name=b["role_name"],
                seniority=b["seniority"],
                inferred_needs=b["inferred_needs"]
            )
            self.db.add(buyer)
            created.append(buyer)
            
        self.db.commit()
        return created

    async def score_lead(self, lead_id: int, sales_context: str = None) -> Dict[str, Any]:
        """
        Executes complete multi-dimensional lead scoring pipeline.
        Returns detailed score breakdown, tier assignment, and strategic fit details.
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # 1. Component calculations
        completeness_pts, completeness_reasons = self._calculate_completeness_score(lead)
        reputation_pts, reputation_reasons = self._calculate_digital_reputation_score(lead)
        contactability_pts, contactability_reasons = self._calculate_contactability_score(lead)
        alignment_pts, recommended_play, alignment_reasoning = await self._calculate_strategic_alignment_score(lead, sales_context)
        
        # 2. Total composite score (0 - 100)
        total_score = round(completeness_pts + reputation_pts + contactability_pts + alignment_pts, 1)
        normalized_fit_score = round(total_score / 100.0, 2)
        
        # 3. Tier assignment
        if total_score >= 80:
            tier = "HOT (Tier 1)"
        elif total_score >= 50:
            tier = "WARM (Tier 2)"
        else:
            tier = "COLD (Tier 3)"

        # 4. Buyer Intelligence Extraction
        buyer_personas = await self.extract_buyer_intelligence(lead)
        buyer_list = [{"role_name": b.role_name, "seniority": b.seniority, "needs": b.inferred_needs} for b in buyer_personas]

        # 5. Persist / Update StrategicFit table
        fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead_id).first()
        if not fit:
            fit = models.StrategicFit(lead_id=lead_id)
            self.db.add(fit)
            
        score_breakdown = {
            "total_score": total_score,
            "tier": tier,
            "components": {
                "profile_completeness_score": round(completeness_pts, 1),
                "digital_reputation_score": round(reputation_pts, 1),
                "contactability_score": round(contactability_pts, 1),
                "strategic_alignment_score": round(alignment_pts, 1)
            },
            "reasons": completeness_reasons + reputation_reasons + contactability_reasons,
            "strategy": recommended_play.get("strategy", "Standard Outreach"),
            "channels": recommended_play.get("channels", ["Email"]),
            "buyer_personas": buyer_list
        }

        fit.fit_score = normalized_fit_score
        fit.reasoning = f"[{tier} - {total_score}/100] {alignment_reasoning}"
        fit.recommended_play = score_breakdown
        
        # Update Lead Status
        lead.status = "SCORED"
        self.db.commit()
        self.db.refresh(lead)
        self.db.refresh(fit)

        logger.info(f"Lead {lead.company_name} scored: {total_score}/100 ({tier})")

        return {
            "success": True,
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "total_score": total_score,
            "tier": tier,
            "fit_score": normalized_fit_score,
            "breakdown": score_breakdown,
            "reasoning": fit.reasoning
        }

    async def score_batch(self, lead_ids: List[int], sales_context: str = None) -> List[Dict[str, Any]]:
        results = []
        for lid in lead_ids:
            try:
                res = await self.score_lead(lid, sales_context=sales_context)
                results.append(res)
            except Exception as e:
                logger.error(f"Failed scoring lead {lid}: {e}")
                results.append({"success": False, "lead_id": lid, "error": str(e)})
        return results
