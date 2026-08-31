from sqlalchemy import Column, Integer, String, Float, DateTime, Text, func, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    industry = Column(String, index=True, nullable=False)
    location = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)
    phone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    website = Column(String, index=True, nullable=True)
    google_rating = Column(Float, nullable=True)
    social_links = Column(Text, nullable=True) # Legacy text field
    description = Column(Text, nullable=True)
    status = Column(String, default="NEW", index=True)
    
    # Enrichment Fields
    google_place_id = Column(String, nullable=True)
    google_maps_url = Column(String, nullable=True)
    business_description = Column(Text, nullable=True)
    services = Column(JSON, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    
    official_website = Column(String, nullable=True)
    business_email = Column(String, nullable=True)
    
    instagram_url = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    
    owner_name = Column(String, nullable=True)
    founder_name = Column(String, nullable=True)
    
    enrichment_status = Column(String, default="NOT_STARTED", index=True)
    enriched_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to sources and profile
    evidence = relationship("Evidence", back_populates="lead", cascade="all, delete-orphan")
    profile = relationship("CompanyProfile", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    buyers = relationship("BuyerIntelligence", back_populates="lead", cascade="all, delete-orphan")
    strategic_fit = relationship("StrategicFit", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    approvals = relationship("ApprovalQueue", back_populates="lead", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    field_name = Column(String, nullable=False, index=True)
    field_value = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    source_type = Column(String, nullable=False) # e.g. official_website, web_search, business_directory
    confidence = Column(Float, nullable=False)
    confidence_reasons = Column(JSON, nullable=True) # list of reasons
    
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    lead = relationship("Lead", back_populates="evidence")

class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)
    
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    services = Column(JSON, nullable=True)
    products = Column(JSON, nullable=True)
    business_categories = Column(JSON, nullable=True)
    
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    whatsapp_url = Column(String, nullable=True)
    address = Column(String, nullable=True)
    opening_hours = Column(JSON, nullable=True)
    
    official_website = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    
    owner_name = Column(String, nullable=True)
    founder_name = Column(String, nullable=True)
    team_members = Column(JSON, nullable=True)
    additional_locations = Column(JSON, nullable=True)
    
    profile_completeness = Column(Integer, default=0)
    profile_status = Column(String, default="NOT_STARTED", index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="profile")

class IndustryPlaybook(Base):
    __tablename__ = "industry_playbooks"

    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, index=True, nullable=False)
    sub_sector = Column(String, index=True, nullable=True)
    industry = Column(String, index=True, nullable=False)
    sub_industry = Column(String, nullable=True)
    business_model = Column(String, nullable=True)
    
    sales_cycle_length = Column(String, nullable=True) # e.g. "SHORT", "MEDIUM", "LONG"
    complexity = Column(String, nullable=True) # e.g. "LOW", "HIGH"
    
    typical_buyer_roles = Column(JSON, nullable=True)
    qualification_criteria = Column(JSON, nullable=True)
    preferred_channels = Column(JSON, nullable=True)
    compliance_requirements = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CompanyCapabilityProfile(Base):
    __tablename__ = "company_capabilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    offerings = Column(JSON, nullable=True)
    target_industries = Column(JSON, nullable=True)
    value_propositions = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BuyerIntelligence(Base):
    __tablename__ = "buyer_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    
    role_name = Column(String, nullable=False)
    seniority = Column(String, nullable=True)
    inferred_needs = Column(JSON, nullable=True)
    
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    lead = relationship("Lead", back_populates="buyers")

class StrategicFit(Base):
    __tablename__ = "strategic_fits"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)
    
    fit_score = Column(Float, nullable=False, default=0.0)
    reasoning = Column(Text, nullable=True)
    recommended_play = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="strategic_fit")

class ApprovalQueue(Base):
    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    
    action_type = Column(String, nullable=False) # e.g., 'SEND_EMAIL'
    proposed_content = Column(Text, nullable=True)
    status = Column(String, default="PENDING", index=True) # PENDING, APPROVED, REJECTED, TIMEOUT
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="approvals")

class SalespersonSettings(Base):
    __tablename__ = "salesperson_settings"

    id = Column(Integer, primary_key=True, index=True)
    # Email settings (SMTP)
    email_address = Column(String, nullable=True)
    email_password = Column(String, nullable=True) # App Password
    
    # Phone / Calling / WhatsApp settings
    phone_number = Column(String, nullable=True)
    twilio_account_sid = Column(String, nullable=True)
    twilio_auth_token = Column(String, nullable=True)
    bland_api_key = Column(String, nullable=True)
    
    # Instagram Settings
    instagram_username = Column(String, nullable=True)
    instagram_password = Column(String, nullable=True)
    
    # Telegram Settings
    telegram_bot_token = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
