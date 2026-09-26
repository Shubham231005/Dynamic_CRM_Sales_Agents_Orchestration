"""
Memory Architecture
====================
Three-tier memory system inspired by cognitive science:

  1. WorkingMemory   — ephemeral per-operation scratchpad (in-memory only)
  2. EpisodicMemory  — interaction history per lead       (persistent, DB-backed)
  3. SemanticMemory  — domain knowledge & learned facts   (persistent, evolving)

References:
  - Atkinson & Shiffrin (1968) — multi-store model
  - Tulving (1972) — episodic vs. semantic distinction
  - Park et al. (2023) — memory architecture for generative agents
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, func
from sqlalchemy.orm import Session

from app.database.database import Base

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 1. WORKING MEMORY — ephemeral, per-operation scratchpad
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WorkingMemory:
    """
    Per-operation scratchpad for an agent.

    Lives only in-memory for the duration of one ``execute()`` call.
    Agents use it to track intermediate reasoning: hypotheses formed,
    queries tried, partial results accumulated.

    Not persisted — discarded after the operation completes.
    """

    lead_id: int
    agent_name: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Reasoning trace
    observations: List[str] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)

    # Intermediate data
    search_queries_tried: List[str] = field(default_factory=list)
    urls_visited: List[str] = field(default_factory=list)
    partial_results: Dict[str, Any] = field(default_factory=dict)

    # Token budget
    tokens_used: int = 0
    token_budget: int = 4096

    def observe(self, observation: str) -> None:
        self.observations.append(observation)

    def hypothesise(self, hypothesis: str) -> None:
        self.hypotheses.append(hypothesis)

    def decide(self, decision: str) -> None:
        self.decisions.append(decision)

    def has_budget(self, needed: int = 0) -> bool:
        return (self.tokens_used + needed) <= self.token_budget

    def summary(self) -> str:
        """Compact summary for logging / audit trail."""
        return (
            f"[{self.agent_name}] lead={self.lead_id} | "
            f"obs={len(self.observations)} hyp={len(self.hypotheses)} "
            f"dec={len(self.decisions)} | tokens={self.tokens_used}/{self.token_budget}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 2. EPISODIC MEMORY — persistent interaction history per lead
# ═══════════════════════════════════════════════════════════════════════════

class EpisodicMemory(Base):
    """
    Records every interaction and outcome for a specific lead.

    Enables agents to learn from past behaviour:
      - "Last email to this lead was ROI-focused and got no response."
      - "This lead has been contacted 3 times — time to switch channels."
      - "Response tone shifted from neutral to positive after case study."
    """
    __tablename__ = "episodic_memory"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True, nullable=False)
    agent_name = Column(String, nullable=False, index=True)

    event_type = Column(String, nullable=False, index=True)
    # Event types:
    #   INTELLIGENCE_GATHERED, PROFILE_BUILT, RELATIONSHIPS_MAPPED,
    #   SCORE_COMPUTED, STRATEGY_DECIDED, OUTREACH_SENT,
    #   RESPONSE_RECEIVED, FOLLOW_UP_SCHEDULED, MEETING_BOOKED,
    #   DEAL_WON, DEAL_LOST, OBJECTION_RAISED

    channel = Column(String, nullable=True)       # email | linkedin | whatsapp | call | ...
    content_summary = Column(Text, nullable=True)  # LLM-generated summary
    raw_content = Column(Text, nullable=True)      # full text (email body, call transcript)

    outcome = Column(String, nullable=True)        # POSITIVE | NEGATIVE | NEUTRAL | NO_RESPONSE
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0

    key_signals = Column(JSON, nullable=True)
    # e.g. ["mentioned_budget", "asked_for_demo", "raised_compliance_concern"]

    lessons_learned = Column(Text, nullable=True)
    # LLM-generated: "This buyer responds better to data-driven pitches"

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EpisodicMemoryStore:
    """Convenience methods for reading/writing episodic memories."""

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        lead_id: int,
        agent_name: str,
        event_type: str,
        *,
        channel: Optional[str] = None,
        content_summary: Optional[str] = None,
        raw_content: Optional[str] = None,
        outcome: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        key_signals: Optional[List[str]] = None,
        lessons_learned: Optional[str] = None,
    ) -> EpisodicMemory:
        """Record a new episodic memory for a lead."""
        mem = EpisodicMemory(
            lead_id=lead_id,
            agent_name=agent_name,
            event_type=event_type,
            channel=channel,
            content_summary=content_summary,
            raw_content=raw_content,
            outcome=outcome,
            sentiment_score=sentiment_score,
            key_signals=key_signals,
            lessons_learned=lessons_learned,
        )
        self.db.add(mem)
        self.db.flush()  # get the id without committing (pipeline commits)
        return mem

    def recall(
        self,
        lead_id: int,
        event_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[EpisodicMemory]:
        """Recall episodic memories for a lead, newest first."""
        q = self.db.query(EpisodicMemory).filter(EpisodicMemory.lead_id == lead_id)
        if event_type:
            q = q.filter(EpisodicMemory.event_type == event_type)
        return q.order_by(EpisodicMemory.created_at.desc()).limit(limit).all()

    def recall_recent(
        self,
        lead_id: int,
        hours: int = 72,
        event_type: Optional[str] = None,
    ) -> List[EpisodicMemory]:
        """Recall memories from the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = self.db.query(EpisodicMemory).filter(
            EpisodicMemory.lead_id == lead_id,
            EpisodicMemory.created_at >= cutoff,
        )
        if event_type:
            q = q.filter(EpisodicMemory.event_type == event_type)
        return q.order_by(EpisodicMemory.created_at.desc()).all()

    def count_interactions(self, lead_id: int, channel: Optional[str] = None) -> int:
        """How many times have we contacted this lead?"""
        q = self.db.query(EpisodicMemory).filter(
            EpisodicMemory.lead_id == lead_id,
            EpisodicMemory.event_type == "OUTREACH_SENT",
        )
        if channel:
            q = q.filter(EpisodicMemory.channel == channel)
        return q.count()

    def last_outcome(self, lead_id: int) -> Optional[str]:
        """What was the outcome of the most recent interaction?"""
        mem = (
            self.db.query(EpisodicMemory)
            .filter(
                EpisodicMemory.lead_id == lead_id,
                EpisodicMemory.outcome.isnot(None),
            )
            .order_by(EpisodicMemory.created_at.desc(), EpisodicMemory.id.desc())
            .first()
        )
        return mem.outcome if mem else None


# ═══════════════════════════════════════════════════════════════════════════
# 3. SEMANTIC MEMORY — domain knowledge & learned facts
# ═══════════════════════════════════════════════════════════════════════════

class SemanticMemory(Base):
    """
    Domain knowledge the system has learned or been taught.

    Categories:
      INDUSTRY_KNOWLEDGE  — facts about an industry (regulations, typical cycles)
      BUYER_PERSONA       — role-based buyer profiles
      OBJECTION_PATTERN   — common objections + counter-strategies
      CHANNEL_PERFORMANCE — learned response rates per channel per industry
      MESSAGING_TEMPLATE  — proven messaging structures
      COMPLIANCE_RULE     — regulatory constraints per industry

    Knowledge evolves:
      - IKPs seed initial knowledge (source = "ikp_default")
      - The system updates statistics from outcomes (source = "learned_from_data")
      - Users can add knowledge manually (source = "user_provided")
      - Confidence decays over time for learned knowledge (refresh needed)
    """
    __tablename__ = "semantic_memory"

    id = Column(Integer, primary_key=True, index=True)

    category = Column(String, nullable=False, index=True)
    industry = Column(String, nullable=False, index=True)  # "*" = all industries

    knowledge_key = Column(String, nullable=False, index=True)  # unique within category+industry
    knowledge_value = Column(JSON, nullable=False)

    source = Column(String, default="ikp_default")   # ikp_default | learned_from_data | user_provided
    confidence = Column(Float, default=1.0)           # 0.0–1.0, decays for learned knowledge

    times_applied = Column(Integer, default=0)
    times_successful = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)


class SemanticMemoryStore:
    """Convenience methods for reading/writing semantic memories."""

    def __init__(self, db: Session):
        self.db = db

    def recall(
        self,
        category: str,
        industry: str,
        key: Optional[str] = None,
    ) -> List[SemanticMemory]:
        """
        Recall semantic knowledge.
        Searches for industry-specific knowledge first, then falls back to
        universal ("*") knowledge.
        """
        q = self.db.query(SemanticMemory).filter(
            SemanticMemory.category == category,
            SemanticMemory.industry.in_([industry, "*"]),
        )
        if key:
            q = q.filter(SemanticMemory.knowledge_key == key)
        return q.order_by(SemanticMemory.confidence.desc()).all()

    def store(
        self,
        category: str,
        industry: str,
        key: str,
        value: Dict[str, Any],
        source: str = "ikp_default",
        confidence: float = 1.0,
    ) -> SemanticMemory:
        """Store or update a semantic memory entry."""
        existing = self.db.query(SemanticMemory).filter(
            SemanticMemory.category == category,
            SemanticMemory.industry == industry,
            SemanticMemory.knowledge_key == key,
        ).first()

        if existing:
            existing.knowledge_value = value
            existing.source = source
            existing.confidence = confidence
            existing.version = (existing.version or 0) + 1
            self.db.flush()
            return existing

        mem = SemanticMemory(
            category=category,
            industry=industry,
            knowledge_key=key,
            knowledge_value=value,
            source=source,
            confidence=confidence,
        )
        self.db.add(mem)
        self.db.flush()
        return mem

    def record_outcome(self, memory_id: int, was_successful: bool) -> None:
        """Update the success statistics for a knowledge entry."""
        mem = self.db.query(SemanticMemory).filter(SemanticMemory.id == memory_id).first()
        if not mem:
            return
        mem.times_applied = (mem.times_applied or 0) + 1
        if was_successful:
            mem.times_successful = (mem.times_successful or 0) + 1
        mem.success_rate = mem.times_successful / max(mem.times_applied, 1)
        self.db.flush()

    def get_channel_performance(self, industry: str) -> Dict[str, float]:
        """Get learned channel response rates for an industry."""
        entries = self.recall("CHANNEL_PERFORMANCE", industry)
        result = {}
        for entry in entries:
            val = entry.knowledge_value or {}
            for channel in ["email", "linkedin", "whatsapp", "call", "telegram", "instagram"]:
                rate_key = f"{channel}_response_rate"
                if rate_key in val:
                    result[channel] = val[rate_key]
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 4. AGENT EVENT LOG — full audit trail
# ═══════════════════════════════════════════════════════════════════════════

class AgentEventLog(Base):
    """
    Records every agent execution for reproducibility and debugging.
    This is the system's complete audit trail.
    """
    __tablename__ = "agent_event_log"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, index=True, nullable=True)
    agent_name = Column(String, nullable=False, index=True)

    event_type = Column(String, nullable=False, index=True)
    # STARTED | COMPLETED | FAILED | SKIPPED | APPROVAL_REQUESTED | ROUTED

    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)

    state_before = Column(String, nullable=True)
    state_after = Column(String, nullable=True)

    duration_ms = Column(Float, nullable=True)
    llm_calls_made = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventLogger:
    """Convenience methods for writing audit log entries."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        agent_name: str,
        event_type: str,
        *,
        lead_id: Optional[int] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        state_before: Optional[str] = None,
        state_after: Optional[str] = None,
        duration_ms: Optional[float] = None,
        llm_calls_made: int = 0,
        tokens_used: int = 0,
    ) -> AgentEventLog:
        entry = AgentEventLog(
            lead_id=lead_id,
            agent_name=agent_name,
            event_type=event_type,
            input_summary=input_summary,
            output_summary=output_summary,
            state_before=state_before,
            state_after=state_after,
            duration_ms=duration_ms,
            llm_calls_made=llm_calls_made,
            tokens_used=tokens_used,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_lead_history(self, lead_id: int, limit: int = 50) -> List[AgentEventLog]:
        return (
            self.db.query(AgentEventLog)
            .filter(AgentEventLog.lead_id == lead_id)
            .order_by(AgentEventLog.created_at.desc())
            .limit(limit)
            .all()
        )


# ═══════════════════════════════════════════════════════════════════════════
# 5. BLACKBOARD — inter-agent communication
# ═══════════════════════════════════════════════════════════════════════════

class BlackboardMessage(Base):
    """
    Shared communication space for inter-agent coordination.

    Message types:
      FINDING  — "Intelligence Agent found 3 LinkedIn profiles"
      REQUEST  — "Strategy Agent requests tech stack info from Profiler"
      CONFLICT — "Website says 50 employees, LinkedIn says 200"
      DECISION — "Orchestrator resolved: use LinkedIn count"
    """
    __tablename__ = "blackboard_messages"

    id = Column(Integer, primary_key=True, index=True)
    source_agent = Column(String, nullable=False, index=True)
    target_agent = Column(String, nullable=True)  # None = broadcast

    message_type = Column(String, nullable=False, index=True)
    # FINDING | REQUEST | CONFLICT | DECISION

    lead_id = Column(Integer, index=True, nullable=True)
    payload = Column(JSON, nullable=True)
    priority = Column(String, default="MEDIUM")  # LOW | MEDIUM | HIGH | CRITICAL

    consumed_by = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Blackboard:
    """Read/write interface for inter-agent blackboard messages."""

    def __init__(self, db: Session):
        self.db = db

    def post(
        self,
        source_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        *,
        lead_id: Optional[int] = None,
        target_agent: Optional[str] = None,
        priority: str = "MEDIUM",
    ) -> BlackboardMessage:
        msg = BlackboardMessage(
            source_agent=source_agent,
            target_agent=target_agent,
            message_type=message_type,
            lead_id=lead_id,
            payload=payload,
            priority=priority,
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def read_for_agent(
        self,
        agent_name: str,
        lead_id: Optional[int] = None,
        message_type: Optional[str] = None,
        unconsumed_only: bool = True,
    ) -> List[BlackboardMessage]:
        """Read messages targeted at (or broadcast to) a specific agent."""
        q = self.db.query(BlackboardMessage).filter(
            (BlackboardMessage.target_agent == agent_name)
            | (BlackboardMessage.target_agent.is_(None))
        )
        if lead_id:
            q = q.filter(BlackboardMessage.lead_id == lead_id)
        if message_type:
            q = q.filter(BlackboardMessage.message_type == message_type)
        # Note: unconsumed filtering would need JSON contains check;
        # for SQLite we do it in Python.
        msgs = q.order_by(BlackboardMessage.created_at.desc()).all()
        if unconsumed_only:
            msgs = [m for m in msgs if agent_name not in (m.consumed_by or [])]
        return msgs

    def mark_consumed(self, message_id: int, agent_name: str) -> None:
        msg = self.db.query(BlackboardMessage).filter(BlackboardMessage.id == message_id).first()
        if msg:
            consumed = list(msg.consumed_by or [])
            if agent_name not in consumed:
                consumed.append(agent_name)
                msg.consumed_by = consumed
                self.db.flush()
