from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import models
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    email_address: Optional[str] = None
    email_password: Optional[str] = None
    phone_number: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    bland_api_key: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

@router.get("", response_model=SettingsUpdate)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(models.SalespersonSettings).first()
    if not settings:
        return SettingsUpdate()
    return settings

@router.post("", response_model=SettingsUpdate)
def update_settings(update_data: SettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(models.SalespersonSettings).first()
    if not settings:
        settings = models.SalespersonSettings()
        db.add(settings)
        
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
        
    db.commit()
    db.refresh(settings)
    return settings
