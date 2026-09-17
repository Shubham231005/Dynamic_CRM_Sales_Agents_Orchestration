import pytest
from app.schemas.lead import LeadCreate
from app.research.providers.base_search import MockSearchProvider
from app.research.source_verifier import SourceVerifier
from app.research.evidence_extractor import EvidenceExtractor
from app.research.web_discovery_agent import WebDiscoveryAgent

def test_source_verifier():
    verifier = SourceVerifier()
    
    # Mock Lead
    class MockLead:
        company_name = "BonBon Supermarket"
        location = "Andheri"
        phone = "098333 62100"
        industry = "SuperMarket"
        
    lead = MockLead()
    
    candidate = {
        "url": "https://bonbonsupermarket.com",
        "title": "BonBon Supermarket - Official Website",
        "snippet": "Welcome to BonBon Supermarket in Andheri. Call us at 098333 62100.",
        "source_type": "web_search"
    }
    
    verified = verifier.verify(candidate, lead)
    
    assert verified["confidence"] > 0.60
    assert "exact_name_match" in verified["confidence_reasons"]
    assert "location_match" in verified["confidence_reasons"]
    assert "phone_match" in verified["confidence_reasons"]
    assert verified["classification"] == "OFFICIAL_WEBSITE"

def test_whatsapp_classification():
    verifier = SourceVerifier()
    
    class MockLead:
        company_name = "BonBon Supermarket"
        location = "Andheri"
        phone = "098333 62100"
        industry = "SuperMarket"
        
    lead = MockLead()
    
    candidate = {
        "url": "https://api.whatsapp.com/send/?phone=919833362100",
        "title": "Message on WhatsApp",
        "snippet": "Chat with BonBon Supermarket.",
        "source_type": "web_search"
    }
    
    verified = verifier.verify(candidate, lead)
    assert verified["classification"] == "WHATSAPP_LINK"
    
def test_evidence_extractor():
    extractor = EvidenceExtractor()
    
    verified_candidate = {
        "url": "https://bonbonsupermarket.com",
        "classification": "OFFICIAL_WEBSITE",
        "confidence": 0.90,
        "confidence_reasons": ["name_match"]
    }
    
    evidence = extractor.extract(verified_candidate, lead_id=1)
    
    assert len(evidence) == 1
    assert evidence[0]["field_name"] == "official_website"
    assert evidence[0]["field_value"] == "https://bonbonsupermarket.com"
    assert evidence[0]["confidence"] == 0.90

@pytest.mark.asyncio
async def test_web_discovery_agent(db_session):
    from app.services.lead_service import LeadService
    service = LeadService(db_session)
    
    lead = service.create_lead(LeadCreate(
        company_name="BonBon Supermarket",
        industry="SuperMarket",
        location="Andheri",
        phone="098333 62100"
    ))
    
    mock_provider = MockSearchProvider()
    agent = WebDiscoveryAgent(db_session, search_provider=mock_provider)
    
    result = await agent.discover(lead.id)
    
    assert result["success"] == True
    assert result["candidates_found"] > 0
    assert result["verified_sources"] > 0
    assert result["evidence_found"] > 0
    
    # Check if evidence was saved
    updated_lead = service.get_lead(lead.id)
    assert updated_lead.enrichment_status == "COMPLETED"
    assert len(updated_lead.evidence) > 0
    
    evidence_fields = [e.field_name for e in updated_lead.evidence]
    assert "official_website" in evidence_fields
    assert "instagram_url" in evidence_fields
    assert "whatsapp_url" in evidence_fields
