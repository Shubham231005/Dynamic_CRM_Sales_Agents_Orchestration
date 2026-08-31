from sqlalchemy.orm import Session
from app.database import models
import logging

logger = logging.getLogger(__name__)

class IndustryAgent:
    def __init__(self, db: Session):
        self.db = db

    def get_playbook(self, sector: str, industry: str, sub_sector: str = None, sub_industry: str = None, business_model: str = None) -> models.IndustryPlaybook:
        """
        Dynamically finds the best matching industry playbook based on the multi-dimensional classification.
        """
        query = self.db.query(models.IndustryPlaybook).filter(
            models.IndustryPlaybook.sector == sector,
            models.IndustryPlaybook.industry == industry
        )
        if sub_sector:
            query = query.filter(models.IndustryPlaybook.sub_sector == sub_sector)
        
        if sub_industry:
            # Try to find exact sub_industry match, otherwise fallback to industry
            sub_query = query.filter(models.IndustryPlaybook.sub_industry == sub_industry)
            if business_model:
                bm_query = sub_query.filter(models.IndustryPlaybook.business_model == business_model)
                if bm_query.first():
                    return bm_query.first()
            if sub_query.first():
                return sub_query.first()

        playbook = query.first()
        if not playbook:
            logger.warning(f"No playbook found for {sector} -> {industry}. Using fallback.")
            # We could return a default generic playbook here
            
        return playbook

    def create_or_update_playbook(self, data: dict) -> models.IndustryPlaybook:
        """
        Seed or update playbooks in the database.
        """
        playbook = self.get_playbook(
            sector=data.get("sector"), 
            sub_sector=data.get("sub_sector"),
            industry=data.get("industry"), 
            sub_industry=data.get("sub_industry"),
            business_model=data.get("business_model")
        )
        
        if playbook:
            for key, value in data.items():
                setattr(playbook, key, value)
        else:
            playbook = models.IndustryPlaybook(**data)
            self.db.add(playbook)
            
        self.db.commit()
        self.db.refresh(playbook)
        return playbook
