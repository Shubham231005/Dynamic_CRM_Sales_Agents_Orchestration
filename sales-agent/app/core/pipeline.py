"""
Sales Pipeline Orchestrator
=============================
The central scheduler that moves leads through the state machine by
dispatching to the correct agent at each stage.

Responsibilities:
  - Maintain the ordered agent registry.
  - Build an ``AgentContext`` from the DB for each lead.
  - Call agents via ``BaseAgent.run()`` and apply the returned result
    transactionally (state change + updates + artifacts).
  - Respect human-approval gates.
  - Log a full audit trail.

Usage::

    pipeline = SalesPipeline(db)
    result   = await pipeline.advance(lead_id)
    # Or run a lead through every stage it qualifies for:
    result   = await pipeline.run_full(lead_id)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.base_agent import AgentContext, AgentResult, AgentStatus, BaseAgent
from app.core.state_machine import LeadState, LeadStateMachine
from app.database import models

logger = logging.getLogger(__name__)


class SalesPipeline:
    """
    Orchestrates lead progression through the multi-agent pipeline.
    """

    def __init__(self, db: Session, agents: Optional[List[BaseAgent]] = None):
        self.db = db
        self._agents: List[BaseAgent] = agents or []
        self._sm = LeadStateMachine()

    # ── Agent registry ─────────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> "SalesPipeline":
        """Add an agent to the pipeline (builder pattern)."""
        self._agents.append(agent)
        return self

    # ── Pipeline execution ─────────────────────────────────────────────────

    async def advance(
        self,
        lead_id: int,
        sales_context: Optional[str] = None,
    ) -> AgentResult:
        """
        Advance a single lead by exactly one step.

        Finds the first registered agent whose ``can_handle`` returns True
        for the lead's current state, runs it, and applies the result.
        """
        lead = self.db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        if not lead:
            return AgentResult(status=AgentStatus.FAILED, error="Lead not found")

        ctx = self._build_context(lead, sales_context)

        # Find matching agent
        for agent in self._agents:
            if await agent.can_handle(ctx):
                result = await agent.run(ctx)
                self._apply_result(lead, result)
                return result

        return AgentResult(
            status=AgentStatus.SKIPPED,
            message=f"No agent handles state '{ctx.lead_state.value}' for lead {lead_id}.",
        )

    async def run_full(
        self,
        lead_id: int,
        sales_context: Optional[str] = None,
        max_steps: int = 10,
    ) -> List[AgentResult]:
        """
        Keep advancing the lead until no agent can handle it, a human gate
        is hit, a terminal state is reached, or ``max_steps`` is exhausted.
        """
        results: List[AgentResult] = []

        for _ in range(max_steps):
            result = await self.advance(lead_id, sales_context)
            results.append(result)

            # Stop conditions
            if result.status in (AgentStatus.FAILED, AgentStatus.SKIPPED):
                break
            if result.status == AgentStatus.REQUIRES_APPROVAL:
                break
            if result.next_state and result.next_state in self._sm.terminal_states():
                break

        return results

    # ── Context builder ────────────────────────────────────────────────────

    def _build_context(self, lead: models.Lead, sales_context: Optional[str] = None) -> AgentContext:
        """
        Snapshot the lead into an AgentContext.
        """
        # Map DB status string to LeadState enum (default to NEW)
        try:
            current_state = LeadState(lead.status)
        except ValueError:
            current_state = LeadState.NEW

        lead_data = {
            "id": lead.id,
            "company_name": lead.company_name,
            "industry": lead.industry,
            "location": lead.location,
            "address": lead.address,
            "phone": lead.phone,
            "email": lead.email,
            "website": str(lead.website) if lead.website else None,
            "google_rating": lead.google_rating,
            "description": lead.description,
            "enrichment_status": lead.enrichment_status,
        }

        profile_data = None
        if lead.profile:
            profile_data = {
                "profile_completeness": lead.profile.profile_completeness,
                "profile_status": lead.profile.profile_status,
                "services": lead.profile.services,
                "products": lead.profile.products,
                "official_website": lead.profile.official_website,
            }

        evidence = [
            {
                "field_name": e.field_name,
                "field_value": e.field_value,
                "source_type": e.source_type,
                "confidence": e.confidence,
            }
            for e in (lead.evidence or [])
        ]

        return AgentContext(
            lead_id=lead.id,
            lead_state=current_state,
            lead_data=lead_data,
            profile_data=profile_data,
            evidence=evidence,
            sales_context=sales_context,
            db_session=self.db,
        )

    # ── Result application ─────────────────────────────────────────────────

    def _apply_result(self, lead: models.Lead, result: AgentResult) -> None:
        """
        Transactionally apply an AgentResult to the database.
        """
        # 1. Apply field-level updates
        for key, value in result.updates.items():
            if hasattr(lead, key) and value is not None:
                setattr(lead, key, value)

        # 2. State transition (if provided and legal)
        if result.next_state is not None:
            try:
                current = LeadState(lead.status)
            except ValueError:
                current = LeadState.NEW

            try:
                new_state = self._sm.transition(current, result.next_state)
                lead.status = new_state.value
            except ValueError as e:
                logger.warning(f"State transition blocked: {e}")

        # 3. Persist evidence artifacts
        new_evidence = result.artifacts.get("evidence", [])
        for ev in new_evidence:
            self.db.add(models.Evidence(
                lead_id=lead.id,
                field_name=ev.get("field_name"),
                field_value=ev.get("field_value"),
                source_url=ev.get("source_url"),
                source_type=ev.get("source_type"),
                confidence=ev.get("confidence", 0.0),
                confidence_reasons=ev.get("confidence_reasons"),
            ))

        # 4. Persist approval-queue items
        approvals = result.artifacts.get("approvals", [])
        for appr in approvals:
            self.db.add(models.ApprovalQueue(
                lead_id=lead.id,
                action_type=appr.get("action_type"),
                proposed_content=appr.get("proposed_content"),
            ))

        self.db.commit()
        self.db.refresh(lead)
