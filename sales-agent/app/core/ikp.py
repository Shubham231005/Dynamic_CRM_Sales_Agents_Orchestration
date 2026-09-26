"""
Industry Knowledge Packs (IKPs)
=================================
Declarative, pluggable configurations that tell every agent how to behave
for a specific industry.  No code changes needed — drop in a new IKP and
the entire system adapts.

Usage::

    registry = IKPRegistry(db)
    ikp = registry.load("finance_banking")
    channels = ikp["outreach_rules"]["channels_allowed"]

Or seed defaults::

    registry.seed_defaults()  # loads 4 built-in IKPs
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, func
from sqlalchemy.orm import Session

from app.database.database import Base

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DB model
# ═══════════════════════════════════════════════════════════════════════════

class IndustryKnowledgePack(Base):
    __tablename__ = "industry_knowledge_packs"

    id = Column(Integer, primary_key=True, index=True)
    ikp_id = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    version = Column(String, default="1.0")
    config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════

class IKPRegistry:
    def __init__(self, db: Session):
        self.db = db

    def load(self, ikp_id: str) -> Dict[str, Any]:
        """Load an IKP config by its id.  Raises ValueError if not found."""
        pack = self.db.query(IndustryKnowledgePack).filter(
            IndustryKnowledgePack.ikp_id == ikp_id,
            IndustryKnowledgePack.is_active.is_(True),
        ).first()
        if not pack:
            raise ValueError(f"IKP '{ikp_id}' not found or inactive.")
        return pack.config

    def load_for_industry(self, industry: str) -> Dict[str, Any]:
        """
        Fuzzy-match an industry string to the best IKP.
        Falls back to the 'generic_b2b' IKP if nothing matches.
        """
        industry_lower = industry.lower() if industry else ""

        # Direct match on ikp_id
        for ikp_id in _INDUSTRY_ALIASES.get(industry_lower, []):
            try:
                return self.load(ikp_id)
            except ValueError:
                continue

        # Keyword match
        all_packs = self.db.query(IndustryKnowledgePack).filter(
            IndustryKnowledgePack.is_active.is_(True)
        ).all()
        for pack in all_packs:
            keywords = pack.config.get("industry_context", {}).get("keywords", [])
            if any(kw in industry_lower for kw in keywords):
                return pack.config

        # Fallback
        try:
            return self.load("generic_b2b")
        except ValueError:
            logger.warning(f"No IKP found for '{industry}' and no generic fallback. Using empty config.")
            return {}

    def list_all(self) -> List[Dict[str, Any]]:
        packs = self.db.query(IndustryKnowledgePack).filter(
            IndustryKnowledgePack.is_active.is_(True)
        ).all()
        return [
            {"ikp_id": p.ikp_id, "display_name": p.display_name, "version": p.version}
            for p in packs
        ]

    def upsert(self, ikp_id: str, display_name: str, config: Dict[str, Any], version: str = "1.0") -> IndustryKnowledgePack:
        existing = self.db.query(IndustryKnowledgePack).filter(
            IndustryKnowledgePack.ikp_id == ikp_id
        ).first()
        if existing:
            existing.display_name = display_name
            existing.config = config
            existing.version = version
        else:
            existing = IndustryKnowledgePack(
                ikp_id=ikp_id,
                display_name=display_name,
                config=config,
                version=version,
            )
            self.db.add(existing)
        self.db.flush()
        return existing

    def seed_defaults(self) -> None:
        """Seed the 4 built-in IKPs if they don't exist."""
        for ikp_data in _DEFAULT_IKPS:
            existing = self.db.query(IndustryKnowledgePack).filter(
                IndustryKnowledgePack.ikp_id == ikp_data["ikp_id"]
            ).first()
            if not existing:
                self.upsert(
                    ikp_id=ikp_data["ikp_id"],
                    display_name=ikp_data["display_name"],
                    config=ikp_data["config"],
                    version=ikp_data.get("version", "1.0"),
                )
                logger.info(f"Seeded IKP: {ikp_data['ikp_id']}")
        self.db.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Industry keyword aliases for fuzzy matching
# ═══════════════════════════════════════════════════════════════════════════

_INDUSTRY_ALIASES: Dict[str, List[str]] = {
    "finance": ["finance_banking"],
    "banking": ["finance_banking"],
    "fintech": ["finance_banking"],
    "insurance": ["finance_banking"],
    "financial services": ["finance_banking"],
    "nbfc": ["finance_banking"],

    "it": ["it_saas"],
    "saas": ["it_saas"],
    "software": ["it_saas"],
    "technology": ["it_saas"],
    "tech": ["it_saas"],
    "cloud": ["it_saas"],
    "ai": ["it_saas"],

    "manufacturing": ["b2b_manufacturing"],
    "b2b": ["b2b_manufacturing", "generic_b2b"],
    "industrial": ["b2b_manufacturing"],
    "oem": ["b2b_manufacturing"],

    "supply chain": ["supply_chain"],
    "logistics": ["supply_chain"],
    "shipping": ["supply_chain"],
    "warehousing": ["supply_chain"],
    "distribution": ["supply_chain"],
    "freight": ["supply_chain"],
}


# ═══════════════════════════════════════════════════════════════════════════
# Default IKP definitions
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_IKPS: List[Dict[str, Any]] = [
    # ── 1. Finance / Banking ─────────────────────────────────────────────
    {
        "ikp_id": "finance_banking",
        "display_name": "Finance — Banking & Financial Services",
        "version": "1.0",
        "config": {
            "industry_context": {
                "description": "Banking, insurance, fintech, NBFC, and financial services companies",
                "keywords": ["bank", "finance", "fintech", "insurance", "nbfc", "lending", "payment"],
                "regulatory_bodies": ["RBI", "SEBI", "IRDAI", "SEC", "FCA"],
                "compliance_frameworks": ["PCI-DSS", "SOC 2", "ISO 27001", "GDPR"],
                "sales_cycle": {
                    "typical_length_days": 90,
                    "complexity": "HIGH",
                    "stages": ["Discovery", "Technical Evaluation", "Security Review", "Procurement", "Legal"],
                },
            },
            "buyer_personas": [
                {
                    "role": "CTO / CIO",
                    "seniority": "C-Suite",
                    "priorities": ["digital_transformation", "security", "scalability"],
                    "messaging_tone": "technical_consultative",
                    "preferred_channels": ["linkedin", "email"],
                    "typical_objections": ["security_concerns", "legacy_integration", "vendor_lock_in"],
                },
                {
                    "role": "CISO / VP Security",
                    "seniority": "VP",
                    "priorities": ["compliance", "threat_detection", "audit_readiness"],
                    "messaging_tone": "security_focused_formal",
                    "preferred_channels": ["email", "conference"],
                    "typical_objections": ["certification_requirements", "data_residency", "pen_test_results"],
                },
                {
                    "role": "CFO / VP Finance",
                    "seniority": "C-Suite",
                    "priorities": ["cost_reduction", "regulatory_compliance", "risk_management"],
                    "messaging_tone": "data_driven_formal",
                    "preferred_channels": ["email"],
                    "typical_objections": ["budget_freeze", "roi_unclear", "existing_vendor"],
                },
            ],
            "qualification_criteria": {
                "minimum_signals": 3,
                "required_signals": ["has_budget_indicators", "has_decision_maker_identified"],
                "disqualification_signals": ["competitor_customer", "too_small_revenue", "recent_vendor_switch"],
                "scoring_weights": {
                    "company_size": 0.15,
                    "growth_signals": 0.20,
                    "pain_point_match": 0.30,
                    "budget_indicators": 0.20,
                    "relationship_access": 0.15,
                },
            },
            "outreach_rules": {
                "max_touchpoints_before_pause": 7,
                "minimum_gap_between_touches_hours": 48,
                "channels_allowed": ["email", "linkedin", "call"],
                "channels_blocked": ["whatsapp", "instagram"],
                "requires_approval_for": ["first_outreach", "pricing_discussion"],
                "compliance_disclaimers": ["This communication is for business purposes only."],
            },
            "intelligence_sources": {
                "primary": ["company_website", "linkedin", "rbi_registry", "crunchbase"],
                "secondary": ["news", "job_postings"],
                "skip": ["google_maps"],
            },
        },
    },

    # ── 2. IT / SaaS ────────────────────────────────────────────────────
    {
        "ikp_id": "it_saas",
        "display_name": "IT — Software & SaaS",
        "version": "1.0",
        "config": {
            "industry_context": {
                "description": "Software companies, SaaS, cloud, AI/ML, and IT services",
                "keywords": ["software", "saas", "cloud", "tech", "ai", "ml", "devops", "startup"],
                "regulatory_bodies": ["SOC 2", "GDPR", "CCPA"],
                "compliance_frameworks": ["SOC 2 Type II", "ISO 27001", "GDPR"],
                "sales_cycle": {
                    "typical_length_days": 30,
                    "complexity": "MEDIUM",
                    "stages": ["Demo", "Trial", "Technical Validation", "Negotiation"],
                },
            },
            "buyer_personas": [
                {
                    "role": "CTO / VP Engineering",
                    "seniority": "C-Suite / VP",
                    "priorities": ["developer_experience", "scalability", "integration_ease"],
                    "messaging_tone": "technical_peer",
                    "preferred_channels": ["linkedin", "email"],
                    "typical_objections": ["build_vs_buy", "migration_effort", "api_limitations"],
                },
                {
                    "role": "Head of Product",
                    "seniority": "Director",
                    "priorities": ["time_to_market", "user_experience", "analytics"],
                    "messaging_tone": "product_focused",
                    "preferred_channels": ["linkedin", "email"],
                    "typical_objections": ["feature_parity", "roadmap_alignment"],
                },
            ],
            "qualification_criteria": {
                "minimum_signals": 2,
                "required_signals": ["has_technical_need"],
                "disqualification_signals": ["competitor_customer", "no_budget"],
                "scoring_weights": {
                    "company_size": 0.10,
                    "growth_signals": 0.25,
                    "pain_point_match": 0.35,
                    "budget_indicators": 0.15,
                    "relationship_access": 0.15,
                },
            },
            "outreach_rules": {
                "max_touchpoints_before_pause": 5,
                "minimum_gap_between_touches_hours": 24,
                "channels_allowed": ["email", "linkedin", "call"],
                "channels_blocked": ["instagram"],
                "requires_approval_for": ["first_outreach"],
            },
            "intelligence_sources": {
                "primary": ["company_website", "linkedin", "crunchbase", "github"],
                "secondary": ["news", "job_postings", "product_hunt"],
                "skip": ["google_maps"],
            },
        },
    },

    # ── 3. B2B Manufacturing ────────────────────────────────────────────
    {
        "ikp_id": "b2b_manufacturing",
        "display_name": "B2B — Manufacturing & Industrial",
        "version": "1.0",
        "config": {
            "industry_context": {
                "description": "B2B manufacturers, OEMs, industrial equipment, raw materials",
                "keywords": ["manufacturing", "industrial", "oem", "factory", "machinery", "steel", "chemical"],
                "regulatory_bodies": ["BIS", "ISO", "OSHA"],
                "compliance_frameworks": ["ISO 9001", "ISO 14001", "CE Marking"],
                "sales_cycle": {
                    "typical_length_days": 180,
                    "complexity": "HIGH",
                    "stages": ["RFI", "Technical Spec", "Sample/Trial", "RFQ", "Negotiation", "Contract"],
                },
            },
            "buyer_personas": [
                {
                    "role": "Procurement Head / Purchase Manager",
                    "seniority": "Director",
                    "priorities": ["cost_optimisation", "supply_reliability", "quality_certification"],
                    "messaging_tone": "formal_relationship",
                    "preferred_channels": ["email", "call"],
                    "typical_objections": ["existing_supplier", "moq_too_high", "lead_time"],
                },
                {
                    "role": "Plant Manager / Operations Head",
                    "seniority": "Director",
                    "priorities": ["uptime", "efficiency", "safety"],
                    "messaging_tone": "practical_technical",
                    "preferred_channels": ["call", "email"],
                    "typical_objections": ["compatibility", "training_required", "downtime_risk"],
                },
            ],
            "qualification_criteria": {
                "minimum_signals": 3,
                "required_signals": ["has_procurement_process", "is_right_scale"],
                "disqualification_signals": ["competitor_customer_locked", "no_capex_budget"],
                "scoring_weights": {
                    "company_size": 0.20,
                    "growth_signals": 0.15,
                    "pain_point_match": 0.25,
                    "budget_indicators": 0.25,
                    "relationship_access": 0.15,
                },
            },
            "outreach_rules": {
                "max_touchpoints_before_pause": 10,
                "minimum_gap_between_touches_hours": 72,
                "channels_allowed": ["email", "call", "whatsapp", "linkedin"],
                "channels_blocked": ["instagram", "telegram"],
                "requires_approval_for": ["first_outreach", "pricing_quote"],
            },
            "intelligence_sources": {
                "primary": ["company_website", "linkedin", "indiamart", "tradeindia"],
                "secondary": ["news", "google_maps"],
                "skip": [],
            },
        },
    },

    # ── 4. Supply Chain / Logistics ─────────────────────────────────────
    {
        "ikp_id": "supply_chain",
        "display_name": "Supply Chain — Logistics & Distribution",
        "version": "1.0",
        "config": {
            "industry_context": {
                "description": "Logistics, warehousing, freight, distribution, and supply chain services",
                "keywords": ["logistics", "supply chain", "warehouse", "freight", "shipping", "distribution", "3pl"],
                "regulatory_bodies": ["DGFT", "Customs", "FSSAI"],
                "compliance_frameworks": ["GDP", "ISO 28000", "C-TPAT"],
                "sales_cycle": {
                    "typical_length_days": 60,
                    "complexity": "MEDIUM",
                    "stages": ["Discovery", "Capability Assessment", "Pilot/POC", "Contract"],
                },
            },
            "buyer_personas": [
                {
                    "role": "Supply Chain Head / VP Operations",
                    "seniority": "VP",
                    "priorities": ["cost_per_unit", "delivery_speed", "visibility"],
                    "messaging_tone": "roi_focused",
                    "preferred_channels": ["email", "whatsapp", "call"],
                    "typical_objections": ["switching_cost", "integration_with_erp", "regional_coverage"],
                },
                {
                    "role": "Logistics Manager",
                    "seniority": "Manager",
                    "priorities": ["route_optimisation", "damage_reduction", "real_time_tracking"],
                    "messaging_tone": "practical_operational",
                    "preferred_channels": ["whatsapp", "call"],
                    "typical_objections": ["too_complex", "driver_adoption", "existing_contract"],
                },
            ],
            "qualification_criteria": {
                "minimum_signals": 2,
                "required_signals": ["has_logistics_pain"],
                "disqualification_signals": ["too_small_volume"],
                "scoring_weights": {
                    "company_size": 0.15,
                    "growth_signals": 0.15,
                    "pain_point_match": 0.30,
                    "budget_indicators": 0.20,
                    "relationship_access": 0.20,
                },
            },
            "outreach_rules": {
                "max_touchpoints_before_pause": 6,
                "minimum_gap_between_touches_hours": 24,
                "channels_allowed": ["email", "whatsapp", "call", "linkedin"],
                "channels_blocked": ["instagram"],
                "requires_approval_for": ["pricing_discussion"],
            },
            "intelligence_sources": {
                "primary": ["company_website", "linkedin"],
                "secondary": ["news", "google_maps", "job_postings"],
                "skip": [],
            },
        },
    },

    # ── 5. Generic B2B (fallback) ───────────────────────────────────────
    {
        "ikp_id": "generic_b2b",
        "display_name": "Generic B2B (Fallback)",
        "version": "1.0",
        "config": {
            "industry_context": {
                "description": "Generic B2B sales approach for unclassified industries",
                "keywords": [],
                "regulatory_bodies": [],
                "compliance_frameworks": [],
                "sales_cycle": {
                    "typical_length_days": 45,
                    "complexity": "MEDIUM",
                    "stages": ["Discovery", "Evaluation", "Negotiation", "Close"],
                },
            },
            "buyer_personas": [
                {
                    "role": "Decision Maker",
                    "seniority": "Director+",
                    "priorities": ["roi", "efficiency", "risk_reduction"],
                    "messaging_tone": "professional",
                    "preferred_channels": ["email", "linkedin"],
                    "typical_objections": ["budget", "timing", "existing_solution"],
                },
            ],
            "qualification_criteria": {
                "minimum_signals": 2,
                "required_signals": [],
                "disqualification_signals": [],
                "scoring_weights": {
                    "company_size": 0.20,
                    "growth_signals": 0.20,
                    "pain_point_match": 0.20,
                    "budget_indicators": 0.20,
                    "relationship_access": 0.20,
                },
            },
            "outreach_rules": {
                "max_touchpoints_before_pause": 6,
                "minimum_gap_between_touches_hours": 48,
                "channels_allowed": ["email", "linkedin", "call", "whatsapp"],
                "channels_blocked": [],
                "requires_approval_for": ["first_outreach"],
            },
            "intelligence_sources": {
                "primary": ["company_website", "linkedin"],
                "secondary": ["news", "google_maps", "job_postings"],
                "skip": [],
            },
        },
    },
]
