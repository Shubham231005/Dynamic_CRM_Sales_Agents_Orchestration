import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.database import models
from app.main import app

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

def test_generate_leads(client):
    response = client.post(
        "/api/leads/generate",
        json={
            "industry": "Dental Clinics",
            "location": "Mumbai",
            "max_results": 3,
            "provider": "mock"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_found"] == 3
    assert data["new_leads"] == 3
    assert len(data["leads"]) == 3

def test_generate_leads_invalid_provider(client):
    response = client.post(
        "/api/leads/generate",
        json={
            "industry": "Dental Clinics",
            "location": "Mumbai",
            "max_results": 3,
            "provider": "unknown"
        }
    )
    assert response.status_code == 400

def test_generate_leads_google_maps_mocked(client, monkeypatch):
    async def mock_search(*args, **kwargs):
        return [{"company_name": "Mocked Google Maps Lead"}]
    
    from app.providers.google_maps_provider import GoogleMapsProvider
    monkeypatch.setattr(GoogleMapsProvider, "search_businesses", mock_search)
    
    response = client.post(
        "/api/leads/generate",
        json={
            "industry": "Dental Clinics",
            "location": "Mumbai",
            "max_results": 1,
            "provider": "google_maps"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 1

def test_get_and_delete_lead(client):
    # Generate lead first
    gen_res = client.post(
        "/api/leads/generate",
        json={"industry": "Dental Clinics", "location": "Mumbai", "max_results": 1, "provider": "mock"}
    )
    assert gen_res.status_code == 200
    leads = gen_res.json()["leads"]
    assert len(leads) > 0
    lead_id = leads[0]["id"]

    # Get leads
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert type(response.json()) == list

    # Get by id
    response_id = client.get(f"/api/leads/{lead_id}")
    assert response_id.status_code == 200
    assert response_id.json()["id"] == lead_id

    # Delete lead
    res_del = client.delete(f"/api/leads/{lead_id}")
    assert res_del.status_code == 200

    # Verify deleted
    res_404 = client.get(f"/api/leads/{lead_id}")
    assert res_404.status_code == 404
