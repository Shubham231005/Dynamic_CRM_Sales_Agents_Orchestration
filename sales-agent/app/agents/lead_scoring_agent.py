from sqlalchemy.orm import Session
from app.database import models
from app.llm.interface import BaseLLMProvider
from app.llm.groq_provider import GroqLLMProvider
from app.agents.matching_engine import MatchingEngine
from app.agents.critic_validation_agent import CriticValidationAgent
from app.research.financial_parser import FinancialReportParser
import logging
import json
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class LeadScoringAgent:
    def __init__(self, db: Session, llm_provider: BaseLLMProvider = None):
        self.db = db
        self.llm = llm_provider or GroqLLMProvider()
        self.matching_engine = MatchingEngine(db, self.llm)
        self.critic_agent = CriticValidationAgent(db, self.llm)
        self.financial_parser = FinancialReportParser()

    def _calculate_financial_health_score(self, lead: models.Lead) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Dynamic reasoning over actual financial health ratios.
        Replaces static rule-based scoring (e.g. employee count > 500).
        """
        profile = lead.profile
        context_text = f"{lead.company_name} {lead.description or ''}"
        
        fin_data = self.financial_parser.parse_financial_text(context_text)
        
        # Save extracted financial ratios to profile if DB is active
        if profile and self.db:
            profile.annual_revenue = fin_data.get("annual_revenue_millions")
            profile.profit_margin_pct = fin_data.get("profit_margin_pct")
            profile.debt_to_equity_ratio = fin_data.get("debt_to_equity_ratio")
            profile.revenue_growth_yoy = fin_data.get("revenue_growth_yoy")
            profile.financial_health_score = fin_data.get("financial_health_score")
            self.db.commit()

        raw_health_score = fin_data.get("financial_health_score", 75.0)
        fin_pts = (raw_health_score / 100.0) * 25.0 # Max 25 pts
        
        reasons = [
            f"Dynamic Financial Ratio Health Score {raw_health_score}/100 (+{round(fin_pts, 1)} pts)",
            f"Profit Margin: {fin_data.get('profit_margin_pct')}%, YoY Growth: {fin_data.get('revenue_growth_yoy')}%, D/E Ratio: {fin_data.get('debt_to_equity_ratio')}"
        ]
        return min(25.0, fin_pts), reasons, fin_data

    def _calculate_completeness_score(self, lead: models.Lead) -> Tuple[float, List[str]]:
        reasons = []
        score = 0.0
        
        profile = lead.profile
        completeness = profile.profile_completeness if profile else 0
        score += (completeness / 100.0) * 15.0 # Max 15 pts
        reasons.append(f"Profile completeness {completeness}% (+{round((completeness / 100.0) * 15.0, 1)} pts)")
        
        if lead.description or (profile and profile.description):
            score += 2.5
            reasons.append("Company description available (+2.5 pts)")
            
        services = (profile.services if profile else None) or (lead.services if hasattr(lead, 'services') else None)
        if services and len(services) > 0:
            score += 2.5
            reasons.append(f"Identified {len(services)} services (+2.5 pts)")
            
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
        
        rating = lead.google_rating or 0.0
        if rating > 0:
            rating_score = (rating / 5.0) * 15.0
            score += rating_score
            reasons.append(f"Google rating {rating}/5.0 (+{round(rating_score, 1)} pts)")
        else:
            reasons.append("No Google rating available (+0 pts)")
            
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

    async def _calculate_strategic_alignment_score(
        self, lead: models.Lead, sales_context: str = None
    ) -> Tuple[float, Dict[str, Any], str]:
        try:
            fit = await self.matching_engine.determine_strategic_fit(lead.id, sales_context=sales_context)
            ai_score = (fit.fit_score or 0.5) * 25.0 # Max 25 pts
            play = fit.recommended_play or {}
            reasoning = fit.reasoning or "Strategic alignment calculated via LLM Matching Engine."
            return min(25.0, ai_score), play, reasoning
        except Exception as e:
            logger.error(f"Error evaluating strategic alignment for lead {lead.id}: {e}")
            return 12.5, {"strategy": "Standard Outreach", "channels": ["Email"]}, "Fallback alignment score due to error."

    async def extract_buyer_intelligence(self, lead: models.Lead) -> List[models.BuyerIntelligence]:
        if not self.db:
            return []
            
        existing_buyers = self.db.query(models.BuyerIntelligence).filter(models.BuyerIntelligence.lead_id == lead.id).all()
        if existing_buyers:
            return existing_buyers
            
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
        Executes multi-agent lead scoring pipeline with Critic validation and Financial Health Ratios.
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # 1. Run Reflexive Critic Validation Loop first
        critic_res = await self.critic_agent.validate_lead_profile(lead.id)
        critic_confidence = critic_res.get("critic_confidence_score", 0.95)

        # 2. Component calculations (25 pts each = 100 max)
        fin_pts, fin_reasons, fin_ratios = self._calculate_financial_health_score(lead)
        completeness_pts, completeness_reasons = self._calculate_completeness_score(lead)
        reputation_pts, reputation_reasons = self._calculate_digital_reputation_score(lead)
        alignment_pts, recommended_play, alignment_reasoning = await self._calculate_strategic_alignment_score(lead, sales_context)
        
        # 3. Total composite score weighted by Critic confidence
        raw_score = completeness_pts + reputation_pts + contactability_pts if 'contactability_pts' in locals() else (completeness_pts + reputation_pts + fin_pts + alignment_pts)
        total_score = round(raw_score * (0.85 + (critic_confidence * 0.15)), 1)
        normalized_fit_score = round(total_score / 100.0, 2)
        
        # 4. Tier assignment
        if total_score >= 80:
            tier = "HOT (Tier 1)"
        elif total_score >= 50:
            tier = "WARM (Tier 2)"
        else:
            tier = "COLD (Tier 3)"

        # 5. Buyer Personas
        buyer_personas = await self.extract_buyer_intelligence(lead)
        buyer_list = [{"role_name": b.role_name, "seniority": b.seniority, "needs": b.inferred_needs} for b in buyer_personas]

        # 6. Update StrategicFit table
        fit = self.db.query(models.StrategicFit).filter(models.StrategicFit.lead_id == lead_id).first()
        if not fit:
            fit = models.StrategicFit(lead_id=lead_id)
            self.db.add(fit)
            
        score_breakdown = {
            "total_score": total_score,
            "tier": tier,
            "components": {
                "financial_health_score": round(fin_pts, 1),
                "profile_completeness_score": round(completeness_pts, 1),
                "digital_reputation_score": round(reputation_pts, 1),
                "strategic_alignment_score": round(alignment_pts, 1)
            },
            "financial_ratios": fin_ratios,
            "critic_validation": {
                "critic_confidence_score": critic_confidence,
                "hallucination_risk_score": critic_res.get("hallucination_risk_score", 0.05)
            },
            "reasons": fin_reasons + completeness_reasons + reputation_reasons,
            "strategy": recommended_play.get("strategy", "Standard Outreach"),
            "channels": recommended_play.get("channels", ["Email"]),
            "buyer_personas": buyer_list
        }

        fit.fit_score = normalized_fit_score
        fit.reasoning = f"[{tier} - {total_score}/100 | Critic Conf: {round(critic_confidence*100)}%] {alignment_reasoning}"
        fit.recommended_play = score_breakdown
        
        lead.status = "SCORED"
        self.db.commit()
        self.db.refresh(lead)
        self.db.refresh(fit)

        logger.info(f"Lead {lead.company_name} scored: {total_score}/100 ({tier}) [Critic Conf: {critic_confidence}]")

        return {
            "success": True,
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "total_score": total_score,
            "tier": tier,
            "fit_score": normalized_fit_score,
            "critic_confidence": critic_confidence,
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
