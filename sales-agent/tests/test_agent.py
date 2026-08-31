import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.services.lead_service import LeadService
from app.agents.lead_generation_agent import LeadGenerationAgent
from app.schemas.lead import LeadCreate

from sqlalchemy.pool import StaticPool

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

@pytest.mark.asyncio
async def test_agent_execution_with_mock_provider(db_session):
    lead_service = LeadService(db_session)
    agent = LeadGenerationAgent(lead_service)
    
    total, new_leads, duplicates, stored = await agent.execute(
        industry="Dental Clinics",
        location="Mumbai",
        max_results=5,
        provider_name="mock"
    )
    
    assert total == 5
    assert new_leads == 5
    assert duplicates == 0
    assert len(stored) == 5
    
    # Run again to test duplicates
    total2, new_leads2, duplicates2, stored2 = await agent.execute(
        industry="Dental Clinics",
        location="Mumbai",
        max_results=5,
        provider_name="mock"
    )
    
    assert total2 == 5
    assert new_leads2 == 0
    assert duplicates2 == 5
    assert len(stored2) == 0

def test_duplicate_detection(db_session):
    lead_service = LeadService(db_session)
    
    # Create first lead
    lead1 = LeadCreate(
        company_name="Test Company",
        industry="Test Industry",
        location="Test Location",
        website="http://test.com"
    )
    
    res1 = lead_service.create_lead(lead1)
    assert res1 is not None
    
    # Try creating same lead
    res2 = lead_service.create_lead(lead1)
    assert res2 is None
