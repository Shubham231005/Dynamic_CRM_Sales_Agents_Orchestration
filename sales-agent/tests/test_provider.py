import pytest
from app.providers.mock_provider import MockLeadProvider
from app.providers.google_maps_provider import GoogleMapsProvider

@pytest.mark.asyncio
async def test_mock_provider():
    provider = MockLeadProvider()
    results = await provider.search_businesses("Dental Clinics", "Mumbai", max_results=3)
    
    assert len(results) == 3
    assert results[0]["industry"] == "Dental Clinics"
    assert results[0]["location"] == "Mumbai"
    assert "company_name" in results[0]

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Playwright browsers and network connection")
async def test_google_maps_provider():
    provider = GoogleMapsProvider()
    results = await provider.search_businesses("Dental Clinics", "Mumbai", max_results=1)
    assert type(results) == list
