from sqlalchemy.orm import Session
from app.database import models
from app.schemas.lead import LeadCreate
from typing import List, Tuple
from app.utils.cleaner import normalize_company_name, normalize_website, normalize_phone

class LeadService:
    def __init__(self, db: Session):
        self.db = db

    def is_duplicate(self, lead_data: LeadCreate) -> bool:
        """
        Checks if a lead already exists in the database based on:
        - normalized company name
        - website (if available)
        - phone (if available)
        """
        query = self.db.query(models.Lead)
        
        # Check by company name
        if query.filter(models.Lead.company_name == lead_data.company_name).first():
            return True
            
        # Check by website
        if lead_data.website:
            if query.filter(models.Lead.website == str(lead_data.website)).first():
                return True
                
        # Check by phone
        if lead_data.phone:
            if query.filter(models.Lead.phone == lead_data.phone).first():
                return True
                
        return False

    def create_lead(self, lead_data: LeadCreate) -> models.Lead | None:
        """
        Creates a new lead if it's not a duplicate.
        """
        if self.is_duplicate(lead_data):
            return None
            
        db_lead = models.Lead(
            company_name=lead_data.company_name,
            industry=lead_data.industry,
            location=lead_data.location,
            address=lead_data.address,
            phone=lead_data.phone,
            email=lead_data.email,
            website=str(lead_data.website) if lead_data.website else None,
            google_rating=lead_data.google_rating,
            social_links=lead_data.social_links,
            description=lead_data.description,
            status=lead_data.status
        )
        self.db.add(db_lead)
        self.db.commit()
        self.db.refresh(db_lead)
        return db_lead

    def get_leads(self, skip: int = 0, limit: int = 100, industry: str = None, location: str = None, status: str = None) -> List[models.Lead]:
        query = self.db.query(models.Lead)
        if industry:
            query = query.filter(models.Lead.industry == industry)
        if location:
            query = query.filter(models.Lead.location == location)
        if status:
            query = query.filter(models.Lead.status == status)
            
        return query.order_by(models.Lead.id.desc()).offset(skip).limit(limit).all()

    def get_lead(self, lead_id: int) -> models.Lead | None:
        return self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        
    def delete_lead(self, lead_id: int) -> bool:
        db_lead = self.get_lead(lead_id)
        if db_lead:
            self.db.delete(db_lead)
            self.db.commit()
            return True
        return False

    def update_lead(self, lead_id: int, update_data: dict, new_evidence: List[dict] = None) -> models.Lead | None:
        db_lead = self.get_lead(lead_id)
        if not db_lead:
            return None
            
        for key, value in update_data.items():
            if hasattr(db_lead, key) and value is not None:
                setattr(db_lead, key, value)
                
        if new_evidence:
            for ev in new_evidence:
                db_evidence = models.Evidence(
                    lead_id=db_lead.id,
                    field_name=ev.get("field_name"),
                    field_value=ev.get("field_value"),
                    source_url=ev.get("source_url"),
                    source_type=ev.get("source_type"),
                    confidence=ev.get("confidence"),
                    confidence_reasons=ev.get("confidence_reasons")
                )
                self.db.add(db_evidence)
                
        self.db.commit()
        self.db.refresh(db_lead)
        return db_lead
        
    def get_leads_for_discovery(self, limit: int = 50) -> List[models.Lead]:
        """Returns leads that have not been enriched yet, or failed."""
        return self.db.query(models.Lead).filter(
            models.Lead.status == "NEW",
            models.Lead.enrichment_status.in_(["NOT_STARTED", "FAILED"])
        ).limit(limit).all()

    def update_lead_status(self, lead_id: int, new_status: str) -> models.Lead | None:
        """Updates lead state cleanly with transaction commit."""
        db_lead = self.get_lead(lead_id)
        if not db_lead:
            return None
        db_lead.status = new_status
        self.db.commit()
        self.db.refresh(db_lead)
        return db_lead

    def get_leads_by_status(self, status: str, limit: int = 100) -> List[models.Lead]:
        """Fetches leads matching a specific pipeline status."""
        return self.db.query(models.Lead).filter(models.Lead.status == status).order_by(models.Lead.id.desc()).limit(limit).all()

    def get_pipeline_stage_counts(self) -> dict:
        """Aggregates total count of leads at each stage of the sales pipeline."""
        from sqlalchemy import func
        results = self.db.query(models.Lead.status, func.count(models.Lead.id)).group_by(models.Lead.status).all()
        counts = {
            "NEW": 0,
            "RESEARCHING": 0,
            "RESEARCHED": 0,
            "SCORED": 0,
            "APPROVAL_PENDING": 0,
            "OUTREACH_QUEUED": 0,
            "OUTREACH_COMPLETED": 0,
            "OUTREACH_FAILED": 0
        }
        for status, count in results:
            if status:
                counts[status] = count
        counts["TOTAL"] = sum(counts.values())
        return counts

