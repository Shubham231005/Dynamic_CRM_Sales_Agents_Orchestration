import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.database import Base, get_db
from app.database import models
from app.main import app
from app.agents.critic_validation_agent import CriticValidationAgent
from app.research.financial_parser import FinancialReportParser
from app.orchestrators.mcp_event_bus import mcp_event_bus, MCPEventBus
from app.orchestrators.benchmark_engine import BenchmarkEngine
from app.agents.lead_scoring_agent import LeadScoringAgent
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
        company_name="BonBon Supermarket",
        industry="SuperMarket",
        location="New York",
        phone="+12125550199",
        email="contact@bonbon.com",
        website="https://bonbon.com",
        google_rating=4.7,
        description="BonBon Supermarket reported annual revenue of $24.5M with profit margin of 18.2% and YoY growth of 15.5%.",
        status="NEW"
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    profile = models.CompanyProfile(
        lead_id=lead.id,
        company_name=lead.company_name,
        industry=lead.industry,
        description=lead.description,
        official_website=lead.website,
        email=lead.email,
        phone=lead.phone,
        services=["Grocery", "Organic Produce", "Express Delivery"],
        profile_completeness=90,
        profile_status="COMPLETED"
    )
    db_session.add(profile)
    db_session.commit()
    return lead

@pytest.mark.asyncio
async def test_critic_validation_agent():
    critic = CriticValidationAgent()
    evidence = [
        {"field_name": "email", "field_value": "contact@bonbon.com"},
        {"field_name": "email", "field_value": "fake_image_asset.png@domain.com"},
        {"field_name": "phone", "field_value": "+12125550199"},
        {"field_name": "official_website", "field_value": "https://bonbon.com"}
    ]
    context = "Welcome to BonBon Supermarket in New York at https://bonbon.com. Contact us at contact@bonbon.com or +12125550199"

    res = await critic.validate_extracted_data(evidence, context)

    assert res["success"] is True
    assert res["verified_count"] >= 3
    assert res["rejected_count"] >= 1
    assert res["critic_confidence_score"] > 0.70

def test_financial_parser():
    parser = FinancialReportParser()
    sample_text = "BonBon Supermarket reports revenue of $45.2M with net profit margin of 19.5% and YoY growth of 22.0% with debt to equity of 0.35."

    metrics = parser.parse_financial_text(sample_text)

    assert metrics["annual_revenue_millions"] == 45.2
    assert metrics["profit_margin_pct"] == 19.5
    assert metrics["debt_to_equity_ratio"] == 0.35
    assert metrics["revenue_growth_yoy"] == 22.0
    assert metrics["financial_health_score"] > 80.0

@pytest.mark.asyncio
async def test_mcp_event_bus():
    bus = MCPEventBus()
    received_payloads = []

    async def sample_handler(payload):
        received_payloads.append(payload)

    bus.subscribe("test_event", sample_handler)
    event = await bus.publish("test_event", {"lead_id": 42, "status": "SCORED"})

    assert event["jsonrpc"] == "2.0"
    assert event["method"] == "mcp/test_event"
    assert len(received_payloads) == 1
    assert received_payloads[0]["lead_id"] == 42

@pytest.mark.asyncio
async def test_benchmark_engine(db_session, sample_lead):
    engine = BenchmarkEngine(db_session)
    engine.scoring_agent.llm = MockLLMProvider()

    res = await engine.run_comparative_benchmark(sample_lead.id, sales_context="Retail ROI Outreach")

    assert res["success"] is True
    assert "baseline" in res
    assert "multi_agent" in res
    assert "comparative_summary" in res

    # Verify baseline vs multi-agent delta
    baseline = res["baseline"]
    multi_agent = res["multi_agent"]

    assert baseline["financial_ratios_analyzed"] is False
    assert multi_agent["financial_ratios_analyzed"] is True
    assert multi_agent["mcp_event_driven"] is True
    assert multi_agent["critic_validation_enabled"] is True

def test_api_benchmark_and_critic(client, sample_lead):
    # Critic endpoint
    res_critic = client.post(f"/api/strategy/critic/validate/{sample_lead.id}")
    assert res_critic.status_code == 200
    assert res_critic.json()["success"] is True

    # Benchmark endpoint
    res_bench = client.post(f"/api/strategy/benchmark/{sample_lead.id}", json={"sales_context": "Financial ROI"})
    assert res_bench.status_code == 200
    bench_data = res_bench.json()
    assert bench_data["success"] is True
    assert "comparative_summary" in bench_data

    # MCP events endpoint
    res_mcp = client.get("/api/strategy/mcp/events")
    assert res_mcp.status_code == 200
    assert res_mcp.json()["success"] is True
