from sqlalchemy.orm import Session
from app.services.lead_service import LeadService
from app.research.providers.base_search import BaseSearchProvider
from app.research.providers.playwright_search import PlaywrightSearchProvider
from app.research.source_verifier import SourceVerifier
from app.research.evidence_extractor import EvidenceExtractor
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class WebDiscoveryAgent:
    def __init__(self, db: Session, search_provider: BaseSearchProvider = None):
        self.db = db
        self.lead_service = LeadService(db)
        self.search_provider = search_provider or PlaywrightSearchProvider()
        self.verifier = SourceVerifier()
        self.extractor = EvidenceExtractor()
        
    def _generate_queries(self, lead) -> list[str]:
        queries = []
        name = lead.company_name
        loc = lead.location
        ind = lead.industry
        phone = lead.phone
        
        if name and loc:
            queries.append(f"{name} {loc}")
        if name and ind and loc:
            queries.append(f"{name} {ind} {loc}")
        if name and phone:
            queries.append(f"{name} {phone}")
            
        return queries[:2] # Limit to max 2 queries to avoid excessive searches
        
    async def discover(self, lead_id: int) -> dict:
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
            
        try:
            self.lead_service.update_lead(lead.id, {"enrichment_status": "IN_PROGRESS"})
            
            queries = self._generate_queries(lead)
            
            all_candidates = []
            for q in queries:
                logger.info(f"[DISCOVERY] Querying: '{q}'")
                candidates = await self.search_provider.search(q, max_results=5)
                all_candidates.extend(candidates)
                
            # Deduplicate candidates by URL
            seen_urls = set()
            unique_candidates = []
            for c in all_candidates:
                url = c.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_candidates.append(c)
                    
            verified_count = 0
            all_evidence = []
            
            # If Google Maps already provided a website, it's an instant 100% confidence official website
            if lead.website:
                all_evidence.append({
                    "lead_id": lead.id,
                    "field_name": "official_website",
                    "field_value": lead.website,
                    "source_url": lead.website,
                    "source_type": "google_maps",
                    "confidence": 1.0,
                    "confidence_reasons": ["provided_by_google_maps"]
                })
                verified_count += 1
            
            for candidate in unique_candidates:
                # 1. Verify
                verified_candidate = self.verifier.verify(candidate, lead)
                
                logger.info(f"[VERIFICATION] URL: {verified_candidate['url']} | Class: {verified_candidate['classification']} | Conf: {verified_candidate['confidence']}")
                
                # 2. Extract Evidence
                extracted_evidence_list = self.extractor.extract(verified_candidate, lead.id)
                
                if extracted_evidence_list:
                    verified_count += 1
                    all_evidence.extend(extracted_evidence_list)
                    
            # 3. Store Evidence
            if all_evidence:
                db_lead = self.lead_service.update_lead(lead.id, {}, new_evidence=all_evidence)
                status = "COMPLETED"
            else:
                status = "PARTIAL" if unique_candidates else "FAILED"
                db_lead = lead
                
            db_lead = self.lead_service.update_lead(lead.id, {"enrichment_status": status, "enriched_at": datetime.now(timezone.utc)})
            
            return {
                "success": True,
                "lead_id": lead.id,
                "candidates_found": len(unique_candidates),
                "verified_sources": verified_count,
                "evidence_found": len(all_evidence),
                "sources": db_lead.evidence if db_lead else []
            }
            
        except Exception as e:
            logger.error(f"Error discovering lead {lead_id}: {e}")
            self.lead_service.update_lead(lead.id, {"enrichment_status": "FAILED"})
            return {"success": False, "error": str(e)}

    async def discover_batch(self, lead_ids: list[int]) -> dict:
        results = {"success": True, "total_processed": 0, "completed": 0, "partial": 0, "failed": 0}
        for lid in lead_ids:
            res = await self.discover(lid)
            results["total_processed"] += 1
            if res.get("success"):
                status = self.lead_service.get_lead(lid).enrichment_status
                if status == "COMPLETED": results["completed"] += 1
                elif status == "PARTIAL": results["partial"] += 1
                else: results["failed"] += 1
            else:
                results["failed"] += 1
                
        return results
