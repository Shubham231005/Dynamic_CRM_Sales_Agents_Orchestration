from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

class IndustryPlaybookBase(BaseModel):
    sector: str
    sub_sector: Optional[str] = None
    industry: str
    sub_industry: Optional[str] = None
    business_model: Optional[str] = None
    
    sales_cycle_length: Optional[str] = None
    complexity: Optional[str] = None
    
    typical_buyer_roles: Optional[List[str]] = None
    qualification_criteria: Optional[List[str]] = None
    preferred_channels: Optional[List[str]] = None
    compliance_requirements: Optional[List[str]] = None

class IndustryPlaybookResponse(IndustryPlaybookBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class CompanyCapabilityProfileBase(BaseModel):
    name: str
    offerings: Optional[List[str]] = None
    target_industries: Optional[List[str]] = None
    value_propositions: Optional[List[str]] = None

class CompanyCapabilityProfileResponse(CompanyCapabilityProfileBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class BuyerIntelligenceBase(BaseModel):
    role_name: str
    seniority: Optional[str] = None
    inferred_needs: Optional[List[str]] = None

class BuyerIntelligenceResponse(BuyerIntelligenceBase):
    id: int
    lead_id: int
    discovered_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class StrategicFitBase(BaseModel):
    fit_score: float
    reasoning: Optional[str] = None
    recommended_play: Optional[Dict[str, Any]] = None

class StrategicFitResponse(StrategicFitBase):
    id: int
    lead_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class ApprovalQueueBase(BaseModel):
    action_type: str
    proposed_content: Optional[str] = None
    status: str = "PENDING"

class ApprovalQueueResponse(ApprovalQueueBase):
    id: int
    lead_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}
