from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database import models
from app.agents.outreach_agent import OutreachAgent

router = APIRouter(prefix="/api/outreach", tags=["outreach"])

@router.post("/execute/{lead_id}/{channel}")
async def execute_outreach(lead_id: int, channel: str, db: Session = Depends(get_db)):
    """
    Executes the outreach action for a lead using their generated strategy.
    Channels: email, whatsapp, call, instagram, telegram
    """
    agent = OutreachAgent(db)
    try:
        result = await agent.execute_channel(lead_id, channel)
        return {"success": True, "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
