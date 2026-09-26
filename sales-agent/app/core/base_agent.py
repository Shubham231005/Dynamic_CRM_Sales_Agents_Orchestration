"""
Base Agent Contract
====================
Every agent in the sales pipeline implements this interface.
This guarantees a uniform execution model that the Pipeline Orchestrator
can schedule, retry, and observe without knowing agent internals.

Design principles:
  - Agents are stateless.  All mutable state lives in AgentContext / the DB.
  - Agents declare what lead states they handle (via ``handles_states``).
  - Results carry the next state the lead should transition to, or an error.
  - Human-in-the-loop gates are expressed as a special ``REQUIRES_APPROVAL``
    result status; the pipeline pauses until the gate clears.
"""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.core.state_machine import LeadState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    """Outcome status returned by every agent execution."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"                    # some work done, but not complete
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"  # human gate
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"                    # preconditions not met, no error


@dataclass
class AgentContext:
    """
    Immutable-ish bag of inputs handed to an agent on each run.

    Agents must NOT mutate ``lead`` directly; they return an ``AgentResult``
    and let the pipeline apply the changes transactionally.
    """
    lead_id: int
    lead_state: LeadState
    lead_data: Dict[str, Any]          # snapshot of the Lead row
    profile_data: Optional[Dict[str, Any]] = None   # CompanyProfile snapshot
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    sales_context: Optional[str] = None  # user-supplied text / PDF context
    extra: Dict[str, Any] = field(default_factory=dict)  # per-agent extras

    # Runtime helpers injected by the pipeline
    db_session: Any = None               # SQLAlchemy Session (set at call-time)


@dataclass
class AgentResult:
    """
    Returned by every agent after execution.

    ``next_state`` tells the pipeline where the lead goes next.
    ``updates`` is a dict applied to the Lead row.
    ``artifacts`` carries any structured side-effects (evidence rows,
    approval-queue items, drafted messages, etc.).
    """
    status: AgentStatus
    next_state: Optional[LeadState] = None
    updates: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """
    Abstract base for every sales-pipeline agent.

    Subclasses must set ``name`` and ``handles_states`` and implement
    ``execute``.  The pipeline calls ``can_handle`` before dispatching;
    override it for richer precondition checks.
    """

    name: str = "unnamed_agent"
    handles_states: Set[LeadState] = set()

    async def can_handle(self, ctx: AgentContext) -> bool:
        """Return True if this agent should run for the given context."""
        return ctx.lead_state in self.handles_states

    @abstractmethod
    async def execute(self, ctx: AgentContext) -> AgentResult:
        """
        Do the agent's work and return an AgentResult.

        Implementations should:
          - NOT commit to the DB (the pipeline handles transactions).
          - Return ``AgentStatus.FAILED`` with ``error`` on exceptions
            rather than raising (the pipeline logs + retries).
        """
        ...

    async def run(self, ctx: AgentContext) -> AgentResult:
        """
        Wrapper that adds timing, logging, and guardrails.
        Agents should override ``execute``, not ``run``.
        """
        start = time.perf_counter()
        logger.info(f"[{self.name}] Starting for lead {ctx.lead_id} (state={ctx.lead_state.value})")

        try:
            result = await self.execute(ctx)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"[{self.name}] Unhandled error for lead {ctx.lead_id}: {exc}", exc_info=True)
            result = AgentResult(
                status=AgentStatus.FAILED,
                error=str(exc),
                duration_ms=elapsed,
            )

        result.duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[{self.name}] Finished lead {ctx.lead_id} -> "
            f"status={result.status.value}, next_state={result.next_state}, "
            f"duration={result.duration_ms:.0f}ms"
        )
        return result
