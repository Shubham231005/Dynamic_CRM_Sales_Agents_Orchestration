from typing import List, Dict, Any
from app.providers.base import BaseLeadProvider
import asyncio

class MockLeadProvider(BaseLeadProvider):
    async def search_businesses(self, industry: str, location: str, max_results: int) -> List[Dict[str, Any]]:
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # A static list of realistic dummy data
        dummy_data = [
            {
                "company_name": " Bright Smiles Dental Clinic ",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "123 Marine Drive, Mumbai",
                "phone": "+91 98765 43210",
                "email": " CONTACT@BRIGHTSMILES.COM ",
                "website": "www.brightsmiles.com",
                "google_rating": 4.8,
                "social_links": "linkedin.com/company/bright-smiles",
                "description": "Leading dental clinic in South Mumbai."
            },
            {
                "company_name": "Apex Dental Care",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "45 Andheri West, Mumbai",
                "phone": "022-12345678",
                "email": "info@apexdental.in",
                "website": "https://apexdental.in",
                "google_rating": 4.2,
                "social_links": None,
                "description": "Specialists in root canals."
            },
            {
                "company_name": "Mumbai Smiles",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": " Bandra East, Near Station ",
                "phone": "",
                "email": "",
                "website": "",
                "google_rating": 3.9,
                "social_links": "",
                "description": "Affordable dental care."
            },
            {
                "company_name": "Perfect Teeth Hub",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Powai Plaza, Powai",
                "phone": "+919999988888",
                "email": "hello@perfectteeth.co.in",
                "website": "perfectteeth.co.in",
                "google_rating": 4.9,
                "social_links": "twitter.com/perfectteeth",
                "description": ""
            },
            {
                "company_name": "Dr. Sharma's Orthodontics",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Dadar West, Mumbai",
                "phone": "9876512345",
                "email": "sharma.ortho@gmail.com",
                "website": "http://sharmaortho.com",
                "google_rating": 4.5,
                "social_links": "facebook.com/sharmaortho",
                "description": "Expert in braces and aligners."
            },
            {
                "company_name": "Urban Dental Centre",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Malad West, Link Road",
                "phone": "022-87654321",
                "email": "urban.dental@outlook.com",
                "website": "https://www.urbandental.com",
                "google_rating": 4.1,
                "social_links": "instagram.com/urbandental",
                "description": "Modern dentistry for urban professionals."
            },
            {
                "company_name": "Family Dental Clinic",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Borivali East, Mumbai",
                "phone": "+91 88888 77777",
                "email": "care@familydental.org",
                "website": "familydental.org",
                "google_rating": 4.6,
                "social_links": "",
                "description": "Comprehensive care for the whole family."
            },
            {
                "company_name": "White Pearl Dentistry",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Colaba Causeway, Mumbai",
                "phone": "+91 77777 66666",
                "email": "info@whitepearl.co.in",
                "website": "https://whitepearl.co.in",
                "google_rating": 4.7,
                "social_links": "linkedin.com/company/white-pearl",
                "description": "Cosmetic dentistry experts."
            },
            {
                "company_name": "The Tooth Fairy Clinic",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Juhu, Mumbai",
                "phone": "022-23456789",
                "email": "toothfairy.juhu@yahoo.com",
                "website": "http://thetoothfairy.in",
                "google_rating": 4.3,
                "social_links": "facebook.com/toothfairyjuhu",
                "description": "Pediatric dentistry specialists."
            },
            {
                "company_name": "Gentle Care Dental",
                "industry": "Dental Clinics",
                "location": "Mumbai",
                "address": "Goregaon East, Mumbai",
                "phone": "+91 9988776655",
                "email": "appointments@gentlecare.com",
                "website": "www.gentlecare.com",
                "google_rating": 4.4,
                "social_links": "",
                "description": "Pain-free treatments guaranteed."
            }
        ]
        
        # Modify industry and location to loosely match the request if needed, 
        # but for this mock we just return the dummy data up to max_results.
        results = []
        for item in dummy_data:
            item_copy = item.copy()
            # If user asks for something else, we still return these but modify the fields to match
            # so the mock is responsive to input.
            item_copy["industry"] = industry
            item_copy["location"] = location
            results.append(item_copy)
            if len(results) >= max_results:
                break
                
        return results
