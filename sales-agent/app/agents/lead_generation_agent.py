from typing import List, Dict, Any, Tuple
from app.providers.base import BaseLeadProvider
from app.providers.mock_provider import MockLeadProvider
from app.providers.google_maps_provider import GoogleMapsProvider
from app.utils.cleaner import (
    normalize_company_name,
    normalize_phone,
    normalize_email,
    normalize_website,
    clean_address
)
from app.utils.validators import validate_lead_data
from app.services.lead_service import LeadService
from app.services.enrichment_service import EnrichmentService
from app.schemas.lead import LeadCreate, LeadResponse

class LeadGenerationAgent:
    def __init__(self, lead_service: LeadService):
        self.lead_service = lead_service
        self.providers: Dict[str, BaseLeadProvider] = {
            "mock": MockLeadProvider(),
            "google_maps": GoogleMapsProvider()
        }

    def _get_provider(self, provider_name: str) -> BaseLeadProvider:
        provider = self.providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Provider '{provider_name}' is not supported.")
        return provider

    def _clean_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cleans the raw data received from a provider.
        """
        return {
            "company_name": normalize_company_name(raw_data.get("company_name", "")),
            "industry": raw_data.get("industry", ""),
            "location": raw_data.get("location", ""),
            "address": clean_address(raw_data.get("address", "")),
            "phone": normalize_phone(raw_data.get("phone", "")),
            "email": normalize_email(raw_data.get("email", "")),
            "website": normalize_website(raw_data.get("website", "")),
            "google_rating": raw_data.get("google_rating"),
            "social_links": raw_data.get("social_links"),
            "description": raw_data.get("description", "")
        }

    async def execute(self, industry: str, location: str, max_results: int, provider_name: str) -> Tuple[int, int, int, List[LeadResponse]]:
        """
        Executes the lead generation workflow.
        Returns (total_found, new_leads, duplicates, stored_leads)
        """
        provider = self._get_provider(provider_name)
        
        try:
            raw_leads = await provider.search_businesses(industry, location, max_results)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Provider '{provider_name}' search failed: {e}. Falling back to mock provider.")
            fallback = MockLeadProvider()
            raw_leads = await fallback.search_businesses(industry, location, max_results)
        
        total_found = len(raw_leads)
        new_leads_count = 0
        duplicates_count = 0
        stored_leads = []

        for raw_lead in raw_leads:
            # 1. Clean Data
            cleaned_data = self._clean_data(raw_lead)
            
            # 2. Validate Data
            validated_lead = validate_lead_data(cleaned_data)
            if not validated_lead:
                continue # Skip invalid leads
                
            # 3. Store Data (checking for duplicates)
            db_lead = self.lead_service.create_lead(validated_lead)
            
            if db_lead:
                new_leads_count += 1
                stored_leads.append(db_lead)
            else:
                duplicates_count += 1

        # 4. Deep Web Enrichment (Extract Emails & Socials in background)
        if stored_leads:
            enricher = EnrichmentService(self.lead_service.db)
            lead_ids = [l.id for l in stored_leads]
            await enricher.batch_enrich(lead_ids)

        # 5. Refresh models to get the new email/social data
        final_leads = []
        for l in stored_leads:
            self.lead_service.db.refresh(l)
            final_leads.append(LeadResponse.model_validate(l))

        return total_found, new_leads_count, duplicates_count, final_leads
