from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.schemas.lead import LeadGenerateRequest, LeadGenerateResponse, LeadResponse
from app.services.lead_service import LeadService
from app.agents.lead_generation_agent import LeadGenerationAgent
import logging

router = APIRouter(prefix="/api/leads", tags=["leads"])
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=LeadGenerateResponse)
async def generate_leads(request: LeadGenerateRequest, db: Session = Depends(get_db)):
    try:
        lead_service = LeadService(db)
        agent = LeadGenerationAgent(lead_service)
        
        total_found, new_leads, duplicates, leads = await agent.execute(
            industry=request.industry,
            location=request.location,
            max_results=request.max_results,
            provider_name=request.provider
        )
        # Calculate how many leads were discarded due to validation failures
        validation_warnings = total_found - (new_leads + duplicates)

        
        return LeadGenerateResponse(
            success=True,
            total_found=total_found,
            new_leads=new_leads,
            duplicates=duplicates,
            leads=leads,
            validation_warnings=validation_warnings,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        import traceback
        with open("error_log.txt", "w") as f:
            f.write(traceback.format_exc())
        logger.error(f"Error generating leads: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.get("", response_model=List[LeadResponse])
def get_leads(
    industry: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    try:
        service = LeadService(db)
        leads = service.get_leads(skip=skip, limit=limit, industry=industry, location=location, status=status)
        logger.info(f"get_leads: fetched {len(leads)} leads from DB")
        # Manually validate each lead so serialization errors are logged rather than crashing
        result = []
        for lead in leads:
            try:
                result.append(LeadResponse.model_validate(lead))
            except Exception as e:
                logger.error(f"Serialization error for lead id={lead.id} ({lead.company_name}): {e}")
        return result
    except Exception as e:
        import traceback
        logger.error(f"get_leads error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch leads: {str(e)}")


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    service = LeadService(db)
    success = service.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"detail": "Lead deleted successfully"}
