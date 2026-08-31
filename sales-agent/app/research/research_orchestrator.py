from sqlalchemy.orm import Session
from app.services.lead_service import LeadService
from app.research.website_researcher import WebsiteResearcher
from app.research.social_researcher import SocialResearcher
from app.database import models
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class ResearchOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.lead_service = LeadService(db)
        self.website_researcher = WebsiteResearcher()
        self.social_researcher = SocialResearcher()
        
    def _get_best_evidence(self, all_evidence, field_name: str):
        # Priority: official_website (1) > social_profile (2) > google_maps (3) > web_search (4)
        priority_map = {
            "official_website": 1,
            "social_profile": 2,
            "google_maps": 3,
            "web_search": 4
        }
        
        matches = [e for e in all_evidence if e.field_name == field_name]
        if not matches:
            return None
            
        # Sort by priority (lowest number is best), then by confidence
        matches.sort(key=lambda x: (priority_map.get(x.source_type, 99), -x.confidence))
        return matches[0].field_value

    def _get_all_evidence_values(self, all_evidence, field_name: str):
        # For array fields like services
        matches = [e for e in all_evidence if e.field_name == field_name]
        return list(set(m.field_value for m in matches))

    def _calculate_completeness(self, profile: models.CompanyProfile) -> int:
        fields = [
            profile.description,
            profile.services or profile.products,
            profile.email,
            profile.phone,
            profile.official_website,
            profile.instagram_url or profile.facebook_url or profile.linkedin_url,
            profile.address,
            profile.opening_hours
        ]
        
        available = sum(1 for f in fields if f)
        total = len(fields)
        return int((available / total) * 100)

    async def research_lead(self, lead_id: int, force_refresh: bool = False) -> dict:
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
            
        # 1. Caching check
        if lead.profile and not force_refresh:
            if lead.profile.updated_at and lead.profile.updated_at > datetime.now(timezone.utc) - timedelta(hours=24):
                return {
                    "success": True,
                    "lead_id": lead.id,
                    "profile_status": lead.profile.profile_status,
                    "profile_completeness": lead.profile.profile_completeness,
                    "company_profile": lead.profile
                }
                
        new_evidence_list = []
        status = "NOT_STARTED"
        
        try:
            # Add base map info as evidence if it hasn't been added yet (simulating existing map evidence)
            existing_fields = [e.field_name for e in lead.evidence]
            if "phone" not in existing_fields and lead.phone:
                new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="phone", field_value=lead.phone, source_type="google_maps", confidence=0.9))
            
            if "official_website" not in existing_fields and lead.website:
                new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="official_website", field_value=lead.website, source_type="google_maps", confidence=1.0))
            
            # Find verified official website
            website_evidence = [e for e in lead.evidence if e.field_name == "official_website"]
            # Prioritize google_maps or high confidence if multiple exist
            if website_evidence:
                website_evidence.sort(key=lambda x: -x.confidence)
                
            website_url = website_evidence[0].field_value if website_evidence else None
            
            website_success = False
            
            if website_url:
                logger.info(f"Researching website: {website_url}")
                site_data = await self.website_researcher.research(website_url)
                
                if site_data.get("description"):
                    new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="description", field_value=site_data["description"], source_url=website_url, source_type="official_website", confidence=0.95))
                    website_success = True
                    
                for em in site_data.get("emails", []):
                    new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="email", field_value=em, source_url=website_url, source_type="official_website", confidence=0.95))
                    website_success = True
                    
                for ph in site_data.get("phones", []):
                    new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="phone", field_value=ph, source_url=website_url, source_type="official_website", confidence=0.95))
                    website_success = True
                    
                for srv in site_data.get("services", []):
                    new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="services", field_value=srv, source_url=website_url, source_type="official_website", confidence=0.90))
                    
                for prod in site_data.get("products", []):
                    new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name="products", field_value=prod, source_url=website_url, source_type="official_website", confidence=0.90))
                    
                for soc in site_data.get("social_links", []):
                    plat = "instagram" if "instagram.com" in soc else "facebook" if "facebook.com" in soc else "linkedin" if "linkedin.com" in soc else "youtube" if "youtube.com" in soc else "unknown"
                    if plat != "unknown":
                        new_evidence_list.append(models.Evidence(lead_id=lead.id, field_name=f"{plat}_url", field_value=soc, source_url=website_url, source_type="official_website", confidence=0.98))
                        
            # Save new evidence to DB
            if new_evidence_list:
                for ev in new_evidence_list:
                    self.db.add(ev)
                self.db.commit()
                self.db.refresh(lead)
                
            # Build Profile
            all_evidence = lead.evidence
            
            if not lead.profile:
                lead.profile = models.CompanyProfile(lead_id=lead.id)
                self.db.add(lead.profile)
                
            # Resolve canonicals
            lead.profile.company_name = self._get_best_evidence(all_evidence, "company_name") or lead.company_name
            lead.profile.industry = lead.industry
            lead.profile.location = lead.location
            lead.profile.description = self._get_best_evidence(all_evidence, "description")
            lead.profile.email = self._get_best_evidence(all_evidence, "email")
            lead.profile.phone = self._get_best_evidence(all_evidence, "phone")
            lead.profile.whatsapp_url = self._get_best_evidence(all_evidence, "whatsapp_url")
            lead.profile.address = self._get_best_evidence(all_evidence, "address") or lead.address
            lead.profile.official_website = self._get_best_evidence(all_evidence, "official_website")
            
            lead.profile.instagram_url = self._get_best_evidence(all_evidence, "instagram_url")
            lead.profile.facebook_url = self._get_best_evidence(all_evidence, "facebook_url")
            lead.profile.linkedin_url = self._get_best_evidence(all_evidence, "linkedin_url")
            lead.profile.youtube_url = self._get_best_evidence(all_evidence, "youtube_url")
            
            # JSON arrays
            services = self._get_all_evidence_values(all_evidence, "services")
            if services: lead.profile.services = services
            
            products = self._get_all_evidence_values(all_evidence, "products")
            if products: lead.profile.products = products
            
            # Status and completeness
            status = "FAILED"
            if website_success or len(new_evidence_list) > 0:
                status = "COMPLETED"
            elif website_url: # We had a website but couldn't scrape anything useful
                status = "PARTIAL"
                
            lead.profile.profile_status = status
            lead.profile.profile_completeness = self._calculate_completeness(lead.profile)
            
            self.db.commit()
            self.db.refresh(lead.profile)
            
            return {
                "success": True,
                "lead_id": lead.id,
                "profile_status": status,
                "profile_completeness": lead.profile.profile_completeness,
                "company_profile": lead.profile
            }
            
        except Exception as e:
            logger.error(f"Error researching lead {lead_id}: {e}")
            if lead.profile:
                lead.profile.profile_status = "FAILED"
                self.db.commit()
            return {"success": False, "error": str(e)}

    async def research_batch(self, lead_ids: list[int]) -> dict:
        results = {"success": True, "total": 0, "completed": 0, "partial": 0, "failed": 0}
        for lid in lead_ids:
            res = await self.research_lead(lid)
            results["total"] += 1
            if res.get("success"):
                status = res["profile_status"]
                if status == "COMPLETED": results["completed"] += 1
                elif status == "PARTIAL": results["partial"] += 1
                else: results["failed"] += 1
            else:
                results["failed"] += 1
                
        return results
