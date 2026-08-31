from typing import Dict, Any, List

class EvidenceExtractor:
    def extract(self, verified_candidate: Dict[str, Any], lead_id: int) -> List[Dict[str, Any]]:
        """
        Extracts structured Evidence records from a verified candidate source.
        """
        evidence_records = []
        
        classification = verified_candidate.get("classification")
        url = verified_candidate.get("url")
        confidence = verified_candidate.get("confidence", 0.0)
        reasons = verified_candidate.get("confidence_reasons", [])
        
        if not url or confidence < 0.30:
            return evidence_records
            
        if classification == "OFFICIAL_WEBSITE":
            evidence_records.append({
                "lead_id": lead_id,
                "field_name": "official_website",
                "field_value": url,
                "source_url": url,
                "source_type": "web_search",
                "confidence": confidence,
                "confidence_reasons": reasons
            })
            
        elif classification == "SOCIAL_PROFILE":
            platform = "unknown"
            if "instagram.com" in url: platform = "instagram"
            elif "facebook.com" in url: platform = "facebook"
            elif "linkedin.com" in url: platform = "linkedin"
            elif "youtube.com" in url: platform = "youtube"
            
            if platform != "unknown":
                evidence_records.append({
                    "lead_id": lead_id,
                    "field_name": f"{platform}_url",
                    "field_value": url,
                    "source_url": url,
                    "source_type": "web_search",
                    "confidence": confidence,
                    "confidence_reasons": reasons
                })
                
        elif classification == "WHATSAPP_LINK":
            evidence_records.append({
                "lead_id": lead_id,
                "field_name": "whatsapp_url",
                "field_value": url,
                "source_url": url,
                "source_type": "web_search",
                "confidence": confidence,
                "confidence_reasons": reasons
            })
            
        # We don't necessarily extract "BUSINESS_DIRECTORY" as a primary field unless requested,
        # but the architecture is here.
            
        return evidence_records
