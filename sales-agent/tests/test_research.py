import pytest
from app.schemas.lead import LeadCreate
from app.research.research_orchestrator import ResearchOrchestrator
from app.database import models

@pytest.mark.asyncio
async def test_research_orchestrator_caching(db_session, monkeypatch):
    from app.services.lead_service import LeadService
    service = LeadService(db_session)
    lead = service.create_lead(LeadCreate(
        company_name="Test Company",
        industry="Tech",
        location="NY"
    ))
    
    # Pre-populate profile
    profile = models.CompanyProfile(
        lead_id=lead.id,
        profile_status="COMPLETED",
        profile_completeness=100
    )
    db_session.add(profile)
    db_session.commit()
    
    orchestrator = ResearchOrchestrator(db_session)
    
    # Should hit cache
    res = await orchestrator.research_lead(lead.id)
    assert res["success"] == True
    assert res["profile_status"] == "COMPLETED"
    
@pytest.mark.asyncio
async def test_research_orchestrator_execution(db_session, monkeypatch):
    from app.services.lead_service import LeadService
    service = LeadService(db_session)
    lead = service.create_lead(LeadCreate(
        company_name="BonBon",
        industry="SuperMarket",
        location="NY"
    ))
    
    # Add verified official website evidence
    ev = models.Evidence(
        lead_id=lead.id,
        field_name="official_website",
        field_value="https://bonbon.com",
        source_type="web_search",
        confidence=0.9,
        classification="OFFICIAL_WEBSITE"
    )
    db_session.add(ev)
    db_session.commit()
    
    # Mock researchers
    async def mock_website_research(self, url):
        return {
            "description": "We are a supermarket",
            "emails": ["contact@bonbon.com"],
            "services": ["Delivery"],
            "social_links": ["https://instagram.com/bonbon"]
        }
    
    from app.research.website_researcher import WebsiteResearcher
    monkeypatch.setattr(WebsiteResearcher, "research", mock_website_research)
    
    orchestrator = ResearchOrchestrator(db_session)
    res = await orchestrator.research_lead(lead.id)
    
    assert res["success"] == True
    profile = res["company_profile"]
    assert profile.email == "contact@bonbon.com"
    assert profile.description == "We are a supermarket"
    assert profile.instagram_url == "https://instagram.com/bonbon"
    assert "Delivery" in profile.services
    
    # Test completeness logic
    assert profile.profile_completeness > 0
    assert profile.profile_status == "COMPLETED"
