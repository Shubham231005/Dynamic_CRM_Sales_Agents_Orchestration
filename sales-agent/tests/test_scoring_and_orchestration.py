import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.database import Base, get_db
from app.database import models
from app.main import app
from app.services.lead_service import LeadService
from app.agents.lead_scoring_agent import LeadScoringAgent
from app.orchestrators.sales_orchestrator import SalesOrchestrator
from app.llm.mock_provider import MockLLMProvider

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_lead(db_session):
    lead = models.Lead(
        company_name="Apex Dental Care",
        industry="Dental Clinics",
        location="Mumbai",
        phone="+919876543210",
        email="info@apexdental.com",
        website="https://apexdental.com",
        google_rating=4.8,
        description="Premier dental care clinic offering cosmetic dentistry and implants.",
        status="NEW"
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    # Attach sample profile
    profile = models.CompanyProfile(
        lead_id=lead.id,
        company_name=lead.company_name,
        industry=lead.industry,
        description=lead.description,
        official_website=lead.website,
        email=lead.email,
        phone=lead.phone,
        services=["Teeth Whitening", "Root Canal", "Cosmetic Dentistry"],
        instagram_url="https://instagram.com/apexdental",
        profile_completeness=85,
        profile_status="COMPLETED"
    )
    db_session.add(profile)
    db_session.commit()
    return lead

@pytest.mark.asyncio
async def test_lead_scoring_agent(db_session, sample_lead):
    mock_llm = MockLLMProvider()
    scoring_agent = LeadScoringAgent(db_session, llm_provider=mock_llm)

    res = await scoring_agent.score_lead(sample_lead.id, sales_context="Focus on appointment scheduling software.")
    
    assert res["success"] is True
    assert res["total_score"] > 50.0
    assert "HOT" in res["tier"] or "WARM" in res["tier"]
    assert sample_lead.status == "SCORED"
    
    # Check Buyer Intelligence creation
    buyers = db_session.query(models.BuyerIntelligence).filter(models.BuyerIntelligence.lead_id == sample_lead.id).all()
    assert len(buyers) >= 1
    assert buyers[0].role_name is not None

@pytest.mark.asyncio
async def test_sales_orchestrator(db_session, sample_lead):
    orchestrator = SalesOrchestrator(db_session)
    orchestrator.llm_provider = MockLLMProvider()
    orchestrator.scoring_agent.llm = MockLLMProvider()
    orchestrator.matching_engine.llm = MockLLMProvider()

    fit = await orchestrator.orchestrate_lead(sample_lead.id, sales_context="Test Context")

    assert fit is not None
    assert fit.fit_score >= 0.0
    assert sample_lead.status == "APPROVAL_PENDING"

    # Verify queue entries created
    approvals = db_session.query(models.ApprovalQueue).filter(models.ApprovalQueue.lead_id == sample_lead.id).all()
    assert len(approvals) >= 1

def test_pipeline_summary(db_session, sample_lead):
    service = LeadService(db_session)
    counts = service.get_pipeline_stage_counts()

    assert counts["TOTAL"] >= 1
    assert "NEW" in counts

def test_api_strategy_routes(client, sample_lead):
    # Score lead endpoint
    res = client.post(f"/api/strategy/leads/{sample_lead.id}/score", json={"sales_context": "B2B AI Software"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    # Strategize lead endpoint
    res_strat = client.post(f"/api/strategy/leads/{sample_lead.id}/strategize", json={"sales_context": "B2B AI Software"})
    assert res_strat.status_code == 200

    # Pipeline summary endpoint
    res_sum = client.get("/api/strategy/pipeline-summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert "pipeline_stages" in sum_data

    # Lead pipeline state endpoint
    res_state = client.get(f"/api/strategy/leads/{sample_lead.id}/pipeline-state")
    assert res_state.status_code == 200
    state_data = res_state.json()
    assert state_data["lead_id"] == sample_lead.id
