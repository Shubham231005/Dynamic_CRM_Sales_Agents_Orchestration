import httpx
from bs4 import BeautifulSoup
import re
import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database import models

logger = logging.getLogger(__name__)

class EnrichmentService:
    def __init__(self, db: Session):
        self.db = db

    async def enrich_lead_website(self, lead_id: int):
        """
        Visits the lead's website to scrape emails, Instagram, Facebook, and LinkedIn links.
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead or not lead.website:
            return

        website = lead.website if lead.website.startswith("http") else f"https://{lead.website}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # Basic headers to bypass simple anti-bot mechanisms
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
                response = await client.get(website, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {website}: Status {response.status_code}")
                    return
                    
                html = response.text
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract Email via Regex
                emails = set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html))
                # Filter out image/png extensions that look like emails
                valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'))]
                
                if valid_emails and not lead.email:
                    lead.email = valid_emails[0]
                    lead.business_email = valid_emails[0]
                
                # Extract Social Links
                links = soup.find_all('a', href=True)
                for a in links:
                    href = a['href'].lower()
                    if 'instagram.com/' in href and not lead.instagram_url:
                        # Ensure it's not a generic share link
                        if 'share' not in href:
                            lead.instagram_url = href
                    if 'linkedin.com/company/' in href and not lead.linkedin_url:
                        lead.linkedin_url = href
                    if 'facebook.com/' in href and not lead.facebook_url:
                        if 'share' not in href:
                            lead.facebook_url = href

                lead.enrichment_status = "COMPLETED"
                self.db.commit()
                logger.info(f"Enriched Lead {lead.company_name}: Email={lead.email}, Insta={lead.instagram_url}")
                
        except Exception as e:
            logger.error(f"Error enriching website {website}: {e}")
            lead.enrichment_status = "FAILED"
            self.db.commit()

    async def batch_enrich(self, lead_ids: List[int]):
        """
        Concurrently enrich a batch of leads.
        """
        tasks = [self.enrich_lead_website(lid) for lid in lead_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
