from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.database import models
from app.schemas.integration2 import (
    StrategicFitResponse, 
    ApprovalQueueResponse, 
    IndustryPlaybookResponse,
    IndustryPlaybookBase
)
from app.orchestrators.sales_orchestrator import SalesOrchestrator
from app.agents.industry_agent import IndustryAgent
from app.agents.lead_scoring_agent import LeadScoringAgent
from app.agents.critic_validation_agent import CriticValidationAgent
from app.orchestrators.benchmark_engine import BenchmarkEngine
from app.orchestrators.mcp_event_bus import mcp_event_bus
from pydantic import BaseModel
from fastapi import UploadFile, File
import io

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

class StrategizeRequest(BaseModel):
    sales_context: Optional[str] = None

class OrchestrateBatchRequest(BaseModel):
    lead_ids: List[int]
    sales_context: Optional[str] = None

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

@router.post("/playbooks", response_model=IndustryPlaybookResponse)
def create_playbook(request: IndustryPlaybookBase, db: Session = Depends(get_db)):
    agent = IndustryAgent(db)
    playbook = agent.create_or_update_playbook(request.model_dump())
    return playbook

@router.get("/playbooks", response_model=List[IndustryPlaybookResponse])
def get_playbooks(db: Session = Depends(get_db)):
    return db.query(models.IndustryPlaybook).all()

@router.post("/leads/{lead_id}/score")
async def score_lead(lead_id: int, request: StrategizeRequest, db: Session = Depends(get_db)):
    """
    Explicitly runs the Lead Scoring Agent with financial ratio analysis and Critic weighting.
    """
    scoring_agent = LeadScoringAgent(db)
    try:
        score_res = await scoring_agent.score_lead(lead_id, sales_context=request.sales_context)
        return score_res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/critic/validate/{lead_id}")
async def validate_critic_loop(lead_id: int, db: Session = Depends(get_db)):
    """
    Executes the Reflexive Critic Validation Loop to detect and eliminate hallucinations.
    """
    critic = CriticValidationAgent(db)
    try:
        res = await critic.validate_lead_profile(lead_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/benchmark/{lead_id}")
async def run_benchmark(lead_id: int, request: StrategizeRequest, db: Session = Depends(get_db)):
    """
    Runs Empirical Study Benchmark comparing Baseline (Traditional) vs Multi-Agent Architecture.
    """
    engine = BenchmarkEngine(db)
    try:
        res = await engine.run_comparative_benchmark(lead_id, sales_context=request.sales_context)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/mcp/events")
def get_mcp_events():
    """
    Returns live log of Model Context Protocol (MCP) JSON-RPC event dispatches.
    """
    return {
        "success": True,
        "mcp_event_bus": "active",
        "events": mcp_event_bus.get_event_log(limit=50)
    }

@router.post("/leads/{lead_id}/strategize", response_model=StrategicFitResponse)
async def strategize_lead(lead_id: int, request: StrategizeRequest, db: Session = Depends(get_db)):
    """
    Orchestrates full end-to-end sales pipeline for a single lead.
    """
    orchestrator = SalesOrchestrator(db)
    try:
        fit = await orchestrator.orchestrate_lead(lead_id, sales_context=request.sales_context)
        return fit
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/orchestrate-batch")
async def orchestrate_batch(request: OrchestrateBatchRequest, db: Session = Depends(get_db)):
    """
    Orchestrates pipeline for multiple leads in batch.
    """
    orchestrator = SalesOrchestrator(db)
    res = await orchestrator.orchestrate_batch(request.lead_ids, sales_context=request.sales_context)
    return res

@router.get("/pipeline-summary")
def get_pipeline_summary(db: Session = Depends(get_db)):
    """
    Returns pipeline metrics: count of leads at each stage and pending approval counts.
    """
    orchestrator = SalesOrchestrator(db)
    return orchestrator.get_pipeline_summary()

@router.get("/leads/{lead_id}/pipeline-state")
def get_lead_pipeline_state(lead_id: int, db: Session = Depends(get_db)):
    """
    Returns state snapshot for a single lead.
    """
    orchestrator = SalesOrchestrator(db)
    state = orchestrator.get_lead_pipeline_state(lead_id)
    if not state:
        raise HTTPException(status_code=404, detail="Lead not found")
    return state

@router.get("/approvals", response_model=List[ApprovalQueueResponse])
def get_pending_approvals(db: Session = Depends(get_db)):
    return db.query(models.ApprovalQueue).filter(models.ApprovalQueue.status == "PENDING").all()

@router.post("/approvals/{approval_id}/decide", response_model=ApprovalQueueResponse)
def decide_approval(approval_id: int, decision: str, db: Session = Depends(get_db)):
    if decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED")
        
    approval = db.query(models.ApprovalQueue).filter(models.ApprovalQueue.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
        
    approval.status = decision
    db.commit()
    db.refresh(approval)
    return approval

@router.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    if not PyPDF2:
        raise HTTPException(status_code=501, detail="PyPDF2 not installed")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Must be a PDF file")
        
    try:
        content = await file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return {"success": True, "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
