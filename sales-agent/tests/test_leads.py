from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base, get_db
from app.main import app

from sqlalchemy.pool import StaticPool
from app.database import models

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_generate_leads():
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

def test_generate_leads_invalid_provider():
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

def test_generate_leads_google_maps_mocked(monkeypatch):
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

def test_get_leads():
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert type(response.json()) == list
    assert len(response.json()) > 0 # From the previous test

def test_get_lead_by_id():
    # Assuming lead with ID 1 was created
    response = client.get("/api/leads/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_delete_lead():
    response = client.delete("/api/leads/1")
    assert response.status_code == 200
    
    # Try fetching again
    response_get = client.get("/api/leads/1")
    assert response_get.status_code == 404
