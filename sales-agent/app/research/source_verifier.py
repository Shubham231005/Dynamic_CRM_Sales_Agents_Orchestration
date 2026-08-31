import re
from typing import Dict, Any, List
from urllib.parse import urlparse

class SourceVerifier:
    def verify(self, candidate: Dict[str, Any], lead: Any) -> Dict[str, Any]:
        """
        Takes a candidate dict and compares it against the Lead model.
        Returns the updated candidate with confidence, reasons, and classification.
        """
        confidence = 0.0
        reasons = []
        
        url = candidate.get("url", "").lower()
        title = candidate.get("title", "").lower()
        snippet = candidate.get("snippet", "").lower()
        
        combined_text = f"{title} {snippet}"
        
        # 1. Company Name Match
        if lead.company_name:
            lead_name_lower = lead.company_name.lower()
            name_parts = [p for p in lead_name_lower.split() if len(p) > 2]
            
            matched_parts = sum(1 for p in name_parts if p in combined_text)
            
            if matched_parts == len(name_parts) and len(name_parts) > 0:
                confidence += 0.40
                reasons.append("exact_name_match")
            elif matched_parts > 0:
                confidence += 0.25
                reasons.append("partial_name_match")
                
            domain = urlparse(url).netloc.replace("www.", "").lower()
            if len(name_parts) > 0 and name_parts[0] in domain:
                confidence += 0.20
                reasons.append("domain_name_match")
                
        # 2. Location Match (+0.20)
        if lead.location and lead.location.lower() in combined_text:
            confidence += 0.20
            reasons.append("location_match")
            
        # 3. Phone Match (+0.30)
        if lead.phone:
            # strip spaces from phone for matching
            phone_clean = re.sub(r'\D', '', lead.phone)
            if phone_clean and len(phone_clean) >= 8 and phone_clean in re.sub(r'\D', '', combined_text):
                confidence += 0.30
                reasons.append("phone_match")
                
        # 4. Relevance (+0.10)
        if lead.industry and lead.industry.lower() in combined_text:
            confidence += 0.10
            reasons.append("industry_match")
            
        # Cap confidence at 0.98 for purely heuristic searches
        confidence = min(confidence, 0.98)
        
        candidate["confidence"] = round(confidence, 2)
        candidate["confidence_reasons"] = reasons
        
        # Classify
        candidate["classification"] = self._classify(url, confidence)
        
        return candidate
        
    def _classify(self, url: str, confidence: float) -> str:
        url_lower = url.lower()
        
        if "api.whatsapp.com" in url_lower or "wa.me/" in url_lower:
            return "WHATSAPP_LINK"
            
        social_domains = ["instagram.com", "facebook.com", "linkedin.com", "youtube.com", "twitter.com", "x.com"]
        if any(d in url_lower for d in social_domains):
            return "SOCIAL_PROFILE"
            
        directory_domains = ["justdial.com", "sulekha.com", "indiamart.com", "yelp.com", "yellowpages.com"]
        if any(d in url_lower for d in directory_domains):
            return "BUSINESS_DIRECTORY"
            
        # Lowered threshold to 0.25 to catch partial matches with domains
        if confidence >= 0.25:
            return "OFFICIAL_WEBSITE"
            
        return "OTHER"
