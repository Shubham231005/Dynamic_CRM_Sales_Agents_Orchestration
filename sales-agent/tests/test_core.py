"""
Tests for the MASAA core architecture:
  - State machine (including new cognitive states)
  - Base agent contract
  - LLM gateway
  - Pipeline orchestrator
  - Memory layer (episodic, semantic, working, blackboard)
  - IKP registry
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.database import models
from app.services.lead_service import LeadService
from app.schemas.lead import LeadCreate

from app.core.state_machine import LeadState, LeadStateMachine
from app.core.base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus
from app.core.llm_gateway import LLMGateway
from app.core.pipeline import SalesPipeline
from app.core.memory import (
    WorkingMemory,
    EpisodicMemoryStore,
    SemanticMemoryStore,
    EventLogger,
    Blackboard,
)
from app.core.ikp import IKPRegistry


# ── Fixtures ───────────────────────────────────────────────────────────────

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ── Stub agents for testing ───────────────────────────────────────────────

class StubIntelligenceAgent(BaseAgent):
    name = "stub_intelligence"
    handles_states = {LeadState.NEW}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.INTELLIGENCE_GATHERED,
            message="Multi-source intelligence collected.",
            artifacts={"evidence": [
                {
                    "field_name": "official_website",
                    "field_value": "https://example.com",
                    "source_type": "web_search",
                    "confidence": 0.85,
                }
            ]}
        )


class StubProfilerAgent(BaseAgent):
    name = "stub_profiler"
    handles_states = {LeadState.INTELLIGENCE_GATHERED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.PROFILED,
            message="Company profile built.",
        )


class StubRelationshipMapper(BaseAgent):
    name = "stub_relationship_mapper"
    handles_states = {LeadState.PROFILED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.RELATIONSHIPS_MAPPED,
            message="Stakeholders identified.",
        )


class StubScoringAgent(BaseAgent):
    name = "stub_scoring"
    handles_states = {LeadState.RELATIONSHIPS_MAPPED, LeadState.DISCOVERED, LeadState.RESEARCHED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.SCORED,
            updates={"enrichment_status": "COMPLETED"},
            message="Lead scored at 0.78.",
        )


class StubStrategyAgent(BaseAgent):
    name = "stub_strategy"
    handles_states = {LeadState.SCORED}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(
            status=AgentStatus.SUCCESS,
            next_state=LeadState.APPROVAL_PENDING,
            artifacts={"approvals": [
                {"action_type": "SEND_EMAIL", "proposed_content": "Hello, let's connect."}
            ]},
        )


class FailingAgent(BaseAgent):
    name = "failing_agent"
    handles_states = {LeadState.NEW}

    async def execute(self, ctx: AgentContext) -> AgentResult:
        raise RuntimeError("Something broke!")


# ══════════════════════════════════════════════════════════════════════════
# State Machine Tests
# ══════════════════════════════════════════════════════════════════════════

class TestLeadStateMachine:
    def test_new_to_intelligence_gathered(self):
        sm = LeadStateMachine()
        assert sm.can_transition(LeadState.NEW, LeadState.INTELLIGENCE_GATHERED)

    def test_full_cognitive_path(self):
        """NEW → INTELLIGENCE_GATHERED → PROFILED → RELATIONSHIPS_MAPPED → SCORED"""
        sm = LeadStateMachine()
        path = [
            (LeadState.NEW, LeadState.INTELLIGENCE_GATHERED),
            (LeadState.INTELLIGENCE_GATHERED, LeadState.PROFILED),
            (LeadState.PROFILED, LeadState.RELATIONSHIPS_MAPPED),
            (LeadState.RELATIONSHIPS_MAPPED, LeadState.SCORED),
            (LeadState.SCORED, LeadState.STRATEGY_SET),
            (LeadState.STRATEGY_SET, LeadState.APPROVAL_PENDING),
            (LeadState.APPROVAL_PENDING, LeadState.APPROVED),
            (LeadState.APPROVED, LeadState.OUTREACH_SENT),
            (LeadState.OUTREACH_SENT, LeadState.FOLLOW_UP),
            (LeadState.FOLLOW_UP, LeadState.WON),
        ]
        for current, target in path:
            assert sm.can_transition(current, target), f"Failed: {current} → {target}"

    def test_invalid_transition_raises(self):
        sm = LeadStateMachine()
        assert not sm.can_transition(LeadState.NEW, LeadState.OUTREACH_SENT)
        with pytest.raises(ValueError, match="Illegal state transition"):
            sm.transition(LeadState.NEW, LeadState.OUTREACH_SENT)

    def test_terminal_states(self):
        terminals = LeadStateMachine.terminal_states()
        assert LeadState.WON in terminals
        assert LeadState.LOST in terminals
        assert LeadState.DORMANT in terminals

    def test_needs_human(self):
        assert LeadStateMachine.needs_human(LeadState.APPROVAL_PENDING)
        assert not LeadStateMachine.needs_human(LeadState.SCORED)

    def test_failed_can_retry_to_new(self):
        sm = LeadStateMachine()
        assert sm.can_transition(LeadState.FAILED, LeadState.NEW)

    def test_paused_can_resume_anywhere(self):
        sm = LeadStateMachine()
        for state in LeadState:
            assert sm.can_transition(LeadState.PAUSED, state)

    def test_skip_states_allowed(self):
        """Pre-enriched imports can skip directly to SCORED."""
        sm = LeadStateMachine()
        assert sm.can_transition(LeadState.NEW, LeadState.SCORED)

    def test_legacy_discovered_state(self):
        """Legacy DISCOVERED state should transition to new states."""
        sm = LeadStateMachine()
        assert sm.can_transition(LeadState.DISCOVERED, LeadState.PROFILED)
        assert sm.can_transition(LeadState.DISCOVERED, LeadState.SCORED)


# ══════════════════════════════════════════════════════════════════════════
# Base Agent Tests
# ══════════════════════════════════════════════════════════════════════════

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_can_handle(self):
        agent = StubIntelligenceAgent()
        ctx_new = AgentContext(lead_id=1, lead_state=LeadState.NEW, lead_data={})
        ctx_scored = AgentContext(lead_id=1, lead_state=LeadState.SCORED, lead_data={})
        assert await agent.can_handle(ctx_new) is True
        assert await agent.can_handle(ctx_scored) is False

    @pytest.mark.asyncio
    async def test_run_wraps_errors(self):
        agent = FailingAgent()
        ctx = AgentContext(lead_id=1, lead_state=LeadState.NEW, lead_data={})
        result = await agent.run(ctx)
        assert result.status == AgentStatus.FAILED
        assert "Something broke" in result.error
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_run_records_duration(self):
        agent = StubIntelligenceAgent()
        ctx = AgentContext(lead_id=1, lead_state=LeadState.NEW, lead_data={})
        result = await agent.run(ctx)
        assert result.status == AgentStatus.SUCCESS
        assert result.duration_ms >= 0


# ══════════════════════════════════════════════════════════════════════════
# LLM Gateway Tests
# ══════════════════════════════════════════════════════════════════════════

class TestLLMGateway:
    @pytest.mark.asyncio
    async def test_mock_fallback(self):
        gateway = LLMGateway.default()
        result = await gateway.generate_json("strategic fit for healthcare")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_text(self):
        gateway = LLMGateway.default()
        result = await gateway.generate_text("Write me an email pitch.")
        assert isinstance(result, str)
        assert len(result) > 0


# ══════════════════════════════════════════════════════════════════════════
# Pipeline Tests
# ══════════════════════════════════════════════════════════════════════════

class TestSalesPipeline:
    @pytest.mark.asyncio
    async def test_advance_single_step(self, db_session):
        service = LeadService(db_session)
        lead = service.create_lead(LeadCreate(
            company_name="TestCo", industry="SaaS", location="Bangalore"
        ))
        assert lead.status == "NEW"

        pipeline = SalesPipeline(db_session)
        pipeline.register(StubIntelligenceAgent())

        result = await pipeline.advance(lead.id)
        assert result.status == AgentStatus.SUCCESS
        assert result.next_state == LeadState.INTELLIGENCE_GATHERED

        db_session.refresh(lead)
        assert lead.status == "INTELLIGENCE_GATHERED"

    @pytest.mark.asyncio
    async def test_run_full_cognitive_path(self, db_session):
        """Run through the full 5-agent cognitive pipeline until approval gate."""
        service = LeadService(db_session)
        lead = service.create_lead(LeadCreate(
            company_name="CognitiveCo", industry="Finance", location="Mumbai"
        ))

        pipeline = SalesPipeline(db_session)
        pipeline.register(StubIntelligenceAgent())
        pipeline.register(StubProfilerAgent())
        pipeline.register(StubRelationshipMapper())
        pipeline.register(StubScoringAgent())
        pipeline.register(StubStrategyAgent())

        results = await pipeline.run_full(lead.id)

        # 5 agents run + 1 final SKIPPED (no agent handles APPROVAL_PENDING)
        assert len(results) >= 5
        assert results[0].next_state == LeadState.INTELLIGENCE_GATHERED
        assert results[1].next_state == LeadState.PROFILED
        assert results[2].next_state == LeadState.RELATIONSHIPS_MAPPED
        assert results[3].next_state == LeadState.SCORED
        assert results[4].next_state == LeadState.APPROVAL_PENDING

        db_session.refresh(lead)
        assert lead.status == "APPROVAL_PENDING"

    @pytest.mark.asyncio
    async def test_advance_nonexistent_lead(self, db_session):
        pipeline = SalesPipeline(db_session)
        pipeline.register(StubIntelligenceAgent())
        result = await pipeline.advance(99999)
        assert result.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_no_agent_matches(self, db_session):
        service = LeadService(db_session)
        lead = service.create_lead(LeadCreate(
            company_name="SkipCo", industry="Mining", location="Delhi"
        ))
        lead.status = "WON"
        db_session.commit()

        pipeline = SalesPipeline(db_session)
        pipeline.register(StubIntelligenceAgent())
        result = await pipeline.advance(lead.id)
        assert result.status == AgentStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_failing_agent_preserves_state(self, db_session):
        service = LeadService(db_session)
        lead = service.create_lead(LeadCreate(
            company_name="CrashCo", industry="Fintech", location="Pune"
        ))

        pipeline = SalesPipeline(db_session)
        pipeline.register(FailingAgent())

        result = await pipeline.advance(lead.id)
        assert result.status == AgentStatus.FAILED

        db_session.refresh(lead)
        assert lead.status == "NEW"  # unchanged


# ══════════════════════════════════════════════════════════════════════════
# Memory Tests
# ══════════════════════════════════════════════════════════════════════════

class TestWorkingMemory:
    def test_scratchpad_basics(self):
        wm = WorkingMemory(lead_id=1, agent_name="test_agent")
        wm.observe("Found 3 LinkedIn profiles")
        wm.hypothesise("Company is in growth phase")
        wm.decide("Prioritise CTO over VP")

        assert len(wm.observations) == 1
        assert len(wm.hypotheses) == 1
        assert len(wm.decisions) == 1
        assert "test_agent" in wm.summary()

    def test_token_budget(self):
        wm = WorkingMemory(lead_id=1, agent_name="test", token_budget=100)
        assert wm.has_budget(50)
        wm.tokens_used = 80
        assert wm.has_budget(50) is False
        assert wm.has_budget(20) is True


class TestEpisodicMemory:
    def test_record_and_recall(self, db_session):
        store = EpisodicMemoryStore(db_session)

        store.record(
            lead_id=1,
            agent_name="communication_agent",
            event_type="OUTREACH_SENT",
            channel="email",
            content_summary="Sent ROI-focused email",
            outcome="NO_RESPONSE",
        )
        db_session.commit()

        memories = store.recall(lead_id=1)
        assert len(memories) == 1
        assert memories[0].channel == "email"
        assert memories[0].outcome == "NO_RESPONSE"

    def test_count_interactions(self, db_session):
        store = EpisodicMemoryStore(db_session)
        for i in range(3):
            store.record(lead_id=42, agent_name="comm", event_type="OUTREACH_SENT", channel="email")
        store.record(lead_id=42, agent_name="comm", event_type="OUTREACH_SENT", channel="linkedin")
        db_session.commit()

        assert store.count_interactions(42) == 4
        assert store.count_interactions(42, channel="email") == 3

    def test_last_outcome(self, db_session):
        store = EpisodicMemoryStore(db_session)
        store.record(lead_id=10, agent_name="sent", event_type="OUTREACH_SENT", outcome="NO_RESPONSE")
        store.record(lead_id=10, agent_name="sent", event_type="RESPONSE_RECEIVED", outcome="POSITIVE")
        db_session.commit()

        assert store.last_outcome(10) == "POSITIVE"


class TestSemanticMemory:
    def test_store_and_recall(self, db_session):
        store = SemanticMemoryStore(db_session)
        store.store(
            category="BUYER_PERSONA",
            industry="finance",
            key="cfo_persona",
            value={"role": "CFO", "priorities": ["cost_reduction"]},
        )
        db_session.commit()

        results = store.recall("BUYER_PERSONA", "finance")
        assert len(results) == 1
        assert results[0].knowledge_value["role"] == "CFO"

    def test_universal_fallback(self, db_session):
        store = SemanticMemoryStore(db_session)
        store.store(
            category="COMPLIANCE_RULE",
            industry="*",
            key="gdpr",
            value={"rule": "Must allow data deletion"},
        )
        db_session.commit()

        # Should find the * industry entry when searching for any industry
        results = store.recall("COMPLIANCE_RULE", "fintech")
        assert len(results) == 1

    def test_outcome_tracking(self, db_session):
        store = SemanticMemoryStore(db_session)
        mem = store.store("CHANNEL_PERFORMANCE", "it_saas", "email_rate", {"rate": 0.12})
        db_session.commit()

        store.record_outcome(mem.id, was_successful=True)
        store.record_outcome(mem.id, was_successful=True)
        store.record_outcome(mem.id, was_successful=False)
        db_session.commit()

        db_session.refresh(mem)
        assert mem.times_applied == 3
        assert mem.times_successful == 2
        assert abs(mem.success_rate - 0.6667) < 0.01


class TestBlackboard:
    def test_post_and_read(self, db_session):
        bb = Blackboard(db_session)
        bb.post(
            source_agent="intelligence_agent",
            message_type="FINDING",
            payload={"found": "3 LinkedIn profiles"},
            lead_id=1,
        )
        db_session.commit()

        msgs = bb.read_for_agent("profiler_agent", lead_id=1)
        assert len(msgs) == 1
        assert msgs[0].payload["found"] == "3 LinkedIn profiles"

    def test_mark_consumed(self, db_session):
        bb = Blackboard(db_session)
        msg = bb.post(
            source_agent="intel",
            message_type="FINDING",
            payload={"data": "test"},
            lead_id=2,
        )
        db_session.commit()

        bb.mark_consumed(msg.id, "profiler_agent")
        db_session.commit()

        # Should be filtered out now
        unread = bb.read_for_agent("profiler_agent", lead_id=2, unconsumed_only=True)
        assert len(unread) == 0


class TestEventLogger:
    def test_log_and_history(self, db_session):
        logger = EventLogger(db_session)
        logger.log(
            agent_name="intelligence_agent",
            event_type="COMPLETED",
            lead_id=5,
            state_before="NEW",
            state_after="INTELLIGENCE_GATHERED",
            duration_ms=1234.5,
        )
        db_session.commit()

        history = logger.get_lead_history(5)
        assert len(history) == 1
        assert history[0].agent_name == "intelligence_agent"
        assert history[0].duration_ms == 1234.5


# ══════════════════════════════════════════════════════════════════════════
# IKP Registry Tests
# ══════════════════════════════════════════════════════════════════════════

class TestIKPRegistry:
    def test_seed_and_load(self, db_session):
        registry = IKPRegistry(db_session)
        registry.seed_defaults()

        ikp = registry.load("finance_banking")
        assert ikp["industry_context"]["description"].startswith("Banking")
        assert "email" in ikp["outreach_rules"]["channels_allowed"]

    def test_load_for_industry_fuzzy(self, db_session):
        registry = IKPRegistry(db_session)
        registry.seed_defaults()

        # "fintech" should match finance_banking
        ikp = registry.load_for_industry("fintech")
        assert "Banking" in ikp["industry_context"]["description"]

        # "SaaS" should match it_saas
        ikp = registry.load_for_industry("SaaS")
        assert "Software" in ikp["industry_context"]["description"]

    def test_fallback_to_generic(self, db_session):
        registry = IKPRegistry(db_session)
        registry.seed_defaults()

        # Unknown industry → generic_b2b
        ikp = registry.load_for_industry("underwater basket weaving")
        assert ikp["industry_context"]["description"].startswith("Generic")

    def test_list_all(self, db_session):
        registry = IKPRegistry(db_session)
        registry.seed_defaults()

        all_ikps = registry.list_all()
        assert len(all_ikps) == 5  # 4 industries + 1 generic

    def test_upsert_updates_existing(self, db_session):
        registry = IKPRegistry(db_session)
        registry.seed_defaults()

        # Update finance IKP
        registry.upsert("finance_banking", "Finance v2", {"updated": True}, version="2.0")
        db_session.commit()

        ikp = registry.load("finance_banking")
        assert ikp["updated"] is True
