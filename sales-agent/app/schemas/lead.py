from pydantic import BaseModel, HttpUrl, Field, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime

class EvidenceBase(BaseModel):
    field_name: str
    field_value: str
    source_url: Optional[str] = None
    source_type: str
    confidence: float
    confidence_reasons: Optional[List[str]] = None

class EvidenceResponse(EvidenceBase):
    id: int
    discovered_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class LeadBase(BaseModel):
    company_name: str
    industry: str
    location: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[HttpUrl] = None
    google_rating: Optional[float] = Field(None, ge=0, le=5)
    social_links: Optional[str] = None
    description: Optional[str] = None
    status: str = "NEW"
    
    # Enrichment fields
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    business_description: Optional[str] = None
    services: Optional[List[str]] = None
    opening_hours: Optional[Dict[str, Any]] = None
    
    official_website: Optional[str] = None
    business_email: Optional[EmailStr] = None
    
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    youtube_url: Optional[str] = None
    
    owner_name: Optional[str] = None
    founder_name: Optional[str] = None
    
    enrichment_status: str = "NOT_STARTED"

class LeadCreate(LeadBase):
    pass

class CompanyProfileBase(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    services: Optional[List[str]] = None
    products: Optional[List[str]] = None
    business_categories: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp_url: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    official_website: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    youtube_url: Optional[str] = None
    owner_name: Optional[str] = None
    founder_name: Optional[str] = None
    team_members: Optional[List[str]] = None
    additional_locations: Optional[List[str]] = None
    profile_completeness: int = 0
    profile_status: str = "NOT_STARTED"

class CompanyProfileResponse(CompanyProfileBase):
    id: int
    lead_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

from app.schemas.integration2 import BuyerIntelligenceResponse, StrategicFitResponse, ApprovalQueueResponse

class LeadResponse(LeadBase):
    id: int
    enriched_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    evidence: List[EvidenceResponse] = []
    profile: Optional[CompanyProfileResponse] = None
    
    buyers: List[BuyerIntelligenceResponse] = []
    strategic_fit: Optional[StrategicFitResponse] = None
    approvals: List[ApprovalQueueResponse] = []

    model_config = {"from_attributes": True}

class LeadGenerateRequest(BaseModel):
    industry: str
    location: str
    max_results: int = 10
    provider: str = "mock"

class LeadGenerateResponse(BaseModel):
    success: bool
    total_found: int
    new_leads: int
    duplicates: int
    leads: List[LeadResponse]

class LeadDiscoverBatchRequest(BaseModel):
    lead_ids: List[int]

class LeadDiscoverResponse(BaseModel):
    success: bool
    lead_id: int
    candidates_found: int
    verified_sources: int
    evidence_found: int
    sources: List[EvidenceResponse]

class LeadDiscoverBatchResponse(BaseModel):
    success: bool
    total_processed: int
    completed: int
    partial: int
    failed: int

class LeadResearchBatchRequest(BaseModel):
    lead_ids: List[int]

class LeadResearchResponse(BaseModel):
    success: bool
    lead_id: int
    profile_status: str
    profile_completeness: int
    company_profile: Optional[CompanyProfileResponse] = None

class LeadResearchBatchResponse(BaseModel):
    success: bool
    total: int
    completed: int
    partial: int
    failed: int
